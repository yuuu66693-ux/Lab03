# Lab 04 — BJT CE Amplifier Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Lab 03 Flask BJT bias app with real ngspice DC, AC, and transient simulation of one reference common-emitter voltage-divider amplifier, shown as engineering values and server-rendered SVG charts.

**Architecture:** A pure `spice_engine.py` adapter builds a netlist, runs `ngspice_con -b -o run.log`, and parses the `.print` text tables into rows. `plotting.py` turns rows into SVG geometry. `app.py` adds one `/simulate` route; Jinja renders values and charts. Lab 03 analytical paths stay untouched.

**Tech Stack:** Python 3.10, Flask 3, Jinja, ngspice 47 (external), unittest, server-rendered SVG.

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-ce-simulator-design.md`

## Global Constraints

- Preserve `GET /`, `POST /calculate`, all three Lab 03 modes, and the existing 8 tests unchanged.
- `dc_bias.py`: no Flask/HTML. `app.py`: no circuit equations. Templates: no physics.
- ngspice is called as `[exe, "-b", "-o", log, netlist]`, `shell=False`, `timeout=20`, unique temp dir per run.
- Engine resolution order: `NGSPICE_BIN`, `ngspice_con` on PATH, `ngspice` on PATH. On Windows prefer `ngspice_con` (the GUI `ngspice.exe` blocks).
- Reference values: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, Cin = Cout = 10 µF, source 10 mV peak, 1 kHz.
- Model: generic 2N3904 card (`IS=6.734f BF=416.4 VAF=74.03 ...`), stated in the UI and docs.
- AC: `.ac dec 20 10 10meg`, reference node `in`, gain = `vdb(out)-vdb(in)`, phase = `(vp(out)-vp(in))` converted from radians to degrees and wrapped to ±180°.
- Transient: stop = 5 periods clamped to [1 ms, 20 ms], step = period/200, minimum 5 µs.
- Errors never leave an old chart visible beside a success status.
- No new Python runtime dependency.

## Review Focus

- Engine missing or not executable → clear error, no crash, no stale chart.
- ngspice prints paginated tables (header repeats, index continues) → parser must merge pages, not truncate.
- `vp()` is radians in this build → phase must be converted, not labelled as degrees raw.
- `RE = 0`, negative/zero frequency, or non-numeric input → validation error before any netlist is written.
- ngspice exits 0 but produces no parseable table (e.g. singular matrix) → `parse_failed`, not success.

---

### Task 1: Engine discovery and input validation

**Files:**
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `MODEL_NAME`, `MODEL_CARD`, `DEFAULT_PARAMS: dict`, `find_engine() -> str | None`, `engine_info() -> dict`, `validate_sim_inputs(values: dict) -> tuple[dict | None, list[dict]]`.

- [ ] **Step 1: Write failing tests** for `validate_sim_inputs` (valid reference set returns SI floats: `r1 == 100000.0`, `cin_f == 10e-6`, `amp_v == 0.01`; `re == 0` returns error with `field == "re"`; `freq_hz = -1` errors; `amp_mv = "abc"` errors; missing `rl` errors) and for `find_engine` returning `None` when `NGSPICE_BIN` is unset and PATH lookups fail (patch `shutil.which`).
- [ ] **Step 2: Run** `python -m unittest tests.test_spice_engine -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `spice_engine.py` with the constants above, SI conversion (`kΩ` handled in `app.py`, engine takes SI only), and field labels matching the UI.
- [ ] **Step 4: Run tests** → PASS. Commit `feat: add spice engine input validation`.

### Task 2: Netlist builder

**Files:** Modify `spice_engine.py`; Test `tests/test_spice_engine.py`.

**Interfaces:** Produces `build_netlist(params: dict, analysis: str) -> str`; `analysis in {"dc","ac","tran"}`.

- [ ] **Step 1: Failing tests** asserting the netlist contains `VCC vcc 0 12`, `R1 vcc base 100000`, `Q1 col base emit Q2N3904`, `CIN in base 1e-05`, `RL out 0 10000`, `.model Q2N3904 NPN`, and exactly one of `.op` + `.print op`, `.ac dec 20 10 10meg` + `.print ac vdb(out) vp(out) vdb(in) vp(in)`, `.tran` + `.print tran v(in) v(out)`; unknown analysis raises `ValueError`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** with `VIN in 0 DC 0 AC 1 SIN(0 {amp} {freq})` so one source serves all analyses.
- [ ] **Step 4: Run** → PASS. Commit `feat: build CE reference netlist`.

### Task 3: Print-table parsing

**Files:** Modify `spice_engine.py`; Test `tests/test_spice_engine.py`.

**Interfaces:** Produces `parse_print_tables(log: str) -> list[dict]`, `parse_op(log) -> dict` (`vb, ve, vc, vce, ic, ib, ie`), `parse_ac(log) -> list[dict]` (`frequency_hz, gain_db, phase_deg`), `parse_tran(log) -> list[dict]` (`time_s, vin_v, vout_v`).

