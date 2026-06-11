# Ball Speed Calculation Utility

## Overview

This utility provides a Python script (`ball_speed_calculator.py`) containing a basic function to calculate the speed of an object (e.g., a ball) based on video frame information and a known distance the object has traveled. It is designed as a core calculation component.

## `ball_speed_calculator.py`

The script contains the `calculate_speed` function.

### `calculate_speed(start_frame: int, end_frame: int, video_fps: float, known_distance_meters: float) -> dict`

This function calculates the speed of an object given the following parameters:

*   `start_frame (int)`: The frame number where the object is at the beginning of the measured distance.
*   `end_frame (int)`: The frame number where the object is at the end of the measured distance.
*   `video_fps (float)`: The frames per second (FPS) of the video.
*   `known_distance_meters (float)`: The known distance the object traveled in meters between the `start_frame` and `end_frame`.

It returns a dictionary containing the calculated speed in:
*   Meters per second (key: `"mps"`)
*   Kilometers per hour (key: `"kmh"`)

The function will raise a `ValueError` if `video_fps` is not greater than 0, or if `start_frame` is not less than `end_frame`.

### Example Usage

```python
from ball_speed_calculator import calculate_speed

# Example parameters
start_frame_example = 10
end_frame_example = 40
video_fps_example = 60.0
known_distance_meters_example = 18.44  # e.g., Baseball pitch distance

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

# Expected output:
# Ball Speed Calculation:
#   Frames: 10 to 40
#   Video FPS: 60.0
#   Distance: 18.44 meters
# ------------------------------
#   Speed: 36.88 m/s
#   Speed: 132.77 km/h
```

## Assumptions and Limitations

The `calculate_speed` function operates under the following key assumptions:

*   **Accurate Frame Identification:** The user can accurately identify the `start_frame` (when the object is at the beginning of the measured segment) and `end_frame` (when the object is at the end of the segment).
*   **Accurate Distance:** The `known_distance_meters` provided is an accurate measurement of the distance the object traveled between the specified frames.
*   **Constant Speed (Average):** The calculation assumes the object's speed is relatively constant over the measured segment. The result represents the average speed during this interval.
*   **Constant and Known FPS:** The `video_fps` is constant throughout the video segment and is accurately known.

This script **does not** perform:

*   Video loading or processing.
*   Object detection or tracking (i.e., it cannot automatically find the ball or object in video frames).
*   Automated determination of `start_frame`, `end_frame`, or `known_distance_meters`. These must be provided as inputs.
*   Any form of user interface for video interaction or data input beyond programmatic function calls.

It is intended as a core calculation component that would typically be part of a larger system or application that handles video input, object tracking, and user interaction to obtain the necessary parameters for this function.

## How to Use

A developer would typically integrate the `ball_speed_calculator.py` script into a larger application. This application would be responsible for:

1.  Loading and processing the video.
2.  Allowing the user (or an automated system) to identify the object and the relevant `start_frame` and `end_frame`.
3.  Determining the `known_distance_meters` corresponding to the segment between these frames.
4.  Calling the `calculate_speed` function with these parameters.
5.  Displaying or further processing the returned speed results.

To use the function, import it into your Python project:

```python
from ball_speed_calculator import calculate_speed

# ... obtain your start_frame, end_frame, video_fps, known_distance_meters ...
# speed_data = calculate_speed(start_frame, end_frame, video_fps, known_distance_meters)
# print(f"Speed in m/s: {speed_data['mps']}")
```

## Real-Time Measurement (Experimental)

An additional script `real_time_ball_speed.py` allows measuring ball speed from a live camera feed using OpenCV. The script tracks a colored ball as it crosses two on-screen lines and calculates the speed between those points.

Run the script (ensure `opencv-python` is installed and a camera is connected). You can optionally save the session to a video file for evidence:

```bash
python real_time_ball_speed.py --distance 18.44 --output capture.mp4
```

Press `ESC` to exit. Adjust the HSV color range and distance values in the script for your environment.

### Personal Records

You can keep track of personal best speeds by specifying a player name. The best
speed for each player is stored in `personal_records.json` (or a custom path via
`--record-file`):

```bash
python real_time_ball_speed.py --distance 18.44 --player Alice --output capture.mp4
```

The script will indicate whether a new record was set.

### Spin Rate

If you place a distinct colored marker on the ball, the script can estimate spin
rate in rotations per minute (RPM). Provide HSV ranges for the marker using
`--marker-lower` and `--marker-upper`:

```bash
python real_time_ball_speed.py --distance 18.44 \
    --marker-lower 0,150,150 --marker-upper 10,255,255
```

The RPM value is printed along with the speed after the throw.

