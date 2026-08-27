"""Literature-inspired Phase 1 smartphone baseball velocity measurement.

The implementation combines ideas from iPhoneSG-style lateral-view image
processing (frame differencing, known-distance calibration, predicted search
region) with Kalman tracking and timestamp-based velocity estimation.

For best Phase 1 accuracy, use a side-view 120/240 fps recorded video rather
than a generic 30 fps webcam feed.
"""

import argparse
import cv2
import math
import time
from typing import Optional, Tuple, List

import numpy as np

from personal_record import update_personal_record
from ball_speed_calculator import (
    calculate_speed,
    calculate_spin_rpm,
    estimate_speed_from_timed_trajectory,
)


class BallKalmanTracker:
    """Constant-velocity Kalman tracker for ball centroid prediction."""

    def __init__(self):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32
        )
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 4.0
        self.kf.errorCovPost = np.eye(4, dtype=np.float32)
        self.initialized = False
        self.last_time = None

    def _set_dt(self, dt: float) -> None:
        dt = max(1e-4, float(dt))
        self.kf.transitionMatrix = np.array(
            [[1, 0, dt, 0],
             [0, 1, 0, dt],
             [0, 0, 1, 0],
             [0, 0, 0, 1]],
            dtype=np.float32,
        )

    def initialize(self, x: float, y: float, timestamp: float) -> None:
        self.kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
        self.kf.statePre = self.kf.statePost.copy()
        self.initialized = True
        self.last_time = timestamp

    def predict(self, timestamp: float) -> Optional[Tuple[float, float]]:
        if not self.initialized:
            return None
        dt = timestamp - self.last_time if self.last_time is not None else 1 / 240
        self._set_dt(dt)
        pred = self.kf.predict()
        return float(pred[0, 0]), float(pred[1, 0])

    def correct(self, x: float, y: float, timestamp: float) -> Tuple[float, float]:
        if not self.initialized:
            self.initialize(x, y, timestamp)
            return x, y
        measurement = np.array([[np.float32(x)], [np.float32(y)]])
        state = self.kf.correct(measurement)
        self.last_time = timestamp
        return float(state[0, 0]), float(state[1, 0])


def _video_timestamp_seconds(
    cap: cv2.VideoCapture,
    frame_count: int,
    nominal_fps: float,
    is_file: bool,
    live_start: float,
) -> float:
    """Use media timestamps for files and a monotonic clock for live capture."""
    if is_file:
        pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos_ms > 0:
            return pos_ms / 1000.0
        return frame_count / nominal_fps
    return time.perf_counter() - live_start


def _predict_from_two_points(
    points: List[Tuple[float, float, float]],
) -> Optional[Tuple[float, float]]:
    """iPhoneSG-style next-position prediction from the latest two detections."""
    if len(points) < 2:
        return None
    t1, x1, y1 = points[-2]
    t2, x2, y2 = points[-1]
    dt = t2 - t1
    if dt <= 0:
        return None
    return x2 + (x2 - x1), y2 + (y2 - y1)


def _detect_moving_ball(
    prev_gray: Optional[np.ndarray],
    gray: np.ndarray,
    predicted: Optional[Tuple[float, float]],
    roi_radius: int = 100,
    diff_threshold: int = 24,
) -> Optional[Tuple[float, float, float]]:
    """Detect a small moving object using frame differencing and prediction ROI.

    Returns x, y, radius. Candidate contours are scored by proximity to the
    predicted position, compactness, and plausible small-object size.
    """
    if prev_gray is None:
        return None

    diff = cv2.absdiff(prev_gray, gray)
    diff = cv2.GaussianBlur(diff, (5, 5), 0)
    _, mask = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    x0 = y0 = 0
    roi = mask
    if predicted is not None:
        px, py = predicted
        x0 = max(0, int(px - roi_radius))
        y0 = max(0, int(py - roi_radius))
        x1 = min(mask.shape[1], int(px + roi_radius))
        y1 = min(mask.shape[0], int(py + roi_radius))
        if x1 > x0 and y1 > y0:
            roi = mask[y0:y1, x0:x1]

    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = -1e18

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 3 or area > 1200:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        cx += x0
        cy += y0
        if radius < 1.0 or radius > 30.0:
            continue

        perimeter = cv2.arcLength(contour, True)
        circularity = 0.0 if perimeter <= 0 else 4.0 * math.pi * area / (perimeter * perimeter)
        proximity_penalty = 0.0
        if predicted is not None:
            proximity_penalty = math.hypot(cx - predicted[0], cy - predicted[1])

        score = 20.0 * min(circularity, 1.0) + math.log1p(area) - 0.08 * proximity_penalty
        if score > best_score:
            best_score = score
            best = (float(cx), float(cy), float(radius))

    return best


