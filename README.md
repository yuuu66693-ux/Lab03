# Lab 03 — BJT DC Bias Web App (Divider / Fixed / Emitter)

Flask web application for ENG29 2121 (Computer Programming for Electrical Engineers), Week 3.  
It extends the Lab 02 voltage-divider calculator with **Fixed Bias** and **single-supply Emitter Bias**. All circuit equations remain in the Python backend; the browser is only form + results.

## Scope
- DC bias analysis only (Forward-Active approximation, constant `β` and constant `VBE`)
- Modes selectable from a dropdown (GET reload, no JavaScript):
  - **Divider**: inputs `VCC, R1, R2, RC, RE, β, VBE` (Lab 02 behaviour preserved)
  - **Fixed**: inputs `VCC, RB, RC, β, VBE` (no `RE`)
  - **Emitter**: inputs `VCC, RB, RC, RE, β, VBE`
- Outputs: `VB, VE, VC, VCE, IC` (and `IB, IE`) with Operating Region and warnings
- No AC/transient/signal generator/SPICE in this lab

## Project structure
```
eng29-2121-git-lab01/
├── app.py                     # Flask routes, mode dispatch, unit conversion (no equations)
├── dc_bias.py                 # Engineering calculations + mode-aware validation (no HTML/HTTP)
├── templates/index.html       # Jinja form + results (no physics formulas)
├── static/style.css           # UI styling
├── tests/
│   ├── test_dc_bias.py        # Lab 02 engineering tests
│   └── test_web.py            # Lab 02 Flask HTTP tests
├── docs/
│   ├── design-note.md
│   ├── validation.md          # Lab 02 validation
│   ├── lab03-validation.md    # Lab 03 A1–A5 browser acceptance
│   ├── reflection.md
│   └── superpowers/           # Lab 03 design + implementation plan
├── opencode.json              # Playwright MCP config for OpenCode V2
├── requirements.txt
├── AGENTS.md
└── README.md
```

## Setup
From the project directory:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
```

`.venv/`, `.env` and credentials are not committed.

## Run
```bash
python -m flask --app app run --debug
```
Open: <http://127.0.0.1:5000/>

Do **not** open `templates/index.html` via `file://` — calculation is performed by the Flask/Python backend.

## Use
1. Choose **Voltage Divider Bias**, **Fixed Bias**, or **Emitter Bias** from the Circuit Mode dropdown.
2. Click **Load mode / เปลี่ยนโหมด** to reload only the fields used by that mode.
3. Enter values using the unit shown next to each field (`Ω`, `kΩ`, `MΩ`, `V`).
4. Click **Calculate DC Bias / คำนวณจุดทำงาน DC**.

Unit conversion happens once in `app.py::_to_si_inputs`: `1 MΩ = 1,000 kΩ = 1,000,000 Ω`. Unknown modes and invalid values produce a visible error and never reuse a previous result.

## Tests
```bash
python -m unittest discover -s tests -v
```
Expected: `Ran 8 tests ... OK` (the Lab 02 tests were kept unchanged; no new unittest files were added for Lab 03).

Additional engineering checks used during Lab 03 TDD lived outside the repository, so they are not part of the submission. Browser acceptance A1–A5 is recorded in `docs/lab03-validation.md`.

## Engineering assumptions & limitations
- Model: NPN BJT, Forward-Active approximation with constant `β` and constant `VBE`.
- If `IB <= 0` or `VCE <= 0.2 V`, the app reports cutoff/saturation warnings and results must not be treated as trustworthy DC bias predictions.
- This is not a SPICE/ngspice simulation.
- The SVG circuit-diagram panel is decorative and still shows the Lab 2 divider illustration; the mode-aware form, results and validation are authoritative.

## Reference cases (independent calculation)
Shared: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`.

| Mode | Extra inputs | Expected IC | Expected VCE |
|---|---|---:|---:|
| Divider | `R1=100 kΩ, R2=22 kΩ, RE=1 kΩ` | `1.230 mA` | `8.052 V` |
| Fixed | `RB=1 MΩ` | `1.130 mA` | `9.514 V` |
| Emitter | `RB=1 MΩ, RE=1 kΩ` | `1.026 mA` | `8.705 V` |
| Emitter | `RB=1 MΩ, RE=2 kΩ` | `0.940 mA` | `8.033 V` |

See `docs/validation.md` and `docs/lab03-validation.md` for full comparisons and browser evidence.

## AI assistance and student check
AI generated the Lab 03 functions, mode dispatch, form changes, design/plan notes and this README. The browser table in `docs/lab03-validation.md` records values actually observed with Playwright MCP. Before submission, the student must independently recalculate at least one new-mode case from the equations and repeat at least one browser case personally.

## Submission
GitHub repository: <https://github.com/yuuu66693-ux/Lab03>  
Branch: `main`  
Commit SHA: `3f6cdfc6197ba116762a3c200821257198a1e4fd`
