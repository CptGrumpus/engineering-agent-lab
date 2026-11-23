# Study 7: the client data pack

Written 2026-11-23 13:55 (time from `date`), shortly after the user changed the study's mode: from here on it runs as a regular client
project. Everything a client would hand over (drawings, bill of materials and masses, material data, routine test
results) is collected here and used as model input. Anything missing is looked up before it is assumed. The test
results the job must predict (locked-rotor torque, efficiency map) stay validation targets, not inputs. The blind
pass (`RESULTS.md`) and revisions 1-4 (`CALIBRATION_PLAN.md`) stay as the record.

## Sources

| Short name | Report | File (sha256, first 12) | Client-type content |
|---|---|---|---|
| Drawing | ORNL/TM-2005/33, Fig. 21 (lamination drawing) | Pub57487.pdf (179407ecf90a) | Stator and rotor lamination dimensions |
| BOM | **ORNL/TM-2010/253** (Burress et al., March 2011), Table 2.7, 2004 Prius column; Figs. 2.71-2.73 | Pub26762.pdf (4d989e77e3d9), downloaded 2026-11-23 | Dimensions, masses, winding, measured phase resistance, magnet size and mass, magnet remanence and coercivity against temperature |
| Teardown | ORNL/TM-2004/137 | Pub57348.pdf (32469ab008f7) | Winding connection, lamination thickness, slot fill, polymer-moulded magnets, magnet B-H line |
| Design report | ORNL/TM-2004/120 | tm2004_120.pdf (6548edc4618c) | ORNL's own design-study model of this motor: inputs, not hardware data (see below) |
| Test report | ORNL/TM-2006/423 (and interim TM-2004/247) | tm2006_423.pdf (e2685ea9...) | Back-EMF test and conditions, static inductances, component masses, efficiency map (target) |
| Torque report | **ORNL/TM-2004/185** rev. 2007 (Hsu et al.) | 921782.pdf (c985c0ce2858), downloaded 2026-11-23 | Back-EMF measurement method, locked-rotor torque (target) |
| Thermal report | ORNL/TM-2005/33 | ornl_thermal.pdf | 900 rpm load tests with winding temperatures |

## The pack, against the model

