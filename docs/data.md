# Data

## NASA data

| Data | Role in the model |
|---|---|
| **Wood et al. (2015), Table III.** Preflight means, landing-day values and recovery time constants of the Sensory Organization Test in 37 ISS crew members | Retest estimate, comparison with typical crew, simulated post-landing sessions, calibration |
| **Jain et al. (2010).** Posturography in Space Shuttle crew after short flights | The 75% NO-GO line, the 5th-percentile floor, the problem statement |
| **NASA Human Research Roadmap.** *Risk of Altered Sensorimotor/Vestibular Function Impacting Critical Mission Tasks* | Problem definition |
| **NASA Open Science Data Repository, SpaceX Inspiration4 crew blood panels.** OSD-569 (complete blood count) and OSD-575 (comprehensive metabolic panel), seven analytes for 4 crew members at 7 time points | Context tab: each value relative to the crew member's own preflight mean, the same within-subject principle as the balance test. Not part of the decision |
| **Shi et al. (2011); Boyd et al. (2009).** NASA promethazine studies | Warnings shown with a dose |

Every cited value is listed with its page locator and link in `params/nasa_sources.csv` in the repository.

## Human Balance Evaluation Database

The Human Balance Evaluation Database (Santos and Duarte 2016, PhysioNet) contains force-plate recordings of 163
adults: 1,930 trials of 60 s at 100 Hz, in the four conditions used here. It provides the baselines, the test–retest
margins and the population floors. Three participants form the demonstration set:

| Label | HBEDB participant | Age group |
|---|---|---|
| A · younger adult | 117 | Younger |
| B · older adult | 71 | Older |
| C · low baseline balance | 13 | Younger |

Only the files of these three participants are included in the repository. The full database is downloaded by
`scripts/fetch_data.py` to reproduce every reported value.

## Other published values

| Source | Value | Use |
|---|---|---|
| Pang et al. (2011) | Minimal detectable change of the head-shake Sensory Organization Test | Literature test–retest margin |
| Gandia et al. (2006) | Promethazine half-life, time to peak and peak concentration | Pharmacological scenario |
| Diaz-Artiles et al. (2017) | Roll-tilt threshold after 25 mg oral promethazine (+31%) | Pharmacological scenario |
| Bermúdez Rey et al. (2016) | Roll-tilt threshold rise with age (+32% per decade) | Pharmacological scenario |

## Licences

| Material | Licence |
|---|---|
| HBEDB and files derived from it | Open Data Commons Attribution License v1.0 (ODC-By) |
| NASA OSDR data | Publicly released NASA data, reused with citation of the study accessions |
| Published values | Cited. No text or figures are reproduced |
| Code and the team's own material | MIT |

No NASA logos or branding are used.
