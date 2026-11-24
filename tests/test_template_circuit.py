import unittest
from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parents[1] / "templates" / "index.html").read_text(
    encoding="utf-8"
)


class TestCircuitDiagrams(unittest.TestCase):
    def test_ce_has_one_common_ground_rail(self):
        # All four grounds (source, R2, RE, RL) must meet the same rail.
        self.assertIn('<line x1="40" y1="288" x2="380" y2="288"', TEMPLATE)
        for line in (
            '<line x1="40" y1="220" x2="40" y2="288"',
            '<line x1="130" y1="244" x2="130" y2="288"',
            '<line x1="300" y1="282" x2="300" y2="288"',
            '<line x1="380" y1="236" x2="380" y2="288"',
        ):
            self.assertIn(line, TEMPLATE)
        self.assertEqual(TEMPLATE.count('class="svg-small">Vout<'), 1)

    def test_ce_divider_and_output_nodes_are_connected(self):
        self.assertIn('<circle cx="130" cy="140" r="3"', TEMPLATE)
        self.assertIn('<circle cx="300" cy="140" r="3"', TEMPLATE)
        self.assertIn('<circle cx="300" cy="220" r="3"', TEMPLATE)
        self.assertIn('<line x1="130" y1="140" x2="204" y2="140"', TEMPLATE)
        self.assertIn('<line x1="300" y1="140" x2="336" y2="140"', TEMPLATE)

    def test_lab03_emitter_resistor_starts_at_emitter_node(self):
        # Regression for the old transformed zigzag that overlapped the emitter wire.
        self.assertIn(
            '<polyline points="260,255 250,265 270,280 250,295 270,310 250,325 260,335"',
            TEMPLATE,
        )
        self.assertNotIn('260,370" fill="none" stroke="#334155" stroke-width="2" transform=', TEMPLATE)
        self.assertIn('<line x1="260" y1="335" x2="260" y2="340"', TEMPLATE)


if __name__ == "__main__":
    unittest.main()
