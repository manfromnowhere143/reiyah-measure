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
| Result C | **hypothesis rejected** — the published estimate does not inherit the filter |
| Result D | **measured** — RSS coefficient c is 1.24 to 2.37; independence rejected |
| Corrections | two claims from Results A and B withdrawn, recorded in Result D |
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
together. The filter removes that cell by construction, so a dependence estimate computed
*through the official pipeline* would be biased toward independence.

We tested whether the published estimate is affected. It is not — see Result C, where that
hypothesis is recorded as rejected. The consequence turns out to be structural rather than
corrective: the field's benchmark cannot reflect a phenomenon that has already been measured
elsewhere.

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

## Result C: a hypothesis of ours, killed — and what replaced it

We expected the published dependence literature to have inherited this filter. If Qiu's 2024 FAU
dissertation, which measured camera-lidar error correlation on nuScenes, had run through the
official evaluation pipeline, its estimate would be biased toward independence and we could
report a correction.

**It did not, and the hypothesis is dead.** Qiu builds an independent pipeline: a front-facing
region of interest of 30 m lateral by 50 m longitudinal, split at 30 m, with Hungarian assignment
between perception results and ground truths on GIoU. The dissertation describes exactly one
ground-truth filter — *"Ps and GTs are filtered by the ROI"* — and the terms `num_lidar_pts`,
`num_pts`, devkit, and zero-point appear nowhere in the document. Absence in the text is not
proof of absence in the code, but the described method contains no point-count filter.

What replaced the hypothesis is more interesting than the hypothesis was.

**Two communities are measuring on two different denominators, and neither has noticed.** Qiu
measured camera-lidar failure dependence on an *uncensored* ground-truth set and found
correlation of 0.43 to 0.53 for false negatives. The detection benchmark that the entire field
optimizes against removes 9.43% of its ground truth, selected by a range-sensor criterion —
which is to say, it removes a biased sample of exactly the objects where lidar fails and the
correlation Qiu measured would show up.

So the phenomenon has been measured, and the leaderboard is structurally incapable of reflecting
it. That is not a correction to Qiu. It is a reason their result has been ignorable: the numbers
the field actually competes on cannot see what they found.

This strengthens their work rather than undermining it, and we will say so in those words.

## Result D (measured): the RSS coefficient, and a correction to Result A

RSS Definition 32 calls two subsystem error events *one side c-approximate independent* when
`P[r1 AND r2] <= c * P[r1] * P[r2]`, and Corollary 3 uses that to cut required validation evidence
from roughly 10⁹ examples to 10⁵. The coefficient is never estimated in that paper. The smallest
value consistent with an observed pair is the lift, `c = P[both miss] / (P[cam miss] * P[lid miss])`.

We measured it, on the official camera-only and lidar-only detection results nuScenes publishes
itself: **Mapillary MonoDIS** (29.8 mAP, camera) against **Megvii CBGS** (51.9 mAP, lidar), same
val split, same format.

| Operating point | N | cam miss | lid miss | joint observed | joint if independent | **c** |
|---|---|---|---|---|---|---|
| score >= 0.1 | 134,565 | 0.3137 | 0.1344 | 0.0958 | 0.0422 | **2.271** |
| score >= 0.2 | 134,565 | 0.3945 | 0.2196 | 0.1627 | 0.0866 | **1.878** |
| score >= 0.3 | 134,565 | 0.4643 | 0.3399 | 0.2505 | 0.1578 | **1.587** |
| score >= 0.4 | 134,565 | 0.5590 | 0.4887 | 0.3724 | 0.2731 | **1.363** |
| score >= 0.5 | 134,565 | 0.6862 | 0.5982 | 0.5085 | 0.4105 | **1.239** |

**Independence is rejected at every operating point, and in every stratum we looked at.** The
lowest value anywhere is 1.03; the highest is 2.37. Camera and lidar fail together substantially
more often than the product of their marginals predicts.

Read against Corollary 3: for this detector pair, the reduction in required validation evidence
is overstated by a factor of roughly **1.2 to 2.3**, depending on where you set the threshold.

By class at score >= 0.3, worst first: car 1.994, bus 1.609, barrier 1.579, traffic cone 1.444,
pedestrian 1.361, motorcycle 1.301, truck 1.274, bicycle 1.259, construction vehicle 1.080,
trailer 1.033.

### Two things we got wrong, stated plainly

**One: the direction of the censoring bias.** Result A closed by reasoning that a dependence
estimate computed on the filtered denominator would be biased *toward* independence. Measurement
says otherwise. At score >= 0.3 the official denominator gives c = 1.630 and the full denominator
gives c = 1.587. The censoring inflates the coefficient by about 3%, it does not deflate it.
Adding the removed objects raises the lidar marginal faster than it raises the joint, so the lift
falls. **That claim is withdrawn.** The measured effect is small and runs the other way.

**Two: where dependence is worst.** Result B's narrative assumed the interesting effects live at
long range. For the coefficient they do not. At score >= 0.3, c falls from 1.970 within 20 m to
1.173 at 40-50 m — because at long range both channels miss so often that the product of the
marginals approaches the joint. Result B's *inflation* gradient is real and does grow with
distance; the *dependence* gradient runs the opposite way. Two different quantities, and we
conflated their narratives.

### What survives

The measurement itself, which is the point. RSS's coefficient has a value, it is not 1, and it is
not close to 1 at any operating point a deployed system would use.

### Caveats that belong on the number

The matcher reproduces published mAP to within 0.07 (lidar) and 0.22 (camera), so the underlying
per-object outcomes are sound. But: these are two specific detectors, one of them a 2019
monocular model at 29.8 mAP; "miss" requires choosing a score threshold and the two detectors'
confidences are not mutually calibrated, which is why the table sweeps the operating point rather
than picking one; and dependence here is *marginal*, not conditional on scene difficulty. Range,
occlusion and object size drive both channels and inflate any marginal association. A
Cochran-Mantel-Haenszel treatment stratified on those covariates is the next refinement, and it
will lower these numbers. It is unlikely to take them to 1.

## Independent replication

Results A and B were re-derived on a second copy of nuScenes obtained separately and years
earlier (file timestamps of March 2019), on different hardware, using code rewritten from scratch
for the extracted directory layout rather than the streamed tarball.

Every figure matches to the object:

| Quantity | macOS, GCS tarball | Linux/L4, disk copy |
|---|---|---|
| Surviving distance filter | 134,565 | 134,565 |
| Removed by point filter | 12,694 (9.43%) | 12,694 (9.43%) |
| Of those, v80-100 visible | 2,207 | 2,207 |
| Inflation 0-20 m | x1.0421 | x1.0421 |
| Inflation 20-30 m | x1.1110 | x1.1110 |
| Inflation 30-40 m | x1.1600 | x1.1600 |
| Inflation 40-50 m | x1.2461 | x1.2461 |

Three axes vary at once: the data copy, the machine, and the code path. Transcript at
[`results/replication_independent_copy.txt`](results/replication_independent_copy.txt); the
second implementation is [`tools/replicate_on_disk.py`](tools/replicate_on_disk.py).

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
