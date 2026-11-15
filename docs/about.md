---
hide:
  - navigation
---

# About

The Gravity-Transition Readiness Model was developed for the NASA Space Apps Challenge 2026, in response to the
challenge *Create Health Monitoring Software for Astronauts on Space Missions*.

## Scope

Most health-monitoring tools display vital signs. This prototype converts a measurement into a decision at a moment
that NASA documents as hazardous: leaving the vehicle after landing. It addresses one part of crew health
monitoring, sensorimotor readiness, and is designed so that further modules can be added on the same principle of
comparison with the crew member's own preflight values. The *Additional crew data* tab already presents NASA OSDR
crew blood panels in this form, as context.

## Intended use

The application supports the crew surgeon. It does not constitute clearance, and its thresholds are provisional and
have not been validated for egress. It is a prototype for research and demonstration and is not a medical device.

## Code and reproducibility

The source code, tests, demonstration data and validation report are available in the
[repository](https://github.com/vishram0905/gravity-readiness). Every value reported on this site can be reproduced
with the scripts described in the repository README.

## Use of AI

AI was used to assist in collecting literature, writing code and refining language.

## Licence and acknowledgements

Code: MIT. HBEDB-derived files: Open Data Commons Attribution License v1.0. Data from the Human Balance Evaluation
Database (Santos and Duarte 2016, PhysioNet) and the NASA Open Science Data Repository are gratefully acknowledged.
No NASA endorsement is implied, and no NASA logos or branding are used.
