# Custom algorithm: Adaptive Delay/Loss AIMD

This is the design for Assignment 2 Question 3(b) and the algorithm implemented
by `assignment3/kernel/tcp_cs422.c`. It controls the congestion window
(`cwnd`), measured in TCP segments. TCP still performs retransmission, loss
detection, and recovery. The algorithm uses ACK-derived delivered packets per
second as its throughput signal; the Python client separately reports
acknowledged goodput in bits per second.

## Motivation from the current measurements

The first completed repetition of the live Part 3 run had eight destinations
with successful CUBIC, Reno, and BBR tests. Reno had the highest mean goodput
on five destinations, BBR on two, and CUBIC on one. BBR's median destination
goodput was about 126 Mbps versus Reno's 120 Mbps, but BBR often had higher
RTT. On the Jamaica path, BBR delivered much more than Reno despite many
retransmissions. These observations motivate Reno-like growth when a path is
stable, a gentler response to loss without evidence of queueing, and an early
response when RTT rises without additional delivered throughput. They do not
prove that the new algorithm will outperform any baseline. The live run was
still in progress when these choices were made, so parameters are hypotheses
to evaluate, not fitted constants.

## State, units, and initial values

- `cwnd` and `ssthresh`: TCP segments. Keep Linux's initial values.
- `min_rtt_us`: minimum measured RTT over a 10-second window; initially unknown.
- `srtt_us`: Linux's smoothed RTT estimate.
- `bw_pps`: EWMA of delivered packets per second, updated once per RTT using
  `(3 * old + new_sample) / 4`; initially unknown. Skip a rate update when
  the sender is not congestion-window-limited at the round boundary. This is
  only a proxy for fully identifying application-limited samples.
- `previous_bw_pps`: previous EWMA value.
- `high_delay_rounds`, `plateau_rounds`: consecutive RTT counters, initially 0.
- `delay_reduction_armed`: true initially; a delay-only reduction can occur
  once per queueing episode and is rearmed only after the queue clears.
- `cooldown_rounds`: initially 0; prevents immediate regrowth after reduction.

`queue_ratio = (srtt_us - min_rtt_us) / min_rtt_us`, clamped at zero.
`growth = (bw_pps - previous_bw_pps) / previous_bw_pps`. An unknown RTT or
throughput estimate causes Reno-like fallback, not a guessed zero.

## Pseudocode

```text
on each valid RTT sample:
    update min_rtt_us (refresh the minimum after 10 seconds)

on each ACK:
    if approximately one smoothed RTT has elapsed:
        if sender was cwnd-limited:
            delivered_rate = new_delivered_packets / actual_elapsed_seconds
            previous_bw_pps = bw_pps
            bw_pps = EWMA(delivered_rate, weight=1/4)
            update high_delay_rounds and plateau_rounds
        decrement cooldown_rounds if positive

    if sender was not cwnd-limited or TCP is in loss recovery:
        do not grow cwnd

    if still in slow start:
        if at least 3 valid rate rounds AND
           (queue_ratio >= 0.20 for 2 RTTs OR
            throughput growth <= 0.05 for 2 RTTs):
            ssthresh = cwnd                 # leave slow start
        else:
            use normal TCP slow start
            return

    if cooldown_rounds > 0:
        return

    if queue_ratio >= 0.20 for 2 RTTs AND growth < 0.03
       AND delay_reduction_armed:
        cwnd = max(2, floor(0.90 * cwnd))
        ssthresh = cwnd
        delay_reduction_armed = false
        cooldown_rounds = 1
        return

    if queue_ratio < 0.10:
        delay_reduction_armed = true
        if growth > 0.03:
            increase cwnd by about 2 segments per RTT
        else:
            increase cwnd by about 1 segment per RTT
    else if queue_ratio < 0.20:
        increase cwnd by about 1 segment per RTT
    else:
        hold cwnd

when TCP detects loss and requests a new slow-start threshold:
    if this is a timeout OR throughput/RTT estimates are unavailable OR
       queue_ratio >= 0.20 OR throughput fell by more than 10%:
        ssthresh = max(2, floor(0.50 * cwnd))
    else:
        ssthresh = max(2, floor(0.85 * cwnd))
    cooldown_rounds = 1
    let TCP's existing recovery machinery reduce cwnd toward ssthresh

on timeout:
    use the strong loss branch; TCP performs its normal timeout recovery
```

## Expected behavior and limits

The one-segment-per-RTT mode and halving on clear congestion are Reno-like.
Two-segment growth is allowed only while delay is low and delivery is rising;
it could still affect competing flows, so fairness must be measured rather
than assumed. A single delay reduction per queueing episode and one-RTT
cooldown limit oscillation. RTT can rise for reasons other than a queue, and
isolated loss can still be congestion, so the classifications can be wrong.
The public Internet paths and server load also change between runs. We will
compare goodput, RTT, retransmissions, and run-to-run variability against all
three baselines before claiming an improvement.
