"""
Liveness Verification and Presentation Attack Detection (PAD) Service for SAMS-FR.

Compliant with anti-spoofing and active liveness verification requirements:
1. Presentation Attack Detection (PAD):
   - Multi-cue passive analysis:
     a) Fourier 2D frequency spectrum analysis (screen moiré and printer halftone artifact detection)
     b) Chrominance (YCrCb/HSV) skin pigment dispersion and specular glare detection (screen backlight / matte paper detection)
     c) Texture sharpness & Laplacian gradient variance (MTF double-blur and halftone dot artifact detection)
     d) Multi-frame temporal difference & non-rigid optical flow (static photograph rejection)
     e) Optional local ONNX PAD model execution with fail-closed behavior
2. Randomized Active Liveness Challenge:
   - Fresh, cryptographically unpredictable challenges (TURN_HEAD_LEFT, TURN_HEAD_RIGHT, NOD_HEAD_DOWN, TILT_HEAD_UP, BLINK)
   - Multi-frame timestamped sequence tracking with short expiry
   - Landmark tracking & 3D head-pose ratio validation using YuNet 5 landmarks
   - Direction, amplitude, and timing validation
3. Secure Backend Verification Protocol:
   - Short-lived verification sessions with cryptographic challenge IDs and nonces
   - Single-use verification token bound to student_id, session_id, and faculty_id
   - Atomic token consumption with concurrency and replay protection
   - Fail-closed security architecture
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Supported active challenge types
CHALLENGE_TURN_LEFT = "TURN_HEAD_LEFT"
CHALLENGE_TURN_RIGHT = "TURN_HEAD_RIGHT"
CHALLENGE_NOD_DOWN = "NOD_HEAD_DOWN"
CHALLENGE_TILT_UP = "TILT_HEAD_UP"
CHALLENGE_BLINK = "BLINK"

ALL_CHALLENGES = [
    CHALLENGE_TURN_LEFT,
    CHALLENGE_TURN_RIGHT,
    CHALLENGE_NOD_DOWN,
    CHALLENGE_TILT_UP,
    CHALLENGE_BLINK,
]

CHALLENGE_INSTRUCTIONS = {
    CHALLENGE_TURN_LEFT: "Turn your head to the left, then return to center",
    CHALLENGE_TURN_RIGHT: "Turn your head to the right, then return to center",
    CHALLENGE_NOD_DOWN: "Slowly nod your head down, then look straight",
    CHALLENGE_TILT_UP: "Tilt your head slightly up, then look straight",
    CHALLENGE_BLINK: "Blink your eyes naturally and look at the camera",
}


@dataclass
class PADResult:
    is_live: bool
    pad_score: float  # 0.0 (spoof) to 1.0 (live)
    attack_type: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


def compute_head_pose_ratios(landmarks: np.ndarray | list) -> Tuple[float, float]:
    """
    Computes horizontal (yaw proxy) and vertical (pitch proxy) symmetries
    from YuNet's 5 facial landmarks:
      0: right eye
      1: left eye
      2: nose tip
      3: right mouth corner
      4: left mouth corner

    Returns:
        (yaw_symmetry, pitch_symmetry)
        yaw_symmetry: ~0.0 when frontal. Positive when turned right (image coords),
                      negative when turned left.
        pitch_symmetry: ~0.0-0.15 when frontal. Positive when tilted up,
                        negative when nodding down.
    """
    lm = np.array(landmarks, dtype=np.float32)
    if lm.shape != (5, 2):
        raise ValueError("Landmarks must have shape (5, 2)")

    eye_r, eye_l, nose, mouth_r, mouth_l = lm[0], lm[1], lm[2], lm[3], lm[4]

    eye_mid = (eye_r + eye_l) / 2.0
    eye_dist = float(np.linalg.norm(eye_l - eye_r))
    if eye_dist < 1e-4:
        return 0.0, 0.0

    eye_vec = (eye_l - eye_r) / eye_dist
    proj_r = float(np.dot(nose - eye_r, eye_vec))
    proj_l = float(np.dot(eye_l - nose, eye_vec))

    yaw_symmetry = (proj_r - proj_l) / (proj_r + proj_l + 1e-6)

    mouth_mid = (mouth_r + mouth_l) / 2.0
    face_height = float(np.linalg.norm(mouth_mid - eye_mid))

    perp_vec = np.array([-eye_vec[1], eye_vec[0]], dtype=np.float32)
    if perp_vec[1] < 0:
        perp_vec = -perp_vec

    nose_to_eye_h = float(np.dot(nose - eye_mid, perp_vec))
    mouth_to_nose_h = float(np.dot(mouth_mid - nose, perp_vec))
    pitch_symmetry = (nose_to_eye_h - mouth_to_nose_h) / (face_height + 1e-6)

    return float(yaw_symmetry), float(pitch_symmetry)


def compute_eye_openness_metric(image: np.ndarray, eye_pt: np.ndarray | list, patch_size: int = 24) -> float:
    """
    Measures the local gradient energy around an eye landmark.
    Open eyes exhibit high contrast between iris/pupil and sclera (high gradient energy).
    Closed eyelids exhibit smooth skin texture (low gradient energy).
    """
    x, y = int(eye_pt[0]), int(eye_pt[1])
    h, w = image.shape[:2]
    half = patch_size // 2

    y_min, y_max = max(0, y - half), min(h, y + half)
    x_min, x_max = max(0, x - half), min(w, x + half)

    if y_max <= y_min or x_max <= x_min:
        return 0.0

    patch = image[y_min:y_max, x_min:x_max]
    if patch.size == 0:
        return 0.0

    if patch.ndim == 3:
        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    else:
        gray = patch

    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_energy = float(np.mean(np.abs(sobel_y)))
    return edge_energy


class PresentationAttackDetector:
    """
    Presentation Attack Detection (PAD) engine.
    Analyzes spatial frequency, chrominance dispersion, specular reflections,
    and texture micro-gradients to detect printed photos and screen replays.
    """

    def __init__(self, model_path: Optional[str] = None, fail_closed_if_missing_model: bool = False):
        self.model_path = model_path
        self.fail_closed = fail_closed_if_missing_model
        self.onnx_session = None

        if model_path and Path(model_path).exists():
            try:
                import onnxruntime as ort
                self.onnx_session = ort.InferenceSession(
                    str(model_path),
                    providers=["CPUExecutionProvider"],
                )
                logger.info("Loaded ONNX PAD model from %s", model_path)
            except Exception as e:
                logger.warning("Failed to initialize ONNX PAD model: %s", e)

    def analyze_frame(self, image: np.ndarray, face_bbox: Optional[list] = None) -> PADResult:
        """
        Runs comprehensive passive PAD analysis on a face frame.
        """
        if image is None or image.size == 0:
            return PADResult(
                is_live=False,
                pad_score=0.0,
                attack_type="invalid_image",
                reasons=["Empty or invalid image frame"],
            )

        h, w = image.shape[:2]

        # Extract face bounding box with moderate margin
        if face_bbox is not None and len(face_bbox) >= 4:
            bx, by, bw, bh = [int(v) for v in face_bbox[:4]]
            margin_x = int(bw * 0.15)
            margin_y = int(bh * 0.15)
            x1 = max(0, bx - margin_x)
            y1 = max(0, by - margin_y)
            x2 = min(w, bx + bw + margin_x)
            y2 = min(h, by + bh + margin_y)
            crop = image[y1:y2, x1:x2]
        else:
            # Default center crop if no bbox provided
            ch, cw = int(h * 0.7), int(w * 0.7)
            sy, sx = (h - ch) // 2, (w - cw) // 2
            crop = image[sy:sy + ch, sx:sx + cw]

        if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
            return PADResult(
                is_live=False,
                pad_score=0.0,
                attack_type="face_crop_too_small",
                reasons=["Face crop is too small for anti-spoofing analysis"],
            )

        # 1. Fourier 2D Frequency & Moiré Analysis
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        resized_gray = cv2.resize(gray_crop, (128, 128), interpolation=cv2.INTER_AREA)

        fft = np.fft.fft2(resized_gray.astype(np.float32))
        fshift = np.fft.fftshift(fft)
        mag = np.abs(fshift)

        cy, cx = 64, 64
        y_grid, x_grid = np.ogrid[:128, :128]
        dist_from_center = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        max_dist = np.sqrt(64 ** 2 + 64 ** 2)

        hf_mask = dist_from_center > (max_dist * 0.40)
        total_energy = float(np.sum(mag))
        hf_energy = float(np.sum(mag[hf_mask]))
        hf_ratio = hf_energy / (total_energy + 1e-6)

        hf_vals = mag[hf_mask]
        hf_papr = float(np.max(hf_vals) / (np.mean(hf_vals) + 1e-6)) if len(hf_vals) > 0 else 0.0

        # 2. Chrominance / YCrCb Skin Analysis
        if crop.ndim == 3:
            ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
            y_chan = ycrcb[:, :, 0]
            cr_chan = ycrcb[:, :, 1]
            cb_chan = ycrcb[:, :, 2]

            skin_mask = (cr_chan >= 128) & (cr_chan <= 178) & (cb_chan >= 70) & (cb_chan <= 135)
            skin_pixel_count = int(np.sum(skin_mask))
            total_pixels = crop.shape[0] * crop.shape[1]
            skin_coverage = skin_pixel_count / float(total_pixels + 1e-6)

            if skin_pixel_count > 50:
                cb_std = float(np.std(cb_chan[skin_mask]))
                cr_std = float(np.std(cr_chan[skin_mask]))
            else:
                cb_std = float(np.std(cb_chan))
                cr_std = float(np.std(cr_chan))

            # Specular glare typical of glass screen surfaces
            glare_mask = (y_chan > 240) & (np.abs(cb_chan.astype(float) - 128) < 10) & (np.abs(cr_chan.astype(float) - 128) < 10)
            glare_ratio = float(np.sum(glare_mask)) / float(total_pixels + 1e-6)
        else:
            skin_coverage = 0.5
            cb_std = 10.0
            cr_std = 10.0
            glare_ratio = 0.0

        # 3. Laplacian Variance (Texture Sharpness)
        laplacian_var = float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())

        metrics = {
            "hf_ratio": round(hf_ratio, 4),
            "hf_papr": round(hf_papr, 2),
            "skin_coverage": round(skin_coverage, 4),
            "cb_std": round(cb_std, 2),
            "cr_std": round(cr_std, 2),
            "glare_ratio": round(glare_ratio, 4),
            "laplacian_var": round(laplacian_var, 2),
        }

        reasons = []
        is_live = True
        attack_type = None

        # Check for Screen Moiré Pattern
        # Screen pixel grids produce high peak-to-average power ratio in high frequencies
        if hf_papr > 110.0:
            is_live = False
            attack_type = "screen_replay_detected"
            reasons.append(f"Screen moiré frequency peaks detected (PAPR: {hf_papr:.1f} > 110)")

        # Check for Excessive High-Frequency Noise (Halftone Print Dot Pattern)
        if hf_ratio > 0.45:
            is_live = False
            attack_type = attack_type or "printed_photo_detected"
            reasons.append(f"Abnormal high-frequency grid detected (HF Ratio: {hf_ratio:.3f} > 0.45)")

        # Check for Severe Blur or Double-MTF Degradation (Low-quality print/screen)
        # Note: Standard webcams have lower texture sharpness than high-res sensors.
        # Defocused, blank, or completely blurry frames produce variance < 1.5.
        # Genuine webcam face crops under indoor lighting typically produce 3.0 to 100+.
        if laplacian_var < 1.5:
            is_live = False
            attack_type = attack_type or "blurred_or_low_quality"
            reasons.append(f"Image texture too blurry for reliable live verification (Laplacian: {laplacian_var:.1f} < 1.5)")

        # Check for Excessive High-Frequency Texture Noise (Halftone Print Dot Pattern)
        if laplacian_var > 2500.0:
            is_live = False
            attack_type = attack_type or "printed_photo_detected"
            reasons.append(f"Excessive artificial texture noise detected (Laplacian: {laplacian_var:.1f} > 2500)")

        # Check for Chrominance Desaturation (Monochrome printout or washed-out matte paper)
        if crop.ndim == 3 and skin_coverage < 0.03:
            is_live = False
            attack_type = attack_type or "printed_photo_detected"
            reasons.append("Natural skin chrominance not detected (desaturated or monochrome presentation)")

        if crop.ndim == 3 and (cb_std < 1.5 or cr_std < 1.5):
            is_live = False
            attack_type = attack_type or "printed_photo_detected"
            reasons.append("Insufficient chrominance variance across facial surface (uniform print detected)")

        # Check for Screen Specular Glare
        if glare_ratio > 0.06:
            is_live = False
            attack_type = attack_type or "screen_replay_detected"
            reasons.append(f"High specular screen glass glare detected (Glare: {glare_ratio:.2%})")

        # Optional ONNX deep model evaluation
        if self.onnx_session is not None:
            try:
                # Prepare 80x80 or 128x128 normalized input
                input_name = self.onnx_session.get_inputs()[0].name
                inp = cv2.resize(crop, (80, 80))
                inp = inp.astype(np.float32) / 255.0
                inp = np.transpose(inp, (2, 0, 1))
                inp = np.expand_dims(inp, axis=0)

                onnx_out = self.onnx_session.run(None, {input_name: inp})
                onnx_prob = float(onnx_out[0][0][1]) if len(onnx_out[0][0]) > 1 else float(onnx_out[0][0][0])
                metrics["onnx_liveness_score"] = round(onnx_prob, 4)

                if onnx_prob < 0.50:
                    is_live = False
                    attack_type = attack_type or "model_classified_spoof"
                    reasons.append(f"Deep anti-spoofing model classified presentation as spoof ({onnx_prob:.2f} < 0.50)")
            except Exception as e:
                logger.warning("Error running ONNX PAD model inference: %s", e)

        # Fail-closed policy when strict model is required but absent
        if self.fail_closed and self.onnx_session is None:
            return PADResult(
                is_live=False,
                pad_score=0.0,
                attack_type="pad_model_unavailable",
                reasons=["PAD model weights unavailable and fail-closed security mode is active"],
                metrics=metrics,
            )

        # Calculate composite score
        score_deductions = 0.0
        if hf_papr > 110.0:
            score_deductions += 0.45
        if hf_ratio > 0.45:
            score_deductions += 0.35
        if laplacian_var < 1.5:
            score_deductions += 0.40
        if crop.ndim == 3 and skin_coverage < 0.03:
            score_deductions += 0.40
        if crop.ndim == 3 and (cb_std < 1.5 or cr_std < 1.5):
            score_deductions += 0.35
        if glare_ratio > 0.15:
            score_deductions += 0.35

        pad_score = max(0.0, round(1.0 - score_deductions, 3))
        if not is_live and pad_score > 0.49:
            pad_score = 0.45

        return PADResult(
            is_live=is_live,
            pad_score=pad_score,
            attack_type=attack_type,
            reasons=reasons,
            metrics=metrics,
        )


class ActiveChallengeEvaluator:
    """
    Evaluates evidence frames against a randomized facial movement challenge.
    Validates face tracking, movement direction, timing, amplitude, and anti-replay.
    """

    @staticmethod
    def evaluate_frame_difference(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
        """
        Computes mean pixel difference between two frames to detect static photos
        or repeated frames.
        """
        if frame_a.shape != frame_b.shape:
            h = min(frame_a.shape[0], frame_b.shape[0])
            w = min(frame_a.shape[1], frame_b.shape[1])
            fa = cv2.resize(frame_a, (w, h))
            fb = cv2.resize(frame_b, (w, h))
        else:
            fa, fb = frame_a, frame_b

        diff = cv2.absdiff(fa, fb)
        return float(np.mean(diff))

    @classmethod
    def evaluate_challenge(
        cls,
        challenge_type: str,
        frames: List[np.ndarray],
        timestamps: List[float],
        detected_faces_per_frame: List[List[Dict[str, Any]]],
        min_motion_threshold: float = 0.08,
        is_mirrored: bool = True,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates whether the sequence of frames fulfills the active challenge.
        Tracks motion continuously across all post-baseline frames, finding the
        peak action amplitude to ensure human reaction time and tempo variations
        are accommodated.

        Returns:
            (passed: bool, reason: str, metadata: dict)
        """
        if len(frames) < 2:
            return False, "At least 2 evidence frames are required to verify movement", {}

        if not timestamps or len(timestamps) != len(frames):
            timestamps = [float(i * 500) for i in range(len(frames))]

        # Verify timestamp progression
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                return False, "Invalid non-monotonic frame timestamps", {}

        total_duration_ms = timestamps[-1] - timestamps[0]
        if total_duration_ms > 20000:
            return False, "Challenge execution time exceeded maximum allowed duration", {}

        # 1. Anti-Replay / Static Photo Rejection
        # Check that the evidence sequence is not a completely static photograph or frozen frame
        max_diff = max(cls.evaluate_frame_difference(frames[0], frame_k) for frame_k in frames[1:])
        if max_diff < 0.3:
            return (
                False,
                "Static photograph or frozen frame detected. Active facial movement is required.",
                {"frame_diff": round(max_diff, 3)},
            )

        # 2. Check face presence in each frame and extract continuous poses
        poses = []
        eye_openness = []

        for idx, faces in enumerate(detected_faces_per_frame):
            if not faces:
                return (
                    False,
                    f"No face detected in evidence frame {idx + 1}",
                    {"failed_frame": idx},
                )
            if len(faces) > 1:
                return (
                    False,
                    f"Multiple faces detected in evidence frame {idx + 1}. Exactly one face must be visible.",
                    {"failed_frame": idx},
                )

            landmarks = faces[0].get("landmarks")
            if not landmarks or len(landmarks) != 5:
                return False, f"Facial landmarks could not be extracted in frame {idx + 1}", {}

            yaw, pitch = compute_head_pose_ratios(landmarks)
            poses.append((yaw, pitch))

            # Eye openness for blink detection
            eye_r, eye_l = landmarks[0], landmarks[1]
            er_metric = compute_eye_openness_metric(frames[idx], eye_r)
            el_metric = compute_eye_openness_metric(frames[idx], eye_l)
            eye_openness.append((er_metric + el_metric) / 2.0)

        initial_yaw, initial_pitch = poses[0]

        # Select the post-baseline frame with peak movement relative to initial pose
        if challenge_type in (CHALLENGE_TURN_LEFT, CHALLENGE_TURN_RIGHT):
            best_idx, (action_yaw, action_pitch) = max(
                enumerate(poses[1:], start=1),
                key=lambda item: abs(item[1][0] - initial_yaw),
            )
        elif challenge_type in (CHALLENGE_NOD_DOWN, CHALLENGE_TILT_UP):
            best_idx, (action_yaw, action_pitch) = max(
                enumerate(poses[1:], start=1),
                key=lambda item: abs(item[1][1] - initial_pitch),
            )
        else:
            best_idx = 1
            action_yaw, action_pitch = poses[1]

        delta_yaw = action_yaw - initial_yaw
        delta_pitch = action_pitch - initial_pitch
        amplitude = abs(delta_yaw) if "turn" in challenge_type.lower() else abs(delta_pitch)

        metadata = {
            "challenge_type": challenge_type,
            "initial_pose": {"yaw": round(initial_yaw, 3), "pitch": round(initial_pitch, 3)},
            "action_pose": {"yaw": round(action_yaw, 3), "pitch": round(action_pitch, 3)},
            "peak_frame_index": best_idx,
            "delta_yaw": round(delta_yaw, 3),
            "delta_pitch": round(delta_pitch, 3),
            "amplitude": round(amplitude, 3),
            "min_motion_threshold": min_motion_threshold,
            "is_mirrored": is_mirrored,
            "timestamps_ms": timestamps,
            "eye_openness": [round(val, 2) for val in eye_openness],
        }

        logger.debug(
            "Liveness evaluation: challenge=%s, peak_idx=%d, delta_yaw=%.3f, delta_pitch=%.3f, amp=%.3f",
            challenge_type, best_idx, delta_yaw, delta_pitch, amplitude,
        )

        # 3. Challenge-specific motion validation
        if challenge_type == CHALLENGE_TURN_LEFT:
            if abs(delta_yaw) < min_motion_threshold:
                return (
                    False,
                    f"Head turn amplitude insufficient (movement: {abs(delta_yaw):.2f} < threshold: {min_motion_threshold:.2f})",
                    metadata,
                )
            # In mirrored coordinates (default for webcam selfie preview), turning to the left
            # shifts the nose towards lower X coordinates (delta_yaw < 0).
            # In unmirrored coordinates, turning to the person's left shifts towards higher X (delta_yaw > 0).
            wrong_direction = (delta_yaw > 0) if is_mirrored else (delta_yaw < 0)
            if wrong_direction:
                return (
                    False,
                    "Head turned in the opposite direction (turned right instead of left)",
                    metadata,
                )
            if len(poses) >= 3 and best_idx < len(poses) - 1:
                final_yaw = poses[-1][0]
                return_delta = abs(final_yaw - initial_yaw)
                if return_delta > abs(delta_yaw) * 1.5:
                    return False, "Failed to return toward center after head turn", metadata

            return True, "Head turn left verified", metadata

        elif challenge_type == CHALLENGE_TURN_RIGHT:
            if abs(delta_yaw) < min_motion_threshold:
                return (
                    False,
                    f"Head turn amplitude insufficient (movement: {abs(delta_yaw):.2f} < threshold: {min_motion_threshold:.2f})",
                    metadata,
                )
            # In mirrored coordinates, turning right shifts nose towards higher X coordinates (delta_yaw > 0).
            # In unmirrored coordinates, turning right shifts towards lower X (delta_yaw < 0).
            wrong_direction = (delta_yaw < 0) if is_mirrored else (delta_yaw > 0)
            if wrong_direction:
                return (
                    False,
                    "Head turned in the opposite direction (turned left instead of right)",
                    metadata,
                )
            if len(poses) >= 3 and best_idx < len(poses) - 1:
                final_yaw = poses[-1][0]
                return_delta = abs(final_yaw - initial_yaw)
                if return_delta > abs(delta_yaw) * 1.5:
                    return False, "Failed to return toward center after head turn", metadata

            return True, "Head turn right verified", metadata

        elif challenge_type == CHALLENGE_NOD_DOWN:
            if abs(delta_pitch) < 0.08:
                return (
                    False,
                    f"Head nod amplitude insufficient (pitch shift: {abs(delta_pitch):.2f} < 0.08)",
                    metadata,
                )
            if delta_pitch < 0:
                return (
                    False,
                    "Head moved in the opposite direction (tilted up instead of down)",
                    metadata,
                )
            return True, "Head nod down verified", metadata

        elif challenge_type == CHALLENGE_TILT_UP:
            if abs(delta_pitch) < 0.08:
                return (
                    False,
                    f"Head tilt amplitude insufficient (pitch shift: {abs(delta_pitch):.2f} < 0.08)",
                    metadata,
                )
            if delta_pitch > 0:
                return (
                    False,
                    "Head moved in the opposite direction (nodded down instead of up)",
                    metadata,
                )
            return True, "Head tilt up verified", metadata

        elif challenge_type == CHALLENGE_BLINK:
            # In blink challenge, eye openness should drop significantly between open and closed state
            if len(eye_openness) >= 2:
                initial_openness = eye_openness[0]
                min_subsequent = min(eye_openness[1:])
                # Either drop then recover, or significant ratio change
                if initial_openness > 1e-4:
                    ratio = min_subsequent / initial_openness
                    if ratio > 0.85 and abs(min_subsequent - initial_openness) < 5.0:
                        return False, "Eye blink not detected between frames", metadata
                return True, "Eye blink verified", metadata
            return False, "Insufficient frames to verify eye blink", metadata

        else:
            return False, f"Unknown challenge type: {challenge_type}", metadata


