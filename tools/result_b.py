"""Result B: the differential advantage the zero-point filter grants a
lidar-only detector over a camera-only detector on nuScenes.

Result A established that loaders.py:231 removes every GT object with
num_lidar_pts + num_radar_pts == 0 before scoring.

The removal criterion is defined purely on range-sensor returns. It is
therefore correlated with lidar failure BY CONSTRUCTION, and uncorrelated
with camera failure. That asymmetry is the finding: the filter deletes
objects the range sensors could not see, whatever the cameras saw. 2,207 of
the removed objects are annotated 80-100% camera-visible.

STATED ASSUMPTION, AND ITS LIMIT. num_lidar_pts counts returns inside the box
in the KEYFRAME sweep only. Most production lidar detectors accumulate ~10
sweeps, so an object with zero keyframe points may still carry some evidence
in the accumulated stack -- more so if it moved into view, less so if it is
statically occluded, since adjacent sweeps then share almost the same
geometry. "Undetectable" is therefore too strong.

The inflation factor below is consequently an UPPER BOUND on the correction:
it is what a lidar-only detector's recall must be multiplied by IF zero
keyframe returns implies non-detection. The true correction lies between 1.0
and that bound. Closing the gap requires running a detector, which this
script deliberately does not do.

Runs no detector, needs no GPU. Reads the metadata tarball on stdin.

Reported quantities, per stratum:
  N_eval   objects the official protocol scores against
  N_full   objects annotated and within class range (eval + removed)
  infl     1 / (N_eval / N_full) = the factor by which a lidar-only
           detector's recall is overstated relative to the complete
           annotated set, under the stated assumption
  cam_vis  removed objects annotated 80-100% camera-visible: the cleanest
           subset a camera detector could plausibly have found
"""
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
vis_level = {v["token"]: v["level"] for v in tables["visibility.json"]}
sensor_tok = {s["token"]: s["channel"] for s in tables["sensor.json"]}
cs_channel = {c["token"]: sensor_tok[c["sensor_token"]] for c in tables["calibrated_sensor.json"]}
ego_xyz = {e["token"]: e["translation"] for e in tables["ego_pose.json"]}
sample_ego = {sd["sample_token"]: ego_xyz[sd["ego_pose_token"]]
              for sd in tables["sample_data.json"]
              if sd["is_key_frame"] and cs_channel.get(sd["calibrated_sensor_token"]) == "LIDAR_TOP"}

SPLITS = "evidence/nuscenes_splits_devkit.py"
VAL = None
for node in ast.parse(open(SPLITS).read()).body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "val":
                VAL = set(ast.literal_eval(node.value))

DET = {"movable_object.barrier":"barrier","vehicle.bicycle":"bicycle",
 "vehicle.bus.bendy":"bus","vehicle.bus.rigid":"bus","vehicle.car":"car",
 "vehicle.construction":"construction_vehicle","vehicle.motorcycle":"motorcycle",
 "human.pedestrian.adult":"pedestrian","human.pedestrian.child":"pedestrian",
 "human.pedestrian.construction_worker":"pedestrian",
 "human.pedestrian.police_officer":"pedestrian","movable_object.trafficcone":"traffic_cone",
 "vehicle.trailer":"trailer","vehicle.truck":"truck"}
R = {"car":50,"truck":50,"bus":50,"trailer":50,"construction_vehicle":50,
     "pedestrian":40,"motorcycle":40,"bicycle":40,"traffic_cone":30,"barrier":30}

full = Counter(); removed = Counter(); camvis = Counter()
full_b = Counter(); removed_b = Counter(); camvis_b = Counter()
BANDS = ["0-20m", "20-30m", "30-40m", "40-50m"]

for a in tables["sample_annotation.json"]:
    if scene_name[samp_scene[a["sample_token"]]] not in VAL:
        continue
    det = DET.get(inst_cat[a["instance_token"]])
    if det is None:
        continue
    ego = sample_ego[a["sample_token"]]; t = a["translation"]
    d = math.hypot(t[0] - ego[0], t[1] - ego[1])      # data_classes.py:54-56, 2D
    if d >= R[det]:
        continue
    band = "0-20m" if d < 20 else ("20-30m" if d < 30 else ("30-40m" if d < 40 else "40-50m"))
    full[det] += 1; full_b[band] += 1
    if a["num_lidar_pts"] + a["num_radar_pts"] == 0:
        removed[det] += 1; removed_b[band] += 1
        if vis_level.get(a.get("visibility_token", "")) == "v80-100":
            camvis[det] += 1; camvis_b[band] += 1

NF = sum(full.values()); NR = sum(removed.values()); NE = NF - NR
print("=" * 82)
print("RESULT B — recall inflation granted to a lidar-only detector")
print("nuScenes v1.0-trainval, official val split, post class-range filter")
print("=" * 82)
print(f"\nAnnotated and in range (N_full)      : {NF:,}")
print(f"Removed by loaders.py:231            : {NR:,}")
print(f"Officially scored against (N_eval)   : {NE:,}")
print(f"\nLIDAR-ONLY RECALL INFLATION          : x{NF/NE:.4f}   (+{100*(NF/NE-1):.2f}%)")
print(f"Removed objects a camera could see   : {sum(camvis.values()):,} annotated 80-100% visible")

def show(title, f, r, cv, keys):
    print(f"\n--- {title} ---")
    print(f"{'':<22}{'N_full':>10}{'N_eval':>10}{'removed':>9}{'inflation':>11}{'cam-visible':>13}")
    for k in keys:
        if not f[k]:
            continue
        ne = f[k] - r[k]
        print(f"{k:<22}{f[k]:>10,}{ne:>10,}{r[k]:>9,}{f'x{f[k]/ne:.4f}':>11}{cv[k]:>13,}")

show("by ego distance", full_b, removed_b, camvis_b, BANDS)
show("by detection class", full, removed, camvis,
     sorted(full, key=lambda k: -(full[k] / max(full[k] - removed[k], 1))))

print("\n" + "-" * 82)
print("HOW TO READ THIS, AND HOW NOT TO.")
print()
print("The inflation factor is an UPPER BOUND. It is what a lidar-only detector's")
print("recall must be multiplied by to express it over the complete annotated")
print("in-range set, IF zero keyframe lidar returns implies non-detection. Multi-sweep")
print("accumulation means some of those objects may still be detectable, so the true")
print("correction lies between 1.0 and the figure shown.")
print()
print("What does NOT depend on that assumption: the removal criterion is defined on")
print("range-sensor returns alone. It is correlated with lidar failure by construction")
print("and uncorrelated with camera failure. Whatever the exact magnitude, the")
print("direction of the bias is fixed, and it is largest at long range -- which is")
print("where the camera-versus-lidar argument actually lives.")
print()
print("This is not a claim that any published number is wrong. It is a claim that")
print("camera and lidar are not being scored on the same set of objects.")
print("-" * 82)