- [ ] **Step 1: Failing tests** using verbatim log excerpts captured from ngspice 47: paginated AC (two vectors tables, 3 pages, index continues), paginated transient (index continues across pages), op with two tables merged on index 0; assert `phase_deg` for `vp = -3.13931` is about `-179.87`, gain subtracts `vdb(in)`, and a log with no table raises `ValueError`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** a header-driven parser: header `Index ...` sets columns, dashed line skipped, numeric rows appended, pages merged by index. Convert and wrap phase; compute `vce = vc - ve`.
- [ ] **Step 4: Run** → PASS. Commit `feat: parse ngspice print tables`.

### Task 4: Run adapter

**Files:** Modify `spice_engine.py`; Test `tests/test_spice_engine.py`.

**Interfaces:** Produces `run_analysis(params: dict, analysis: str, timeout: float = 20.0) -> dict` with keys `ok, analysis, rows, engine, netlist, log, duration_s, error`.

- [ ] **Step 1: Failing tests**: patched `find_engine` → `None` gives `ok=False, error["kind"]=="engine_missing"`; patched `subprocess.run` raising `TimeoutExpired` gives `timeout`; returncode 1 gives `run_failed`; returncode 0 with unparseable log gives `parse_failed`; success path passes `shell=False`, list args, and the temp dir is removed afterwards.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** with `tempfile.mkdtemp`, `subprocess.run(..., capture_output=True, text=True, timeout=timeout, shell=False)`, read `run.log`, `shutil.rmtree` in `finally`.
- [ ] **Step 4: Run** → PASS. Commit `feat: run ngspice batch analyses`.

### Task 5: Chart geometry

**Files:** Create `plotting.py`; Test `tests/test_plotting.py`.

**Interfaces:** Produces `nice_ticks(lo, hi, count=5) -> list[float]`, `prepare_bode(rows, width=720, height=280) -> dict`, `prepare_tran(rows, width=720, height=280) -> dict`. Each returns `{"series": [{"name","color","points"}], "x_ticks": [{"pos","label"}], "y_ticks": [...], "x_label", "y_label", "empty": bool}` with coordinates already inside the SVG viewBox.

- [ ] **Step 1: Failing tests**: monotonic ticks inside range; `prepare_bode` with 3 rows yields two series (gain, phase) and non-empty points; log-frequency x positions are monotonic; empty rows set `empty=True` and no points.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** pure geometry (log10 for Bode x, linear for transient; clamp y with 5% padding).
- [ ] **Step 4: Run** → PASS. Commit `feat: add SVG chart geometry helpers`.

### Task 6: `/simulate` route and simulation panel

**Files:** Modify `app.py`, `templates/index.html`, `static/style.css`; Test `tests/test_simulate_route.py`.

**Interfaces:** Consumes `validate_sim_inputs`, `run_analysis`, `parse_*`, `prepare_bode`, `prepare_tran`, `calculate_dc_bias`. Produces `POST /simulate` and template context `sim` (params, result, chart, analytical, error, engine).

- [ ] **Step 1: Failing route tests** with patched `run_analysis`: success renders values `VB`, `VE`, `VC`, `VCE`, `IC`, `ngspice`, `2N3904`; `RE=0` renders an error and no chart; engine failure renders the error and no `Success`; Lab 03 `POST /calculate` still returns 200 with the reference values.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** form parsing with the existing unit multipliers, run only when validation passes, compute analytical comparison from `calculate_dc_bias` for the same divider values, render.
- [ ] **Step 4: Run** → PASS. Commit `feat: add simulation route and panel`.

### Task 7: Live verification and documentation

**Files:** Modify `README.md`, `docs/validation.md`, `requirements.txt` (comment only if needed), `.gitignore` (temp run dirs if any); create `docs/captures/` entries only for screenshots.

- [ ] **Step 1: Run the real reference case** through the app (or `run_analysis`) and record ngspice version, model, DC table, AC gain at 1 kHz, transient amplitudes.
- [ ] **Step 2: Compare** SPICE DC against `dc_bias.calculate_dc_bias` and record both plus the model-assumption note.
- [ ] **Step 3: Playwright MCP B1–B8** on the running server; save screenshots for B5 and B8; record PASS/FAIL/NOT RUN with observed values.
- [ ] **Step 4: Impeccable** critique/polish limited to `templates/index.html` and `static/style.css`; re-run tests and one browser case after.
- [ ] **Step 5: Update README** with ngspice install (Windows `ngspice_con.exe`, `NGSPICE_BIN`), run steps, scope, AI/student check.
- [ ] **Step 6: Commit and push**, record commit SHA in README.

## Self-Review

- Spec coverage: engine + 3 analyses (Tasks 1–4), charts (5), route/UI (6), provenance/error states (4, 6), docs and acceptance (7). Lab 03 preservation is asserted in Task 6.
- Types: `run_analysis` returns `rows` only on success; `parse_*` are pure string→data; `prepare_*` never touch Flask.
- Review Focus: each item has a test in Tasks 1, 3, 4, 6.
