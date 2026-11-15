# Pharmacological scenario

Promethazine is used to treat space motion sickness. It is also sedating and may impair balance. The application
lets the crew surgeon enter a planned dose and see how it could shift the retest estimate.

!!! warning "Unvalidated scenario"
    The effect of promethazine on balance after landing has not been measured. The scenario adjusts only the retest
    estimate. A dose is entered as planned at or after the test, so it never changes a test result.

## Concentration

Plasma concentration follows a one-compartment model with first-order absorption:

\[
C(t) = A\left(e^{-k_e t} - e^{-k_a t}\right), \qquad k_e = \frac{\ln 2}{t_{1/2}}
\]

with \(k_a\) solved from the time of peak concentration and \(A\) scaled so that the peak equals the published
maximum. Concentration is assumed to be proportional to dose.

| Route (50 mg) | \(t_{1/2}\), h | \(t_{\max}\), h | \(C_{\max}\), µg/L |
|---|---|---|---|
| Oral | 15.6 | 2.9 | 22.5 |
| Intramuscular | 17.8 | 2.0 | 52.4 |

Source: Gandia et al. (2006), Table II (ambulatory phase of a bed-rest study). Available doses are 12.5, 25 and
50 mg.

## Effect on balance

Concentration is expressed relative to the extrapolated peak of a 25 mg oral dose (11.25 µg/L). Diaz-Artiles et al.
(2017) reported that 25 mg oral promethazine raised the roll-tilt perception threshold by 31%, and Bermúdez Rey et
al. (2016) reported a rise of 32% per decade of age in the same threshold. A 25 mg oral peak is therefore treated as
equivalent to 0.97 of a decade of vestibular ageing, and the ratio decrement is

\[
\delta_c(t) = 0.97\, C_{\text{rel}}(t)\, \frac{b'_c}{b_c}
\]

where \(b'_c\) is the decline in equilibrium score per decade of age estimated from HBEDB. The effect is applied only
in conditions where this age slope is established (foam with eyes open). The drug never raises a score.

## Warnings shown with a dose

- **Orthostatic risk.** In a NASA study of 8 healthy participants given intravenous promethazine, all 8 became
  presyncopal on tilt testing, compared with 3 of 8 without the drug (Shi et al. 2011). Stand only with assistance.
- **Absorption in flight.** A lower and later peak concentration has been reported in flight (Boyd et al. 2009).
  Only the direction of this difference is known, and it is not modelled.
