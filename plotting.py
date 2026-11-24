"""Chart geometry for the Lab 04 simulator.

Pure helpers: turn parsed ngspice rows into SVG coordinates and tick labels.
No Flask, no HTML, no circuit physics.
"""

import math

PAD_LEFT = 48
PAD_RIGHT = 18
PAD_TOP = 18
PAD_BOTTOM = 36

GAIN_COLOR = "#07766e"
PHASE_COLOR = "#a65a2c"
VIN_COLOR = "#0c8e83"
VOUT_COLOR = "#c77a35"


def nice_ticks(lo, hi, count=5):
    """Return human-friendly tick values between lo and hi inclusive."""
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        return [lo]
    raw = (hi - lo) / max(count - 1, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = magnitude
    for multiplier in (1, 2, 2.5, 5, 10):
        if raw <= multiplier * magnitude:
            step = multiplier * magnitude
            break
    start = math.ceil(lo / step - 1e-9) * step
    ticks = []
    value = start
    while value <= hi + step * 1e-9:
        ticks.append(round(value, 12))
        value += step
    return ticks or [lo]


def _scale(value, lo, hi, out_lo, out_hi):
    if hi == lo:
        return (out_lo + out_hi) / 2.0
    return out_lo + (value - lo) * (out_hi - out_lo) / (hi - lo)


def _padded_range(values, fraction=0.06):
    lo = min(values)
    hi = max(values)
    if lo == hi:
        delta = abs(lo) * 0.1 or 1.0
        return lo - delta, hi + delta
    pad = (hi - lo) * fraction
    return lo - pad, hi + pad


def _points(pairs):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in pairs)


def _frequency_label(value):
    if value >= 1e6:
        return f"{value / 1e6:g} MHz"
    if value >= 1e3:
        return f"{value / 1e3:g} kHz"
    return f"{value:g} Hz"


def _number_label(value):
    return f"{value:g}"


def _axis_ticks(ticks, lo, hi, out_lo, out_hi, formatter):
    return [
        {
            "pos": round(_scale(tick, lo, hi, out_lo, out_hi), 2),
            "label": formatter(tick),
        }
        for tick in ticks
    ]


def _empty_chart(width, height, x_label):
    return {
        "empty": True,
        "width": width,
        "height": height,
        "x_label": x_label,
        "x_ticks": [],
        "series": [],
    }


def prepare_bode(rows, width=720, height=280):
    """Scale AC rows into gain and phase series on a log frequency axis."""
    if not rows:
        return _empty_chart(width, height, "Frequency (Hz)")

    plot_left = PAD_LEFT
    plot_right = width - PAD_RIGHT
    plot_top = PAD_TOP
    plot_bottom = height - PAD_BOTTOM

    frequencies = [max(row["frequency_hz"], 1e-9) for row in rows]
    log_values = [math.log10(value) for value in frequencies]
    x_lo, x_hi = min(log_values), max(log_values)
    if x_lo == x_hi:
        x_lo -= 0.5
        x_hi += 0.5

    x_ticks = _axis_ticks(
        nice_ticks(x_lo, x_hi, 5),
        x_lo,
        x_hi,
        plot_left,
        plot_right,
        lambda tick: _frequency_label(10 ** tick),
    )

    def make_series(name, key, color, y_label):
        values = [row[key] for row in rows]
        y_lo, y_hi = _padded_range(values)
        pairs = [
            (
                _scale(log_value, x_lo, x_hi, plot_left, plot_right),
                _scale(value, y_lo, y_hi, plot_bottom, plot_top),
            )
            for log_value, value in zip(log_values, values)
        ]
        return {
            "name": name,
            "unit": y_label,
            "color": color,
            "points": _points(pairs),
            "y_ticks": _axis_ticks(
                nice_ticks(y_lo, y_hi, 5),
                y_lo,
                y_hi,
                plot_bottom,
                plot_top,
                _number_label,
            ),
        }

    return {
        "empty": False,
        "width": width,
        "height": height,
        "x_label": "Frequency (Hz)",
        "x_ticks": x_ticks,
        "series": [
            make_series("Gain", "gain_db", GAIN_COLOR, "dB"),
            make_series("Phase", "phase_deg", PHASE_COLOR, "deg"),
        ],
    }


def prepare_tran(rows, width=720, height=280):
    """Scale transient rows into Vin/Vout waveforms on a millisecond axis."""
    if not rows:
        return _empty_chart(width, height, "Time (ms)")

    plot_left = PAD_LEFT
    plot_right = width - PAD_RIGHT
    plot_top = PAD_TOP
    plot_bottom = height - PAD_BOTTOM

    times_ms = [row["time_s"] * 1000.0 for row in rows]
    x_lo, x_hi = min(times_ms), max(times_ms)
    if x_lo == x_hi:
        x_hi = x_lo + 1.0

    peak = max(
        max(abs(row["vin_v"]) for row in rows),
        max(abs(row["vout_v"]) for row in rows),
    )
    factor = 1.0 if peak >= 1.0 else 1000.0
    unit = "V" if factor == 1.0 else "mV"

    scaled = {
        "Vin": [row["vin_v"] * factor for row in rows],
        "Vout": [row["vout_v"] * factor for row in rows],
    }
    y_lo, y_hi = _padded_range(scaled["Vin"] + scaled["Vout"])
    y_ticks = _axis_ticks(
        nice_ticks(y_lo, y_hi, 5),
        y_lo,
        y_hi,
        plot_bottom,
        plot_top,
        _number_label,
    )
    x_ticks = _axis_ticks(
        nice_ticks(x_lo, x_hi, 6),
        x_lo,
        x_hi,
        plot_left,
        plot_right,
        _number_label,
    )

    series = []
    for name, color in (("Vin", VIN_COLOR), ("Vout", VOUT_COLOR)):
        pairs = [
            (
                _scale(time, x_lo, x_hi, plot_left, plot_right),
                _scale(value, y_lo, y_hi, plot_bottom, plot_top),
            )
            for time, value in zip(times_ms, scaled[name])
        ]
        series.append({
            "name": name,
            "unit": unit,
            "color": color,
            "points": _points(pairs),
            "y_ticks": y_ticks,
        })

    return {
        "empty": False,
        "width": width,
        "height": height,
        "x_label": "Time (ms)",
        "x_ticks": x_ticks,
        "series": series,
    }
