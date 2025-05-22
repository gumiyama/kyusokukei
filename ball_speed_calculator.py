"""
A Python script to calculate the speed of an object (e.g., a ball)
based on video frame analysis.

This script provides a function `calculate_speed` that takes the start frame,
end frame, video frames per second (FPS), and a known distance the object
traveled to compute its speed in meters per second (m/s) and
kilometers per hour (km/h).

The script also includes an example usage section to demonstrate how to use
the `calculate_speed` function and how it handles potential errors.
"""

def calculate_speed(start_frame: int, end_frame: int, video_fps: float, known_distance_meters: float) -> dict:
    """
    Calculates the speed of an object (e.g., a ball) based on frame data and known distance.

    Key Assumptions:
    - The user can accurately identify the `start_frame` and `end_frame` where the
      object is at the beginning and end of the `known_distance_meters` segment.
    - The `known_distance_meters` is accurate for the path traveled by the object
      between these frames.
    - The object's speed is relatively constant over the measured segment for this
      calculation to represent an average speed.
    - The `video_fps` is constant and accurately known.

    Args:
        start_frame (int): The frame number where the object is at the beginning
                           of the measured distance.
        end_frame (int): The frame number where the object is at the end
                         of the measured distance.
        video_fps (float): The frames per second of the video.
        known_distance_meters (float): The known distance the object traveled
                                       in meters between the start_frame and end_frame.

    Returns:
        dict: A dictionary containing the calculated speed in meters per second
              (key: "mps") and kilometers per hour (key: "kmh").

    Raises:
        ValueError: If video_fps is not greater than 0 or
                    if start_frame is not less than end_frame.
    """
    if video_fps <= 0:
        raise ValueError("video_fps must be greater than 0")
    if start_frame >= end_frame:
        raise ValueError("start_frame must be less than end_frame")

    time_seconds = (end_frame - start_frame) / video_fps
    speed_mps = known_distance_meters / time_seconds
    speed_kmh = speed_mps * 3.6

    return {"mps": speed_mps, "kmh": speed_kmh}

if __name__ == "__main__":
    # Example usage
    start_frame_example = 10
    end_frame_example = 40
    video_fps_example = 60
    known_distance_meters_example = 18.44  # Example: Baseball pitch distance

    try:
        speeds = calculate_speed(
            start_frame_example,
            end_frame_example,
            video_fps_example,
            known_distance_meters_example
        )
        print("Ball Speed Calculation:")
        print(f"  Frames: {start_frame_example} to {end_frame_example}")
        print(f"  Video FPS: {video_fps_example}")
        print(f"  Distance: {known_distance_meters_example} meters")
        print("-" * 30)
        print(f"  Speed: {speeds['mps']:.2f} m/s")
        print(f"  Speed: {speeds['kmh']:.2f} km/h")
    except ValueError as e:
        print(f"Error: {e}")

    # Example with invalid input to demonstrate error handling
    print("\nExample with invalid input (start_frame > end_frame):")
    try:
        speeds_error = calculate_speed(
            50, # start_frame
            20, # end_frame
            30, # video_fps
            10.0 # known_distance_meters
        )
        print(f"  Speed: {speeds_error['mps']:.2f} m/s")
        print(f"  Speed: {speeds_error['kmh']:.2f} km/h")
    except ValueError as e:
        print(f"Error: {e}")

    print("\nExample with invalid input (video_fps <= 0):")
    try:
        speeds_error_fps = calculate_speed(
            10, # start_frame
            20, # end_frame
            0,  # video_fps
            10.0 # known_distance_meters
        )
        print(f"  Speed: {speeds_error_fps['mps']:.2f} m/s")
        print(f"  Speed: {speeds_error_fps['kmh']:.2f} km/h")
    except ValueError as e:
        print(f"Error: {e}")
