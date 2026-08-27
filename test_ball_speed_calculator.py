import unittest

from ball_speed_calculator import (
    calculate_speed,
    estimate_speed_from_trajectory,
    estimate_speed_from_timed_trajectory,
)


class TestBallSpeedCalculator(unittest.TestCase):
    def test_normal_conditions(self):
        result = calculate_speed(0, 30, 60.0, 18.44)
        self.assertAlmostEqual(result["mps"], 36.88, places=7)
        self.assertAlmostEqual(result["kmh"], 132.768, places=7)

    def test_invalid_fps(self):
        with self.assertRaisesRegex(ValueError, "video_fps must be greater than 0"):
            calculate_speed(0, 10, 0, 10.0)

    def test_trajectory_estimator_perfect_linear_motion(self):
        samples = [(frame, 100 + frame * 2) for frame in range(20)]
        result = estimate_speed_from_trajectory(samples, 240.0, 100, 700, 18.44)
        self.assertAlmostEqual(result["mps"], 14.752, places=6)
        self.assertAlmostEqual(result["kmh"], 53.1072, places=6)
        self.assertAlmostEqual(result["r2"], 1.0, places=10)

    def test_timestamp_estimator_handles_irregular_intervals(self):
        # 960 px/s with intentionally irregular timestamps.
        times = [0.000, 0.0040, 0.0084, 0.0122, 0.0169, 0.0207, 0.0252]
        samples = [(t, 100 + 960.0 * t) for t in times]
        result = estimate_speed_from_timed_trajectory(
            samples, pitcher_x=100, batter_x=700, known_distance_meters=18.44
        )
        expected_mps = 960.0 * (18.44 / 600.0)
        self.assertAlmostEqual(result["mps"], expected_mps, delta=0.01)
        self.assertGreater(result["initial_r2"], 0.999999)

    def test_robust_estimator_rejects_tracking_glitch(self):
        # Clean motion = 1000 px/s. One centroid is deliberately corrupted.
        samples = [(i / 240.0, 200 + 1000.0 * (i / 240.0)) for i in range(20)]
        samples[10] = (samples[10][0], samples[10][1] + 80.0)
        result = estimate_speed_from_timed_trajectory(
            samples,
            pitcher_x=100,
            batter_x=700,
            known_distance_meters=18.44,
            initial_window=8,
        )
        expected_mps = 1000.0 * (18.44 / 600.0)
        self.assertAlmostEqual(result["average_mps"], expected_mps, delta=0.2)
        self.assertGreaterEqual(result["rejected_count"], 1)

    def test_initial_window_reports_initial_velocity(self):
        # First 8 points = 1200 px/s, then ball slows to 1000 px/s.
        samples = []
        x = 100.0
        dt = 1 / 240.0
        for i in range(20):
            t = i * dt
            if i > 0:
                speed = 1200.0 if i < 8 else 1000.0
                x += speed * dt
            samples.append((t, x))
        result = estimate_speed_from_timed_trajectory(
            samples,
            pitcher_x=100,
            batter_x=700,
            known_distance_meters=18.44,
            initial_window=8,
        )
        self.assertGreater(result["mps"], result["average_mps"])

    def test_timed_trajectory_requires_three_samples(self):
        with self.assertRaisesRegex(ValueError, "at least three timed trajectory samples"):
            estimate_speed_from_timed_trajectory(
                [(0.0, 10), (0.01, 20)], 100, 700, 18.44
            )


if __name__ == "__main__":
    unittest.main()
