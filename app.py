from flask import Flask, render_template, request

from dc_bias import (
    calculate_dc_bias,
    calculate_emitter_bias,
    calculate_fixed_bias,
    validate_mode_inputs,
)
from plotting import prepare_bode, prepare_tran
from spice_engine import (
    MODEL_NAME,
    engine_info,
    run_analysis,
    validate_sim_inputs,
)

app = Flask(__name__)

MODES = ("divider", "fixed", "emitter")
MODE_LABELS = {
    "divider": "Voltage Divider Bias / ไบอัสแบบแบ่งแรงดัน",
    "fixed": "Fixed Bias / ไบอัสแบบคงที่",
    "emitter": "Emitter Bias / ไบอัสแบบมีตัวต้านทานอีมิเตอร์",
}

SIM_MODES = ("dc", "ac", "tran")
SIM_LABELS = {
    "dc": "DC operating point (.op)",
    "ac": "AC frequency response (.ac)",
    "tran": "Transient waveform (.tran)",
}
SIM_RESISTOR_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rl")
SIM_ANALYTICAL_BETA = 100.0
SIM_ANALYTICAL_VBE = 0.7

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

SIM_DEFAULTS = {
    "analysis": "dc",
    "sim_vcc": "12",
    "sim_r1": "100",
    "sim_r1_unit": "kΩ",
    "sim_r2": "22",
    "sim_r2_unit": "kΩ",
    "sim_rc": "2.2",
    "sim_rc_unit": "kΩ",
    "sim_re": "1",
    "sim_re_unit": "kΩ",
    "sim_rl": "10",
    "sim_rl_unit": "kΩ",
    "sim_cin": "10",
    "sim_cout": "10",
    "sim_amp": "10",
    "sim_freq": "1000",
}


def _sim_context(inputs=None, analysis="dc", result=None, chart=None,
                 comparison=None, summary=None, errors=None):
    return {
        "inputs": inputs or dict(SIM_DEFAULTS),
        "analysis": analysis,
        "modes": SIM_MODES,
        "labels": SIM_LABELS,
        "engine": engine_info(),
        "model": MODEL_NAME,
        "result": result,
        "chart": chart,
        "comparison": comparison,
        "summary": summary,
        "errors": errors or [],
    }


def _parse_sim_form(form):
    data = {"analysis": (form.get("analysis", "dc") or "dc").strip().lower()}
    data["sim_vcc"] = form.get("sim_vcc", "").strip()
    for key in ("r1", "r2", "rc", "re", "rl"):
        data[f"sim_{key}"] = form.get(f"sim_{key}", "").strip()
        data[f"sim_{key}_unit"] = form.get(f"sim_{key}_unit", "kΩ").strip() or "kΩ"
    for key in ("cin", "cout", "amp", "freq"):
        data[f"sim_{key}"] = form.get(f"sim_{key}", "").strip()
    return data


def _sim_si_values(raw):
    values = {}
    errors = []
    try:
        values["vcc"] = float(raw.get("sim_vcc", ""))
    except (TypeError, ValueError):
        values["vcc"] = raw.get("sim_vcc", "")
    for key in ("r1", "r2", "rc", "re", "rl"):
        unit = raw.get(f"sim_{key}_unit", "kΩ")
        multiplier = RESISTOR_UNIT_MULTIPLIERS.get(unit)
        text = raw.get(f"sim_{key}", "")
        if multiplier is None:
            errors.append({
                "field": f"sim_{key}_unit",
                "message": f"Unknown unit for {key.upper()}: {unit}.",
            })
            values[key] = text
            continue
        try:
            values[key] = float(text) * multiplier
        except (TypeError, ValueError):
            values[key] = text
    for target, source, scale in (
        ("cin_f", "sim_cin", 1e-6),
        ("cout_f", "sim_cout", 1e-6),
        ("amp_v", "sim_amp", 1e-3),
        ("freq_hz", "sim_freq", 1.0),
    ):
        text = raw.get(source, "")
        try:
            values[target] = float(text) * scale
        except (TypeError, ValueError):
            values[target] = text
    return values, errors


