// SPDX-License-Identifier: GPL-2.0
/* Adaptive Delay/Loss AIMD for Assignment 3, Option 1.
 * Design and pseudocode: assignment2/part3/custom_congestion_control.md.
 */

#include <linux/build_bug.h>
#include <linux/kernel.h>
#include <linux/ktime.h>
#include <linux/math64.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/time64.h>
#include <net/tcp.h>

#define CS422_NAME "cs422_custom"
#define CS422_MIN_CWND 2U
#define CS422_MIN_RTT_WINDOW_NS (10ULL * NSEC_PER_SEC)

struct cs422_state {
	u64 round_start_ns;
	u64 min_rtt_stamp_ns;
	u64 bw_pps;
	u64 previous_bw_pps;
	u32 delivered_at_round;
	u32 min_rtt_us;
	u32 loss_cwnd;
	u8 valid_rounds;
	u8 high_delay_rounds;
	u8 plateau_rounds;
	u8 cooldown_rounds;
	bool delay_reduction_armed;
	bool growth_positive;
	bool growth_stalled;
	bool growth_under_three;
	bool timeout_seen;
};

static bool cs422_delay_at_least(const struct tcp_sock *tp,
				 const struct cs422_state *ca, u32 percent)
{
	u32 srtt_us = tp->srtt_us >> 3;

	return ca->min_rtt_us && srtt_us &&
	       (u64)srtt_us * 100 >= (u64)ca->min_rtt_us * (100 + percent);
}

static void cs422_init(struct sock *sk)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);

	BUILD_BUG_ON(sizeof(*ca) > ICSK_CA_PRIV_SIZE);
	memset(ca, 0, sizeof(*ca));
	ca->round_start_ns = ktime_get_ns();
	ca->delivered_at_round = tp->delivered;
	ca->delay_reduction_armed = true;
}

static void cs422_pkts_acked(struct sock *sk, const struct ack_sample *sample)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	u64 now;

	if (sample->rtt_us <= 0)
		return;

	now = ktime_get_ns();
	if (!ca->min_rtt_us || sample->rtt_us < ca->min_rtt_us ||
	    now - ca->min_rtt_stamp_ns >= CS422_MIN_RTT_WINDOW_NS) {
		ca->min_rtt_us = sample->rtt_us;
		ca->min_rtt_stamp_ns = now;
	}
}

/* Update the ACK-delivery-rate proxy at most once per smoothed RTT. */
static bool cs422_update_round(struct sock *sk, bool cwnd_limited)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u64 now = ktime_get_ns();
	u64 elapsed_ns = now - ca->round_start_ns;
	u32 srtt_us = tp->srtt_us >> 3;
	u32 delivered;
	u64 sample_pps;

	if (!srtt_us || elapsed_ns < max_t(u64, (u64)srtt_us * 1000, 1000000))
		return false;

	delivered = tp->delivered - ca->delivered_at_round;
	ca->delivered_at_round = tp->delivered;
	ca->round_start_ns = now;
	if (ca->cooldown_rounds)
		ca->cooldown_rounds--;

	if (!cwnd_limited || !delivered || !ca->min_rtt_us) {
		/* Stale throughput samples must not justify mild loss recovery. */
		ca->previous_bw_pps = 0;
		ca->growth_positive = false;
		ca->growth_stalled = false;
		ca->growth_under_three = false;
		ca->valid_rounds = 0;
		ca->high_delay_rounds = 0;
		ca->plateau_rounds = 0;
		return true;
	}

	sample_pps = div64_u64((u64)delivered * NSEC_PER_SEC, elapsed_ns);
	ca->previous_bw_pps = ca->bw_pps;
	ca->bw_pps = ca->bw_pps ?
		div64_u64(3 * ca->bw_pps + sample_pps, 4) : sample_pps;
	if (ca->valid_rounds < 255)
		ca->valid_rounds++;

	ca->growth_positive = ca->previous_bw_pps &&
		ca->bw_pps * 100 > ca->previous_bw_pps * 103;
	ca->growth_stalled = ca->previous_bw_pps &&
		ca->bw_pps * 100 <= ca->previous_bw_pps * 105;
	ca->growth_under_three = ca->previous_bw_pps &&
		ca->bw_pps * 100 < ca->previous_bw_pps * 103;

	if (cs422_delay_at_least(tp, ca, 20)) {
		if (ca->high_delay_rounds < 255)
			ca->high_delay_rounds++;
	} else {
		ca->high_delay_rounds = 0;
	}
	if (ca->growth_stalled) {
		if (ca->plateau_rounds < 255)
			ca->plateau_rounds++;
	} else {
		ca->plateau_rounds = 0;
	}
	if (!cs422_delay_at_least(tp, ca, 10))
		ca->delay_reduction_armed = true;

	return true;
}

