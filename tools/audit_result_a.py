"""Adversarial audit of Result A. Every check is designed to FAIL loudly."""
import ast, json, math, sys, tarfile
from collections import Counter

WANT = {"sample_annotation.json", "instance.json", "category.json", "sample.json",
        "scene.json", "visibility.json", "sample_data.json", "ego_pose.json",
        "calibrated_sensor.json", "sensor.json"}
tables = {}
tar = tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz")
for m in tar:
    b = m.name.rsplit("/", 1)[-1]
    if b in WANT and m.isfile():
        f = tar.extractfile(m)
        if f is not None:
            tables[b] = json.loads(f.read())
    if len(tables) == len(WANT):
        break

cat_name = {c["token"]: c["name"] for c in tables["category.json"]}
inst_cat = {i["token"]: cat_name[i["category_token"]] for i in tables["instance.json"]}
samp_scene = {s["token"]: s["scene_token"] for s in tables["sample.json"]}
scene_name = {s["token"]: s["name"] for s in tables["scene.json"]}
sensor_tok = {s["token"]: s["channel"] for s in tables["sensor.json"]}
cs_channel = {c["token"]: sensor_tok[c["sensor_token"]] for c in tables["calibrated_sensor.json"]}
ego_xyz = {e["token"]: e["translation"] for e in tables["ego_pose.json"]}
sample_ego = {sd["sample_token"]: ego_xyz[sd["ego_pose_token"]]
              for sd in tables["sample_data.json"]
              if sd["is_key_frame"] and cs_channel.get(sd["calibrated_sensor_token"]) == "LIDAR_TOP"}

VAL = None
for node in ast.parse(open("ns_splits.py").read()).body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "val":
                VAL = set(ast.literal_eval(node.value))

FAIL = []
def check(name, got, want, note=""):
    ok = got == want
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got {got:,} expected {want:,} {note}")
    if not ok:
        FAIL.append(name)

# A1: nuScenes publishes 850 trainval scenes, 700 train / 150 val.
check("A1 trainval scenes", len(tables["scene.json"]), 850)
check("A2 val scenes named in splits.py", len(VAL), 150)

# A3: THE key external cross-check. nuScenes val is published as 6,019 samples.
val_samples = sum(1 for s in tables["sample.json"] if scene_name[samp_scene[s["token"]]] in VAL)
check("A3 val samples (published: 6019)", val_samples, 6019)

# A4: every val sample must have a keyframe LIDAR_TOP ego pose, else my
#     distance filter silently skipped annotations.
val_tokens = {s["token"] for s in tables["sample.json"] if scene_name[samp_scene[s["token"]]] in VAL}
missing = sum(1 for t in val_tokens if t not in sample_ego)
check("A4 val samples missing LIDAR_TOP ego pose", missing, 0)

# A5: no val annotation may be skipped for a missing ego pose.
skipped = sum(1 for a in tables["sample_annotation.json"]
              if scene_name[samp_scene[a["sample_token"]]] in VAL
              and a["sample_token"] not in sample_ego)
check("A5 val annotations skipped (no ego pose)", skipped, 0)

# A6: every annotation must carry a visibility token, or my visibility
#     stratification has a silent bucket.
vis_ok = {v["token"] for v in tables["visibility.json"]}
novis = sum(1 for a in tables["sample_annotation.json"]
            if scene_name[samp_scene[a["sample_token"]]] in VAL
            and a.get("visibility_token") not in vis_ok)
check("A6 val annotations with no visibility token", novis, 0)

# A7: num_lidar_pts / num_radar_pts must never be negative or absent.
bad = sum(1 for a in tables["sample_annotation.json"]
          if a.get("num_lidar_pts", -1) < 0 or a.get("num_radar_pts", -1) < 0)
check("A7 annotations with bad point counts", bad, 0)

# A8: the deleted set must be exactly those with BOTH counts zero -- prove
#     the arithmetic, do not trust the earlier script.
DET = {"movable_object.barrier":"barrier","vehicle.bicycle":"bicycle",
 "vehicle.bus.bendy":"bus","vehicle.bus.rigid":"bus","vehicle.car":"car",
 "vehicle.construction":"construction_vehicle","vehicle.motorcycle":"motorcycle",
 "human.pedestrian.adult":"pedestrian","human.pedestrian.child":"pedestrian",
 "human.pedestrian.construction_worker":"pedestrian",
 "human.pedestrian.police_officer":"pedestrian","movable_object.trafficcone":"traffic_cone",
 "vehicle.trailer":"trailer","vehicle.truck":"truck"}
R = {"car":50,"truck":50,"bus":50,"trailer":50,"construction_vehicle":50,
     "pedestrian":40,"motorcycle":40,"bicycle":40,"traffic_cone":30,"barrier":30}
surv = 0; both0 = 0; lid0 = 0; rad0 = 0
for a in tables["sample_annotation.json"]:
    if scene_name[samp_scene[a["sample_token"]]] not in VAL: continue
    det = DET.get(inst_cat[a["instance_token"]])
    if det is None: continue
    ego = sample_ego[a["sample_token"]]; t = a["translation"]
    if math.hypot(t[0]-ego[0], t[1]-ego[1]) >= R[det]: continue
    surv += 1
    nl, nr = a["num_lidar_pts"], a["num_radar_pts"]
    if nl == 0 and nr == 0: both0 += 1
    if nl == 0: lid0 += 1
    if nr == 0: rad0 += 1
print(f"\n[INFO] independent recount  surviving={surv:,}  deleted(both zero)={both0:,}"
      f"  ({100*both0/surv:.2f}%)")
print(f"[INFO] zero-lidar={lid0:,} ({100*lid0/surv:.2f}%)   zero-radar={rad0:,} ({100*rad0/surv:.2f}%)")
check("A8 recount matches result_a2", both0, 12694)
check("A9 surviving recount matches result_a2", surv, 134565)

# A10: an object deleted for zero points must still be a REAL annotated object,
#      i.e. it has nonzero size. A degenerate box would explain the deletion
#      innocently.
degenerate = 0
for a in tables["sample_annotation.json"]:
    if scene_name[samp_scene[a["sample_token"]]] not in VAL: continue
    if a["num_lidar_pts"] + a["num_radar_pts"] == 0:
        if min(a["size"]) <= 0: degenerate += 1
check("A10 deleted boxes that are degenerate (zero size)", degenerate, 0)

print("\n" + ("ALL AUDITS PASSED" if not FAIL else f"FAILURES: {FAIL}"))
