# Validation

The values below are produced by `scripts/validate.py` from the full Human Balance Evaluation Database (163 adults,
1,930 trials) and are reported in `out/VALIDATION.md` in the repository.

## Reference cohort

In this model, the healthy reference group comprises HBEDB participants without a reported disability, excluding
those reporting labyrinthitis. Other illnesses and medication are not excluded: of the 140 participants, 86 report an
illness and 89 a medication. The group therefore represents a general adult population rather than a screened
astronaut population. Its floors and margins are provisional proxies for crew values, and whether they are more or
less conservative than crew-specific values has not been established.

## Calibration against NASA crew preflight scores

Healthy adults aged 25–55 years (n = 43), scored with the method described in
[Measurement and score](measurement.md), compared with the preflight means of 37 ISS crew members (Wood et al.
2015, Table III). The tolerance for the firm conditions, 5 points, was set before the comparison.

| Condition | NASA analogue | This model (median) | NASA preflight (mean) | Difference |
|---|---|---|---|---|
| Firm floor, eyes open | SOT 1 | 94.1 | 94.3 | −0.2 |
| Firm floor, eyes closed | SOT 2 | 92.9 | 89.9 | +3.0 |
| Foam, eyes open | SOT 4 | 86.9 | 87.9 | −1.0 |
| Foam, eyes closed | SOT 5 | 85.8 | 74.9 | +10.9 |

The firm conditions are within tolerance. On foam with eyes closed, the healthy median is 10.9 points above the NASA
mean. The cohorts, estimators and support surfaces differ (foam here, a sway-referenced platform at NASA), so this is
an observed difference between protocols rather than a measured effect of the surface. Agreement on the firm
conditions does not establish equivalence with the NASA method.

## Healthy retest

The thresholds were derived from one half of the healthy participants and applied to the other half (two-fold
cross-validation by participant). The baseline was the first 20-s window of each trial and the retest the second
window of the same trials, so no true change occurred. A single test was scored, without the two-session rule.

| Group | n | GO | CAUTION | NO-GO |
|---|---|---|---|---|
| All | 140 | 42.9% | 56.4% | 0.7% |
| Younger | 82 | 72.0% | 26.8% | 1.2% |
| Older | 58 | 1.7% | 98.3% | 0.0% |

Healthy participants are often held at CAUTION, particularly older participants on foam, where test–retest
variability is large. The rules favour a retest over a false clearance.

## Structural check

When every retest trial is set to 74% of the participant's own baseline trials, the ratio is 0.74 in every
condition, and the 75% rule returned NO-GO in all four conditions for 140 of 140 participants. This confirms that the
rule operates as specified. It is not evidence of safety.

## Automated tests

The test suite (197 tests in the published version of 15 November 2026) checks:

- every rule against an independent statement of the arithmetic, on 200,000 random inputs including invalid ones,
- the exact thresholds and malformed inputs,
- the two-session rules and session ordering,
- the retest and pharmacological solvers against a dense brute-force search,
- the real-data values reported on this page,
- the application itself, in which every example reproduces the result of the decision engine, and randomly set inputs
  give the engine's result.

## Next steps

The thresholds are provisional. The following data would allow them to be tested:

1. **Repeated sessions in healthy adults**, to measure day-to-day test–retest variability, which the single-session
   HBEDB recordings do not provide.
2. **Foam and sway-referenced testing in the same participants**, to quantify the transfer between the two
   protocols.
3. **Post-landing crew data with observed egress performance**, to set the thresholds against a functional outcome.
