"""
Ball speed calculation utilities.

Phase 1 adds trajectory-based speed estimation so that speed can be inferred
from many tracked video frames instead of only two integer frame crossings.
"""

from typing import Iterable, Sequence, Tuple


def calculate_speed(start_frame: int, end_frame: int, video_fps: float, known_distance_meters: float) -> dict:
    """Calculate average speed from two frame indices and a known distance."""
    if video_fps <= 0:
        raise ValueError("video_fps must be greater than 0")
    if start_frame >= end_frame:
        raise ValueError("start_frame must be less than end_frame")
    if known_distance_meters <= 0:
        raise ValueError("known_distance_meters must be greater than 0")

    time_seconds = (end_frame - start_frame) / video_fps
    speed_mps = known_distance_meters / time_seconds
    speed_kmh = speed_mps * 3.6

    return {"mps": speed_mps, "kmh": speed_kmh}


def estimate_speed_from_trajectory(
    samples: Sequence[Tuple[int, float]],
    video_fps: float,
    line1_x: float,
    line2_x: float,
    known_distance_meters: float,
) -> dict:
    """Estimate ball speed from all tracked positions using linear regression.

    ``samples`` contains ``(frame_number, x_pixel)`` observations. The physical
    scale is inferred from the known real-world distance between ``line1_x`` and
    ``line2_x``. A least-squares fit estimates pixel velocity from every sample,
    reducing sensitivity to one-frame crossing errors.

    Returns ``mps``, ``kmh``, ``r2``, ``sample_count`` and ``px_per_second``.
    ``r2`` is useful as a basic confidence signal: values near 1 indicate a very
    consistent trajectory over the measured segment.
    """
    if video_fps <= 0:
        raise ValueError("video_fps must be greater than 0")
    if known_distance_meters <= 0:
        raise ValueError("known_distance_meters must be greater than 0")
    if line1_x == line2_x:
        raise ValueError("line positions must be different")
    if len(samples) < 3:
        raise ValueError("at least three trajectory samples are required")

    ordered = sorted(samples, key=lambda item: item[0])
    frames = [float(frame) for frame, _ in ordered]
    xs = [float(x) for _, x in ordered]

    if len(set(frames)) != len(frames):
        raise ValueError("trajectory samples must have unique frame numbers")

    # Convert frame indices to seconds relative to the first observation. Using
    # relative times improves numerical conditioning for large frame numbers.
    first_frame = frames[0]
    times = [(frame - first_frame) / video_fps for frame in frames]

    mean_t = sum(times) / len(times)
    mean_x = sum(xs) / len(xs)
    denominator = sum((t - mean_t) ** 2 for t in times)
    if denominator == 0:
        raise ValueError("trajectory samples must span multiple frames")

    slope_px_per_second = sum(
        (t - mean_t) * (x - mean_x) for t, x in zip(times, xs)
    ) / denominator
    intercept = mean_x - slope_px_per_second * mean_t

    predicted = [intercept + slope_px_per_second * t for t in times]
    ss_res = sum((x - pred) ** 2 for x, pred in zip(xs, predicted))
    ss_tot = sum((x - mean_x) ** 2 for x in xs)
    r2 = 1.0 if ss_tot == 0 and ss_res == 0 else (0.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot)

    meters_per_pixel = known_distance_meters / abs(line2_x - line1_x)
    speed_mps = abs(slope_px_per_second) * meters_per_pixel

    return {
        "mps": speed_mps,
        "kmh": speed_mps * 3.6,
        "r2": r2,
        "sample_count": len(samples),
        "px_per_second": slope_px_per_second,
    }


def calculate_spin_rpm(angles_deg: list[float], time_seconds: float) -> float:
    """Calculate spin rate in RPM from a sequence of orientation angles."""
    if time_seconds <= 0:
        raise ValueError("time_seconds must be greater than 0")
    if len(angles_deg) < 2:
        raise ValueError("at least two angle samples are required")

    total_change = 0.0
    prev = angles_deg[0]
    for angle in angles_deg[1:]:
        delta = angle - prev
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        total_change += delta
        prev = angle

    rotations = abs(total_change) / 360.0
    return rotations / time_seconds * 60.0


if __name__ == "__main__":
    speeds = calculate_speed(10, 40, 60.0, 18.44)
    print(f"Speed: {speeds['mps']:.2f} m/s ({speeds['kmh']:.2f} km/h)")