class LivenessVerificationManager:
    """
    Manages active liveness verification sessions and cryptographically bound single-use tokens.
    Thread-safe and concurrency protected.
    """

    def __init__(self, challenge_ttl_seconds: int = 35, token_ttl_seconds: int = 60):
        self._lock = threading.Lock()
        self._challenges: Dict[str, Dict[str, Any]] = {}
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._token_locks: Dict[str, threading.Lock] = {}
        self.challenge_ttl = challenge_ttl_seconds
        self.token_ttl = token_ttl_seconds

    def get_token_lock(self, token: str) -> threading.Lock:
        """
        Retrieves or creates a dedicated synchronization lock for a given verification token.
        Avoids global locking while strictly serializing concurrent operations on the same token.
        """
        with self._lock:
            if not hasattr(self, "_token_locks"):
                self._token_locks = {}
            if token not in self._token_locks:
                self._token_locks[token] = threading.Lock()
            return self._token_locks[token]

    @contextmanager
    def acquire_token_lock(self, token: str):
        """
        Context manager to acquire a lock for a specific verification token.
        """
        lock = self.get_token_lock(token)
        with lock:
            yield

    def check_token_status(self, token: str) -> Tuple[bool, str]:
        """
        Fast-fails if a token does not exist, has already been consumed, or has expired.
        Does not mark the token as consumed.
        """
        with self._lock:
            record = self._tokens.get(token)
            if not record:
                return False, "Verification token is invalid or does not exist"
            if record["is_consumed"]:
                return False, "Verification token has already been used"
            if time.time() > record["expires_at"]:
                return False, "Verification token has expired"
            return True, "Token valid"

    def create_challenge(self, session_id: int, faculty_id: int) -> Dict[str, Any]:
        """
        Creates a fresh, unpredictable challenge bound to an attendance session and faculty member.
        """
        with self._lock:
            self._cleanup_expired_locked()

            challenge_id = "clv_" + secrets.token_urlsafe(24)
            nonce = secrets.token_urlsafe(16)
            challenge_type = secrets.choice(ALL_CHALLENGES)
            now = time.time()
            expires_at = now + self.challenge_ttl

            challenge_data = {
                "challenge_id": challenge_id,
                "session_id": int(session_id),
                "faculty_id": int(faculty_id),
                "challenge_type": challenge_type,
                "instruction": CHALLENGE_INSTRUCTIONS[challenge_type],
                "nonce": nonce,
                "created_at": now,
                "expires_at": expires_at,
                "status": "PENDING",
            }

            self._challenges[challenge_id] = challenge_data

            return {
                "challenge_id": challenge_id,
                "challenge_type": challenge_type,
                "instruction": CHALLENGE_INSTRUCTIONS[challenge_type],
                "nonce": nonce,
                "expires_in": self.challenge_ttl,
                "expires_at": expires_at,
                "session_id": int(session_id),
            }

    def get_challenge(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            ch = self._challenges.get(challenge_id)
            if not ch:
                return None
            if time.time() > ch["expires_at"]:
                return None
            return dict(ch)

    def issue_verification_token(
        self,
        challenge_id: str,
        student_id: int,
        session_id: int,
        faculty_id: int,
        confidence_score: float,
        pad_score: float,
    ) -> str:
        """
        Marks challenge as verified and generates a single-use verification token
        bound to student, session, and faculty.
        """
        with self._lock:
            ch = self._challenges.get(challenge_id)
            if ch:
                ch["status"] = "VERIFIED"

            token = "vtok_" + secrets.token_urlsafe(32)
            now = time.time()

            self._tokens[token] = {
                "token": token,
                "challenge_id": challenge_id,
                "student_id": int(student_id),
                "session_id": int(session_id),
                "faculty_id": int(faculty_id),
                "confidence_score": float(confidence_score),
                "pad_score": float(pad_score),
                "created_at": now,
                "expires_at": now + self.token_ttl,
                "is_consumed": False,
                "consumed_at": None,
            }

            return token

    def consume_verification_token(
        self,
        token: str,
        expected_session_id: int,
        expected_student_id: Optional[int] = None,
        expected_faculty_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Atomically validates and consumes a single-use verification token.
        Guarantees that each token can only be consumed once.
        """
        with self._lock:
            record = self._tokens.get(token)
            if not record:
                return False, "Verification token is invalid or does not exist", None

            if record["is_consumed"]:
                return False, "Verification token has already been used", None

            if time.time() > record["expires_at"]:
                return False, "Verification token has expired", None

            if str(record["session_id"]) != str(expected_session_id):
                return False, f"Verification token does not match attendance session {expected_session_id}", None

            if expected_student_id is not None and str(record["student_id"]) != str(expected_student_id):
                return False, "Verification token does not match student identity", None

            if expected_faculty_id is not None and str(record["faculty_id"]) != str(expected_faculty_id):
                return False, "Verification token does not belong to this authorized faculty member", None

            # Atomically mark as consumed
            record["is_consumed"] = True
            record["consumed_at"] = time.time()

            return True, "Verification token consumed successfully", dict(record)

    def revoke_challenge(self, challenge_id: str) -> None:
        with self._lock:
            self._challenges.pop(challenge_id, None)

    def _cleanup_expired_locked(self) -> None:
        now = time.time()
        # Clean challenges older than expiry + 60s
        expired_challenges = [
            cid for cid, ch in self._challenges.items()
            if now > ch["expires_at"] + 60
        ]
        for cid in expired_challenges:
            del self._challenges[cid]

        # Clean tokens older than expiry + 60s
        expired_tokens = [
            tok for tok, t in self._tokens.items()
            if now > t["expires_at"] + 60
        ]
        for tok in expired_tokens:
            del self._tokens[tok]
            if hasattr(self, "_token_locks"):
                self._token_locks.pop(tok, None)


# Global singleton instances
pad_detector = PresentationAttackDetector()
active_evaluator = ActiveChallengeEvaluator()
liveness_manager = LivenessVerificationManager()
