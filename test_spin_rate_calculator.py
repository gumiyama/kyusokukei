import unittest
from ball_speed_calculator import calculate_spin_rpm

class TestSpinRateCalculator(unittest.TestCase):
    def test_single_rotation(self):
        angles = [0, 90, 180, 270, 360]
        rpm = calculate_spin_rpm(angles, 1.0)
        self.assertAlmostEqual(rpm, 60.0)

    def test_multiple_rotations(self):
        angles = [0, 120, 240, 0, 120]
        rpm = calculate_spin_rpm(angles, 2.0)
        # total change = 480, rotations = 1.3333, rpm = 40
        self.assertAlmostEqual(rpm, 40.0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_spin_rpm([0], 1.0)
        with self.assertRaises(ValueError):
            calculate_spin_rpm([0, 10], 0)

if __name__ == '__main__':
    unittest.main()
