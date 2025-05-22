import unittest
from ball_speed_calculator import calculate_speed

class TestBallSpeedCalculator(unittest.TestCase):

    def test_normal_conditions(self):
        """Test with typical valid inputs."""
        start_frame = 0
        end_frame = 30
        video_fps = 60.0
        known_distance_meters = 18.44

        expected_speed_mps = 36.88
        expected_speed_kmh = 132.768

        result = calculate_speed(start_frame, end_frame, video_fps, known_distance_meters)

        self.assertIn("mps", result)
        self.assertIn("kmh", result)
        self.assertAlmostEqual(result["mps"], expected_speed_mps, places=7)
        self.assertAlmostEqual(result["kmh"], expected_speed_kmh, places=7)

    def test_another_set_of_valid_inputs(self):
        """Test with another set of valid inputs."""
        start_frame = 100
        end_frame = 110
        video_fps = 30.0
        known_distance_meters = 10.0

        # time_seconds = (110 - 100) / 30 = 10 / 30 = 1/3
        # speed_mps = 10.0 / (1/3) = 30.0
        # speed_kmh = 30.0 * 3.6 = 108.0
        expected_speed_mps = 30.0
        expected_speed_kmh = 108.0

        result = calculate_speed(start_frame, end_frame, video_fps, known_distance_meters)

        self.assertIn("mps", result)
        self.assertIn("kmh", result)
        self.assertAlmostEqual(result["mps"], expected_speed_mps, places=7)
        self.assertAlmostEqual(result["kmh"], expected_speed_kmh, places=7)

    def test_invalid_fps(self):
        """Test that ValueError is raised for invalid FPS."""
        # Test with video_fps = 0
        with self.assertRaisesRegex(ValueError, "video_fps must be greater than 0"):
            calculate_speed(start_frame=0, end_frame=10, video_fps=0, known_distance_meters=10.0)

        # Test with video_fps < 0
        with self.assertRaisesRegex(ValueError, "video_fps must be greater than 0"):
            calculate_speed(start_frame=0, end_frame=10, video_fps=-30, known_distance_meters=10.0)

    def test_invalid_frame_order(self):
        """Test that ValueError is raised for invalid frame order."""
        # Test with start_frame == end_frame
        with self.assertRaisesRegex(ValueError, "start_frame must be less than end_frame"):
            calculate_speed(start_frame=10, end_frame=10, video_fps=30, known_distance_meters=10.0)

        # Test with start_frame > end_frame
        with self.assertRaisesRegex(ValueError, "start_frame must be less than end_frame"):
            calculate_speed(start_frame=20, end_frame=10, video_fps=30, known_distance_meters=10.0)

if __name__ == '__main__':
    unittest.main()
