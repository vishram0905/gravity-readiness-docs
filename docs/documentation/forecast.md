# Retest estimate

When a session is CAUTION or NO-GO after a landing, the application estimates when every condition is expected to
reach its GO threshold. The estimate tells the crew surgeon when a retest is worthwhile. It never yields GO.

## NASA crew recovery model

Wood et al. (2015) fitted an exponential recovery model to Sensory Organization Test scores of 37 ISS crew members
after landing. Expressed as a ratio to the preflight mean, the typical recovery in condition \(c\) is

\[
r_c(t) = 1 - D_c\, e^{-t/\tau_c}, \qquad D_c = 1 - \frac{\mathrm{EQ}_{c}(0)}{\mathrm{EQ}_{c,\text{pre}}}
\]

where \(t\) is the time after landing in hours, \(\mathrm{EQ}_c(0)\) the fitted landing-day score and \(\tau_c\) the
recovery time constant.

| Condition | NASA analogue | Preflight mean | Landing day (95% limits) | \(\tau\), h (95% limits) | \(D\) |
|---|---|---|---|---|---|
| Firm floor, eyes open | SOT 1 | 94.3 | 90.0 (±2.2) | 116.1 (±86.6) | 0.046 |
| Firm floor, eyes closed | SOT 2 | 89.9 | 82.6 (±3.9) | 99.4 (±74.6) | 0.081 |
| Foam, eyes open | SOT 4 | 87.9 | 68.2 (±8.3) | 44.6 (±25.6) | 0.224 |
| Foam, eyes closed | SOT 5 | 74.9 | 13.2 (±21.1) | 19.4 (±10.7) | 0.824 |

Source: Wood et al. (2015), Table III, p. A49. The mapping of the conditions used here to the NASA conditions is
stated in [Measurement and score](measurement.md).

## Applying the model to an individual

The typical recovery rate is applied to the deficit measured in the crew member. A session at time \(t_m\) with
ratio \(r_m\) fixes the individual deficit

\[
D_i = (1 - r_m)\, e^{t_m/\tau_c}
\]

so that the curve passes through the measurement. The time after the session at which the curve reaches the GO
threshold \(q_c\) is

\[
\Delta t_c = \tau_c \ln\!\left(\frac{1 - r_m}{1 - q_c}\right)
\]

The retest estimate is the largest \(\Delta t_c\) across the four conditions, because every condition must be GO.
The range is obtained by repeating the calculation with the lower and upper 95% limits of \(\tau_c\). It describes
the uncertainty of the published crew model, not a 95% interval for the individual.

If \(q_c \ge 1\) in any condition, the threshold cannot be reached under the model, and no time is given. A
condition that is already at or above its threshold needs no recovery.

## Worked example

Participant A, 6 h after a simulated landing:

| Condition | \(r_m\) | \(q\) | \(\tau\), h | \(\Delta t\), h (range) |
|---|---|---|---|---|
| Firm floor, eyes open | 0.957 | 0.975 | 116.1 | **62.9** (16.0–109.9) |
| Firm floor, eyes closed | 0.924 | 0.950 | 99.4 | 41.2 (10.3–72.2) |
| Foam, eyes open | 0.804 | 0.946 | 44.6 | 57.6 (24.5–90.7) |
| Foam, eyes closed | 0.395 | 0.950 | 19.4 | 48.5 (21.7–75.2) |

Foam with eyes closed causes the NO-GO, but firm floor with eyes open reaches its threshold last. The application
reports a retest in approximately 63 h (≈69 h after landing), with a range of 25–110 h, the largest lower and upper
values across conditions.

## Comparison with typical NASA crew

After a landing, the application also plots each recorded session on the curve \(r_c(t)\) of each condition and
reports the difference from the typical crew member at the latest session, in percentage points of baseline. With
several sessions, the points show whether the crew member recovers faster or slower than the typical crew member.
This comparison is descriptive and does not enter the decision.
