"""Ball speed calculation utilities.

Phase 1 implements a literature-inspired smartphone velocity estimator:
calibration from two known field markers, real timestamps, robust outlier
rejection, early-trajectory regression, and full-trajectory diagnostics.

The legacy frame-index API is preserved for compatibility.
"""

from statistics import median
from typing import Sequence, Tuple


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
    return {"mps": speed_mps, "kmh": speed_mps * 3.6}


def _linear_fit(samples: Sequence[Tuple[float, float]]) -> Tuple[float, float, float]:
    """Return slope, intercept and R-squared for time/x samples."""
    if len(samples) < 2:
        raise ValueError("at least two samples are required")

    ts = [float(t) for t, _ in samples]
    xs = [float(x) for _, x in samples]
    mean_t = sum(ts) / len(ts)
    mean_x = sum(xs) / len(xs)
    denom = sum((t - mean_t) ** 2 for t in ts)
    if denom <= 0:
        raise ValueError("trajectory samples must span multiple timestamps")

    slope = sum((t - mean_t) * (x - mean_x) for t, x in zip(ts, xs)) / denom
    intercept = mean_x - slope * mean_t
    predicted = [intercept + slope * t for t in ts]
    ss_res = sum((x - pred) ** 2 for x, pred in zip(xs, predicted))
    ss_tot = sum((x - mean_x) ** 2 for x in xs)
    r2 = 1.0 if ss_tot == 0 and ss_res == 0 else (0.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot)
    return slope, intercept, r2


def _reject_outliers(
    samples: Sequence[Tuple[float, float]],
    max_iterations: int = 3,
    outlier_sigma: float = 3.5,
    minimum_pixel_threshold: float = 2.0,
) -> list[Tuple[float, float]]:
    """Reject tracking glitches with iterative MAD residual filtering."""
    kept = list(samples)
    if len(kept) < 4:
        return kept

    for _ in range(max_iterations):
        slope, intercept, _ = _linear_fit(kept)
        residuals = [x - (intercept + slope * t) for t, x in kept]
        center = median(residuals)
        deviations = [abs(r - center) for r in residuals]
        mad = median(deviations)
        robust_sigma = 1.4826 * mad
        threshold = max(minimum_pixel_threshold, outlier_sigma * robust_sigma)

        filtered = [
            sample
            for sample, residual in zip(kept, residuals)
            if abs(residual - center) <= threshold
        ]
        if len(filtered) < 3 or len(filtered) == len(kept):
            break
        kept = filtered

    return kept


def estimate_speed_from_timed_trajectory(
    samples: Sequence[Tuple[float, float]],
    pitcher_x: float,
    batter_x: float,
    known_distance_meters: float = 18.44,
    initial_window: int = 10,
    max_outlier_iterations: int = 3,
    outlier_sigma: float = 3.5,
) -> dict:
    """Estimate radar-like initial velocity from timestamped ball positions.

    pitcher_x and batter_x are image x-coordinates of two field markers with a
    known real-world separation. The earliest valid points estimate initial
    velocity; the complete inlier trajectory is also fit for quality checks.
    """
    if known_distance_meters <= 0:
        raise ValueError("known_distance_meters must be greater than 0")
    if pitcher_x == batter_x:
        raise ValueError("pitcher_x and batter_x must be different")
    if len(samples) < 3:
        raise ValueError("at least three timed trajectory samples are required")
    if initial_window < 3:
        raise ValueError("initial_window must be at least 3")

    ordered = sorted((float(t), float(x)) for t, x in samples)
    timestamps = [t for t, _ in ordered]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("trajectory timestamps must be unique")

    t0 = timestamps[0]
    normalized = [(t - t0, x) for t, x in ordered]
    inliers = _reject_outliers(
        normalized,
        max_iterations=max_outlier_iterations,
        outlier_sigma=outlier_sigma,
    )
    if len(inliers) < 3:
        raise ValueError("too few inlier trajectory samples")

    meters_per_pixel = known_distance_meters / abs(float(batter_x) - float(pitcher_x))

    full_slope, _, full_r2 = _linear_fit(inliers)
    early = inliers[: min(initial_window, len(inliers))]
    initial_slope, _, initial_r2 = _linear_fit(early)

    initial_mps = abs(initial_slope) * meters_per_pixel
    average_mps = abs(full_slope) * meters_per_pixel
    duration = inliers[-1][0] - inliers[0][0]
    inlier_ratio = len(inliers) / len(normalized)
    quality = max(0.0, min(1.0, full_r2)) * inlier_ratio

    return {
        "mps": initial_mps,
        "kmh": initial_mps * 3.6,
        "average_mps": average_mps,
        "average_kmh": average_mps * 3.6,
        "r2": full_r2,
        "initial_r2": initial_r2,
        "quality": quality,
        "sample_count": len(normalized),
        "inlier_count": len(inliers),
        "rejected_count": len(normalized) - len(inliers),
        "px_per_second": initial_slope,
        "meters_per_pixel": meters_per_pixel,
        "duration_seconds": duration,
    }


def estimate_speed_from_trajectory(
    samples: Sequence[Tuple[int, float]],
    video_fps: float,
    line1_x: float,
    line2_x: float,
    known_distance_meters: float,
) -> dict:
    """Compatibility wrapper for frame-index trajectory samples."""
    if video_fps <= 0:
        raise ValueError("video_fps must be greater than 0")
    if len(samples) < 3:
        raise ValueError("at least three trajectory samples are required")

    ordered = sorted(samples, key=lambda item: item[0])
    frames = [float(frame) for frame, _ in ordered]
    if len(set(frames)) != len(frames):
        raise ValueError("trajectory samples must have unique frame numbers")
    first_frame = frames[0]
    timed = [
        ((float(frame) - first_frame) / video_fps, float(x))
        for frame, x in ordered
    ]
    return estimate_speed_from_timed_trajectory(
        timed,
        pitcher_x=line1_x,
        batter_x=line2_x,
        known_distance_meters=known_distance_meters,
        initial_window=min(10, len(timed)),
    )


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
