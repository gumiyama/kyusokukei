"""Simple real-time ball speed measurement using OpenCV."""

import argparse
import cv2
import math
from typing import Optional, Tuple, List

from personal_record import update_personal_record

from ball_speed_calculator import calculate_speed, calculate_spin_rpm


def track_ball_speed(
    known_distance_meters: float,
    hsv_lower=(30, 150, 50),
    hsv_upper=(50, 255, 255),
    camera_index: int = 0,
    line_positions=(0.2, 0.8),
    save_path: Optional[str] = None,
    player_name: Optional[str] = None,
    record_file: str = "personal_records.json",
    marker_lower: Optional[Tuple[int, int, int]] = None,
    marker_upper: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Track ball speed in real time using a webcam.

    This function uses simple color detection to track a ball as it crosses two
    vertical lines on the video feed. The time between crossings is measured and
    converted to speed using :func:`calculate_speed`.

    Args:
        known_distance_meters: Distance in meters between the two on-screen
            lines the ball must travel through.
        hsv_lower: Lower HSV color threshold for the ball.
        hsv_upper: Upper HSV color threshold for the ball.
        camera_index: Index of the camera to use.
        line_positions: Tuple with the relative x-positions (0-1) of the start
            and end lines on the frame.
        save_path: Optional path to save the video evidence. If provided,
            all frames are written to this file.
        player_name: Optional player name used for personal record keeping.
        record_file: File path used to store personal records.
        marker_lower: Optional lower HSV threshold for a marker on the ball used
            to compute spin rate.
        marker_upper: Optional upper HSV threshold for the marker.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Unable to open camera")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # Fallback if FPS cannot be determined

    writer = None

    start_frame = None
    end_frame = None
    frame_count = 0
    angles: List[float] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        if writer is None and save_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(save_path, fourcc, fps, (frame.shape[1], frame.shape[0]))

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        center = None
        marker_center = None
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            if radius > 5:
                center = (int(x), int(y))
                cv2.circle(frame, center, int(radius), (0, 255, 0), 2)

        if marker_lower is not None and marker_upper is not None:
            marker_mask = cv2.inRange(hsv, marker_lower, marker_upper)
            marker_cnts, _ = cv2.findContours(marker_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if marker_cnts:
                m = max(marker_cnts, key=cv2.contourArea)
                ((mx, my), mr) = cv2.minEnclosingCircle(m)
                if mr > 2:
                    marker_center = (int(mx), int(my))
                    cv2.circle(frame, marker_center, int(mr), (0, 255, 255), 2)

        width = frame.shape[1]
        line1_x = int(width * line_positions[0])
        line2_x = int(width * line_positions[1])
        cv2.line(frame, (line1_x, 0), (line1_x, frame.shape[0]), (255, 0, 0), 2)
        cv2.line(frame, (line2_x, 0), (line2_x, frame.shape[0]), (0, 0, 255), 2)

        if center:
            if start_frame is None and center[0] >= line1_x:
                start_frame = frame_count
            elif start_frame is not None and end_frame is None and center[0] >= line2_x:
                end_frame = frame_count
            if start_frame is not None and end_frame is None and marker_center is not None:
                angle = math.degrees(math.atan2(marker_center[1]-center[1], marker_center[0]-center[0]))
                angles.append(angle)

        if writer is not None:
            writer.write(frame)

        cv2.imshow("Real-Time Ball Speed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        if start_frame is not None and end_frame is not None:
            break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    if start_frame is not None and end_frame is not None:
        result = calculate_speed(start_frame, end_frame, fps, known_distance_meters)
        print(f"Speed: {result['mps']:.2f} m/s ({result['kmh']:.2f} km/h)")
        if angles:
            duration = (end_frame - start_frame) / fps
            rpm = calculate_spin_rpm(angles, duration)
            print(f"Spin: {rpm:.2f} rpm")
        if player_name:
            best, is_new = update_personal_record(player_name, result['kmh'], record_file)
            if is_new:
                print(f"New personal best for {player_name}: {best:.2f} km/h")
            else:
                print(f"Personal best for {player_name}: {best:.2f} km/h")
    else:
        print("Could not determine speed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure ball speed from a webcam feed")
    parser.add_argument(
        "--distance",
        type=float,
        default=18.44,
        help="Known distance in meters between the two on-screen lines",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the recorded video for evidence",
    )
    parser.add_argument(
        "--player",
        type=str,
        default=None,
        help="Name for personal record keeping",
    )
    parser.add_argument(
        "--record-file",
        type=str,
        default="personal_records.json",
        help="File path to store personal records",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index to use",
    )
    parser.add_argument(
        "--marker-lower",
        type=str,
        default=None,
        help="Lower HSV threshold for the spin marker (e.g. '0,150,150')",
    )
    parser.add_argument(
        "--marker-upper",
        type=str,
        default=None,
        help="Upper HSV threshold for the spin marker (e.g. '10,255,255')",
    )

    args = parser.parse_args()

    def parse_hsv(val: Optional[str]) -> Optional[Tuple[int, int, int]]:
        if val is None:
            return None
        parts = [int(x) for x in val.split(",")]
        if len(parts) != 3:
            raise ValueError("HSV values must be H,S,V")
        return tuple(parts)

    track_ball_speed(
        known_distance_meters=args.distance,
        camera_index=args.camera,
        save_path=args.output,
        player_name=args.player,
        record_file=args.record_file,
        marker_lower=parse_hsv(args.marker_lower),
        marker_upper=parse_hsv(args.marker_upper),
    )
