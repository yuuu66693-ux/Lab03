# Validation — Lab 02 → Lab 04

## 1. Lab 02/03 DC bias reference (kept unchanged)

**Inputs:** `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`, `β = 100`, `VBE = 0.70 V`

| Quantity | Independent calculation | `dc_bias.py` | Match |
|---|---:|---:|:---:|
| VTH (V) | 2.16393442623 | 2.16393442623 | ✅ |
| RTH (Ω) | 18032.7868852459 | 18032.7868852459 | ✅ |
| IB (A) | 1.22985814626e-05 | 1.22985814626e-05 | ✅ |
| IC (A) | 0.00122985814626 | 0.00122985814626 | ✅ |
| IE (A) | 0.00124215672772 | 0.00124215672772 | ✅ |
| VB (V) | 1.94215672772 | 1.94215672772 | ✅ |
| VE (V) | 1.24215672772 | 1.24215672772 | ✅ |
| VC (V) | 9.29431207823 | 9.29431207823 | ✅ |
| VCE (V) | 8.05215535050 | 8.05215535050 | ✅ |
| Region | Active | `active` | ✅ |

Warnings (cutoff / saturation) and invalid-input handling are covered in `tests/test_dc_bias.py` and `tests/test_web.py`. The Lab 03 A1–A5 browser record is in `docs/lab03-validation.md`.

---

## 2. Lab 04 engine and reproducibility

**Engine used:** `ngspice-47`, console build `ngspice_con.exe`
**Model card:** `Q2N3904` (generic 2N3904 NPN card embedded in `spice_engine.py`)
**Discovery order:** `NGSPICE_BIN` → `ngspice_con` on `PATH` → `ngspice` on `PATH` → common Windows `Spice64\bin` locations. The GUI build is avoided because it blocks waiting for a window.

**Circuit (single reference CE amplifier):** VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, Cin = Cout = 10 µF, source 10 mV peak at 1 kHz, unbypassed emitter resistor, load capacitively coupled at the collector.

**Commands:**
```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m flask --app app run --port 5000
```
Open <http://127.0.0.1:5000/>. On Windows, add `%LOCALAPPDATA%\Programs\Spice64\bin` to `PATH` or set `NGSPICE_BIN` to the full path of `ngspice_con.exe`.

**Automated result:** `Ran 47 tests ... OK`
- `test_dc_bias.py` 5 — Lab 02/03 engineering math
- `test_web.py` 3 — Lab 03 Flask client
- `test_spice_engine.py` 23 — validation, netlist, parsing, engine discovery, failure handling
- `test_plotting.py` 7 — Bode panels, transient scaling, ticks, empty state
- `test_simulate_route.py` 6 — `/simulate` success, invalid input, engine failure, provenance, regression
- `test_template_circuit.py` 3 — CE common ground/one Vout label, connected nodes, Lab 03 emitter resistor continuity

---

## 3. Real SPICE results (all numbers read from ngspice output)

### DC operating point (`.op`)
| Quantity | SPICE (`2N3904`) | Analytical (Lab 03, β=100, VBE=0.70 V) |
|---|---:|---:|
| VB | 2.004 V | 1.942 V |
| VE | 1.333 V | 1.242 V |
| VC | 9.087 V | 9.294 V |
| VCE | 7.754 V | 8.052 V |
| IC | 1.324 mA | 1.230 mA |

The two columns are deliberately separate: the analytical model uses constant β/VBE, while SPICE uses the 2N3904 model card. They are not expected to match to every digit.

### AC frequency response (`.ac dec 20 10 10meg`)
- 121 frequency points from 10 Hz to 10 MHz.
- At 1 kHz: gain `4.89 dB`, phase `-179.9 deg` (inverting midband).
- Gain = `vdb(out) − vdb(in)`; phase = `vp(out) − vp(in)` converted from radians and unwrapped across frequency.
- Bode plot uses two stacked panels with independent gain (dB) and phase (deg) axes on a log frequency axis.

### Transient (`.tran`, 10 mV peak, 1 kHz)
- 1008 points over a 5 ms window (five periods).
- Vin peak `10.00 mV`, Vout peak `17.60 mV`, `|Vout/Vin| = 1.760 V/V`, output inverted relative to input.

---

## 4. Browser acceptance B1–B8 (Playwright MCP, real runs)

