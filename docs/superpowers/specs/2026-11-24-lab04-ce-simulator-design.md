# Lab 04 — BJT Common-Emitter Amplifier Simulator v1 Design

**Date:** 2026-11-24
**Status:** Approved by student (approach A approved in session; run to completion authorized)

**Intent:** Extend the existing Lab 03 Flask BJT DC-bias app into a first working
Common-Emitter (CE) voltage-divider amplifier simulator that runs **real ngspice**
for `.op`, `.ac`, and `.tran`, shows engineering values and charts that come from
those runs, and keeps every Lab 03 analytical mode and test intact.

**Why:** Lab 04 requires demonstrable simulation, not a mock UI. The grader must be
able to trace each plotted point and each DC value back to an ngspice run, and must
see the SPICE results clearly separated from the Lab 03 analytical approximation.

## Goals

- Preserve all three Lab 03 modes (divider / fixed / emitter), their validation,
  results, and the existing 8 unittests.
- Add one reference CE voltage-divider circuit with real ngspice runs:
  - `.op` → VB, VE, VC, VCE, IC (plus IB, IE) from the solver output.
  - `.ac` → frequency, |Vout/Vin| in dB, phase in degrees, with a stated Vin node.
  - `.tran` → time, Vin, Vout from a `SIN` source, with amplitude/frequency inputs.
- Show engine status (found / version / model / run time), units, and provenance
  on every SPICE result; label analytical vs SPICE values separately.
- Reject invalid input (including `RE = 0`) and engine failures with a visible
  error; never keep old charts next to a success banner.
- Charts are server-rendered SVG built from parsed ngspice arrays (no client-side
  physics, no hard-coded traces).
- Record B1–B8 browser acceptance with real observations in `docs/validation.md`.

## Non-goals

- Drag-and-drop or free-form circuit editing; other bias modes in SPICE.
- Emitter bypass capacitor, FETs, animated current overlays, deployment.
- Writing a SPICE solver or a general netlist parser.
- Replacing Lab 03 architecture or its equations.

## Constraints

- Flask + Jinja, Python 3.10 (`python`), no new runtime dependency beyond Flask.
- `dc_bias.py` stays pure engineering logic; `app.py` stays routing/validation glue.
- ngspice is an external process: call it with an argument list, `shell=False`,
  a timeout, and a fresh working directory per run.
- The reference circuit and model must be reproducible and documented:
  VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ,
  Cin = Cout = 10 µF, source 10 mV peak at 1 kHz, generic 2N3904 model card.
- Windows: ngspice binary is not on PATH by default; the app must resolve
  `NGSPICE_BIN`, then `ngspice` on PATH, and report a clear error when missing.

## Approaches

1. **Extend in place + server-rendered SVG (chosen).** One `spice_engine.py`
   adapter (netlist → batch run → text parse) plus a small pure `plotting.py` that
   scales arrays into SVG point strings; Jinja renders the SVG. Smallest new
   surface, works offline, and the grader can diff numbers in the run log against
   the plotted points.
2. Extend in place + Chart.js + JSON API. Prettier/interactive, but adds a JS
   layer and an API where a chart could drift from the parsed data.
3. Separate simulator service/CLI. Cleaner isolation, unnecessary for one circuit.

## Design

### Files

- `spice_engine.py` (new, pure adapter, no Flask):
  - `MODEL_CARD`, `DEFAULT_SIM_PARAMS`, `check_engine()`.
  - `validate_sim_inputs(values)` → `(clean, errors)` with SI units.
  - `build_netlist(params, analysis)` → netlist text with `.op` / `.ac` /
    `.tran` directives and `.print` lines.
  - `run_analysis(params, analysis, workdir=None, timeout=20)` → dict with
    `ok`, `rows`, `columns`, `log`, `netlist`, `engine`, `duration_s`, `error`.
  - `parse_op`, `parse_ac`, `parse_tran` → list of row dicts (text tables).
- `plotting.py` (new, pure geometry): `scale_series`, `nice_ticks`,
  `polyline_points`; returns plain dicts/strings consumed by Jinja. No physics.
- `app.py`: adds `POST /simulate`, keeps `GET /` and `POST /calculate` unchanged;
  builds the simulation panel state, catches engine errors, renders one template.
- `templates/index.html`: adds "Simulation" card (analysis mode, source, run
  button, status/provenance, SPICE DC table, analytical comparison, two SVG
  charts) without changing Lab 03 form behaviour.
- `static/style.css`: new result/chart/status styles; existing styles preserved.
- `tests/test_spice_engine.py` (new): netlist content, input validation, parser
  against captured ngspice log samples, error/timeout behaviour.
- `tests/test_simulate_route.py` (new): Flask client test with a stubbed engine
  (no ngspice needed in CI) covering success, invalid input, engine failure.
- `docs/validation.md`: Lab 04 B1–B8 table + ngspice version/model + method.
- `README.md`: Lab 04 scope, ngspice install, run steps, reproducibility.

### Simulation contract

- Netlist nodes: `vcc`, `base`, `col`, `emit`, `in`, `out`, `0`.
- `.op`: `.print op v(base) v(emit) v(col) i(vcc) @rc[i] @re[i]`.
- `.ac`: `dec` sweep 10 Hz → 10 MHz, 20 pts/dec; `.print ac vdb(out) vp(out) vdb(in)`.
  Gain = `vdb(out) - vdb(in)` (dB), phase = `vp(out) - vp(in)` (deg), so the
  reference node is explicit and the report states it.
- `.tran`: `SIN(0 <amp> <freq>)`, stop time = 5 periods (min 1 ms, max 20 ms),
  max step = period/200; `.print tran v(in) v(out)`.
- Every run writes `circuit.cir`, `run.log` in a unique temp directory; the
  directory is removed after parsing (netlist text is returned for provenance).
- Errors are structured: `engine_missing`, `invalid_input`, `timeout`,
  `run_failed`, `parse_failed`, each with a human message.

### UI states

- Idle: simulation card with defaults and "Run simulation".
- Success: status chip `ngspice 47 · 2N3904 · 0.3 s`, DC table, analytical
  comparison (Lab 03 `calculate_dc_bias` with the same divider values, labelled
  as approximation), and only the chart for the selected analysis.
- Error: red panel with the message and no chart; previous results are not reused.

### Verification

- Unit tests for netlist, validation, parsers, route states.
- Real ngspice run for the reference case; compare DC against `dc_bias.py`
  within a stated tolerance and record both.
- Playwright MCP B1–B8 on the running app; screenshots for B5/B8; record
  PASS/FAIL/NOT RUN with observed values in `docs/validation.md`.
- Impeccable critique/polish limited to UI files after functional verification.
