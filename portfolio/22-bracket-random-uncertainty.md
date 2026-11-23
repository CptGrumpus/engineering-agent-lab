# Bracket arm under random vibration: how robust is the PASS?

[Portfolio index](../PORTFOLIO.md) · Verification and uncertainty

| | |
|---|---|
| **Answer** | Robust. With damping, test level, fatigue strength and plate thickness all uncertain, the chance that [study 21](21-bracket-random-vibration.md)'s arm fails any of its three requirements is about 2 in a million (limit 1 in 1000). The tip clearance is the closest (reliability index 4.55). Damping drives 71 % of the variance of the fatigue damage and over 80 % of the stress and tip; failing any requirement needs damping about ten times below the 1 % lower bound assumed. Measure damping first. All input distributions are synthetic. |
| **Discipline** | Verification and uncertainty quantification |
| **Tools** | CalculiX, Python (NumPy, SciPy) |
| **Methods** | Monte Carlo, Sobol sensitivity indices (Saltelli / Jansen estimators with bootstrap intervals), FORM (HL-RF with an SLSQP fallback), importance sampling at the design point, a modal surrogate checked off its grid |

## The question

Study 21 passed on nominal inputs. A project never knows those exactly. Four inputs were given distributions (agreed
with the client as synthetic):
- **modal damping**: lognormal, median 2 %, 90 % between 1 % and 4 %;
- **test level**: ±1.5 dB on the spectrum (the shaker's control tolerance), uniform;
- **fatigue strength**: a lognormal factor on the EN 1993-1-9 curve, median 1, 10 % scatter;
- **plate thickness**: 7.0 mm, standard deviation 0.1 mm (a ±0.3 mm drawing tolerance as 3 sigma).

Requirement REQ-H1: the probability of failing any of study 21's requirements stays below 1e-3. And which input is
worth measuring first?

## The answer

- **Probability of failure 2.2e-6** (importance sampling, the sum over the three requirements: an upper bound on the
  union). Plain Monte Carlo saw no failure in 32,768 samples (95 % bound 5.9e-5), consistent with it.
- **Tip clearance governs:** reliability index 4.55 (failure probability 1.7e-6). Fatigue 4.82, stress 8.0.
- **Damping is the input to measure:** Sobol total index of the log damage 0.71 for damping, 0.16 for the test level,
  0.16 for the fatigue strength, 0.001 for thickness. For stress and tip, damping carries over 80 %.
- **How far damping would have to fall** to fail each requirement alone: 0.054 % (stress), 0.24 % (tip), 0.175 %
  (fatigue). A bolted steel bracket shows well over 1 %.
- **99th percentiles:** damage 0.055 (limit 0.5), 3-sigma stress 66 MPa (limit 237), tip 0.59 mm (limit 1).

## How it works

Six CalculiX modal solves on study 21's finest mesh (1.22 mm): five thicknesses from 6.5 to 7.5 mm, made by scaling
the mesh through the thickness (remeshing added a 1 % stress scatter that the damage amplified to 5 %), plus one
off-grid check. Damping, test level and fatigue strength enter the random-response sum and the fatigue calculation
directly, so the only interpolation is in thickness. From that surrogate, 2,048 to 32,768 Monte Carlo and Sobol
samples, FORM for each requirement's design point, and importance sampling around each design point for the small
probabilities that plain sampling cannot reach.

## How I know it's right

- **The surrogate against direct solves off its grid:** stress and tip within 1.1 × 10⁻⁴, damage 3.6 × 10⁻⁴.
- **The nominal point reproduces study 21** to rounding (2 × 10⁻¹⁶).
- **The uncertainty code against closed forms** (a linear limit state with known failure probability, analytic
  Sobol indices): unit tests in `tests/test_uncertainty.py`.
- **FORM against importance sampling** within a factor of 1.8 on every requirement; importance-sampling scatter
  2.6 %; Monte Carlo consistent with both.
- **Sample-size convergence:** Sobol intervals ±0.012 at 32,768 samples; the indices move 0.002 from 8,192 to 32,768.
- **Predictions before the run:** five of six held; the fatigue reliability index came in at 4.82 against a
  predicted 4.9-5.2, and its failing damping at 0.175 % against about 0.14 %.

## Limits

- Every distribution is synthetic. The probability is only as good as the damping distribution; that is the point of
  measuring damping first.
- Damping is one value for all modes; the clamp, its stiffness and fretting are not uncertain inputs here (study 21's
  limits apply).
- Thickness is uniform over the plate.

## Evidence

- [evidence run](../runs/20261123-104847_bracket_random_uq/report.md) (verification PASS)
- case file: `cases/bracket_random_uq.toml` (framing, prototype, predictions, results)
- code: `harness/uncertainty.py`, `studies/bracket_random_uq.py`
