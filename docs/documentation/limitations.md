# Assumptions and limitations

The application supports the decision of a crew surgeon and is not a clearance authority. Every threshold is a
provisional decision assumption informed by NASA working definitions, not a validated egress boundary.

## Assumptions

| | Assumption | Basis |
|---|---|---|
| A1 | Firm floor with eyes open and closed corresponds to Sensory Organization Test conditions 1 and 2 in sensory content. Foam approximates conditions 4 and 5. | Jain et al. (2010); Bermúdez Rey et al. (2016) |
| A2 | The typical recovery rate of ISS crew applies to the measured deficit of an individual. | Wood et al. (2015) describe the median crew member |
| A3 | The 25% decrement, the 5th-percentile floor, the test–retest margin and the 2-h two-session rule are suitable decision thresholds. | Jain et al. (2010); HBEDB; Pang et al. (2011) |
| A4 | Promethazine concentration is proportional to dose, and its effect is linear in concentration. | Gandia et al. (2006), 50 mg study |
| A5 | The link between promethazine and balance follows the vestibular-ageing equivalence described in [Pharmacological scenario](medicine.md). | Diaz-Artiles et al. (2017); Bermúdez Rey et al. (2016) |
| A6 | The zero-point-to-zero-point centre-of-mass estimator gives scores comparable with the NASA estimator. | Calibration on the firm conditions |
| A7 | Recovery after landing on the Moon (0.17 g) or Mars (0.38 g) follows the Earth-return data. | Not characterised (transfer assumption) |
| A8 | The test is administered with a spotter or a safety harness. | Test design |

## Limitations

- The HBEDB participants are not astronauts, and each was recorded in a single session, so day-to-day test–retest
  variability is not measured. Their reference scores serve as preflight proxies.
- No public dataset labels individuals as fit or unfit to leave a vehicle, so the thresholds cannot be validated
  against outcomes.
- Post-landing sessions in the demonstration are simulated by scaling a participant's own trials onto the typical
  NASA crew recovery curve, and they are labelled as simulated.
- The benefit of the two-session rule assumes independent retest errors. Learning effects reduce it.
- Under literature-level test–retest variability, older adults rarely reach GO on foam. This is a deliberate safety
  trade-off.
- The single-exponential model of Wood et al. (2015) does not represent the slower recovery phase over the
  following weeks. The supported range is 240 h after landing.
- The pharmacological scenario is unvalidated and adjusts only the retest estimate.
