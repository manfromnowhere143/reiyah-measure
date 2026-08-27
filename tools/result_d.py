"""Result D: the joint camera/lidar miss table, and the RSS independence
coefficient measured on both denominators.

RSS (Shalev-Shwartz, Shammah, Shashua, arXiv:1708.06374) Definition 32 calls
two subsystem error events "one side c-approximate independent" when

    P[r1 AND r2]  <=  c * P[r1] * P[r2]

and Corollary 3 uses that to cut required validation evidence from ~10^9 to
~10^5 examples. The smallest coefficient consistent with an observed pair is
the lift:

    c_hat = P[both miss] / (P[camera miss] * P[lidar miss])

c_hat = 1 means independence. c_hat > 1 means the channels fail together more
often than independence predicts, and the validation reduction is overstated by
that factor.

We compute c_hat twice:
  OFFICIAL  denominator with the zero-point filter applied (what the benchmark scores)
  FULL      denominator with every in-range annotated object (what actually exists)

Inputs are the outputs of tools/match.py, whose matcher reproduces the
published mAP for both detectors to within 0.25.

Usage: python3 tools/result_d.py gt_val_cache.json matched_mapillary.json matched_megvii.json
"""
import json
import sys
from collections import Counter

gt = json.load(open(sys.argv[1]))
cam = json.load(open(sys.argv[2]))["matched_at_2m"]
lid = json.load(open(sys.argv[3]))["matched_at_2m"]

cam_score = {}
lid_score = {}
for d, dst in ((cam, cam_score), (lid, lid_score)):
    for cls, m in d.items():
        for k, v in m.items():
            dst[int(k)] = v


def table(idxs, thr):
    """2x2 over the given GT indices at a shared score threshold."""
    both = conly = lonly = neither = 0
    for i in idxs:
        c = cam_score.get(i, -1.0) >= thr
        l = lid_score.get(i, -1.0) >= thr
        if c and l:
            both += 1
        elif c:
            conly += 1
        elif l:
            lonly += 1
        else:
            neither += 1
    n = both + conly + lonly + neither
    cam_miss = (lonly + neither) / n
    lid_miss = (conly + neither) / n
    joint = neither / n
    expected = cam_miss * lid_miss
    c_hat = joint / expected if expected > 0 else float("nan")
    return dict(n=n, both=both, cam_only=conly, lid_only=lonly, neither=neither,
                cam_miss=cam_miss, lid_miss=lid_miss, joint=joint,
                expected=expected, c_hat=c_hat)


ALL = list(range(len(gt)))
OFFICIAL = [i for i in ALL if gt[i]["nl"] + gt[i]["nr"] > 0]

print("=" * 84)
print("RESULT D — joint camera/lidar miss, and the RSS coefficient c")
print("camera-only: Mapillary MonoDIS 29.8 mAP | lidar-only: Megvii CBGS 51.9 mAP")
print("nuScenes val, matched at 2.0 m by a matcher validated against published mAP")
print("=" * 84)

# A threshold of -1 saturates: with ~800k predictions for ~134k objects every
# object matches something. Real operating points only.
for thr, label in ((0.1, "score >= 0.1"), (0.2, "score >= 0.2"),
                   (0.3, "score >= 0.3"), (0.4, "score >= 0.4"),
                   (0.5, "score >= 0.5")):
    print(f"\n### operating point: {label}")
    print(f"{'denominator':<12}{'N':>9}{'cam miss':>10}{'lid miss':>10}"
          f"{'joint obs':>11}{'joint exp':>11}{'c_hat':>9}")
    for name, idxs in (("OFFICIAL", OFFICIAL), ("FULL", ALL)):
        r = table(idxs, thr)
        print(f"{name:<12}{r['n']:>9,}{r['cam_miss']:>10.4f}{r['lid_miss']:>10.4f}"
              f"{r['joint']:>11.4f}{r['expected']:>11.4f}{r['c_hat']:>9.3f}")

THR = 0.3
print(f"\n### by ego distance, at score >= {THR}")
print(f"{'band':<10}{'denominator':<11}{'N':>9}{'cam miss':>10}{'lid miss':>10}"
      f"{'joint obs':>11}{'c_hat':>9}")
for lo, hi, lab in ((0, 20, "0-20m"), (20, 30, "20-30m"), (30, 40, "30-40m"), (40, 50, "40-50m")):
    for name, pool in (("OFFICIAL", OFFICIAL), ("FULL", ALL)):
        idxs = [i for i in pool if lo <= gt[i]["dist"] < hi]
        if not idxs:
            continue
        r = table(idxs, THR)
        print(f"{lab:<10}{name:<11}{r['n']:>9,}{r['cam_miss']:>10.4f}"
              f"{r['lid_miss']:>10.4f}{r['joint']:>11.4f}{r['c_hat']:>9.3f}")

print(f"\n### by class, FULL denominator, score >= {THR}")
print(f"{'class':<22}{'N':>8}{'cam miss':>10}{'lid miss':>10}{'joint obs':>11}{'c_hat':>9}")
by_cls = {}
for i, g in enumerate(gt):
    by_cls.setdefault(g["cls"], []).append(i)
for cls in sorted(by_cls, key=lambda c: -len(by_cls[c])):
    r = table(by_cls[cls], THR)
    print(f"{cls:<22}{r['n']:>8,}{r['cam_miss']:>10.4f}{r['lid_miss']:>10.4f}"
          f"{r['joint']:>11.4f}{r['c_hat']:>9.3f}")

print("\n" + "-" * 84)
print("c_hat = 1 is independence. Above 1, the two channels fail together more")
print("often than independence predicts, and RSS Corollary 3's reduction in")
print("required validation evidence is overstated by that factor.")
print()
print("The OFFICIAL row is what the benchmark can see. The FULL row includes the")
print("12,694 objects the zero-point filter removes. Compare them.")
print("-" * 84)
