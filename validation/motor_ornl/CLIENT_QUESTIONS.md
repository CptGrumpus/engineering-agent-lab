# Study 7: questions for the client

Status 2026-11-23 21:23 (question 2 revised after measuring the drawing's magnet stops). The model is built from your drawings, bill of materials, magnet data and routine
tests. It reads about 18 % high on back-EMF and on locked-rotor torque. A second, independent solver
confirms the field calculation to 0.1 %. Lamination grade and end effects explain at most about 4 %. The
answers below decide what remains. They are listed in order of how much they could change the result.

| # | Question | Why it matters | What would settle it |
|---|---|---|---|
| 1 | How are the rotor magnets magnetised in production (in the assembled rotor, or before insertion), and what fraction of saturation does the process reach? | The magnet data you supplied is a re-saturated sample (1.255 T at 20 C). If the magnets in the rotor sit at 88-90 % of that, it accounts for the whole gap. Partial demagnetisation in service would look the same. | Your production engineer's figure. Or take one magnet out of a production rotor, measure it in a Helmholtz coil with a fluxmeter, re-saturate it and measure again (about half a day). |
| 2 | Do the magnets sit on the drawn stops in production, or is there an as-built offset along the pocket? | Measured on your drawing, every magnet sits on its stop with at most 0.4 mm of play, as modelled. A confirmation closes the point; we do not expect it to be large. | A section of one rotor, or the assembly drawing's dimension. |
| 3 | What material is the rotor's end clamping piece? | A non-magnetic piece (it looks non-ferrous in the teardown photo) leaves the end effects at 1-4 %. A steel piece would short part of the magnet flux at both ends. | One line from the parts list. |
| 4 | Which lamination grade is used (stator and rotor)? | Three plausible grades change the back-EMF by under 0.4 %. It matters more for iron loss and for the bridges' stress at overspeed. | The material specification. |
| 5 | Can a Hall-probe scan of the no-load air-gap flux density be taken on one motor? | It separates "less magnet flux" from "more leakage" directly and would confirm the answer to 1 or 2. | About a day on the test bench. |
