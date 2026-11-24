import unittest

import plotting


def bode_rows():
    return [
        {"frequency_hz": 10.0, "gain_db": 4.77, "phase_deg": -166.9},
        {"frequency_hz": 100.0, "gain_db": 4.88, "phase_deg": -179.0},
        {"frequency_hz": 1000.0, "gain_db": 4.89, "phase_deg": -179.8},
    ]


def tran_rows():
    return [
        {"time_s": 0.0, "vin_v": 0.0, "vout_v": 0.0},
        {"time_s": 0.00025, "vin_v": 0.01, "vout_v": -0.017},
        {"time_s": 0.0005, "vin_v": 0.0, "vout_v": 0.0},
    ]


class TestNiceTicks(unittest.TestCase):
    def test_ticks_are_monotonic_and_inside_range(self):
        ticks = plotting.nice_ticks(0.0, 10.0, 5)

        self.assertGreaterEqual(len(ticks), 3)
        self.assertEqual(ticks, sorted(ticks))
        self.assertTrue(all(0.0 <= tick <= 10.0 for tick in ticks))


class TestPrepareBode(unittest.TestCase):
    def test_bode_returns_gain_and_phase_series(self):
        chart = plotting.prepare_bode(bode_rows())

        self.assertFalse(chart["empty"])
        self.assertEqual([series["name"] for series in chart["series"]], ["Gain", "Phase"])
        for series in chart["series"]:
            self.assertEqual(len(series["points"].split()), 3)

    def test_bode_x_positions_follow_log_frequency(self):
        chart = plotting.prepare_bode(bode_rows())

        xs = [float(pair.split(",")[0]) for pair in chart["series"][0]["points"].split()]

        self.assertEqual(xs, sorted(xs))
        self.assertLess(xs[0], xs[1])
        self.assertLess(xs[1], xs[2])

    def test_bode_has_separate_gain_and_phase_panels(self):
        chart = plotting.prepare_bode(bode_rows())

        self.assertEqual([panel["name"] for panel in chart["panels"]], ["Gain", "Phase"])
        self.assertEqual([panel["unit"] for panel in chart["panels"]], ["dB", "deg"])
        self.assertNotEqual(
            chart["panels"][0]["y_ticks"][0]["label"],
            chart["panels"][1]["y_ticks"][0]["label"],
        )

    def test_bode_marks_empty_input(self):
        chart = plotting.prepare_bode([])

        self.assertTrue(chart["empty"])
        self.assertEqual(chart["series"], [])


class TestPrepareTran(unittest.TestCase):
    def test_tran_returns_input_and_output_waveforms(self):
        chart = plotting.prepare_tran(tran_rows())

        self.assertFalse(chart["empty"])
        self.assertEqual([series["name"] for series in chart["series"]], ["Vin", "Vout"])
        self.assertEqual(chart["x_label"], "Time (ms)")
        self.assertEqual(
            chart["series"][0]["y_ticks"],
            chart["series"][1]["y_ticks"],
        )

    def test_tran_marks_empty_input(self):
        chart = plotting.prepare_tran([])

        self.assertTrue(chart["empty"])


if __name__ == "__main__":
    unittest.main()
