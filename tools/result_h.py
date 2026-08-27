"""Result H: does modality diversity actually buy failure independence?

Every multi-sensor safety argument rests on an unstated premise: that a second
modality fails differently from the first. RSS makes it explicit in Definition
32 and never measures it. Everyone else assumes it implicitly when they add a
sensor.

It is measurable. Take three published detectors on the same split:

    Mapillary MonoDIS   camera   29.8 mAP
    Megvii CBGS         lidar    51.9 mAP
    PointPillars        lidar    29.5 mAP

and compute the lift c for each pair. Two of the pairs cross modalities; one
does not. The comparison is the answer.

If modality diversity buys independence, the same-modality pair should show a
markedly higher lift than the cross-modality pairs. If it does not, the case
for paying for a second modality has to rest on something other than failure
independence.

The PointPillars/Mapillary pair is the useful control: it is cross-modality at
almost identical accuracy (29.5 vs 29.8 mAP), so any difference from the
Megvii/Mapillary pair is not an accuracy artifact.

Usage:
  python3 tools/result_h.py gt_val_cache.json A=matched_a.json B=matched_b.json ...
"""
import json
import sys
from collections import defaultdict
from itertools import combinations

THR = 0.3
MIN_STRATUM = 30

gt = json.load(open(sys.argv[1]))
det = {}
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1)
    flat = {}
    for _c, m in json.load(open(path))["matched_at_2m"].items():
        for k, v in m.items():
            flat[int(k)] = v
    det[name] = flat


def band(d):
    return "0-20" if d < 20 else ("20-30" if d < 30 else ("30-40" if d < 40 else "40-50"))


def lift(a, b, thr, stratify):
    """Marginal or stratified lift between detectors a and b."""
    cells = defaultdict(lambda: [0, 0, 0, 0])
    for i in range(len(gt)):
        am = det[a].get(i, -1.0) < thr
        bm = det[b].get(i, -1.0) < thr
        k = (gt[i]["cls"], band(gt[i]["dist"]), gt[i]["vis"]) if stratify else "all"
        if am and bm:
            cells[k][0] += 1
        elif am:
            cells[k][1] += 1
        elif bm:
            cells[k][2] += 1
        else:
            cells[k][3] += 1
    obs = exp = 0.0
    mh_n = mh_d = 0.0
    for k, (x, y, z, w) in cells.items():
        n = x + y + z + w
        if n < MIN_STRATUM:
            continue
        obs += x
        exp += ((x + y) / n) * ((x + z) / n) * n
        mh_n += x * w / n
        mh_d += y * z / n
    return (obs / exp if exp else float("nan"),
            mh_n / mh_d if mh_d else float("nan"))


MODALITY = {"mapillary": "camera", "megvii": "lidar", "pointpillars": "lidar",
            "centerpoint": "lidar"}
MAP = {"mapillary": 29.8, "megvii": 51.9, "pointpillars": 29.5, "centerpoint": 61.6}

print("=" * 90)
print("RESULT H — does modality diversity buy failure independence?")
print(f"pairwise lift between published nuScenes detectors, val split, score >= {THR}")
print("=" * 90)
print(f"\n{'pair':<28}{'modalities':<20}{'marginal c':>12}{'cond. c':>10}"
      f"{'cond. MH OR':>13}")

rows = []
for a, b in combinations(sorted(det), 2):
    mc, _ = lift(a, b, THR, stratify=False)
    cc, mh = lift(a, b, THR, stratify=True)
    ma, mb = MODALITY.get(a, "?"), MODALITY.get(b, "?")
    kind = "SAME modality" if ma == mb else "cross-modality"
    rows.append((a, b, kind, ma, mb, mc, cc, mh))

for a, b, kind, ma, mb, mc, cc, mh in sorted(rows, key=lambda r: -r[5]):
    pair = f"{a} x {b}"
    mods = f"{ma}/{mb}"
    print(f"{pair:<28}{mods:<20}{mc:>12.3f}{cc:>10.3f}{mh:>13.3f}   {kind}")

same = [r for r in rows if r[3] == r[4]]
cross = [r for r in rows if r[3] != r[4]]
print("\n" + "-" * 90)
if same and cross:
    sm = sum(r[5] for r in same) / len(same)
    cm = sum(r[5] for r in cross) / len(cross)
    sc = sum(r[6] for r in same) / len(same)
    cc_ = sum(r[6] for r in cross) / len(cross)
    print(f"same-modality  mean marginal c = {sm:.3f}   conditional c = {sc:.3f}")
    print(f"cross-modality mean marginal c = {cm:.3f}   conditional c = {cc_:.3f}")
    print(f"\nmodality diversity reduces the marginal lift by "
          f"{100*(1 - (cm-1)/(sm-1)):.0f}% of its excess over independence"
          if sm > 1 else "")
print()
print("Accuracy control: PointPillars 29.5 mAP against Mapillary 29.8 mAP is a")
print("cross-modality pair at matched accuracy. Comparing it to Megvii 51.9 x")
print("Mapillary separates a modality effect from an accuracy effect.")
print("-" * 90)
