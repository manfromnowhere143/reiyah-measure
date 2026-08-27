# reiyah-measure

An evidence-producing measurement engine for the Reiyah research program.

This repository is **deliberately separate from Reiyah**. Reiyah's Gate A control GA-15 requires
that its architecture contain no product runtime and no live inference. Model execution and
dataset analysis therefore cannot live inside the Reiyah packet without invalidating it. This
repository produces evidence artifacts; Reiyah may later admit them through its source ledger,
under its own rules, as it would admit any third-party evidence. Nothing here has Reiyah
authority.

## Status

| Field | Value |
|---|---|
| Lifecycle status | `proposed` |
| Result A | **measured** — all ten audits passed on a checksum-verified copy |
| Result B | **measured** — analytic, derived from the same audited object set |
| Reiyah Gate B | not authorized; not required for the work in this repository |
| Operator acceptance | none |
| Claims created | none |

No finding in this repository may be described as a result until its audit passes. A computed
number is not a measurement. Result A has now passed; the audit transcript is retained at
[`results/audit_result_a.txt`](results/audit_result_a.txt).

## What this is for

Reiyah asks whether a versioned human-automation system can support independently falsifiable
analysis of object-level belief, readiness, recoverability, joint silent misses, causal policy
effects, transfer, and worst-group behaviour. Answering any of that requires counting things
correctly, on a denominator that is stated rather than assumed.

This repository is where the counting happens.

## Result A (measured)

**Question.** The official nuScenes 3D detection evaluation removes ground-truth objects before
any detector is scored. How many, and which ones?

**The mechanism.** In `nuscenes-devkit`, `python-sdk/nuscenes/eval/common/loaders.py`:

```python
# line 231
eval_boxes.boxes[sample_token] = [box for box in eval_boxes[sample_token]
                                  if not box.num_pts == 0]
```

and at line 137, `num_pts = num_lidar_pts + num_radar_pts`. Every annotated object that returned
no lidar points and no radar points is deleted from the ground truth. This applies to every
detector evaluated on nuScenes, including camera-only detectors, for which some of those objects
are precisely the ones only they could have found.

`filter_eval_boxes` applies its filters in order: the class-range distance filter first
(lines 226-227), then this point filter (line 231), then bike-rack filtering (line 234+). The
honest denominator for this question is therefore *boxes surviving the distance filter*.

**Measured figures.** nuScenes v1.0-trainval, official 150-scene validation split, ten evaluated
detection classes:

| Quantity | Value |
|---|---|
| Val annotations in evaluated classes | 187,528 |
| Removed first by the distance filter | 52,963 |
| Surviving distance filter (denominator) | 134,565 |
| **Removed by the zero-point filter** | **12,694 (9.43%)** |
| ...of those, annotated 80-100% visible in cameras | 2,207 |

Gradients matter more than the headline:

| Ego distance | % removed | | Camera visibility | % removed |
|---|---|---|---|---|
| 0-20 m | 4.04% | | v0-40 | 27.02% |
| 20-30 m | 9.99% | | v40-60 | 7.10% |
| 30-40 m | 13.80% | | v60-80 | 4.47% |
| 40-50 m | 19.75% | | v80-100 | 3.15% |

By class, the most affected are traffic cones (15.38%), bicycles (10.97%) and cars (10.89%);
the least affected is bus (1.10%).

**What this does and does not mean.** A zero point count means no lidar or radar return fell
inside the annotated box in that keyframe, which for a distant or heavily occluded object is
expected physics rather than detector failure. The finding is not that the objects are easy. It
is that the evaluation denominator silently excludes roughly one annotated object in eleven,
with a five-fold gradient in range, and that this is invisible in every published nuScenes
number. The 2,207 objects annotated as 80-100% visible in the cameras are the cleanest case:
fully camera-visible, and excluded.

**Why it bears on dependence estimation.** An object the camera can see and the range sensors
cannot is the single most informative case for estimating whether two sensing channels fail
together. The filter removes that cell by construction, so any dependence estimate computed
through the official pipeline is biased toward independence.

## Result B (measured): camera and lidar are not scored on the same objects

Result A says 9.43% of the ground truth is removed. The obvious next question is how much that
moves anything. It can be answered without running a detector.

The removal criterion is `num_lidar_pts + num_radar_pts == 0`. It is defined on range-sensor
returns and nothing else. So it is correlated with lidar failure **by construction**, and
uncorrelated with camera failure. The benchmark deletes objects the range sensors could not see,
regardless of what the cameras saw. 2,207 of the deleted objects are annotated 80-100%
camera-visible.

Expressing a lidar-only detector's recall over the complete in-range annotated set instead of the
filtered one gives an inflation factor of `N_full / N_eval`:

| Stratum | N_full | N_eval | Removed | Inflation | Camera-visible |
|---|---|---|---|---|---|
| **All** | 134,565 | 121,871 | 12,694 | **x1.1042** | 2,207 |
| 0-20 m | 54,626 | 52,418 | 2,208 | x1.0421 | 482 |
| 20-30 m | 38,242 | 34,420 | 3,822 | x1.1110 | 856 |
| 30-40 m | 26,385 | 22,745 | 3,640 | x1.1600 | 373 |
| **40-50 m** | 15,312 | 12,288 | 3,024 | **x1.2461** | 496 |

