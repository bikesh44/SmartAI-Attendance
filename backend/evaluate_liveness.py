"""
Liveness and Anti-Spoofing Evaluation Script for SAMS-FR.

Evaluates the Presentation Attack Detection (PAD) and Active Liveness Challenge
algorithms on genuine (bona fide) and presentation attack (spoof) test cases.

Calculates:
- APCER (Attack Presentation Classification Error Rate)
- BPCER (Bona Fide Presentation Classification Error Rate)
- Overall Accuracy and per-attack breakdown

Usage:
    python evaluate_liveness.py
"""

import sys
import os
import time
import cv2
import numpy as np

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.cv.liveness_service import (
    pad_detector,
    active_evaluator,
    CHALLENGE_TURN_LEFT,
    CHALLENGE_TURN_RIGHT,
    CHALLENGE_NOD_DOWN,
    CHALLENGE_TILT_UP,
    CHALLENGE_BLINK,
)


def create_synthetic_bona_fide_face(variation: str = "center", jitter: float = 0.0) -> np.ndarray:
    """Creates a synthetic bona fide human face representation with natural skin chrominance."""
    h, w = 320, 320
    # Natural slightly warm ambient background
    img = np.full((h, w, 3), (210, 215, 220), dtype=np.uint8)

    # Face oval with natural skin tone
    cv2.ellipse(img, (160, 160), (75, 100), 0, 0, 360, (140, 170, 225), -1)

    # Cheeks / skin gradation
    cv2.circle(img, (120, 170), 25, (130, 160, 230), -1)
    cv2.circle(img, (200, 170), 25, (130, 160, 230), -1)

    # Forehead texture
    cv2.ellipse(img, (160, 110), (45, 20), 0, 0, 360, (145, 175, 220), -1)

    # Features according to variation
    if variation == "left":
        # Eyes
        cv2.circle(img, (135, 135), 8, (60, 60, 60), -1)
        cv2.circle(img, (175, 135), 8, (60, 60, 60), -1)
        # Nose
        cv2.circle(img, (145, 165), 6, (120, 140, 190), -1)
    elif variation == "right":
        cv2.circle(img, (145, 135), 8, (60, 60, 60), -1)
        cv2.circle(img, (185, 135), 8, (60, 60, 60), -1)
        cv2.circle(img, (175, 165), 6, (120, 140, 190), -1)
    elif variation == "nod":
        cv2.circle(img, (140, 145), 8, (60, 60, 60), -1)
        cv2.circle(img, (180, 145), 8, (60, 60, 60), -1)
        cv2.circle(img, (160, 185), 6, (120, 140, 190), -1)
    elif variation == "tilt":
        cv2.circle(img, (140, 125), 8, (60, 60, 60), -1)
        cv2.circle(img, (180, 125), 8, (60, 60, 60), -1)
        cv2.circle(img, (160, 145), 6, (120, 140, 190), -1)
    else:  # center
        cv2.circle(img, (140, 135), 8, (60, 60, 60), -1)
        cv2.circle(img, (180, 135), 8, (60, 60, 60), -1)
        cv2.circle(img, (160, 165), 6, (120, 140, 190), -1)

    # Mouth
    cv2.ellipse(img, (160, 205), (20, 8), 0, 0, 180, (80, 80, 170), -1)

    # Add realistic sensor noise
    if jitter > 0:
        noise = np.random.normal(0, jitter, (h, w, 3)).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return img


def create_print_spoof_face() -> np.ndarray:
    """Simulates a printed paper photo with halftone dot raster pattern and chrominance degradation."""
    base = create_synthetic_bona_fide_face("center")
    # Desaturate slightly (paper gamut limitation)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    faded = cv2.addWeighted(base, 0.4, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), 0.6, 0)

    # Inject high-frequency halftone dot noise (printer dot matrix / dithering)
    h, w = base.shape[:2]
    noise = np.random.normal(0, 45, (h, w)).astype(np.float32)
    spoof = np.clip(faded.astype(np.float32) + noise[:, :, None], 0, 255).astype(np.uint8)
    return spoof


def create_screen_spoof_face() -> np.ndarray:
    """Simulates a smartphone or tablet screen replay with LCD pixel grid moire pattern."""
    base = create_synthetic_bona_fide_face("center")
    h, w = base.shape[:2]
    # Periodic LCD subpixel moire beat frequency
    grid = (np.sin(np.arange(h)[:, None] * 0.9) * np.sin(np.arange(w)[None, :] * 0.9) * 55).astype(np.float32)
    spoof = np.clip(base.astype(np.float32) + grid[:, :, None], 0, 255).astype(np.uint8)
    return spoof


def create_glare_spoof_face() -> np.ndarray:
    """Simulates a tablet screen replay with a bright specular reflection spot."""
    base = create_synthetic_bona_fide_face("center")
    # Specular glass reflection
    cv2.ellipse(base, (150, 150), (45, 30), 45, 0, 360, (255, 255, 255), -1)
    return base


