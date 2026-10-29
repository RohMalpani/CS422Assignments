# Custom algorithm: Adaptive Delay/Loss AIMD

This is the design for Assignment 2 Question 3(b) and the algorithm implemented
by `assignment3/kernel/tcp_cs422.c`. It controls the congestion window
(`cwnd`), measured in TCP segments. TCP still performs retransmission, loss
detection, and recovery. The algorithm uses ACK-derived delivered packets per
second as its throughput signal; the Python client separately reports
acknowledged goodput in bits per second.

## Motivation from the current measurements

The design was drafted while the live baseline experiment was still running.
The completed run has ten selected destinations and 85 successful selected-path
tests. Comparisons use 28 destination/repetition triples where all three
algorithms succeeded: Reno has the highest mean goodput on five destinations,
BBR on four, and CUBIC on one. Floreal favors Reno (62.41 Mbps versus BBR 57.35
and CUBIC 46.97); Portmore favors BBR (183.02 Mbps versus CUBIC 101.98 and Reno
70.05), at higher RTT and more retransmissions. These measurements motivate
Reno-like growth on stable paths, gentler response to loss without rising delay,
and a delay response when extra sending fails to improve delivery. They do not
prove that this design outperforms a baseline. Thresholds are hypotheses, not
fitted constants. See the report and `results/part3-live/part3_matched_runs.csv`
for the complete-run analysis; these figures replace the preliminary counts.

## State, units, and initial values

This pseudocode follows `assignment3/kernel/tcp_cs422.c`, including its
measurement-validity checks and TCP callback ordering.

- `c` and `s` are the congestion window and slow-start threshold in segments;
  retain Linux's initial values.
- `r` is Linux's smoothed RTT (`srtt_us >> 3`) in microseconds.
- `r0` is replaced on the first positive RTT sample, a lower sample, or after
  ten seconds since its last replacement. It is not an exact sliding-window minimum.
- `q = max(0, (r-r0)/r0)` when RTT measurements are available.
- `b` is an integer EWMA of delivered packets per second; `b_old` is its
  previous value. `dt` below is measured in seconds.
- Private counters, rates, flags and saved loss window start at zero, except
  delay reduction starts armed. Round time and delivered counters start at
  their current values. Valid-round, high-delay and plateau counters saturate at 255.
- Invalid rounds clear previous-rate evidence, growth flags and persistence
  counters but retain the EWMA. The cwnd-limited gate is only a proxy for
  filtering application-limited samples.

## Pseudocode

```text
On a positive RTT sample x:
  if r0 unknown OR x < r0 OR time since replacement >=10 s:
    r0 = x; record replacement time

On each congestion-avoidance callback:
  new_round = false
  if r >0 AND elapsed >= max(r, 1 ms):
    new_round = true
    d = newly delivered packets; dt = actual elapsed time
    advance delivery/time baselines; decrement cooldown if >0
    if not cwnd-limited OR d ==0 OR r0 unknown:
      b_old =0; clear growth flags
      valid_rounds = high_delay = plateau =0
      retain b
    else:
      rate = floor(d / dt)
      b_old = b
      b = floor((3*b + rate)/4) if b >0, otherwise rate
      increment valid_rounds (cap 255)
      positive = b_old >0 AND 100*b > 103*b_old
      stalled  = b_old >0 AND 100*b <=105*b_old
      under3   = b_old >0 AND 100*b < 103*b_old
      high_delay = consecutive valid rounds with q >=0.20
      plateau = consecutive valid rounds with stalled=true
      if q <0.10: arm delay reduction
  continue with the window update below
```

```text
After the round update:
  if not cwnd-limited OR TCP is in window reduction: return
  if in slow start:
    if valid_rounds >=3 AND (high_delay >=2 OR plateau >=2):
      s = c
    else:
      use tcp_slow_start; retain any remaining ACK credit
      if no ACK credit remains: return
  if cooldown >0: return

  if new_round AND valid_rounds >=3 AND high_delay >=2
     AND under3 AND delay reduction is armed:
    c = max(2, floor(0.90*c)); s = c
    reset additive-increase ACK counter
    disarm delay reduction; cooldown =1; return

  if r0 unknown OR valid_rounds <3 OR q <0.10:
    divisor =2 if valid_rounds >=3 AND positive, else 1
    tcp_cong_avoid_ai(max(floor(c/divisor),1), ACK credit)
  else if q <0.20:
    tcp_cong_avoid_ai(c, ACK credit)
  else: hold c

When TCP requests a new slow-start threshold:
  mild = no timeout flag AND no timeout-retransmission count
         AND valid_rounds >=3 AND r0 known AND b_old >0
         AND q <0.20 AND 100*b >=90*b_old
  save loss_cwnd = c; cooldown =1
  return max(2, floor(0.85*c)) if mild, else max(2,floor(c/2))
  TCP performs the recovery/window reduction.

On CA_EVENT_LOSS (timeout-style loss):
  set timeout flag; cooldown =1
  if loss_cwnd >0: s = min(s, max(2,floor(loss_cwnd/2)))
On return to TCP_CA_Open: clear timeout flag and loss_cwnd
For spurious-loss window undo: use tcp_reno_undo_cwnd
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
