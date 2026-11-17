# Lab 03 — Browser acceptance (A1–A5)

Date: 2026-11-17  
App URL: <http://127.0.0.1:5000/>  
Browser method: **Playwright MCP** (`browser_navigate`, `browser_snapshot`, `browser_select_option`, `browser_click`, `browser_fill_form`, `browser_find`) using Chrome.  
Tolerance: compared with unrounded independent values; `|ΔIC| <= 0.01 mA`, `|ΔVCE| <= 0.02 V`.

## Independent reference calculation (before comparing with app values)

The following were calculated from the lab equations with a calculator, **not from `dc_bias.py`**.

Shared case values: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`.

- **Fixed bias, A2** (`RB = 1 MΩ`, emitter grounded):
  - `IB = (VCC − VBE)/RB = (12 − 0.7)/1,000,000 = 11.3 µA`
  - `IC = β·IB = 100 × 11.3 µA = 1.130000 mA`
  - `VC = VCC − IC·RC = 12 − (1.13 mA)(2.2 kΩ) = 9.514000 V`
  - `VE = 0 V`, so `VCE = VC − VE = 9.514000 V`
- **Emitter bias, A3/A4** (single supply):
  - `IB = (VCC − VBE)/(RB + (β+1)·RE)`, `IC = β·IB`, `IE = (β+1)·IB`
  - `VE = IE·RE`, `VC = VCC − IC·RC`, `VCE = VC − VE`
  - A3 (`RE = 1 kΩ`): `IC = 1.0263397 mA`, `VCE = 8.7054496 V`
  - A4 (`RE = 2 kΩ`): `IC = 0.9400998 mA`, `VCE = 8.0327787 V`
  - A4 prediction: **IC decreases** from A3 because `RB + (β+1)·RE` increases, reducing `IB` and therefore `IC`.
- **Divider bias, A1** (`R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ`):
  - `VTH = VCC·R2/(R1+R2) = 2.1639344 V`, `RTH = R1∥R2 = 18.0327869 kΩ`
  - `IB = (VTH − VBE)/(RTH + (β+1)·RE)`, `IC = β·IB`
  - `IC = 1.2298581 mA`, `VCE = 8.0521554 V`

## A1–A5 results

| ID | Method | Inputs entered in browser | Expected (unrounded → shown) | Observed in browser (with units) | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 · โหมดเดิม | Playwright MCP | Divider: `VCC=12 V`, `R1=100 kΩ`, `R2=22 kΩ`, `RC=2.2 kΩ`, `RE=1 kΩ`, `β=100`, `VBE=0.70 V` | `IC=1.2298581 mA → 1.230 mA`; `VCE=8.0521554 V → 8.052 V`; Active | `IC 1.230 mA`, `VCE 8.052 V`, `ACTIVE`; heading shows Voltage Divider Bias | **PASS** | Snapshot after `browser_click(Calculate)` showed `rowheader "IC" / cell "1.230 mA"` and `rowheader "VCE" / cell "8.052 V"`. |
| A2 · Fixed | Playwright MCP | Mode changed with dropdown → `fixed`, then `RB=1000000 Ω`, `RC=2200 Ω`, `VCC=12 V`, `β=100`, `VBE=0.70 V`; no `RE` field present | `IC=1.130000 mA`; `VCE=9.514000 V`; `VE=0 V` | `IC 1.130 mA`, `VCE 9.514 V`, `VE 0.000 V`, `ACTIVE`; heading shows Fixed Bias | **PASS** | Snapshot excerpt below. |
| A3 · Emitter | Playwright MCP | Mode changed with dropdown → `emitter`, then `RB=1000000 Ω`, `RE=1000 Ω`, `RC=2200 Ω`, `VCC=12 V`, `β=100`, `VBE=0.70 V` | `IC=1.0263397 mA → 1.026 mA`; `VCE=8.7054496 V → 8.705 V`; `RE` field present and used | `IC 1.026 mA`, `VCE 8.705 V`, `VE 1.037 V`, `ACTIVE` | **PASS** | Snapshot showed `rowheader "IC" / cell "1.026 mA"` and `rowheader "VCE" / cell "8.705 V"` under Emitter Bias heading. |
| A4 · เปลี่ยนค่าเดียว | Playwright MCP | Emitter mode retained; only `RE` changed from `1000 Ω` to `2000 Ω`; all other A3 values unchanged, then Calculate clicked | Prediction: IC decreases; `IC=0.9400998 mA → 0.940 mA`, `VCE=8.0327787 V → 8.033 V` | `IC 0.940 mA` (lower than A3's `1.026 mA`), `VCE 8.033 V`, `ACTIVE` | **PASS** | Snapshot showed `RE 2000 Ω` in the form and `rowheader "IC" / cell "0.940 mA"`. |
| A5 · อินพุตผิด | Playwright MCP | Mode changed to `fixed`; `RB=0`, `VCC=12 V`, `RC=2200 Ω`, `β=100`, `VBE=0.70 V`; Calculate clicked | Visible message asking to correct `RB`; web app must not crash and must not show previous results as this run's result | Alert: `rb: RB must be greater than 0.`; page rendered normally; no `results-table` and no stale `0.940 mA` from A4 | **PASS** | Snapshot excerpt below. Message came from Flask validation (form uses `novalidate`, so native browser validation did not block submission). |

## Evidence snippets from the browser snapshots

A2 result table:

```text
heading "DC Bias Results / ผลลัพธ์จุดทำงาน DC — Fixed Bias / ไบอัสแบบคงที่"
  rowheader "VE"  -> cell "0.000 V"
  rowheader "VCE" -> cell "9.514 V"
  rowheader "IC"  -> cell "1.130 mA"
  generic "Operating Region Status / สถานะการทำงาน" -> "ACTIVE"
