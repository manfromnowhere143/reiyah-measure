"""Build a compact ground-truth cache for the nuScenes val split.

One record per annotated object in the ten evaluated detection classes that
survives the official class-range distance filter. Everything downstream reads
this instead of re-parsing 461 MB of metadata.

Reads the metadata tarball on stdin. Writes JSON to the path given as argv[1].

Filter order follows nuscenes-devkit filter_eval_boxes():
  1. class-range distance filter   loaders.py:226-227
  2. zero-point filter             loaders.py:231     <- recorded, NOT applied
We record num_lidar_pts and num_radar_pts so the point filter can be applied or
withheld downstream. That switch is the whole experiment.
"""
import ast, json, math, sys, tarfile

WANT = {"sample_annotation.json", "instance.json", "category.json", "sample.json",
        "scene.json", "visibility.json", "sample_data.json", "ego_pose.json",
        "calibrated_sensor.json", "sensor.json"}
t = {}
tar = tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz")
for m in tar:
    b = m.name.rsplit("/", 1)[-1]
    if b in WANT and m.isfile():
        f = tar.extractfile(m)
        if f is not None:
            t[b] = json.loads(f.read())
            print(f"  {b}: {len(t[b]):,}", file=sys.stderr)
    if len(t) == len(WANT):
        break

cat = {c["token"]: c["name"] for c in t["category.json"]}
inst = {i["token"]: cat[i["category_token"]] for i in t["instance.json"]}
samp = {s["token"]: s["scene_token"] for s in t["sample.json"]}
scn = {s["token"]: s["name"] for s in t["scene.json"]}
desc = {s["token"]: s.get("description", "") for s in t["scene.json"]}
vis = {v["token"]: v["level"] for v in t["visibility.json"]}
sen = {s["token"]: s["channel"] for s in t["sensor.json"]}
csc = {c["token"]: sen[c["sensor_token"]] for c in t["calibrated_sensor.json"]}
ego = {e["token"]: e["translation"] for e in t["ego_pose.json"]}
sego = {sd["sample_token"]: ego[sd["ego_pose_token"]] for sd in t["sample_data.json"]
        if sd["is_key_frame"] and csc.get(sd["calibrated_sensor_token"]) == "LIDAR_TOP"}

VAL = None
for node in ast.parse(open("evidence/nuscenes_splits_devkit.py").read()).body:
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "val":
                VAL = set(ast.literal_eval(node.value))

DET = {"movable_object.barrier": "barrier", "vehicle.bicycle": "bicycle",
       "vehicle.bus.bendy": "bus", "vehicle.bus.rigid": "bus", "vehicle.car": "car",
       "vehicle.construction": "construction_vehicle", "vehicle.motorcycle": "motorcycle",
       "human.pedestrian.adult": "pedestrian", "human.pedestrian.child": "pedestrian",
       "human.pedestrian.construction_worker": "pedestrian",
       "human.pedestrian.police_officer": "pedestrian",
       "movable_object.trafficcone": "traffic_cone", "vehicle.trailer": "trailer",
       "vehicle.truck": "truck"}
R = {"car": 50, "truck": 50, "bus": 50, "trailer": 50, "construction_vehicle": 50,
     "pedestrian": 40, "motorcycle": 40, "bicycle": 40, "traffic_cone": 30, "barrier": 30}

out = []
for a in t["sample_annotation.json"]:
    st = samp[a["sample_token"]]
    if scn[st] not in VAL:
        continue
    d = DET.get(inst[a["instance_token"]])
    if d is None:
        continue
    e = sego[a["sample_token"]]
    tr = a["translation"]
    dist = math.hypot(tr[0] - e[0], tr[1] - e[1])   # data_classes.py:54-56, 2D
    if dist >= R[d]:
        continue
    dsc = desc[st].lower()
    out.append({
        "sample_token": a["sample_token"],
        "instance_token": a["instance_token"],
        "cls": d,
        "raw_cls": inst[a["instance_token"]],
        "xy": [tr[0], tr[1]],
        "ego_xy": [e[0], e[1]],
        "dist": round(dist, 3),
        "nl": a["num_lidar_pts"],
        "nr": a["num_radar_pts"],
        "vis": vis.get(a.get("visibility_token", ""), "unknown"),
        "cond": "night" if "night" in dsc else ("rain" if "rain" in dsc else "clear"),
    })

with open(sys.argv[1], "w") as f:
    json.dump(out, f)
zero = sum(1 for r in out if r["nl"] + r["nr"] == 0)
print(f"\nGT cache: {len(out):,} objects  |  zero-point: {zero:,} ({100*zero/len(out):.2f}%)")
print(f"written to {sys.argv[1]}")
