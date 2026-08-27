# Phase 1 — Literature-Inspired Smartphone Pitch Speed

## Goal

Measure baseball pitch speed using only a smartphone/video camera, with a
validation target of **MAE <= 3 km/h versus a radar reference** before Phase 1
is considered complete.

This phase intentionally focuses on velocity only. Spin, break and full 3D
trajectory metrics are later phases.

## Research basis

The implementation is inspired by two lines of prior work:

1. **Yamaguchi & Miura, "Real-time Analysis of Baseball Pitching Using Image
   Processing on Smartphone" (2016).**
   - high-frame-rate smartphone video (120/240 fps)
   - lateral/side-view measurement
   - known-distance calibration between pitcher and batter reference positions
   - inter-frame image differencing and morphology
   - prediction of the next ball location to limit the search area

2. **KFYO (2026), vision + biomechanics baseball pitch evaluation.**
   - object detection/tracking pipeline
   - Kalman filtering to stabilize ball tracking
   - temporal information used for velocity estimation

The current implementation does **not** claim to reproduce either paper
exactly. It combines those ideas into a practical Phase 1 baseline that can be
validated against radar.

## What is implemented

### Timestamp-based measurement

Recorded video uses OpenCV media timestamps (CAP_PROP_POS_MSEC) when available,
rather than assuming every frame interval equals exactly 1/FPS. Live capture
uses a monotonic clock.

### Side-view calibration

Two image x-coordinates represent a known real-world separation:

- `--pitcher-x`
- `--batter-x`
- `--distance` (18.44 m by default)

This converts pixel velocity to physical velocity.

### Motion-based ball detection

The detector uses consecutive-frame differencing, thresholding and morphology.
Candidate moving contours are scored for compactness, plausible size and
proximity to the predicted ball location.

### Predictive search region

The next location is predicted from tracking state, and detection is restricted
to a local ROI. A two-point constant-velocity predictor is also implemented as
an iPhoneSG-style fallback concept.

### Kalman tracking

A constant-velocity Kalman filter smooths centroid observations and provides a
prediction for the next frame.

### Robust velocity fitting

Velocity estimation uses multiple timestamped observations instead of only two
integer frame crossings. Tracking glitches are rejected with iterative
median-absolute-deviation residual filtering.

The earliest valid trajectory samples estimate an initial/radar-like velocity.
The full inlier trajectory is separately fit as a diagnostic average velocity.

### Quality diagnostics

Each measurement reports:

- initial speed
- full-track average speed
- sample/inlier count
- rejected point count
- R-squared
- a track-quality score

These values are diagnostics, not a substitute for radar validation.

## Recommended capture

For Phase 1 testing:

- use a **side view**
- prefer **240 fps**, otherwise 120 fps
- keep the phone fixed
- avoid digital zoom changes during the pitch
- make pitcher/batter calibration positions clearly identifiable
- use bright, even lighting and a visually simple background where possible

Example:

```bash
python real_time_ball_speed.py \
  --video pitch_240fps.mov \
  --pitcher-x 210 \
  --batter-x 1680 \
  --distance 18.44
```

## Validation protocol

Phase 1 is not finished merely because the code produces a number.

The required validation is simultaneous smartphone + radar measurement.
Collect at least 100 pitches over a useful speed range and report:

- mean absolute error (MAE)
- mean signed error / bias
- RMSE
- 95th percentile absolute error
- error versus pitch speed
- failure / rejected-measurement rate

**Pass criterion:** MAE <= 3 km/h against the chosen radar reference.

Only after that target is reached should the project move to Phase 2.