def track_ball_speed(
    known_distance_meters: float,
    camera_index: int = 0,
    video_path: Optional[str] = None,
    pitcher_x: Optional[float] = None,
    batter_x: Optional[float] = None,
    line_positions=(0.2, 0.8),
    save_path: Optional[str] = None,
    player_name: Optional[str] = None,
    record_file: str = "personal_records.json",
    marker_lower: Optional[Tuple[int, int, int]] = None,
    marker_upper: Optional[Tuple[int, int, int]] = None,
    roi_radius: int = 100,
    initial_window: int = 10,
) -> None:
    """Track baseball velocity from a side-view camera or recorded video."""
    is_file = video_path is not None
    cap = cv2.VideoCapture(video_path if is_file else camera_index)
    if not cap.isOpened():
        print("Unable to open video source")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 240.0 if is_file else 30.0

    writer = None
    frame_count = 0
    prev_gray = None
    tracker = BallKalmanTracker()
    recent_detections: List[Tuple[float, float, float]] = []
    trajectory: List[Tuple[float, float]] = []
    angles: List[Tuple[float, float]] = []
    live_start = time.perf_counter()
    calibration_ready = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        timestamp = _video_timestamp_seconds(cap, frame_count, fps, is_file, live_start)

        height, width = frame.shape[:2]
        if pitcher_x is None:
            current_pitcher_x = float(width * line_positions[0])
        else:
            current_pitcher_x = float(pitcher_x)
        if batter_x is None:
            current_batter_x = float(width * line_positions[1])
        else:
            current_batter_x = float(batter_x)
        calibration_ready = current_pitcher_x != current_batter_x

        if writer is None and save_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        kalman_pred = tracker.predict(timestamp)
        two_point_pred = _predict_from_two_points(recent_detections)
        predicted = kalman_pred or two_point_pred

        detection = _detect_moving_ball(
            prev_gray,
            gray,
            predicted=predicted,
            roi_radius=roi_radius,
        )
        prev_gray = gray

        center = None
        marker_center = None

        if detection is not None:
            x, y, radius = detection
            filtered_x, filtered_y = tracker.correct(x, y, timestamp)
            center = (filtered_x, filtered_y)
            recent_detections.append((timestamp, filtered_x, filtered_y))
            recent_detections = recent_detections[-4:]

            lo = min(current_pitcher_x, current_batter_x)
            hi = max(current_pitcher_x, current_batter_x)
            margin = abs(current_batter_x - current_pitcher_x) * 0.05
            if lo - margin <= filtered_x <= hi + margin:
                trajectory.append((timestamp, filtered_x))

            cv2.circle(frame, (int(filtered_x), int(filtered_y)), max(2, int(radius)), (0, 255, 0), 2)

        if predicted is not None:
            cv2.circle(frame, (int(predicted[0]), int(predicted[1])), 6, (255, 255, 0), 1)

        if marker_lower is not None and marker_upper is not None and center is not None:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            marker_mask = cv2.inRange(hsv, marker_lower, marker_upper)
            marker_cnts, _ = cv2.findContours(marker_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if marker_cnts:
                m = max(marker_cnts, key=cv2.contourArea)
                ((mx, my), mr) = cv2.minEnclosingCircle(m)
                if mr > 2:
                    marker_center = (float(mx), float(my))
                    cv2.circle(frame, (int(mx), int(my)), int(mr), (0, 255, 255), 2)
            if marker_center is not None:
                angle = math.degrees(
                    math.atan2(marker_center[1] - center[1], marker_center[0] - center[0])
                )
                angles.append((timestamp, angle))

        cv2.line(frame, (int(current_pitcher_x), 0), (int(current_pitcher_x), height), (255, 0, 0), 2)
        cv2.line(frame, (int(current_batter_x), 0), (int(current_batter_x), height), (0, 0, 255), 2)

        if writer is not None:
            writer.write(frame)

        cv2.imshow("Phase 1 Ball Speed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break

        # Stop once the tracked ball has traversed the calibrated measurement zone.
        if center is not None and trajectory:
            direction = 1 if current_batter_x > current_pitcher_x else -1
            if direction * (center[0] - current_batter_x) >= 0 and len(trajectory) >= 3:
                break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    if calibration_ready and len(trajectory) >= 3:
        result = estimate_speed_from_timed_trajectory(
            trajectory,
            pitcher_x=current_pitcher_x,
            batter_x=current_batter_x,
            known_distance_meters=known_distance_meters,
            initial_window=initial_window,
        )
        print(
            f"Initial speed: {result['mps']:.2f} m/s ({result['kmh']:.2f} km/h) "
            f"[n={result['inlier_count']}/{result['sample_count']}, "
            f"R2={result['r2']:.4f}, quality={result['quality']:.3f}]"
        )
        print(
            f"Full-track average: {result['average_mps']:.2f} m/s "
            f"({result['average_kmh']:.2f} km/h)"
        )

        if len(angles) >= 2:
            angle_values = [a for _, a in angles]
            duration = angles[-1][0] - angles[0][0]
            if duration > 0:
                rpm = calculate_spin_rpm(angle_values, duration)
                print(f"Spin: {rpm:.2f} rpm")

        if player_name:
            best, is_new = update_personal_record(player_name, result["kmh"], record_file)
            if is_new:
                print(f"New personal best for {player_name}: {best:.2f} km/h")
            else:
                print(f"Personal best for {player_name}: {best:.2f} km/h")
    else:
        print("Could not determine speed with enough valid trajectory data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 1 literature-inspired smartphone baseball speed estimator"
    )
    parser.add_argument("--distance", type=float, default=18.44)
    parser.add_argument("--video", type=str, default=None, help="Recorded high-FPS video path")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--pitcher-x", type=float, default=None, help="Pitcher-side calibration x pixel")
    parser.add_argument("--batter-x", type=float, default=None, help="Batter-side calibration x pixel")
    parser.add_argument("--roi-radius", type=int, default=100)
    parser.add_argument("--initial-window", type=int, default=10)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--player", type=str, default=None)
    parser.add_argument("--record-file", type=str, default="personal_records.json")
    parser.add_argument("--marker-lower", type=str, default=None)
    parser.add_argument("--marker-upper", type=str, default=None)
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
        video_path=args.video,
        pitcher_x=args.pitcher_x,
        batter_x=args.batter_x,
        save_path=args.output,
        player_name=args.player,
        record_file=args.record_file,
        marker_lower=parse_hsv(args.marker_lower),
        marker_upper=parse_hsv(args.marker_upper),
        roi_radius=args.roi_radius,
        initial_window=args.initial_window,
    )
