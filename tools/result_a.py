"""Result A, exact: reproduce the official nuScenes GT filter ORDER.

loaders.py filter_eval_boxes() applies, in this order:
  1. line 226-227  drop boxes with ego_dist >= class_range[class]
  2. line 231      drop boxes with num_lidar_pts + num_radar_pts == 0

So the honest denominator is "boxes surviving the distance filter", and the
question is what fraction of THOSE the point filter then deletes.

ego_dist is computed in add_center_dist() as the norm of
(box.translation - ego_pose.translation) for the sample's LIDAR_TOP record.
Streams the metadata tarball from stdin; nothing lands on disk.
"""
import ast
import json
import math
import sys
import tarfile
from collections import Counter

WANT = {"sample_annotation.json", "instance.json", "category.json",
        "sample.json", "scene.json", "visibility.json",
        "sample_data.json", "ego_pose.json", "calibrated_sensor.json",
        "sensor.json"}

tables = {}
tar = tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz")
for m in tar:
    b = m.name.rsplit("/", 1)[-1]
    if b in WANT and m.isfile():
        f = tar.extractfile(m)
        if f is not None:
            tables[b] = json.loads(f.read())
            print(f"  loaded {b}: {len(tables[b]):,}", file=sys.stderr)
    if len(tables) == len(WANT):
        break

cat_name = {c["token"]: c["name"] for c in tables["category.json"]}
inst_cat = {i["token"]: cat_name[i["category_token"]] for i in tables["instance.json"]}
samp_scene = {s["token"]: s["scene_token"] for s in tables["sample.json"]}
scene_name = {s["token"]: s["name"] for s in tables["scene.json"]}
scene_desc = {s["token"]: s.get("description", "") for s in tables["scene.json"]}
vis_level = {v["token"]: v["level"] for v in tables["visibility.json"]}

# LIDAR_TOP channel -> the sample_data records the devkit uses for ego pose
sensor_tok = {s["token"]: s["channel"] for s in tables["sensor.json"]}
cs_channel = {c["token"]: sensor_tok[c["sensor_token"]]
              for c in tables["calibrated_sensor.json"]}
ego_xyz = {e["token"]: e["translation"] for e in tables["ego_pose.json"]}
del tables["ego_pose.json"]

sample_ego = {}
for sd in tables["sample_data.json"]:
    if sd["is_key_frame"] and cs_channel.get(sd["calibrated_sensor_token"]) == "LIDAR_TOP":
        sample_ego[sd["sample_token"]] = ego_xyz[sd["ego_pose_token"]]
del tables["sample_data.json"]
print(f"  keyframe LIDAR_TOP ego poses: {len(sample_ego):,}", file=sys.stderr)

SPLITS = ("/private/tmp/claude-501/-Users-danielwahnich-workspace-odeya/"
          "ff9f50eb-bb0b-446c-81f0-bb98c6e10c51/scratchpad/ns_splits.py")
VAL = None
for node in ast.parse(open(SPLITS).read()).body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "val":
                VAL = set(ast.literal_eval(node.value))
print(f"  val scenes: {len(VAL)}", file=sys.stderr)

DET = {"movable_object.barrier": "barrier", "vehicle.bicycle": "bicycle",
       "vehicle.bus.bendy": "bus", "vehicle.bus.rigid": "bus", "vehicle.car": "car",
       "vehicle.construction": "construction_vehicle",
       "vehicle.motorcycle": "motorcycle", "human.pedestrian.adult": "pedestrian",
       "human.pedestrian.child": "pedestrian",
       "human.pedestrian.construction_worker": "pedestrian",
       "human.pedestrian.police_officer": "pedestrian",
       "movable_object.trafficcone": "traffic_cone", "vehicle.trailer": "trailer",
       "vehicle.truck": "truck"}
# detection_cvpr_2019.json class_range
RANGE = {"car": 50, "truck": 50, "bus": 50, "trailer": 50, "construction_vehicle": 50,
         "pedestrian": 40, "motorcycle": 40, "bicycle": 40,
         "traffic_cone": 30, "barrier": 30}

surv = Counter(); killed = Counter()
surv_raw = Counter(); killed_raw = Counter()
surv_vis = Counter(); killed_vis = Counter()
surv_cond = Counter(); killed_cond = Counter()
surv_band = Counter(); killed_band = Counter()
n_in_class = 0; n_dist_dropped = 0
vis80_killed = 0

for a in tables["sample_annotation.json"]:
    st = samp_scene[a["sample_token"]]
    if scene_name[st] not in VAL:
        continue
    det = DET.get(inst_cat[a["instance_token"]])
    if det is None:
        continue
    n_in_class += 1
    ego = sample_ego.get(a["sample_token"])
    if ego is None:
        continue
    t = a["translation"]
    # data_classes.py:54-56  ego_dist is the 2D (xy) norm, z is discarded
    d = math.hypot(t[0] - ego[0], t[1] - ego[1])
    if d >= RANGE[det]:            # step 1: distance filter
        n_dist_dropped += 1
        continue
    raw = inst_cat[a["instance_token"]]
    vis = vis_level.get(a.get("visibility_token", ""), "unknown")
    desc = scene_desc[st].lower()
    cond = "night" if "night" in desc else ("rain" if "rain" in desc else "clear/other")
    band = "0-20m" if d < 20 else ("20-30m" if d < 30 else ("30-40m" if d < 40 else "40-50m"))
    zero = (a["num_lidar_pts"] + a["num_radar_pts"]) == 0
    if zero:                        # step 2: the point filter
        killed[det] += 1; killed_raw[raw] += 1; killed_vis[vis] += 1
        killed_cond[cond] += 1; killed_band[band] += 1
        if vis == "v80-100":
            vis80_killed += 1
    surv[det] += 1; surv_raw[raw] += 1; surv_vis[vis] += 1
    surv_cond[cond] += 1; surv_band[band] += 1

T = sum(surv.values()); K = sum(killed.values())
print("\n" + "=" * 78)
print("RESULT A (exact) — GT deleted by nuscenes-devkit loaders.py:231")
print("nuScenes v1.0-trainval, official val split, official filter ORDER")
print("=" * 78)
print(f"\nVal annotations in the 10 evaluated classes : {n_in_class:,}")
print(f"Dropped first by the DISTANCE filter        : {n_dist_dropped:,}")
print(f"Surviving distance filter (true denominator): {T:,}")
print(f"\nTHEN DELETED by the zero-point filter       : {K:,}  ({100*K/T:.2f}%)")
print(f"  ...of which fully camera-visible (v80-100): {vis80_killed:,}")

def tbl(title, s, k, order=None):
    print(f"\n--- {title} ---")
    print(f"{'':<40}{'kept+del':>10}{'deleted':>9}{'% del':>9}")
    keys = order or sorted(s, key=lambda x: -k[x])
    for c in keys:
        if s[c]:
            print(f"{c:<40}{s[c]:>10,}{k[c]:>9,}{100*k[c]/s[c]:>8.2f}%")

tbl("by detection class", surv, killed)
tbl("by RAW category", surv_raw, killed_raw)
tbl("by annotated camera visibility", surv_vis, killed_vis,
    order=["v0-40", "v40-60", "v60-80", "v80-100"])
tbl("by ego distance", surv_band, killed_band,
    order=["0-20m", "20-30m", "30-40m", "40-50m"])
tbl("by scene condition", surv_cond, killed_cond)
print("=" * 78)
