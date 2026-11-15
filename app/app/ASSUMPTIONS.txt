# Assumptions, limitations and verification

The application supports the decision of a crew surgeon and is not a clearance authority. Every threshold described below is a provisional decision assumption informed by NASA working definitions, not a validated egress boundary.

## Safety principles
1. Status is derived only from a measured balance test. The recovery forecast estimates when to retest and never yields GO.
2. Within each condition, the rules are applied in a fixed order: invalid input, then falls, then the ratio criterion for NO-GO, then the population floor (which limits the result to CAUTION), and finally the GO criterion. The overall status is that of the least favourable condition.
3. Invalid or unvalidated input yields CANNOT ASSESS, never GO. A test with a missing condition cannot yield GO and is limited to CAUTION.
4. An overall GO requires two consecutive measured GO tests in separate sessions at least 2 h apart.

## Assumptions
- **A1 Test conditions.** Firm floor with eyes open and closed corresponds to conditions 1 and 2 of the NASA Sensory Organization Test in sensory content, although not in protocol. Foam with eyes open and closed approximates conditions 4 and 5 (Jain et al. 2010, Bermúdez Rey et al. 2016). On foam with eyes closed, healthy adults score higher here than NASA crew on condition 5, an observed difference across cohorts and protocols (out/VALIDATION.md).
- **A2 Recovery curve.** Wood et al. (2015) describe the median crew member after International Space Station (ISS) missions. The forecast applies this typical recovery rate to the measured deficit of an individual.
- **A3 Thresholds.** The 25% acceptable decrement, the age-matched 5th-percentile population floor, the noise-adjusted GO criterion and the 2-h two-test rule are provisional and have not been validated for egress. Jain et al. (2010) regarded a decrement of less than 25% from a crew member's own preflight score as recovery.
- **A4 Pharmacokinetics.** Promethazine concentration is assumed to be proportional to dose, based on a 50 mg study (Gandia et al. 2006), and the effect is taken as linear in concentration. The 25 mg reference and the intramuscular effect are extrapolations.
- **A5 Drug effect on balance.** The link between promethazine and balance is an unvalidated scenario that adjusts only the retest estimate and never changes a measured status.
- **A6 Signal processing.** The centre of mass is obtained by zero-point-to-zero-point integration of the horizontal force, using the first complete 20-s window of each trial. Noise margins are the larger of the margin derived from HBEDB data and the published test–retest limits (Pang et al. 2011). This estimator is an adaptation: Wood et al. (2015) estimated the centre of mass by low-pass filtering the centre of pressure (second-order Butterworth, 0.85 Hz). The equilibrium-score formula is the same, but the complete NASA measurement pipeline is not reproduced.
- **A7 Gravity transfer.** The NASA recovery data describe return to Earth gravity after ISS missions. Recovery after landing on the Moon (0.17 g) or Mars (0.38 g) has not been characterised, so the retest estimate is a transfer assumption for those missions.
- **A8 Test administration.** The test challenges balance in crew members who may fall. It should be administered with a spotter or a safety harness, and a fall is recorded as a trial outcome.
- **A9 Sessions.** In the application, each recorded session keeps its own trial scores and time after landing, and the two-test rule is applied to the recorded sessions.

## Limitations
- HBEDB participants are not astronauts, and each was recorded in a single session, so day-to-day test–retest variability is not measured. Their reference scores serve as preflight proxies in the demonstration.
- No public dataset labels individuals as fit or unfit to leave a vehicle, so the thresholds cannot be validated against outcomes.
- The benefit of the two-test rule assumes independent retest errors, and learning effects reduce it.
- Under literature-level noise, older individuals rarely reach GO on foam. This is a deliberate safety trade-off.
- The single-exponential curve of Wood et al. (2015) does not represent the slower recovery phase over subsequent weeks.
- Post-landing sessions in the demonstration are simulated by scaling a participant's own HBEDB trials onto the typical NASA crew recovery curve, and they are labelled as simulated.
- The healthy reference group comprises HBEDB participants without a reported disability, excluding reported labyrinthitis. Other illnesses and medication are not excluded (of 140 participants, 86 report an illness and 89 a medication).
- Balance scores improve with repeated testing, and Jain et al. (2010) excluded the first two preflight sessions for this reason. The familiarisation protocol for the preflight baseline is not specified here.
- Jain et al. (2010) report that foam testing was tried with one Shuttle crew on landing day and abandoned after the crew reported concern that it disrupted their postflight recovery. Tolerability on landing day is unresolved.
- The literature noise margin transfers the minimal detectable change of Pang et al. (2011), measured as five-trial means in the head-shake test with age groups divided at 50 years, to three-trial medians in static-head conditions with HBEDB age groups divided at 60 years. Errors are assumed independent and normally distributed.
- Retest times later than 240 h after landing are extrapolations of the recovery model and are labelled as such.

## Verification
- **Application code.** The automated test suite (`pytest`) checks every rule against an independent statement of the arithmetic (200,000 random inputs, including invalid ones), the exact thresholds, malformed inputs, the two-test history rules, the forecast and pharmacological solver against a dense brute-force search, and the real-data values reported in out/VALIDATION.md.
- **Mathematical framework (verified before implementation).** An independent test bench checked the frozen mathematical framework with 826,569 checks and 0 failures, covering signal-to-decision validity, the two-test rule and the GO-time solver. This is evidence about the specification rather than the code. The code reproduces the per-trial scores of the test bench to 1e-14 and its derived parameters exactly.