| Case | What was checked | Observed result | Evidence |
|---|---|---|---|
| **B1 Regression** | Divider / Fixed / Emitter modes opened via **Lab 03 calculator** panel and calculated with the Lab 03 reference values | Divider `VB 1.942, VE 1.242, VC 9.294, VCE 8.052 V, IC 1.230 mA, ACTIVE`; Fixed `VB 0.700, VE 0, VC 9.514 VCE 9.514 V, IC 1.130 mA`; Emitter `VB 1.737, VE 1.037, VC 9.742, VCE 8.705 V, IC 1.026 mA` | `docs/evidence/b1-*-results.png` |
| **B2 DC SPICE** | Run DC with the CE reference | `Simulation succeeded · DC · ngspice_con.exe · 2N3904`; right panel shows VB 2.004 / VE 1.333 / VC 9.087 / VCE 7.754 V / IC 1.324 mA; SPICE-vs-Analytical table visible | `docs/evidence/b2-dc.png` |
| **B3 Change RE** | Only `RE` changed 1 kΩ → 2 kΩ, DC rerun | IC `1.324 → 0.704 mA`, VC `9.087 → 10.450 V`, VCE `7.754 → 9.031 V`. Values changed with the simulation, not stale | `docs/evidence/b3-re-2k.png` |
| **B4 AC** | AC tab run, Bode plot inspected | 2 panels (`Gain versus frequency`, `Phase versus frequency`), 121 points each, units dB / deg / Hz, 1 kHz summary `4.89 dB / -179.9 deg` | `docs/evidence/b4-ac.png` |
| **B5 Transient** | Transient tab run at 10 mV / 1 kHz | Vin 10.00 mV, Vout 17.60 mV, gain 1.760 V/V; legend `Vin (mV) / Vout (mV)`, time axis in ms; inversion confirmed by AC phase ≈ −180° and waveform note | `docs/evidence/b5-tran.png` |
| **B6 Change Source** | Amplitude 10 → 20 mV, then frequency 1 kHz → 2 kHz, each rerun | Vout `17.60 → 35.19 mV` at 20 mV; `17.57 mV` at 2 kHz with amplitude restored to 10 mV. Waveform regenerated from the run, not hard-coded | `docs/evidence/b6-amp-20mv.png`, `docs/evidence/b6-freq-2k.png` |
| **B7 Invalid / Fail** | `RE = 0` submitted | Visible error `re: RE must be greater than 0.`; no success banner and no stale chart; the entered `0` stays in the form. Engine-missing failure is covered by `test_engine_failure_is_visible_and_not_success` and `test_missing_engine_returns_structured_error` | `docs/evidence/b7-invalid-re.png` |
| **B8 UI** | Desktop 1440×900 and phone 390×844, mode tabs clicked on phone | Three-column desktop layout; single-column phone layout; 3 analysis tabs; Run button visible; no horizontal overflow (`scrollWidth ≤ innerWidth`); charts and units readable; zero console errors | `docs/evidence/b8-desktop.png`, `docs/evidence/b8-phone.png`, `docs/evidence/b8-phone-ac.png` |

---

## 5. UI critique and polish (Impeccable pass)

| Finding before polish | Fix |
|---|---|
| Bode magnitude and phase shared one axis; phase looked nearly flat and jumped 360° at the ±180° wrap | Split into two stacked panels with separate dB / deg axes; unwrap phase across the sweep |
| Success banner printed the full Windows engine path | Show only the executable basename plus model and duration |
| `favicon.ico` 404 in the browser console | Inline SVG data-URI favicon; console now has 0 errors |
| CE schematic had separate ground rails (RE/RL side disconnected from R2/Vin side) and a duplicated `Vout` label | Single common ground rail at y=288 with one ground symbol; one `Vout` label; viewBox extended to 310 |
| Lab 03 divider/emitter schematic used a transformed RE zigzag that overlapped the emitter wire and stopped short of ground | RE zigzag now starts at the emitter node (260,255), ends at (260,335), then connects to the ground rail; locked by `test_template_circuit.py` |
| Lab 03 calculator collapsed and closed again after `Load mode` / `Calculate` | Details stays open for non-divider modes, results/errors/warnings, and when the header link is used |
| Wide fixed three-column layout on small screens | Responsive breakpoints at 1180 / 860 / 480 px; parameter summary and inputs stack cleanly |

The final layout follows the supplied reference: **CE Amplifier Lab** header, **Circuit & Parameters** (schematic + values + Run Simulation), **Simulation & Plots** (DC/AC/Transient tabs + charts), and **Engineering Results** (DC / AC / transient summaries + engine chip). The Lab 03 calculator is retained as a collapsible regression panel below the main workspace.

---

## 6. Limitations

- Only one analysis runs per submission; the tabs submit the same form with a different analysis value.
- The SPICE model is a generic 2N3904 card chosen for reproducibility; it is not a manufacturer-specific model supplied by the course.
- The transient summary uses peak amplitudes, not an FFT; frequency-domain gain/phase come from the `.ac` run.
- The simulator requires a local ngspice executable. Without it the UI shows an explicit engine error instead of fabricating results.
