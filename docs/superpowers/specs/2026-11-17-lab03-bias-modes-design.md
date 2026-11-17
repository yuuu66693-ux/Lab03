# Lab 03 — BJT Bias Mode Selection Design

**Intent:** Extend the Lab 02 Flask app so one web form can calculate Fixed Bias, Emitter Bias (single supply), and the existing Voltage Divider Bias, with mode-specific input validation and browser-verifiable results.

**Goals:** three modes; preserve Divider output exactly; equations only in `dc_bias.py`; consistent result dict keys/units; invalid input shows a clear error and never reuses a previous result; browser check A1–A5.
**Non-goals:** AC/transient/SPICE, new unittest files, new web framework, changing Divider math.
**Constraints:** Flask + Jinja; SI units inside Python (Ω, A, V); form uses kΩ/MΩ; β and VBE shared; Forward-Active warning when IB ≤ 0 or VCE ≤ 0.2 V.

**Approaches:**
1. **Mode dispatch in the existing Flask route + three pure functions in `dc_bias.py` (chosen).** Smallest diff, reuses the existing form/results/validation pipeline, keeps the architecture rules in `AGENTS.md`.
2. Separate Flask routes per mode. Rejected: duplicates parsing/rendering and breaks the single-form requirement.
3. One generic function with mode branch inside. Rejected: lab requires separate functions and makes student verification harder.

**Design:** add `calculate_fixed_bias(vcc, rb, rc, beta, vbe)` and `calculate_emitter_bias(vcc, rb, rc, re, beta, vbe)` returning the same dict shape as `calculate_dc_bias`; add `validate_mode_inputs(values, mode)` selecting only the required fields; `app.py` reads `mode`, accepts `divider|fixed|emitter`, rejects unknown modes, converts resistor units once, dispatches with `if/elif`, renders only the fields used by the selected mode; selector is a GET form (`/?mode=...`) so no JavaScript is needed. `docs/lab03-validation.md` records the independent expected values and A1–A5 browser observations.
