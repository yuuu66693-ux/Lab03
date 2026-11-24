# Lab 04 — BJT CE Amplifier Simulator (extends Lab 03 DC Bias Web App)

Flask web application for ENG29 2121 (Computer Programming for Electrical Engineers), Week 4.
It keeps all three Lab 03 analytical DC-bias modes and adds one reference **common-emitter voltage-divider amplifier** driven by real `ngspice` runs (`.op`, `.ac`, `.tran`). No mock data and no hard-coded traces.

## Scope

- **Lab 03 regression:** Divider / Fixed / Emitter bias, Forward-Active approximation, constant `β` and `VBE`.
- **Lab 04 simulator:** one CE reference circuit, values editable in SI via the form, with:
  - DC operating point from `.op` (VB, VE, VC, VCE, IC)
  - AC gain/phase Bode plot from `.ac dec 20 10 10meg`
  - Transient Vin/Vout waveforms from `.tran`
  - Side-by-side SPICE results and analytical Lab 03 results (clearly labelled)
  - Engine status, model name, netlist and ngspice log tail

## Architecture

```
app.py                     # Flask routes, form parsing, unit conversion, rendering. No circuit equations.
dc_bias.py                 # Lab 03 analytical engineering logic only. Unchanged.
spice_engine.py            # ngspice adapter: validation, netlist, batch run, .print parsers. No Flask/HTML.
plotting.py                # Pure SVG chart geometry (Bode panels + transient waveforms).
templates/index.html       # Presentation only: 3-column workspace + collapsible Lab 03 calculator.
static/style.css           # Styling only, responsive.
tests/                     # unittest: dc_bias, web, spice_engine, plotting, simulate route, circuit diagrams.
docs/validation.md         # Lab 02–04 validation and B1–B8 browser evidence.
docs/evidence/             # Playwright screenshots for B1–B8.
docs/superpowers/          # Design note and implementation plan.
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install **ngspice** (tested with ngspice 47). On Windows the console build is required:
`%LOCALAPPDATA%\Programs\Spice64\bin\ngspice_con.exe`. The app finds it in this order:

1. `NGSPICE_BIN` environment variable (full path to the executable)
2. `ngspice_con` on `PATH`
3. `ngspice` on `PATH`
4. Common Windows `Spice64\bin` install locations

`.venv/`, `.env`, credentials and `.playwright-mcp/` are not committed.

## Run

```bash
.venv\Scripts\python.exe -m flask --app app run --port 5000
```

Open <http://127.0.0.1:5000/>. Do not open `templates/index.html` via `file://`.

## Use

1. In **Circuit & Parameters**, check the schematic/parameter summary and edit values in **Parameters** if needed. Resistors use `Ω`, `kΩ` or `MΩ`; capacitors `µF`; amplitude `mV peak`; frequency `Hz`.
2. Click **Run Simulation**, or use the **DC / AC / Transient** tabs in **Simulation & Plots** to submit that analysis directly.
3. Read **Engineering Results** on the right; the engine/model chip reports the actual ngspice version.
4. The **Netlist used for this run** and **ngspice log tail** details are available under the chart.
5. For the Lab 03 calculator, click **Lab 03 calculator** in the header or the regression panel at the bottom of the page.

Invalid input (for example `RE = 0`) shows a visible error, keeps the entered values, and never displays a stale or fabricated success.

## Tests

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: `Ran 47 tests ... OK`

| File | Tests | Covers |
|---|---:|---|
| `tests/test_dc_bias.py` | 5 | Lab 02/03 engineering math |
| `tests/test_web.py` | 3 | Lab 03 Flask client |
| `tests/test_spice_engine.py` | 23 | SI validation, netlist, parsers, engine discovery, timeouts/parse/run failures |
| `tests/test_plotting.py` | 7 | Bode panels, transient scaling, ticks, empty state |
| `tests/test_simulate_route.py` | 6 | `/simulate` success, invalid input, engine failure, provenance, Lab 03 regression |
| `tests/test_template_circuit.py` | 3 | Circuit-diagram connectivity for CE and Lab 03 modes |

## Reference results (real ngspice 47 run)

| Analysis | Observed |
|---|---|
| `.op` | VB 2.004 V, VE 1.333 V, VC 9.087 V, VCE 7.754 V, IC 1.324 mA |
| `.ac @1 kHz` | 4.89 dB, −179.9° (121 points, 10 Hz–10 MHz) |
| `.tran @10 mV, 1 kHz` | Vin 10.00 mV peak, Vout 17.60 mV peak, gain 1.760 V/V, inverted (1008 points, 5 ms) |

Analytical Lab 03 comparison at the same values: VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA.

Browser acceptance **B1–B8** and the UI polish pass are recorded in `docs/validation.md`, with screenshots in `docs/evidence/`.

## AI assistance and student check

AI generated the Lab 03/04 functions, route/plots/template changes, tests, design/plan notes, browser evidence and this README. Before submission, independently recalculate at least one DC case and repeat at least one browser case personally; confirm ngspice runs on your own machine.

## Submission

GitHub repository: <https://github.com/yuuu66693-ux/Lab03> — branch `lab04` for the Lab 04 work, merged to `main` at submission.
