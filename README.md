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
| Result A | computed, **audit incomplete** |
| Reiyah Gate B | not authorized; not required for the work in this repository |
| Operator acceptance | none |
| Claims created | none |

No finding in this repository may be described as a result until its audit passes. A computed
number is not a measurement.

## What this is for

Reiyah asks whether a versioned human-automation system can support independently falsifiable
analysis of object-level belief, readiness, recoverability, joint silent misses, causal policy
effects, transfer, and worst-group behaviour. Answering any of that requires counting things
correctly, on a denominator that is stated rather than assumed.

This repository is where the counting happens.

## Result A (computed, unaudited)

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

**Computed figures.** nuScenes v1.0-trainval, official 150-scene validation split, ten evaluated
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

## Provenance

| Item | Value |
|---|---|
| Dataset | nuScenes v1.0-trainval metadata (`v1.0-trainval_meta.tgz`) |
| Official source | `https://motional-nuscenes.s3.amazonaws.com/public/v1.0/v1.0-trainval_meta.tgz` |
| Byte size | 461,678,030 |
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

**It has not yet completed.** Two runs were terminated by network truncation mid-stream, and a
third transfer was rejected by gsutil's CRC32C integrity check, which detected in-flight
corruption and deleted the local file. Until the audit passes on a checksum-verified local copy,
Result A is a computed number and not a measurement.

One error has already been found and corrected by this process: the first implementation used a
3D distance for the class-range filter, where `data_classes.py:54-56` defines `ego_dist` as the
2D (xy) norm. Correcting it moved the distance-filter count by 47 objects out of ~53,000 and left
the 9.43% headline unchanged. That insensitivity is recorded as a robustness observation, not as
a substitute for the audit.

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
