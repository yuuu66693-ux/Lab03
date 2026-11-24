import unittest
from unittest import mock

import app as flask_app

RUN_OK = {
    "ok": True,
    "analysis": "dc",
    "rows": {
        "vb": 2.003668,
        "ve": 1.332961,
        "vc": 9.087039,
        "vce": 7.754078,
        "ic": 1.324073e-03,
        "ie": 1.332961e-03,
        "ib": 8.888e-06,
    },
    "engine": r"C:\tools\ngspice_con.exe",
    "netlist": "* netlist\n.op\n.end\n",
    "log": "log",
    "duration_s": 0.02,
    "error": None,
}

RUN_FAILED = {
    "ok": False,
    "analysis": "dc",
    "rows": None,
    "engine": None,
    "netlist": "",
    "log": "",
    "duration_s": 0.0,
    "error": {"kind": "engine_missing", "message": "ngspice not found. Install ngspice."},
}

SIM_FORM = {
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


class TestSimulateRoute(unittest.TestCase):
    def setUp(self):
        flask_app.app.config.update(TESTING=True)
        self.client = flask_app.app.test_client()

    def test_index_shows_simulation_panel(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Run Simulation", response.data)
        self.assertIn(b"Engineering Results", response.data)

    def test_successful_dc_run_shows_spice_values_and_provenance(self):
        with mock.patch.object(flask_app, "run_analysis", return_value=RUN_OK):
            response = self.client.post("/simulate", data=SIM_FORM)

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("2.004", body)
        self.assertIn("7.754", body)
        self.assertIn("ngspice", body)
        self.assertIn("2N3904", body)
        self.assertIn("Analytical", body)

    def test_zero_emitter_resistor_reports_error_without_running(self):
        form = dict(SIM_FORM, sim_re="0")

        with mock.patch.object(flask_app, "run_analysis", side_effect=AssertionError("must not run")):
            response = self.client.post("/simulate", data=form)

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("RE must be greater than 0", body)

    def test_engine_failure_is_visible_and_not_success(self):
        with mock.patch.object(flask_app, "run_analysis", return_value=RUN_FAILED):
            response = self.client.post("/simulate", data=SIM_FORM)

        body = response.get_data(as_text=True)
        self.assertIn("ngspice not found", body)
        self.assertNotIn("Simulation succeeded", body)

    def test_vcc_is_not_scaled_by_resistor_units(self):
        captured = {}

        def fake_run(params, analysis):
            captured.update(params)
            return RUN_OK

        with mock.patch.object(flask_app, "run_analysis", side_effect=fake_run):
            self.client.post("/simulate", data=SIM_FORM)

        self.assertEqual(captured["vcc"], 12.0)
        self.assertEqual(captured["r1"], 100000.0)
        self.assertEqual(captured["re"], 1000.0)
        self.assertEqual(captured["amp_v"], 0.01)

    def test_lab03_calculate_route_still_works(self):
        response = self.client.post(
            "/calculate",
            data={
                "mode": "divider",
                "vcc": "12",
                "r1": "100", "r1_unit": "kΩ",
                "r2": "22", "r2_unit": "kΩ",
                "rc": "2.2", "rc_unit": "kΩ",
                "re": "1", "re_unit": "kΩ",
                "beta": "100",
                "vbe": "0.7",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"8.052", response.data)


if __name__ == "__main__":
    unittest.main()
