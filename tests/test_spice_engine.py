import os
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

import spice_engine


def reference_params():
    return {
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


class TestValidateSimInputs(unittest.TestCase):
    def test_reference_values_pass_through_as_floats(self):
        clean, errors = spice_engine.validate_sim_inputs(reference_params())

        self.assertEqual(errors, [])
        self.assertIsInstance(clean["r1"], float)
        self.assertEqual(clean["r1"], 100_000.0)
        self.assertEqual(clean["cin_f"], 10e-6)
        self.assertEqual(clean["amp_v"], 0.01)

    def test_zero_emitter_resistor_is_rejected(self):
        params = reference_params()
        params["re"] = 0

        clean, errors = spice_engine.validate_sim_inputs(params)

        self.assertIsNone(clean)
        self.assertIn("re", [e["field"] for e in errors])

    def test_non_positive_frequency_is_rejected(self):
        params = reference_params()
        params["freq_hz"] = -1

        _, errors = spice_engine.validate_sim_inputs(params)

        self.assertIn("freq_hz", [e["field"] for e in errors])

    def test_non_numeric_amplitude_is_rejected(self):
        params = reference_params()
        params["amp_v"] = "abc"

        _, errors = spice_engine.validate_sim_inputs(params)

        self.assertIn("amp_v", [e["field"] for e in errors])

    def test_missing_load_resistor_is_rejected(self):
        params = reference_params()
        del params["rl"]

        _, errors = spice_engine.validate_sim_inputs(params)

        self.assertIn("rl", [e["field"] for e in errors])


class TestBuildNetlist(unittest.TestCase):
    def test_dc_netlist_uses_reference_components_and_op(self):
        netlist = spice_engine.build_netlist(reference_params(), "dc")

        self.assertIn("VCC vcc 0 12", netlist)
        self.assertIn("R1 vcc base 100000", netlist)
        self.assertIn("R2 base 0 22000", netlist)
        self.assertIn("RC vcc col 2200", netlist)
        self.assertIn("RE emit 0 1000", netlist)
        self.assertIn("Q1 col base emit Q2N3904", netlist)
        self.assertIn("CIN in base 1e-05", netlist)
        self.assertIn("RL out 0 10000", netlist)
        self.assertIn(".model Q2N3904 NPN", netlist)
        self.assertIn(".op", netlist)
        self.assertIn(".print op v(base) v(emit) v(col)", netlist)

    def test_ac_netlist_sets_sweep_and_gain_vectors(self):
        netlist = spice_engine.build_netlist(reference_params(), "ac")

        self.assertIn("VIN in 0 DC 0 AC 1 SIN(0 0.01 1000)", netlist)
        self.assertIn(".ac dec 20 10 10meg", netlist)
        self.assertIn(".print ac vdb(out) vp(out) vdb(in) vp(in)", netlist)
        self.assertNotIn(".op", netlist)

    def test_tran_netlist_sets_window_and_waveforms(self):
        netlist = spice_engine.build_netlist(reference_params(), "tran")

        self.assertIn(".tran 5e-06 0.005", netlist)
        self.assertIn(".print tran v(in) v(out)", netlist)

    def test_unknown_analysis_is_rejected(self):
        with self.assertRaises(ValueError):
            spice_engine.build_netlist(reference_params(), "fft")


OP_LOG = """\
                               ce reference probe
                               Operating Point  Tue Nov 24 17:21:44  2026
--------------------------------------------------------------------------------
Index   v(base)         v(emit)         v(col)          vcc#branch      
--------------------------------------------------------------------------------
0\t2.003668e+00\t1.332961e+00\t9.087039e+00\t-1.42404e-03\t

                               ce reference probe
                               Operating Point  Tue Nov 24 17:21:44  2026
--------------------------------------------------------------------------------
Index   @rc[i]          @re[i]          
--------------------------------------------------------------------------------
0\t1.324073e-03\t1.332961e-03\t
"""

AC_LOG = """\
                               ce reference probe
                               AC Analysis  Tue Nov 24 17:22:03  2026
--------------------------------------------------------------------------------
Index   frequency       vdb(out)        vp(out)         
--------------------------------------------------------------------------------
0\t1.000000e+01\t4.775540e+00\t-2.91434e+00\t
1\t1.122018e+01\t4.798978e+00\t-2.93887e+00\t

Index   frequency       vdb(out)        vp(out)         
--------------------------------------------------------------------------------
2\t1.258925e+01\t4.817644e+00\t-2.96078e+00\t
3\t1.000000e+03\t4.890131e+00\t-3.13931e+00\t

Index   frequency       vdb(in)         vp(in)          
--------------------------------------------------------------------------------
0\t1.000000e+01\t0.000000e+00\t0.000000e+00\t
1\t1.122018e+01\t0.000000e+00\t0.000000e+00\t
2\t1.258925e+01\t0.000000e+00\t0.000000e+00\t
3\t1.000000e+03\t0.000000e+00\t0.000000e+00\t
"""

TRAN_LOG = """\
                               ce reference probe
                               Transient Analysis  Tue Nov 24 17:22:10  2026
--------------------------------------------------------------------------------
Index   time            v(in)           v(out)          
--------------------------------------------------------------------------------
0\t0.000000e+00\t0.000000e+00\t0.000000e+00\t
1\t5.000000e-08\t3.141593e-06\t-7.18241e-06\t

Index   time            v(in)           v(out)          
--------------------------------------------------------------------------------
55\t2.414000e-04\t9.985404e-03\t-1.74985e-02\t
56\t2.464000e-04\t9.997442e-03\t-1.75184e-02\t
"""


class TestParsePrintTables(unittest.TestCase):
    def test_parse_op_merges_tables_and_derives_vce(self):
        result = spice_engine.parse_op(OP_LOG)

        self.assertAlmostEqual(result["vb"], 2.003668, places=6)
        self.assertAlmostEqual(result["ve"], 1.332961, places=6)
        self.assertAlmostEqual(result["vc"], 9.087039, places=6)
        self.assertAlmostEqual(result["vce"], 7.754078, places=6)
        self.assertAlmostEqual(result["ic"], 1.324073e-03, places=9)
        self.assertAlmostEqual(result["ie"], 1.332961e-03, places=9)
        self.assertAlmostEqual(result["ib"], 8.888e-06, places=9)

    def test_parse_ac_merges_pages_and_converts_phase_to_degrees(self):
        rows = spice_engine.parse_ac(AC_LOG)

        self.assertEqual([r["frequency_hz"] for r in rows], [10.0, 11.22018, 12.58925, 1000.0])
        self.assertAlmostEqual(rows[0]["gain_db"], 4.77554, places=5)
        self.assertAlmostEqual(rows[0]["phase_deg"], -166.98, places=1)
        self.assertAlmostEqual(rows[3]["phase_deg"], -179.87, places=1)

    def test_parse_tran_merges_paginated_tables(self):
        rows = spice_engine.parse_tran(TRAN_LOG)

        self.assertEqual(len(rows), 4)
        self.assertAlmostEqual(rows[2]["time_s"], 2.414e-4, places=9)
        self.assertAlmostEqual(rows[3]["vin_v"], 9.997442e-03, places=9)
        self.assertAlmostEqual(rows[3]["vout_v"], -1.75184e-02, places=9)

    def test_parse_ac_unwraps_phase_through_180_degrees(self):
        log = """\
Index   frequency       vdb(out)        vp(out)         vdb(in)         vp(in)
--------------------------------------------------------------------------------
0\t1.000000e+04\t4.890000e+00\t-3.141590e+00\t0.000000e+00\t0.000000e+00
1\t7.943282e+04\t4.890000e+00\t3.141592e+00\t0.000000e+00\t0.000000e+00
"""
        rows = spice_engine.parse_ac(log)

        self.assertLess(abs(rows[0]["phase_deg"] - rows[1]["phase_deg"]), 0.01)

    def test_parse_rejects_log_without_tables(self):
        with self.assertRaises(ValueError):
            spice_engine.parse_print_tables("ngspice-47\nno tables here\n")


class TestRunAnalysis(unittest.TestCase):
    def _fake_run_writing(self, log_text, returncode=0):
        def fake_run(args, **kwargs):
            log_path = args[args.index("-o") + 1]
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(log_text)
            return SimpleNamespace(returncode=returncode, stdout="", stderr="")
        return fake_run

    def test_missing_engine_returns_structured_error(self):
        with mock.patch.object(spice_engine, "find_engine", return_value=None):
            result = spice_engine.run_analysis(reference_params(), "dc")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], "engine_missing")
        self.assertIn("ngspice", result["error"]["message"])

    def test_timeout_is_reported(self):
        with mock.patch.object(spice_engine, "find_engine", return_value="ngspice_con"), \
                mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ngspice_con", 20)):
            result = spice_engine.run_analysis(reference_params(), "dc")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], "timeout")

    def test_non_zero_exit_is_reported(self):
        with mock.patch.object(spice_engine, "find_engine", return_value="ngspice_con"), \
                mock.patch("subprocess.run", side_effect=self._fake_run_writing("boom", 1)):
            result = spice_engine.run_analysis(reference_params(), "dc")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], "run_failed")

    def test_unparseable_success_is_parse_failure(self):
        with mock.patch.object(spice_engine, "find_engine", return_value="ngspice_con"), \
                mock.patch("subprocess.run", side_effect=self._fake_run_writing("no tables")):
            result = spice_engine.run_analysis(reference_params(), "dc")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], "parse_failed")

    def test_success_uses_safe_subprocess_and_cleans_temp_dir(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            log_path = args[args.index("-o") + 1]
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(OP_LOG)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with mock.patch.object(spice_engine, "find_engine", return_value="ngspice_con"), \
                mock.patch("subprocess.run", side_effect=fake_run):
            result = spice_engine.run_analysis(reference_params(), "dc")

        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["rows"]["vb"], 2.003668, places=6)
        self.assertIn(".op", result["netlist"])
        self.assertGreaterEqual(result["duration_s"], 0.0)

        args, kwargs = calls[0]
        self.assertIsInstance(args, list)
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(kwargs.get("timeout"), 20.0)
        workdir = os.path.dirname(args[args.index("-o") + 1])
        self.assertFalse(os.path.exists(workdir))


class TestEngineDiscovery(unittest.TestCase):
    def test_returns_none_when_no_engine_is_available(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch("shutil.which", return_value=None):
            self.assertIsNone(spice_engine.find_engine())

    def test_prefers_explicit_ngspice_bin(self):
        with mock.patch.dict("os.environ", {"NGSPICE_BIN": r"C:\tools\ngspice_con.exe"}), \
                mock.patch("shutil.which", return_value=None), \
                mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(spice_engine.find_engine(), r"C:\tools\ngspice_con.exe")

    def test_prefers_console_build_over_gui_build(self):
        def which(name):
            return {
                "ngspice_con": r"C:\bin\ngspice_con.exe",
                "ngspice": r"C:\bin\ngspice.exe",
            }.get(name)

        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch("shutil.which", side_effect=which):
            self.assertEqual(spice_engine.find_engine(), r"C:\bin\ngspice_con.exe")

    def test_engine_info_reports_missing_engine(self):
        with mock.patch.object(spice_engine, "find_engine", return_value=None):
            info = spice_engine.engine_info()

        self.assertFalse(info["available"])
        self.assertIn("ngspice", info["message"])


if __name__ == "__main__":
    unittest.main()