```

A5 validation (no result table present):

```text
alert:
  heading "Input Error / ข้อมูลนำเข้าไม่ถูกต้อง (fixed)"
  listitem:
    strong "rb:"
    text "RB must be greater than 0."
```

No program files were edited during A1–A5 reporting; each case was submitted through the real form and its post-submit snapshot was read before judging.

## Code map and responsibility

- AI generated `calculate_fixed_bias`, `calculate_emitter_bias`, `validate_mode_inputs` in `dc_bias.py`; `app.py` mode dispatch/unit conversion; and mode-aware fields/headings in `templates/index.html`.
- Mode selection is `if/elif` in `app.py::_calculate`; resistor conversion (`Ω`, `kΩ`, `MΩ` → Ω) happens once in `app.py::_to_si_inputs` before validation/calculation.
- Student action required before submission: independently recalculate at least A2 or A3 from the equations above and repeat one browser case personally; tick/confirm the observed value in this table if it matches.

## Note

The SVG circuit-diagram panel is mode-aware (fixed after the first A1–A5 round): Divider shows `R1/R2/RE`, Fixed shows `RB` with emitter grounded and no `R1/R2/RE`, Emitter shows `RB/RE` with no `R1/R2`. It is illustrative and does not drive the form or calculation.

## Post-review re-verification

A fresh-context review found that `GET /?mode=<unknown>` silently fell back to Divider. This was fixed (`app.py` now renders a visible error on GET and shows the requested mode in the error heading). Because program code changed after the first A1–A5 round, the affected paths were re-run through Playwright MCP:

- `GET /` → Calculate: `VCE 8.052 V`, `IC 1.230 mA` (A1 unchanged) — **PASS**
- `GET /?mode=bogus`: alert `(bogus)` with `mode: Unknown circuit mode: bogus.`, no calculation — **PASS**
- Fixed mode with `RB=0`: alert `(fixed)` with `rb: RB must be greater than 0.`, no `results-table`, no stale `0.940 mA` — **PASS**

Automated verification after the fix: original suite `Ran 8 tests ... OK`; scratch engineering tests `5/5 OK`; scratch Flask tests `6/6 OK`.

## Diagram and input-system fix (user-reported)

Two root causes were confirmed and fixed before any push:

1. `templates/index.html` rendered one static Lab 2 divider SVG regardless of `mode`; the SVG now branches on `mode` for the base network (`R1/R2` vs `RB`), emitter network (`RE` vs direct ground) and `aria-label`.
2. `app.py::_to_si_inputs` used `RESISTOR_UNIT_MULTIPLIERS.get(unit, 1.0)`, so an unknown unit such as `kOhm` was silently treated as Ω and produced bogus saturation results. `app.py::_resistor_unit_errors` now rejects unknown units for the resistor fields used by the selected mode and shows an input error instead of a result table.

Browser verification after restarting Flask (DOM-level check of `svg.circuit` text and `aria-label`, via the in-app browser):

| Mode | SVG labels observed | Status |
|---|---|---|
| Divider | `R1 100 kΩ`, `R2 22 kΩ`, `RC 2.2 kΩ`, `RE 1 kΩ` | **PASS** |
| Fixed | `RB 1 MΩ`, `RC 2.2 kΩ`, no `R1`/`R2`/`RE` | **PASS** |
| Emitter | `RB 1 MΩ`, `RC 2.2 kΩ`, `RE 1 kΩ`, no `R1`/`R2` | **PASS** |

Input-system cases verified by automated Flask tests (scratch TDD, outside repo): unknown unit `rb_unit=kOhm` → `Unknown RB unit: kOhm.` with no `results-table`; `rb_unit=kΩ` with `RB=1000` converts once to `1.130 mA` / `9.514 V`; `RB=0`, missing `RE`, and unknown mode still show errors with no stale results. Original suite: `Ran 8 tests ... OK`; scratch web suite: `Ran 11 tests ... OK`.
