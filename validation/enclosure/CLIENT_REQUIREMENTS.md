# Study 11: the client's thermal requirements (synthetic, revision B)

**Status: synthetic.** The user's decision (2026-11-25): write the requirement list a real client would send, and
treat it as given for the case study. Every number below is typical of practice, not taken from a real product. The
rule behind each limit is stated, so a reader can check that no limit was picked to make a design pass.

**Timing, for the record.** Written on 2026-11-25 at about 16:30. At that point the 3,600 s redesign runs and their
extrapolated settled values were already known (page 27). The 9,000 s verification runs, which give the settled
values, were still running. This list replaces the first study's two blanket limits for the final verdict:
- REQ-D1: hottest component 85 C;
- REQ-D2: mean air 60 C.

Those two limits stay on record, together with their verdicts.

## Operating conditions (unchanged)

- 40 C maximum outside air, still air, continuous duty.
- Outside surface: heat transfer coefficient h 5 W/m2K, emissivity 0.85.
- Dissipation:
  - U1: 5 W;
  - the rest of the board: 10 W, spread over its length.

## Parts and data (the client's bill of materials and datasheets, synthetic)

| Ref | Part | Data |
|---|---|---|
| U1 | Power regulator, 20 mm package, mid-board | Tj max 150 C; junction to case 2.0 K/W |
| PCB | FR-4, 2 mm, copper planes | Tg 140 C; UL 796 maximum operating temperature (MOT) 130 C |
| C1 | Aluminium electrolytic, bulk capacitor | 105 C rated, 5,000 h at 105 C; footprint 5-15 mm from the board's left end |
| Rest | Logic and interface parts (the 10 W) | Commercial grade, 0-70 C ambient |

The client's derating policy:
- junction at least 25 K under Tj max;
- laminate at least 25 K under its MOT;
- electrolytic capacitor life of at least 50,000 h of continuous operation (about 5.7 years).

## Requirements

| ID | Requirement | Limit | Derivation | Model metric |
|---|---|---|---|---|
| REQ-E1 | U1 junction at or below 125 C | U1 case 115 C | 150 - 25 = 125 C junction; case = junction - 2.0 K/W x 5 W | `component_max_C`, the hottest point of the U1 block (conservative for the case) |
| REQ-E2 | The board laminate at or below 105 C anywhere | 105 C | MOT 130 - 25 | `board_max_C` |
| REQ-E3 | C1 at or below 70 C, for at least 50,000 h of life | 70 C | Life doubles per 10 K below rating: 5,000 x 2^((105 - T)/10) >= 50,000 gives T <= 71.8 C; the client rounds down to 70 C to cover ripple self-heating | `C1_board_max_C`: the largest board temperature under C1's footprint |
| REQ-E4 | Commercial-grade parts within their ambient rating | Internal air 70 C | Their 0-70 C ambient rating | `air_mean_C`, the mean internal air (a 2D model has no local air per part: stated limit) |

## Modelling assumptions this adds

- **C1 runs at the board temperature under it:**
  - its own ripple loss is neglected, and the 1.8 K rounding margin covers it;
  - its body sees the board from below and the air around it. The board is the hotter of the two in every run so far.
- **U1's hottest model point stands in for its case.** U1 is a solid block of board material carrying 5 W. Its real
  case is cooler than the block's hottest point, so this errs on the safe side.
- **C1's footprint is given by the client.** Moving C1 is a design change this study can recommend, not assume.

## Evidence

- Redesign, 9,000 s:
  - cases `enclosure_fix_k5_*_long`;
  - rescored against this list from each run's kept final board field (`scripts/score_client_requirements.py`).
- As drawn:
  - cases `enclosure_k5_eps0p9_e`, `enclosure_k20_eps0p9_e`, `enclosure_k5_eps0p1_e` and `enclosure_k20_eps0p1_e`;
  - these are the four corners rerun with this list as their requirements. The emissivity 0.1 corners go to
    9,000 s so they settle.
- Predictions are in each case header, written before the results.