def _comparison_view(rows, analytical):
    pairs = (
        ("VB", "vb", 1.0, "V"),
        ("VE", "ve", 1.0, "V"),
        ("VC", "vc", 1.0, "V"),
        ("VCE", "vce", 1.0, "V"),
        ("IC", "ic", 1000.0, "mA"),
    )
    return [
        {
            "label": label,
            "spice": f"{rows[key] * scale:.3f}",
            "analytical": f"{analytical[key] * scale:.3f}",
            "unit": unit,
        }
        for label, key, scale, unit in pairs
    ]


def _sim_summary(analysis, rows):
    if analysis == "ac":
        nearest = min(rows, key=lambda row: abs(row["frequency_hz"] - 1000.0))
        return {
            "title": "AC response at 1 kHz",
            "items": [
                {"label": "Frequency", "value": f"{nearest['frequency_hz']:.0f}", "unit": "Hz"},
                {"label": "Gain |Vout/Vin|", "value": f"{nearest['gain_db']:.2f}", "unit": "dB"},
                {"label": "Phase", "value": f"{nearest['phase_deg']:.1f}", "unit": "deg"},
            ],
        }
    if analysis == "tran":
        vin_peak = max(abs(row["vin_v"]) for row in rows)
        vout_peak = max(abs(row["vout_v"]) for row in rows)
        gain = vout_peak / vin_peak if vin_peak else 0.0
        return {
            "title": "Transient amplitudes",
            "items": [
                {"label": "Vin peak", "value": f"{vin_peak * 1000:.2f}", "unit": "mV"},
                {"label": "Vout peak", "value": f"{vout_peak * 1000:.2f}", "unit": "mV"},
                {"label": "|Vout/Vin|", "value": f"{gain:.3f}", "unit": "V/V"},
            ],
        }
    return None


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


def _render(inputs, mode, results=None, errors=None, warnings=None, region=None,
            requested_mode=None, sim=None):
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
        sim=sim or _sim_context(),
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


@app.post("/simulate")
def simulate():
    raw = _parse_sim_form(request.form)
    analysis = raw["analysis"]
    if analysis not in SIM_MODES:
        return _render(
            DEFAULT_INPUTS.copy(),
            "divider",
            sim=_sim_context(
                inputs=raw,
                errors=[{
                    "field": "analysis",
                    "message": f"Unknown analysis mode: {analysis}.",
                }],
            ),
        )

    values, unit_errors = _sim_si_values(raw)
    clean, errors = validate_sim_inputs(values)
    errors = unit_errors + errors
    if errors:
        return _render(
            DEFAULT_INPUTS.copy(),
            "divider",
            sim=_sim_context(inputs=raw, analysis=analysis, errors=errors),
        )

    result = run_analysis(clean, analysis)
    if not result["ok"]:
        return _render(
            DEFAULT_INPUTS.copy(),
            "divider",
            sim=_sim_context(
                inputs=raw,
                analysis=analysis,
                result=result,
                errors=[{
                    "field": "engine",
                    "message": result["error"]["message"],
                }],
            ),
        )

    chart = None
    if analysis == "ac":
        chart = prepare_bode(result["rows"])
    elif analysis == "tran":
        chart = prepare_tran(result["rows"])

    analytical = calculate_dc_bias(
        clean["vcc"], clean["r1"], clean["r2"], clean["rc"], clean["re"],
        SIM_ANALYTICAL_BETA, SIM_ANALYTICAL_VBE,
    )
    comparison = None
    if analysis == "dc":
        comparison = _comparison_view(result["rows"], analytical)

    return _render(
        DEFAULT_INPUTS.copy(),
        "divider",
        sim=_sim_context(
            inputs=raw,
            analysis=analysis,
            result=result,
            chart=chart,
            comparison=comparison,
            summary=_sim_summary(analysis, result["rows"]),
        ),
    )


if __name__ == "__main__":
    app.run(debug=True)
