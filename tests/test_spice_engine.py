import unittest
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