static void cs422_cong_avoid(struct sock *sk, u32 ack, u32 acked)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u32 cwnd;
	bool limited = tcp_is_cwnd_limited(sk);
	bool new_round;

	new_round = cs422_update_round(sk, limited);
	if (!limited || tcp_in_cwnd_reduction(sk))
		return;

	if (tcp_in_slow_start(tp)) {
		if (ca->valid_rounds >= 3 &&
		    (ca->high_delay_rounds >= 2 || ca->plateau_rounds >= 2)) {
			tp->snd_ssthresh = tcp_snd_cwnd(tp);
		} else {
			acked = tcp_slow_start(tp, acked);
			if (!acked)
				return;
		}
	}

	if (ca->cooldown_rounds)
		return;

	cwnd = tcp_snd_cwnd(tp);
	if (new_round && ca->valid_rounds >= 3 &&
	    ca->high_delay_rounds >= 2 && ca->growth_under_three &&
	    ca->delay_reduction_armed) {
		cwnd = max_t(u32, CS422_MIN_CWND, ((u64)cwnd * 9) / 10);
		tcp_snd_cwnd_set(tp, cwnd);
		tp->snd_ssthresh = cwnd;
		tp->snd_cwnd_cnt = 0;
		ca->delay_reduction_armed = false;
		ca->cooldown_rounds = 1;
		return;
	}

	/* A missing signal uses Reno-like additive increase. */
	if (!ca->min_rtt_us || ca->valid_rounds < 3 ||
	    !cs422_delay_at_least(tp, ca, 10)) {
		u32 divisor = ca->valid_rounds >= 3 && ca->growth_positive ? 2 : 1;

		tcp_cong_avoid_ai(tp, max(cwnd / divisor, 1U), acked);
	} else if (!cs422_delay_at_least(tp, ca, 20)) {
		tcp_cong_avoid_ai(tp, cwnd, acked);
	}
	(void)ack;
}

/* TCP's recovery code handles the window reduction using this threshold. */
static u32 cs422_ssthresh(struct sock *sk)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);
	u32 cwnd = tcp_snd_cwnd(tp);
	bool stable_delivery = ca->previous_bw_pps &&
		ca->bw_pps * 100 >= ca->previous_bw_pps * 90;
	bool mild_loss = !ca->timeout_seen && !inet_csk(sk)->icsk_retransmits &&
		ca->valid_rounds >= 3 && ca->min_rtt_us &&
		!cs422_delay_at_least(tp, ca, 20) && stable_delivery;

	ca->loss_cwnd = cwnd;
	ca->cooldown_rounds = 1;
	if (!mild_loss)
		return max(CS422_MIN_CWND, cwnd / 2);
	return max_t(u32, CS422_MIN_CWND, ((u64)cwnd * 85) / 100);
}

/* CA_EVENT_LOSS marks timeout-style loss, even if it follows ssthresh(). */
static void cs422_cwnd_event(struct sock *sk, enum tcp_ca_event event)
{
	struct cs422_state *ca = inet_csk_ca(sk);
	struct tcp_sock *tp = tcp_sk(sk);

	if (event != CA_EVENT_LOSS)
		return;
	ca->timeout_seen = true;
	ca->cooldown_rounds = 1;
	if (ca->loss_cwnd)
		tp->snd_ssthresh = min(tp->snd_ssthresh,
					max(CS422_MIN_CWND, ca->loss_cwnd / 2));
}

static void cs422_set_state(struct sock *sk, u8 new_state)
{
	struct cs422_state *ca = inet_csk_ca(sk);

	if (new_state == TCP_CA_Open) {
		ca->timeout_seen = false;
		ca->loss_cwnd = 0;
	}
}

static struct tcp_congestion_ops cs422_ops __read_mostly = {
	.init = cs422_init,
	.pkts_acked = cs422_pkts_acked,
	.cwnd_event = cs422_cwnd_event,
	.set_state = cs422_set_state,
	.ssthresh = cs422_ssthresh,
	.cong_avoid = cs422_cong_avoid,
	.undo_cwnd = tcp_reno_undo_cwnd,
	.flags = TCP_CONG_NON_RESTRICTED,
	.owner = THIS_MODULE,
	.name = CS422_NAME,
};

static int __init cs422_register(void)
{
	return tcp_register_congestion_control(&cs422_ops);
}

static void __exit cs422_unregister(void)
{
	tcp_unregister_congestion_control(&cs422_ops);
}

module_init(cs422_register);
module_exit(cs422_unregister);

MODULE_AUTHOR("CS 422 group");
MODULE_DESCRIPTION("Adaptive delay/loss AIMD TCP congestion control");
MODULE_LICENSE("GPL");