By class, worst first: traffic cone x1.1817, bicycle x1.1232, car x1.1221, pedestrian x1.0927.
Least affected: bus x1.0112.

The gradient is the finding. Near the vehicle the effect is 4%. At 40-50 metres it is 25% — and
long range is exactly where the camera-versus-lidar argument lives.

### The assumption, and its limit

`num_lidar_pts` counts returns inside the box in the **keyframe sweep only**. Most production
lidar detectors accumulate around ten sweeps, so an object with zero keyframe points may still
carry evidence in the accumulated stack. More so if it moved into view; less so if it is
statically occluded, since adjacent sweeps then share nearly the same geometry.

So "undetectable" is too strong, and the inflation factor is an **upper bound**: it is the
correction if zero keyframe returns implies non-detection. The true correction lies between 1.0
and the figure shown. Closing that gap requires running a detector, which this repository has not
yet done.

What does not depend on the assumption is the direction. The removal criterion is a range-sensor
criterion. Whatever its exact magnitude, the bias runs one way, and it grows with distance.

This is not a claim that any published number is wrong. It is a claim that camera-only and
lidar-only methods are not being scored against the same set of objects, and that the difference
is largest where it matters most.

## Provenance

| Item | Value |
|---|---|
| Dataset | nuScenes v1.0-trainval metadata (`v1.0-trainval_meta.tgz`) |
| Official source | `https://motional-nuscenes.s3.amazonaws.com/public/v1.0/v1.0-trainval_meta.tgz` |
| Byte size | 461,678,030 |
| SHA-256 of analysed bytes | `db48746b10e3544d5ef619eaa3d687e3960626fe1b4422ed856711da5aa7325b` |
| Transport used | `gs://sunlit-unison-487018-b0-sentinel/nuscenes/` (mirror) |
| Mirror verification | exact size match, plus five 512 KiB ranges at offsets 0, 104857600, 230000000, 400000000 and 461155630 confirmed byte-identical to the official source |
| Licence | CC BY-NC-SA 4.0, non-commercial research use |
| Devkit reference | `nuscenes-devkit` master, `loaders.py:137,231`, `data_classes.py:54-56` |

The mirror was verified rather than trusted. Provenance runs to Motional; the bucket is
transport only.

## Audit status

`tools/audit_result_a.py` is an adversarial audit designed to fail loudly. It checks scene and
split counts against published figures, verifies every validation sample has a keyframe
`LIDAR_TOP` ego pose, verifies no annotation is silently skipped, verifies visibility tokens
resolve, rejects negative or absent point counts, independently recounts the headline figures,
and rejects degenerate zero-size boxes as an innocent explanation for deletion.

**All ten checks pass** on a checksum-verified local copy. Full transcript:
[`results/audit_result_a.txt`](results/audit_result_a.txt).

The decisive check is A3. nuScenes publishes its validation split as 6,019 samples; this
pipeline's scene, split and sample join reproduces **exactly 6,019**. That is external validation
of the join, not merely internal self-consistency. A8 and A9 then recount the headline figures by
an independent code path and match to the object.

Two errors were found and corrected before the audit passed, and both are recorded rather than
quietly fixed:

1. The class-range filter used a 3D distance where `data_classes.py:54-56` defines `ego_dist` as
   the 2D (xy) norm. Correcting it moved 47 objects out of ~53,000 and left the 9.43% headline
   unchanged. The insensitivity is a robustness observation, not a substitute for the audit.
2. Three transfers were corrupted in flight on an unreliable connection. Two truncated mid-stream
   and failed loudly; a third was silently corrupted and was caught only because `gsutil cp`
   verifies CRC32C and deleted it. **A plain pipe would not have caught it.** The final analysis
   was run against a local copy whose SHA-256 is recorded in the provenance table above and which
   matches an independently downloaded earlier copy.

An additional figure the audit surfaced: 16,162 surviving objects (12.01%) returned **zero lidar
points**, of which radar rescues 3,468 — leaving the 12,694 that are deleted. Separately, 82,340
(61.19%) returned zero radar points.

## Reproducing

```sh
# Both scripts read the metadata tarball on stdin and land nothing on disk.
gsutil cat gs://<bucket>/nuscenes/v1.0-trainval_meta.tgz | python3 tools/result_a.py
gsutil cat gs://<bucket>/nuscenes/v1.0-trainval_meta.tgz | python3 tools/audit_result_a.py
```

Prefer a checksum-verified local copy over a pipe on an unreliable connection. `gsutil cp`
verifies CRC32C; a plain pipe does not.

## Non-claims

This repository does not claim that nuScenes is wrong, that any published detection number is
invalid, that any detector is better or worse than another, that sensor failures are dependent or
independent, or that any safety conclusion follows. It reports what a documented filter removes.
Interpretation beyond that requires evidence this repository does not yet hold.
