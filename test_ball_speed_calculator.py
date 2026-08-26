import unittest

from ball_speed_calculator import calculate_speed, estimate_speed_from_trajectory


class TestBallSpeedCalculator(unittest.TestCase):
    def test_normal_conditions(self):
        result = calculate_speed(0, 30, 60.0, 18.44)
        self.assertAlmostEqual(result["mps"], 36.88, places=7)
        self.assertAlmostEqual(result["kmh"], 132.768, places=7)

    def test_another_set_of_valid_inputs(self):
        result = calculate_speed(100, 110, 30.0, 10.0)
        self.assertAlmostEqual(result["mps"], 30.0, places=7)
        self.assertAlmostEqual(result["kmh"], 108.0, places=7)

    def test_invalid_fps(self):
        with self.assertRaisesRegex(ValueError, "video_fps must be greater than 0"):
            calculate_speed(0, 10, 0, 10.0)
        with self.assertRaisesRegex(ValueError, "video_fps must be greater than 0"):
            calculate_speed(0, 10, -30, 10.0)

    def test_invalid_frame_order(self):
        with self.assertRaisesRegex(ValueError, "start_frame must be less than end_frame"):
            calculate_speed(10, 10, 30, 10.0)
        with self.assertRaisesRegex(ValueError, "start_frame must be less than end_frame"):
            calculate_speed(20, 10, 30, 10.0)

    def test_trajectory_estimator_perfect_linear_motion(self):
        # 600 px corresponds to 18.44 m. At 240 fps, moving 2 px/frame
        # means 480 px/s -> 14.752 m/s -> 53.1072 km/h.
        samples = [(frame, 100 + frame * 2) for frame in range(20)]
        result = estimate_speed_from_trajectory(samples, 240.0, 100, 700, 18.44)
        self.assertAlmostEqual(result["mps"], 14.752, places=6)
        self.assertAlmostEqual(result["kmh"], 53.1072, places=6)
        self.assertAlmostEqual(result["r2"], 1.0, places=10)
        self.assertEqual(result["sample_count"], 20)

    def test_trajectory_estimator_reduces_position_noise(self):
        # Ground truth is 4 px/frame at 240 fps = 960 px/s. Add alternating
        # +/- 1 pixel detection noise; regression should remain very close.
        samples = []
        for frame in range(30):
            noise = -1 if frame % 2 == 0 else 1
            samples.append((frame, 200 + frame * 4 + noise))
        result = estimate_speed_from_trajectory(samples, 240.0, 100, 700, 18.44)
        expected_mps = 960 * (18.44 / 600)
        self.assertAlmostEqual(result["mps"], expected_mps, delta=0.15)
        self.assertGreater(result["r2"], 0.99)

    def test_trajectory_requires_three_samples(self):
        with self.assertRaisesRegex(ValueError, "at least three trajectory samples"):
            estimate_speed_from_trajectory([(1, 10), (2, 20)], 240, 100, 700, 18.44)


if __name__ == "__main__":
    unittest.main()
