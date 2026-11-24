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
import tempfile
import time

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


def parse_print_tables(log):
    """Parse every ``.print`` table in an ngspice log.

    ngspice paginates long tables and may print several tables (one per
    vector group); headers repeat and the row index continues. Rows are
    merged on the index so each analysis point is one record.
    """
    tables = []
    current = None
    for raw in (log or "").splitlines():
        line = raw.strip()
        if line.startswith("Index"):
            current = {"columns": line.split()[1:], "rows": {}}
            tables.append(current)
            continue
        if current is None or not line:
            continue
        if set(line) <= {"-"}:
            continue
        parts = line.split()
        if not parts[0].isdigit():
            current = None
            continue
        try:
            index = int(parts[0])
            values = [float(value) for value in parts[1:]]
        except ValueError:
            current = None
            continue
        current["rows"][index] = values

    merged = {}
    for table in tables:
        for index, values in table["rows"].items():
            record = merged.setdefault(index, {})
            for column, value in zip(table["columns"], values):
                record[column] = value
    if not merged:
        raise ValueError("No ngspice print tables found in the run log.")
    return [merged[index] for index in sorted(merged)]


def _require(row, key):
    if key not in row:
        raise ValueError(f"Expected column {key!r} in the ngspice output.")
    return row[key]


def parse_op(log):
    """Return the DC operating point from a ``.print op`` table."""
    row = parse_print_tables(log)[0]
    vb = _require(row, "v(base)")
    ve = _require(row, "v(emit)")
    vc = _require(row, "v(col)")
    ic = _require(row, "@rc[i]")
    ie = _require(row, "@re[i]")
    return {
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "vce": vc - ve,
        "ic": ic,
        "ie": ie,
        "ib": ie - ic,
    }


def _wrap_degrees(angle):
    return ((angle + 180.0) % 360.0) - 180.0


def parse_ac(log):
    """Return frequency, gain in dB, and phase in degrees from ``.print ac``."""
    rows = []
    for row in parse_print_tables(log):
        gain_db = _require(row, "vdb(out)") - row.get("vdb(in)", 0.0)
        phase_deg = math.degrees(_require(row, "vp(out)") - row.get("vp(in)", 0.0))
        rows.append({
            "frequency_hz": _require(row, "frequency"),
            "gain_db": gain_db,
            "phase_deg": _wrap_degrees(phase_deg),
        })
    return rows


def parse_tran(log):
    """Return time, input, and output waveforms from ``.print tran``."""
    return [
        {
            "time_s": _require(row, "time"),
            "vin_v": _require(row, "v(in)"),
            "vout_v": _require(row, "v(out)"),
        }
        for row in parse_print_tables(log)
    ]


PARSERS = {"dc": parse_op, "ac": parse_ac, "tran": parse_tran}


def _failure(analysis, kind, message, netlist="", log="", started=None):
    return {
        "ok": False,
        "analysis": analysis,
        "rows": None,
        "engine": None,
        "netlist": netlist,
        "log": log,
        "duration_s": round(time.monotonic() - started, 3) if started else 0.0,
        "error": {"kind": kind, "message": message},
    }


def run_analysis(params, analysis, timeout=20.0):
    """Run one ngspice analysis in a throwaway directory.

    Returns a dict with ``ok``, ``rows`` (parsed output), ``engine``,
    ``netlist``, ``log``, ``duration_s``, and ``error``. Never raises for
    engine, process, timeout, or parse problems.
    """
    started = time.monotonic()
    exe = find_engine()
    if not exe:
        return _failure(
            analysis,
            "engine_missing",
            engine_info()["message"],
            started=started,
        )

    netlist = build_netlist(params, analysis)
    workdir = tempfile.mkdtemp(prefix="lab04-spice-")
    netlist_path = os.path.join(workdir, "circuit.cir")
    log_path = os.path.join(workdir, "run.log")
    log_text = ""
    try:
        with open(netlist_path, "w", encoding="ascii", errors="replace") as handle:
            handle.write(netlist)

        try:
            proc = subprocess.run(
                [exe, "-b", "-o", log_path, netlist_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return _failure(
                analysis,
                "timeout",
                f"ngspice did not finish within {timeout:.0f} s.",
                netlist,
                started=started,
            )
        except OSError as exc:
            return _failure(
                analysis,
                "engine_missing",
                f"Could not start ngspice: {exc}",
                netlist,
                started=started,
            )

        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                log_text = handle.read()

        if proc.returncode != 0:
            tail = (log_text or proc.stderr or "").strip().splitlines()[-3:]
            return _failure(
                analysis,
                "run_failed",
                f"ngspice exited with code {proc.returncode}. " + " ".join(tail),
                netlist,
                log_text,
                started,
            )

        try:
            rows = PARSERS[analysis](log_text)
        except ValueError as exc:
            return _failure(
                analysis,
                "parse_failed",
                f"Could not read ngspice output: {exc}",
                netlist,
                log_text,
                started,
            )

        return {
            "ok": True,
            "analysis": analysis,
            "rows": rows,
            "engine": exe,
            "netlist": netlist,
            "log": log_text,
            "duration_s": round(time.monotonic() - started, 3),
            "error": None,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
