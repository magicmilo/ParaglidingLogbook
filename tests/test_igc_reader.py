import unittest
from pathlib import Path

from logbook.igc_reader import parse_igc_file


class TestIGCReader(unittest.TestCase):
    def test_parse_takeoff_values_from_sample_igc(self):
        sample = Path("test_data") / "2026-04-02-XCT-MXX-01.igc"

        flight = parse_igc_file(sample)

        self.assertEqual(flight["pilot"], "Milo Bascombe")
        self.assertEqual(flight["glider"], "OZONE Geo 5")

        # date should include flight time in 24h HH:MM format
        self.assertEqual(flight["date"], "2026-04-02 10:33")
        # Duration: 11:09:52 - 10:33:48 = 36 minutes 4 seconds
        self.assertEqual(flight["duration"], "00:36:04")
        self.assertAlmostEqual(flight["distance_km"], 12.06, places=1)

        # Takeoff
        self.assertEqual(flight["takeoff_site"], "Westbury")
        self.assertEqual(flight["takeoff_time"], "10:33:48")
        self.assertEqual(flight["takeoff_altitude"], 213.0)
        self.assertAlmostEqual(flight["takeoff_latitude"], 51.264133333333334, places=6)
        self.assertAlmostEqual(flight["takeoff_longitude"], -2.1452, places=6)

        # Landing
        self.assertEqual(flight["landing_time"], "11:09:52")
        self.assertEqual(flight["landing_altitude"], 157.0)

        # Altitude
        self.assertEqual(flight["max_altitude"], 585.0)
        self.assertAlmostEqual(flight["max_altitude_gain"], 428.0, places=1)


if __name__ == "__main__":
    unittest.main()