| Quantity | Client value (source) | Model before today | Status |
|---|---|---|---|
| Stator OD / ID | 26.9 / 16.19 cm (BOM); 10.600 / 6.375 in (drawing) | drawing | match |
| Rotor OD / ID | 16.05 / 11.1 cm (BOM); 6.314 / 4.356 in (drawing) | drawing | match |
| Air gap | **0.730 mm** (BOM, stated); 0.775 mm from the drawing's bore and OD | 0.775 mm | **differs**: BOM's own OD/ID give 0.70 mm. Carry 0.73-0.775 as a band |
| Stack | stator 84.0 mm, rotor 83.6 mm (BOM); 3.3 in (teardown) | 83.82 mm | match (0.3 %) |
| Lamination thickness | **0.33 mm** (BOM); 0.014 in = 0.36 mm (teardown) | 0.35 mm (stand-in grade) | minor |
| Lamination grade | not given anywhere found | M330-35A stand-in | open: ask the client; three grades moved back-EMF 0.13 % |
| Stator core mass | **19.05 kg** (BOM) | 18.8 kg solid from the model's area x stack x 7650 (ears not modelled) | match: confirms the stator geometry |
| Slots, slot depth, opening | 48, 33.5 mm, 1.93 mm (BOM) | 48, 33.53, 1.93 | match |
| Turns per coil, coils in series, paths | 9, 8 per phase, one path (BOM; design report; teardown) | 9, 72 series turns, 1 | match |
| Strands | 13 in parallel, AWG 19 = 0.912 mm (BOM) | 13 x 0.912 mm | match |
| Stator copper mass | **6.8 kg** (BOM) | 6.72 kg from the efficiency study's turn length (408.8 mm) | match: confirms the end-winding length |
| **Phase resistance** | **0.069 ohm at 21 C**, average of phase-to-phase / 2 (BOM; a routine test) | 59.6 mOhm at 20 C computed | **differs (-14 %)**: use the measured value from now on (leads, joints and insulation build make a computed value low) |
| **Magnet size** | **83.1 x 18.9 x 6.5 mm**, 10.2 cm3, 77 g each, 16 magnets, 1.232 kg (BOM) | blind: 18.9 x 6.80 (pocket filled); revision 4: 19.24 x 5.31 (design report) | **revision 4 was wrong**: 77 g / 10.2 cm3 = 7.55 g/cm3, bare NdFeB; at 5.31 mm the magnet would need 9.1 g/cm3. The magnet nearly fills its 6.80 mm pocket (0.3 mm left for the polymer) |
| **Magnet remanence** | **12.55 kG = 1.255 T at 20 C**, about 11.55 kG at 100 C, 10.9 kG at 150 C (BOM Fig. 2.72, hysteresisgraph): about -0.10 %/C | 1.243 T (teardown Fig. 14, extrapolated) | match within 1 %: the material was right all along |
| Coercivity Hci | about 17 kOe at 115 C, 12 kOe at 160 C, 6 kOe at 225 C (BOM Fig. 2.73) | not used at open circuit | for demagnetisation checks later |
| Magnet axial length | 83.1 mm (BOM) | = stack 83.82 | minor (-0.9 % on magnet flux) |
| Back-EMF | 89.78 V rms per 1000 rpm, **line to line** (test report Table 3.4; ORNL's own field-weakening calculation uses it as V_LL: 390 V at 4372 rpm); oil at a nominal 25 C; measured with a Yokogawa PZ-4000 power meter across two phases, repeated to rule out heating (torque report). Per-speed values scatter about +-3 % | reference | the measurement side is settled: line to line, room temperature, power meter |
| Static inductances | Ld 1.92 mH, Lq 5.0 mH (test report p. 51; current and convention not stated) | reference | target for the next comparison |
| Component masses | stator 25.9 kg, rotor 10.2 kg with shaft (test report, BOM) | | rotor includes the shaft: not comparable without the shaft drawing |

## Corrections this pack forces

1. **Revision 4's explanation is overturned.** Revision 4 took the magnet thickness (5.31 mm) from ORNL's
   design-study model (TM-2004/120 Table 5.3, SPEED's LM). The measured magnet is 6.5 mm (size, volume and mass
   agree). The 1.5 mm non-magnetic layer that "explained most of the blind miss" does not exist; about 0.3 mm does.
   The polymer moulding (teardown) is real, but thin.
2. **The material was right**: 1.255 T measured at 20 C against our 1.243 T. ORNL's 1.12 T is that magnet at about
   125 C (confirmed by the BOM curve, not only by the coefficient).
3. **So with the client's own data the model is back near the blind geometry**, which read +24 % on back-EMF. The
   gap is not in the magnet's size, the magnet's material, the winding, the stack or the test's temperature or
   connection: every one of those is now measured data that matches the model. What remains is model form or
   manufacturing, for example: how fully the magnets are magnetised in the assembled rotor (TM-2004/137: the rotor
   is magnetised after assembly; a hysteresisgraph re-saturates its sample, so 1.255 T is the fully magnetised
   value), the air gap (0.73-0.775 mm), 3D end effects, or the 2D model itself. Each is a hypothesis to test on
   its own; the first is a question a client's production engineer could answer (magnetising process and the
   fraction of saturation it reaches).
4. Phase resistance: use the measured 69 mOhm at 21 C in the efficiency and thermal work.

## Not used as inputs (validation targets or teardown-only)

Locked-rotor torque (TM-2004/185, TM-2006/423 Fig. 3.10), the efficiency map (TM-2006/423 Table B-1), the measured
air-gap flux map (TM-2004/137 Fig. 13, teardown-only), the 900 rpm load tests (thermal report; a check on the thermal
model).

## Searched, nothing usable (2026-11-23 14:20)

- Magnet grade or supplier datasheet for the 2004 Prius: not found in the literature searched; the measured curve
  (TM-2010/253 Fig. 2.72) replaces it.
- Lamination grade: not found (Cobham's 2013 Opera model of this motor used M19 as a stand-in, as we use M330-35A).
- Independent FEA of this motor: R. Kaczmarek (Cobham / Vector Fields), "Simulating the Toyota Prius electric motor",
  Magnetics Business & Technology, Spring 2013 (magneticsmag.com): 2D Opera model from ORNL data, gap 0.75 mm, stack
  83.56 mm, M19 steel, magnet B-H interpolated from ORNL's points; back-EMF and torque compared with ORNL only in
  plots, described as a "slight difference". No numbers in the text, so it cannot be used as a cross-check.
- Magnetisation level after in-rotor (post-assembly) magnetising: the literature found discusses the effect
  (IEEE Access 2024, Moon, Kim and Kang; VDE 2025, Slatter and Saito) but gives no general percentage. On a real job
  this is a question for the client's production engineer.
