from flask import Flask, render_template, request

from dc_bias import (
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
    validate_mode_inputs,
)

app = Flask(__name__)

MODES = ("divider", "fixed", "emitter")
MODE_LABELS = {
    "divider": "Voltage Divider Bias / ไบอัสแบบแบ่งแรงดัน",
    "fixed": "Fixed Bias / ไบอัสแบบคงที่",
    "emitter": "Emitter Bias / ไบอัสแบบมีตัวต้านทานอีมิเตอร์",
}

RESISTOR_UNIT_MULTIPLIERS = {
    "ohm": 1.0,
    "Ω": 1.0,
    "kohm": 1000.0,
    "kΩ": 1000.0,
    "k": 1000.0,
    "mohm": 1_000_000.0,
    "MΩ": 1_000_000.0,
    "M": 1_000_000.0,
}

DEFAULT_INPUTS = {
    "vcc": "12",
    "r1": "100",
    "r1_unit": "kΩ",
    "r2": "22",
    "r2_unit": "kΩ",
    "rb": "1",
    "rb_unit": "MΩ",
    "rc": "2.2",
    "rc_unit": "kΩ",
    "re": "1",
    "re_unit": "kΩ",
    "beta": "100",
    "vbe": "0.7",
}


def _normalise_mode(raw_mode):
    mode = (raw_mode or "divider").strip().lower()
    return mode if mode in MODES else "divider"


def _parse_form(form):
    return {
        "mode": (form.get("mode", "divider") or "divider").strip().lower(),
        "vcc": form.get("vcc", "").strip(),
        "r1": form.get("r1", "").strip(),
        "r1_unit": form.get("r1_unit", "ohm").strip() or "ohm",
        "r2": form.get("r2", "").strip(),
        "r2_unit": form.get("r2_unit", "ohm").strip() or "ohm",
        "rb": form.get("rb", "").strip(),
        "rb_unit": form.get("rb_unit", "ohm").strip() or "ohm",
        "rc": form.get("rc", "").strip(),
        "rc_unit": form.get("rc_unit", "ohm").strip() or "ohm",
        "re": form.get("re", "").strip(),
        "re_unit": form.get("re_unit", "ohm").strip() or "ohm",
        "beta": form.get("beta", "").strip(),
        "vbe": form.get("vbe", "").strip(),
    }


def _to_si_inputs(raw):
    values = {
        "vcc": raw.get("vcc", ""),
        "beta": raw.get("beta", ""),
        "vbe": raw.get("vbe", ""),
    }
    for r in ("r1", "r2", "rb", "rc", "re"):
        val_str = raw.get(r, "")
        unit = raw.get(f"{r}_unit", "ohm")
        mult = RESISTOR_UNIT_MULTIPLIERS.get(unit, 1.0)
        if val_str == "":
            values[r] = ""
            continue
        try:
            values[r] = float(val_str) * mult
        except (TypeError, ValueError):
            values[r] = val_str
    return values


def _resistor_fields_for_mode(mode):
    if mode == "divider":
        return ("r1", "r2", "rc", "re")
    if mode == "fixed":
        return ("rb", "rc")
    return ("rb", "rc", "re")


def _resistor_unit_errors(raw, mode):
    errors = []
    for r in _resistor_fields_for_mode(mode):
        unit = raw.get(f"{r}_unit", "ohm")
        if unit not in RESISTOR_UNIT_MULTIPLIERS:
            errors.append({
                "field": f"{r}_unit",
                "message": f"Unknown {r.upper()} unit: {unit}.",
            })
    return errors


def _format_results(result):
    if not result:
        return None
    return {
        **result,
        "vb_v": result["vb"],
        "ve_v": result["ve"],
        "vc_v": result["vc"],
        "vce_v": result["vce"],
        "ib_ma": result["ib"] * 1000.0,
        "ic_ma": result["ic"] * 1000.0,
        "ie_ma": result["ie"] * 1000.0,
    }


def _render(inputs, mode, results=None, errors=None, warnings=None, region=None, requested_mode=None):
    return render_template(
        "index.html",
        inputs=inputs,
        mode=mode,
        modes=MODES,
        mode_labels=MODE_LABELS,
        results=results,
        errors=errors or [],
        warnings=warnings or [],
        region=region,
        requested_mode=requested_mode,
    )


def _calculate(clean, mode):
    if mode == "fixed":
        return calculate_fixed_bias(
            clean["vcc"], clean["rb"], clean["rc"], clean["beta"], clean["vbe"]
        )
    if mode == "emitter":
        return calculate_emitter_bias(
            clean["vcc"], clean["rb"], clean["rc"], clean["re"], clean["beta"], clean["vbe"]
        )
    return calculate_dc_bias(
        clean["vcc"], clean["r1"], clean["r2"],
        clean["rc"], clean["re"], clean["beta"], clean["vbe"],
    )


@app.get("/")
def index():
    requested_mode = (request.args.get("mode", "divider") or "divider").strip().lower()
    mode = _normalise_mode(requested_mode)
    if requested_mode not in MODES:
        return _render(
            DEFAULT_INPUTS.copy(),
            mode,
            errors=[{"field": "mode", "message": f"Unknown circuit mode: {requested_mode}."}],
            requested_mode=requested_mode,
        )
    return _render(DEFAULT_INPUTS.copy(), mode)


@app.post("/calculate")
def calculate():
    raw = _parse_form(request.form)
    mode = raw["mode"]
    if mode not in MODES:
        return _render(
            raw,
            _normalise_mode(mode),
            errors=[{"field": "mode", "message": f"Unknown circuit mode: {mode}."}],
            requested_mode=mode,
        )

    unit_errors = _resistor_unit_errors(raw, mode)
    clean, errors = validate_mode_inputs(_to_si_inputs(raw), mode)
    errors = unit_errors + errors
    if errors:
        return _render(raw, mode, errors=errors)

    result = _calculate(clean, mode)
    return _render(
        raw,
        mode,
        results=_format_results(result),
        warnings=result.get("warnings", []),
        region=result.get("region"),
    )


if __name__ == "__main__":
    app.run(debug=True)
