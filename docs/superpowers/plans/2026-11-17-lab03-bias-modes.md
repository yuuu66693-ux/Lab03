# Lab 03 BJT Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add Fixed Bias and single-supply Emitter Bias to the existing Flask app while preserving the Lab 02 Divider result.
**Architecture:** Pure equations and mode-aware validation stay in `dc_bias.py`; `app.py` parses units, rejects unknown modes, dispatches with `if/elif`; Jinja renders only the active mode's fields.
**Tech Stack:** Python 3.12, Flask 3.1, Jinja, unittest, Playwright MCP.
**Spec:** `docs/superpowers/specs/2026-11-17-lab03-bias-modes-design.md`

## Global Constraints
- Divider output for `VCC=12, R1=100kΩ, R2=22kΩ, RC=2.2kΩ, RE=1kΩ, β=100, VBE=0.7` must stay `IC=1.230 mA`, `VCE=8.052 V`.
- Result dict keys stay `vb, ve, vc, vce, ib, ic, ie, region, warnings`; view adds `*_v`/`*_ma` keys.
- Resistances are converted from form units to Ω once in `app.py`; calculation functions receive Ω, V, dimensionless β.
- Unknown mode must be an error, never a fallback to Divider. Invalid input must clear previous results.
- No new unittest files; browser validation uses the student-provided A1–A5 table.

## Review Focus
- `mode=unknown` → clear error, no calculation.
- Fixed Bias with `RB=0` → validation error, no stale results.
- Emitter Bias with `RE` omitted → error, while Divider still requires `R1`/`R2`.
- `IB ≤ 0` or `VCE ≤ 0.2 V` → warning/region, not a crash.
- Unit conversion `1 MΩ = 1,000 kΩ = 1,000,000 Ω` applied exactly once.

---

### Task 1: Engineering functions and validation
**Files:** Modify `dc_bias.py`
**Interfaces:** Produces `calculate_fixed_bias(vcc, rb, rc, beta, vbe)`, `calculate_emitter_bias(vcc, rb, rc, re, beta, vbe)`, `validate_mode_inputs(values, mode) -> (clean|None, errors)`.
- [x] Add both functions using the lab equations; return the same dict shape as `calculate_dc_bias`, including region/warning checks.
- [x] Add mode-aware validation: fixed → `vcc, rb, rc, beta, vbe`; emitter → `vcc, rb, rc, re, beta, vbe`; divider → delegate to `validate_dc_inputs`.
- [x] Verify with the venv Python by importing the module and checking A2/A3/A4 expected values: A2 `IC=1.130 mA, VCE=9.514 V`; A3 `IC≈1.026 mA, VCE≈8.705 V`; A4 `IC≈0.940 mA, VCE≈8.033 V`.

### Task 2: Flask mode dispatch and form
**Files:** Modify `app.py`, `templates/index.html`
**Interfaces:** Consumes Task 1 functions; produces `mode` template variable and hidden form field.
- [x] Add `rb`/`rb_unit` and `mode` to parsing/unit conversion/defaults; accept `GET /?mode=...` to reload the form.
- [x] In `POST /calculate`, reject unknown mode, validate mode-specific inputs, dispatch with `if/elif`, keep `_format_results`.
- [x] Render a mode selector (GET form with select + submit button, no JS), hide unused resistor fields, show mode in headings/errors.
- [x] Run all 8 existing tests and confirm A1 unchanged; restart/keep Flask on port 5000.

### Task 3: Browser acceptance and submission docs
**Files:** Create `docs/lab03-validation.md`; modify `README.md`
- [x] Compute/record independent expected values and run A1–A5 through Playwright MCP, recording method/observed values/status.
- [x] Update README with mode selection, run commands, and note the AI-generated vs student-checked parts.
- [x] `git diff --staged`, commit, push; record commit SHA.