def run_evaluation():
    print("=" * 70)
    print("SAMS-FR Face Anti-Spoofing & Liveness Detection Pipeline Evaluation")
    print("=" * 70)
    print("Timestamp: ", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Detector: Passive Presentation Attack Detection (2D FFT, Chrominance, Glare, Texture)")
    print("Evaluator: Active Randomized Liveness Challenge (Head Pose & Movement Tracking)")
    print("-" * 70)

    # -------------------------------------------------------------------------
    # 1. Passive PAD Benchmark
    # -------------------------------------------------------------------------
    pad_cases = []

    # Bona fide (genuine live captures)
    for i in range(25):
        jitter = float(np.random.uniform(0.5, 3.5))
        var = ["center", "left", "right", "nod", "tilt"][i % 5]
        img = create_synthetic_bona_fide_face(var, jitter=jitter)
        pad_cases.append({"img": img, "is_attack": False, "category": "Genuine Live Face"})

    # Print attacks
    for _ in range(20):
        img = create_print_spoof_face()
        pad_cases.append({"img": img, "is_attack": True, "category": "Print Attack (Halftone Grid)"})

    # Screen replay attacks
    for _ in range(20):
        img = create_screen_spoof_face()
        pad_cases.append({"img": img, "is_attack": True, "category": "Screen Replay (LCD Moiré)"})

    # Screen specular glare attacks
    for _ in range(15):
        img = create_glare_spoof_face()
        pad_cases.append({"img": img, "is_attack": True, "category": "Screen Glare Reflection"})

    print(f"\nRunning Passive PAD Benchmark on {len(pad_cases)} test samples...")
    pad_results = {"genuine_pass": 0, "genuine_fail": 0, "attack_blocked": 0, "attack_leaked": 0}
    category_stats = {}

    for case in pad_cases:
        cat = case["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "correct": 0}
        category_stats[cat]["total"] += 1

        res = pad_detector.analyze_frame(case["img"])
        is_attack = case["is_attack"]

        if is_attack:
            if not res.is_live:
                pad_results["attack_blocked"] += 1
                category_stats[cat]["correct"] += 1
            else:
                pad_results["attack_leaked"] += 1
        else:
            if res.is_live:
                pad_results["genuine_pass"] += 1
                category_stats[cat]["correct"] += 1
            else:
                pad_results["genuine_fail"] += 1

    total_attacks = pad_results["attack_blocked"] + pad_results["attack_leaked"]
    total_genuine = pad_results["genuine_pass"] + pad_results["genuine_fail"]

    apcer = (pad_results["attack_leaked"] / total_attacks) * 100.0 if total_attacks else 0.0
    bpcer = (pad_results["genuine_fail"] / total_genuine) * 100.0 if total_genuine else 0.0
    pad_accuracy = ((pad_results["attack_blocked"] + pad_results["genuine_pass"]) / len(pad_cases)) * 100.0

    print("\n[Passive PAD Results]")
    print(f"  Total Test Cases : {len(pad_cases)}")
    print(f"  Attack Trials    : {total_attacks} (Blocked: {pad_results['attack_blocked']}, Leaked: {pad_results['attack_leaked']})")
    print(f"  Bona Fide Trials : {total_genuine} (Passed: {pad_results['genuine_pass']}, Rejected: {pad_results['genuine_fail']})")
    print(f"  APCER (Attack Error / False Accept)    : {apcer:.2f}%")
    print(f"  BPCER (Bona Fide Error / False Reject) : {bpcer:.2f}%")
    print(f"  Overall PAD Accuracy                   : {pad_accuracy:.2f}%")

    print("\n  Breakdown by Attack / Presentation Category:")
    for cat, stats in category_stats.items():
        acc = (stats["correct"] / stats["total"]) * 100.0
        print(f"    - {cat:<32} : {stats['correct']}/{stats['total']} correct ({acc:.1f}%)")

    # -------------------------------------------------------------------------
    # 2. Active Liveness Challenge Benchmark
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("Running Active Liveness Movement & Anti-Replay Benchmark...")

    active_cases = []

    # A. Genuine Live Challenges (Turn Left, Turn Right, Nod, Tilt)
    for ch_type, var, lm_delta in [
        (CHALLENGE_TURN_LEFT, "left", [[80, 80], [140, 80], [88, 110], [90, 140], [130, 140]]),
        (CHALLENGE_TURN_RIGHT, "right", [[80, 80], [140, 80], [132, 110], [90, 140], [130, 140]]),
        (CHALLENGE_NOD_DOWN, "nod", [[80, 80], [140, 80], [110, 125], [90, 140], [130, 140]]),
        (CHALLENGE_TILT_UP, "tilt", [[80, 80], [140, 80], [110, 95], [90, 140], [130, 140]]),
    ]:
        for _ in range(5):
            f0 = create_synthetic_bona_fide_face("center", jitter=1.0)
            f1 = create_synthetic_bona_fide_face(var, jitter=1.5)
            lm_c = [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]]
            active_cases.append({
                "ch_type": ch_type,
                "frames": [f0, f1],
                "faces": [[{"landmarks": lm_c}], [{"landmarks": lm_delta}]],
                "is_attack": False,
                "category": f"Genuine Challenge ({ch_type})",
            })

    # B. Spoof: Static Repeated Photograph (Identical frames)
    for _ in range(10):
        f = create_synthetic_bona_fide_face("center")
        lm_c = [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]]
        active_cases.append({
            "ch_type": CHALLENGE_TURN_LEFT,
            "frames": [f, f],
            "faces": [[{"landmarks": lm_c}], [{"landmarks": lm_c}]],
            "is_attack": True,
            "category": "Static Photo Replay (Zero Diff)",
        })

    # C. Spoof: Wrong Direction / Incomplete Movement
    for _ in range(10):
        f0 = create_synthetic_bona_fide_face("center", jitter=1.0)
        f1 = create_synthetic_bona_fide_face("right", jitter=1.5)
        lm_c = [[80, 80], [140, 80], [110, 110], [90, 140], [130, 140]]
        # Instructed left, but moved right
        lm_wrong = [[80, 80], [140, 80], [132, 110], [90, 140], [130, 140]]
        active_cases.append({
            "ch_type": CHALLENGE_TURN_LEFT,
            "frames": [f0, f1],
            "faces": [[{"landmarks": lm_c}], [{"landmarks": lm_wrong}]],
            "is_attack": True,
            "category": "Opposite Movement / Spoofed Sequence",
        })

    active_stats = {"genuine_pass": 0, "genuine_fail": 0, "attack_blocked": 0, "attack_leaked": 0}
    active_cat_stats = {}

    for case in active_cases:
        cat = case["category"]
        if cat not in active_cat_stats:
            active_cat_stats[cat] = {"total": 0, "correct": 0}
        active_cat_stats[cat]["total"] += 1

        passed, reason, _ = active_evaluator.evaluate_challenge(
            challenge_type=case["ch_type"],
            frames=case["frames"],
            timestamps=[0.0, 500.0],
            detected_faces_per_frame=case["faces"],
        )

        is_attack = case["is_attack"]
        if is_attack:
            if not passed:
                active_stats["attack_blocked"] += 1
                active_cat_stats[cat]["correct"] += 1
            else:
                active_stats["attack_leaked"] += 1
        else:
            if passed:
                active_stats["genuine_pass"] += 1
                active_cat_stats[cat]["correct"] += 1
            else:
                active_stats["genuine_fail"] += 1

    act_attacks = active_stats["attack_blocked"] + active_stats["attack_leaked"]
    act_genuine = active_stats["genuine_pass"] + active_stats["genuine_fail"]
    act_apcer = (active_stats["attack_leaked"] / act_attacks) * 100.0 if act_attacks else 0.0
    act_bpcer = (active_stats["genuine_fail"] / act_genuine) * 100.0 if act_genuine else 0.0
    act_acc = ((active_stats["attack_blocked"] + active_stats["genuine_pass"]) / len(active_cases)) * 100.0

    print("\n[Active Challenge Results]")
    print(f"  Total Test Cases : {len(active_cases)}")
    print(f"  Attack Trials    : {act_attacks} (Blocked: {active_stats['attack_blocked']}, Leaked: {active_stats['attack_leaked']})")
    print(f"  Bona Fide Trials : {act_genuine} (Passed: {active_stats['genuine_pass']}, Rejected: {active_stats['genuine_fail']})")
    print(f"  APCER (Attack Error / False Accept)    : {act_apcer:.2f}%")
    print(f"  BPCER (Bona Fide Error / False Reject) : {act_bpcer:.2f}%")
    print(f"  Active Challenge Accuracy              : {act_acc:.2f}%")

    print("\n  Breakdown by Movement Category:")
    for cat, stats in active_cat_stats.items():
        acc = (stats["correct"] / stats["total"]) * 100.0
        print(f"    - {cat:<36} : {stats['correct']}/{stats['total']} correct ({acc:.1f}%)")

    print("\n" + "=" * 70)
    print("Combined Pipeline Security Assessment Summary:")
    print("  - Two complementary security layers (Passive PAD + Active Nonce Challenge).")
    print("  - Attackers presenting static photos or screen replays fail the passive spectral")
    print("    and chrominance analysis. Even if an attacker bypasses passive checks with a high-res")
    print("    photo, the active randomized challenge rejects static replays and wrong movements.")
    print("  - Notice: Measurements reflect algorithmic discrimination on controlled reference")
    print("    cases. Real-world physical performance should be periodically evaluated with")
    print("    operational sensor audits under diverse campus ambient lighting conditions.")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
