# Decision rules

## Rules within a condition

For each condition, the rules are applied in numerical order, and the first rule that applies sets the result.

| Rule | Condition | Result |
|---|---|---|
| 1 | Any trial invalid, fewer than three trials, or baseline missing or invalid | <span class="status ca">CANNOT ASSESS</span> |
| 2 | Any trial ended in a fall or was stopped | <span class="status nogo">NO-GO</span> |
| 3 | \(r_c < 0.75\) | <span class="status nogo">NO-GO</span> |
| 4 | Session score below the healthy population floor \(P5_c\) | <span class="status caution">CAUTION</span> and referral |
| 5 | \(r_c \ge q_c\) (GO threshold) | <span class="status go">GO</span> |
| 6 | Any other score | <span class="status caution">CAUTION</span> |
| 7 | Overall result and two-session requirement | see below |

**Rule 3: the 75% line.** Jain et al. (2010) regarded a decrement of less than 25% from a crew member's own preflight
score as recovery. A score below 75% of baseline therefore yields NO-GO.

**Rule 4: the population floor.** Jain et al. (2010) regarded a score below the 5th percentile of normative data as
clinically abnormal. The floor \(P5_c\) is the 5th percentile of reference scores in the same condition and age group,
from HBEDB participants without a reported disability, excluding reported labyrinthitis (see
[Validation](validation.md)). A crew member whose score is below the floor is referred to the crew surgeon, even when the score is
close to their own baseline.

## The GO threshold

A single test is noisy. A score just above 75% of baseline may come from a true score below it. The GO threshold
therefore keeps the score at or above 75% of baseline after allowance for test–retest variability, and at or above
the population floor:

\[
q_c = \max\!\left(0.75\,q_{95,c},\; \frac{P5_c}{b_c}\right)
\]

The margin \(q_{95,c}\) is the 95th percentile of the ratio between the median of three retest trials and the
median of three baseline trials when no true change has occurred. It is the larger of two estimates:

- **From data.** Residuals of healthy HBEDB participants, by condition, age group and baseline tertile, resampled
  200,000 times.
- **From the literature.** The minimal detectable change of the head-shake Sensory Organization Test reported by Pang et al.
  (2011), 2.7 (younger) and 3.6 (older) points on the firm conditions and 16.2 and 22.7 points on the foam
  conditions. Each value, reported for a five-trial mean, is converted to a per-trial standard deviation,
  \(\mathrm{MDC}\sqrt{5}/(1.96\sqrt{2})\), and three-trial medians are simulated 100,000 times at each baseline
  level with independent, normally distributed errors.

The literature margin is a transfer. Pang et al. measured five-trial means with head movements on firm and
sway-referenced surfaces and divided age groups at 50 years. Here it is applied to three-trial medians with the head
still, including foam, with the HBEDB age groups divided at 60 years. Taking the larger of the two margins is the
cautious choice.

If \(q_c \ge 1\), the GO threshold lies at or above baseline. GO is then not reachable under the recovery model, and
no retest time is estimated.

**Example.** For participant A on foam with eyes closed, \(b = 84.7\), \(q_{95} = 1.267\) and \(P5 = 77.1\), so
\(q = \max(0.950, 0.910) = 0.950\). A score must reach 95% of baseline for GO.

## Published values and design choices

| Quantity | Origin |
|---|---|
| 75% line | Published: working definition of recovery (Jain et al. 2010) |
| 5th-percentile floor | Published criterion (Jain et al. 2010), computed from HBEDB reference data |
| Test–retest margin | Computed from HBEDB data and from published values (Pang et al. 2011), with the transfer assumptions above |
| Two sessions, at least 2 h apart | Design choice |
| Recovery model | Published (Wood et al. 2015, Table III) |

## Overall result (rule 7)

- The overall result is that of the least favourable condition, in the order CANNOT ASSESS, NO-GO, CAUTION, GO.
- A test with a condition that was not measured cannot yield GO and is limited to CAUTION.
- **Overall GO requires two consecutive GO tests in separate recorded sessions at least 2 h apart.** A single GO
  session gives CAUTION with a request for a confirmatory session. Session times must be strictly increasing,
  otherwise the result is CANNOT ASSESS.
- The retest estimate never yields GO. Only a measured session can.

## Recommended actions

| Situation | Recommended action |
|---|---|
| NO-GO | Do not leave the vehicle unassisted. Retest at the estimated time, or refer to the crew surgeon if no time can be estimated or a fall occurred |
| CAUTION after one GO session | A confirmatory test in a separate session at least 2 h later |
| CAUTION for any other reason | Retest at the estimated time, or refer to the crew surgeon |
| CANNOT ASSESS | Repeat the test with valid recordings, or correct the session times |
| GO | No further testing is required under the decision rules. The egress decision rests with the crew surgeon |
