"""ngspice adapter for the Lab 04 common-emitter amplifier simulator.

Pure adapter: builds a netlist, runs ngspice in batch mode, and parses the
``.print`` tables from the run log. No Flask or HTML dependencies.

The circuit is the single reference CE voltage-divider amplifier from the
Lab 04 handout; values are passed in SI units.
"""

import math
import os
import shutil
import subprocess

MODEL_NAME = "2N3904"
MODEL_CARD = (
    ".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 "
    "ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKC=0 NF=1 NR=1 "
    "RB=0 IRB=0 RBM=0 RE=0 RC=0 CJE=3.638p MJC=.3085 VJC=.75 FC=.5 "
    "CJB=4.493p MJB=.2593 VJB=.75)"
)

DEFAULT_PARAMS = {
    "vcc": 12.0,
    "r1": 100_000.0,
    "r2": 22_000.0,
    "rc": 2_200.0,
    "re": 1_000.0,
    "rl": 10_000.0,
    "cin_f": 10e-6,
    "cout_f": 10e-6,
    "amp_v": 0.01,
    "freq_hz": 1_000.0,
}

SIM_FIELDS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rl": "RL",
    "cin_f": "CIN",
    "cout_f": "COUT",
    "amp_v": "Source amplitude",
    "freq_hz": "Source frequency",
}

ENGINE_NAMES = ("ngspice_con", "ngspice")


def find_engine():
    """Return the ngspice executable path, or None when unavailable.

    Order: ``NGSPICE_BIN``, ``ngspice_con`` on PATH, ``ngspice`` on PATH.
    On Windows the GUI ``ngspice.exe`` blocks waiting for a window, so the
    console build is preferred.
    """
    explicit = os.environ.get("NGSPICE_BIN")
    if explicit and os.path.isfile(explicit):
        return explicit
    for name in ENGINE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def engine_info():
    """Describe the available engine without raising."""
    exe = find_engine()
    if not exe:
        return {
            "available": False,
            "path": None,
            "version": None,
            "message": (
                "ngspice not found. Install ngspice, add ngspice_con to PATH, "
                "or set NGSPICE_BIN to the executable."
            ),
        }
    version = None
    try:
        proc = subprocess.run(
            [exe, "-v"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        for line in (proc.stdout or "").splitlines():
            marker = line.find("ngspice-")
            if marker >= 0:
                version = line[marker:].split()[0]
                break
    except (OSError, subprocess.SubprocessError):
        version = None
    return {
        "available": True,
        "path": exe,
        "version": version,
        "message": "ngspice available",
    }


def _num(value):
    """Format a number for a SPICE netlist without exponent padding noise."""
    return f"{float(value):.10g}"


def _tran_window(freq_hz):
    period = 1.0 / freq_hz
    stop = min(max(5.0 * period, 0.001), 0.020)
    step = max(period / 200.0, 5e-6)
    return step, stop


def build_netlist(params, analysis):
    """Build the reference CE amplifier netlist for one analysis mode."""
    if analysis not in ("dc", "ac", "tran"):
        raise ValueError(f"Unknown analysis: {analysis}")

    lines = [
        "* Lab 04 CE voltage-divider reference amplifier",
        f"VCC vcc 0 {_num(params['vcc'])}",
        f"R1 vcc base {_num(params['r1'])}",
        f"R2 base 0 {_num(params['r2'])}",
        f"RC vcc col {_num(params['rc'])}",
        f"RE emit 0 {_num(params['re'])}",
        "Q1 col base emit Q2N3904",
        f"CIN in base {_num(params['cin_f'])}",
        f"VIN in 0 DC 0 AC 1 SIN(0 {_num(params['amp_v'])} {_num(params['freq_hz'])})",
        f"COUT col out {_num(params['cout_f'])}",
        f"RL out 0 {_num(params['rl'])}",
        MODEL_CARD,
    ]
    if analysis == "dc":
        lines.append(".op")
        lines.append(".print op v(base) v(emit) v(col) i(vcc) @rc[i] @re[i]")
    elif analysis == "ac":
        lines.append(".ac dec 20 10 10meg")
        lines.append(".print ac vdb(out) vp(out) vdb(in) vp(in)")
    else:
        step, stop = _tran_window(params["freq_hz"])
        lines.append(f".tran {_num(step)} {_num(stop)}")
        lines.append(".print tran v(in) v(out)")
    lines.append(".end")
    return "\n".join(lines) + "\n"


def validate_sim_inputs(values):
    """Validate simulator inputs supplied in SI units.

    Returns ``(clean, errors)``; ``clean`` is None when any field is invalid.
    """
    clean = {}
    errors = []
    for key, label in SIM_FIELDS.items():
        raw = values.get(key, "")
        if raw is None or str(raw).strip() == "":
            errors.append({"field": key, "message": f"{label} is required."})
            continue
        try:
            number = float(raw)
        except (TypeError, ValueError):
            errors.append({"field": key, "message": f"{label} must be a number."})
            continue
        if not math.isfinite(number):
            errors.append({"field": key, "message": f"{label} must be a finite number."})
            continue
        if number <= 0:
            errors.append({"field": key, "message": f"{label} must be greater than 0."})
            continue
        clean[key] = number
    if errors:
        return None, errors
    return clean, []
