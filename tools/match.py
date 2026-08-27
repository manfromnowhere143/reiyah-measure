"""Per-object matching, reimplementing nuscenes-devkit accumulate() but keeping
the match set the devkit discards.

The devkit's eval/detection/algo.py accumulate() builds a local set named
`taken` holding every (sample_token, gt_idx) pair a prediction claimed, then
returns only interpolated precision/recall curves. Every per-object identity is
destroyed on return. This module reproduces the same greedy procedure and
retains, for each ground-truth object, the score of the prediction that matched
it.

The matching procedure, verbatim in structure from the devkit:
  - one pass per detection class
  - predictions of that class sorted by descending score, globally
  - each prediction claims the nearest unclaimed GT of the same class in the
    same sample, by 2D centre distance, if that distance is below dist_th
  - a claimed GT cannot be claimed again

Validation: `--validate` recomputes mAP from the retained matches using the
devkit's own AP definition and prints it against the published figure. If that
does not reproduce, nothing downstream should be believed.

Usage:
  python3 tools/match.py gt_val_cache.json predictions/megvii_val.json out.json [--validate 51.9]
"""
import json
import numpy as np
import math
import sys
from collections import defaultdict

DIST_THS = [0.5, 1.0, 2.0, 4.0]
MIN_RECALL, MIN_PRECISION = 0.1, 0.1
CLASSES = ["car", "truck", "bus", "trailer", "construction_vehicle", "pedestrian",
           "motorcycle", "bicycle", "traffic_cone", "barrier"]


def load(gt_path, pred_path):
    gt = json.load(open(gt_path))
    preds = json.load(open(pred_path))["results"]
    return gt, preds


CLASS_RANGE = {"car": 50, "truck": 50, "bus": 50, "trailer": 50,
               "construction_vehicle": 50, "pedestrian": 40, "motorcycle": 40,
               "bicycle": 40, "traffic_cone": 30, "barrier": 30}


def match_class(gt_idx_by_sample, gt, preds, cls, dist_th, sample_ego):
    """Return {gt_index: matching_score} plus the ordered tp/fp/conf arrays.

    filter_eval_boxes() is applied by the devkit to BOTH gt_boxes and
    pred_boxes, so predictions beyond the class range are removed before
    matching. Omitting that turns out-of-range predictions into false
    positives the official protocol never sees.
    """
    rng = CLASS_RANGE[cls]
    flat = []
    for st, boxes in preds.items():
        e = sample_ego.get(st)
        if e is None:
            continue
        for b in boxes:
            if b["detection_name"] != cls:
                continue
            px, py = b["translation"][0], b["translation"][1]
            if math.hypot(px - e[0], py - e[1]) >= rng:
                continue                      # loaders.py:226-227, applied to preds
            flat.append((b["detection_score"], st, px, py))
    flat.sort(key=lambda x: -x[0])

    taken = set()
    matched = {}
    tp, fp, conf = [], [], []
    for score, st, px, py in flat:
        cands = gt_idx_by_sample.get(st, ())
        best_d, best_i = math.inf, None
        for gi in cands:
            if gi in taken:
                continue
            gx, gy = gt[gi]["xy"]
            d = math.hypot(gx - px, gy - py)
            if d < best_d:
                best_d, best_i = d, gi
        if best_i is not None and best_d < dist_th:
            taken.add(best_i)
            matched[best_i] = score
            tp.append(1); fp.append(0)
        else:
            tp.append(0); fp.append(1)
        conf.append(score)
    return matched, tp, fp, conf


def calc_ap(tp, fp, npos):
    """devkit accumulate() + calc_ap, reproduced exactly.

    algo.py interpolates precision onto 101 evenly spaced recall points with
    np.interp (LINEAR, right=0), then calc_ap clips recall below 0.1 and
    precision below 0.1 and takes the mean, rescaled by 1/(1-min_precision).
    """
    if npos == 0 or not tp:
        return 0.0
    tp = np.cumsum(tp).astype(float)
    fp = np.cumsum(fp).astype(float)
    prec = tp / (fp + tp)
    rec = tp / float(npos)
    rec_interp = np.linspace(0, 1, 101)
    prec = np.interp(rec_interp, rec, prec, right=0)
    prec = prec[round(100 * MIN_RECALL) + 1:]
    prec = prec - MIN_PRECISION
    prec[prec < 0] = 0
    return float(np.mean(prec)) / (1.0 - MIN_PRECISION)


def main():
    gt_path, pred_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    validate = None
    if "--validate" in sys.argv:
        validate = float(sys.argv[sys.argv.index("--validate") + 1])

    gt, preds = load(gt_path, pred_path)
    print(f"GT objects: {len(gt):,}   prediction samples: {len(preds):,}", file=sys.stderr)

    # The official protocol scores against GT with the zero-point filter APPLIED.
    # We match against the FULL in-range set and record which objects the filter
    # would have removed, so both denominators are available downstream.
    by_cls_sample = defaultdict(lambda: defaultdict(list))
    sample_ego = {}
    for i, g in enumerate(gt):
        by_cls_sample[g["cls"]][g["sample_token"]].append(i)
        sample_ego[g["sample_token"]] = g["ego_xy"]

    matched_all = {}
    aps = []
    for cls in CLASSES:
        idx_by_sample = by_cls_sample[cls]
        npos_eval = sum(1 for st, idxs in idx_by_sample.items()
                        for i in idxs if gt[i]["nl"] + gt[i]["nr"] > 0)
        for dth in DIST_THS:
            m, tp, fp, conf = match_class(idx_by_sample, gt, preds, cls, dth, sample_ego)
            if dth == 2.0:
                matched_all[cls] = m
            # AP is computed on the OFFICIAL denominator (filter applied) so the
            # number is comparable to the published one.
            tp2, fp2 = [], []
            # recompute tp/fp restricted to filter-surviving GT
            m_eval, tpe, fpe, _ = match_class(
                {st: [i for i in idxs if gt[i]["nl"] + gt[i]["nr"] > 0]
                 for st, idxs in idx_by_sample.items()}, gt, preds, cls, dth, sample_ego)
            aps.append(calc_ap(tpe, fpe, npos_eval))
        print(f"  {cls:<22} matched@2.0m: {len(matched_all[cls]):,} / "
              f"{sum(len(v) for v in idx_by_sample.values()):,}", file=sys.stderr)

    mAP = 100.0 * sum(aps) / len(aps)
    print(f"\nreconstructed mAP = {mAP:.2f}", file=sys.stderr)
    if validate is not None:
        delta = abs(mAP - validate)
        ok = delta < 1.0
        print(f"published mAP     = {validate:.2f}   delta = {delta:.2f}   "
              f"[{'PASS' if ok else 'FAIL'}]", file=sys.stderr)
        if not ok:
            print("MATCHER DOES NOT REPRODUCE THE OFFICIAL METRIC. Do not use downstream.",
                  file=sys.stderr)

    out = {"matched_at_2m": {c: {str(k): v for k, v in m.items()}
                             for c, m in matched_all.items()},
           "reconstructed_mAP": mAP}
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
