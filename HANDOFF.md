# Session Handoff — reiyah-measure

Read this first, then `README.md`. This file is the continuation contract. It is not authority:
resolve every state from the exact artifacts named here, never from this prose.

## 1. Where this sits

Three roots, deliberately separate:

| Root | Purpose | Enter with |
|---|---|---|
| `~/workspace/reiyah` | Gate A static architecture. No runtime, no inference (GA-15). | `reiyahclaudes` |
| `~/workspace/reiyah-measure` | This repository. Produces evidence artifacts from public data. | needs its own launcher |
| `~/workspace/reiyah-private-evidence` | Quarantined UN/NIST payloads. Read-only in spirit. | never copy bytes out |

Reiyah's `AGENTS.md` identity gate requires project, working directory, Git root and repository
contract to all resolve to Reiyah before repository work. **An Odeya-rooted session fails that
gate.** The work recorded here was performed from an Odeya-rooted session doing read-only
research plus authoring this new repository; no Reiyah byte was modified. That deviation is
recorded rather than hidden.

## 2. The mission, stated plainly

Reiyah is an evidence and benchmark engine for object-level driver-vehicle belief, readiness,
recoverability, joint silent misses, causal policy effects, explicit unknowns, transfer, and
worst-group validation. It is not a driver-monitoring classifier.

The standard is absolute: **no result exists until its gate accepts it.** Missing, unmeasured,
out-of-distribution, sensor-invalid and abstained are distinct states and never become zero.
Engineering pressure increases the burden of proof and never increases confidence.

## 3. Why this repository was created

As of 2026-08-27 Reiyah had completed five release cycles of architecture with **zero
measurements**. Its total retained evidence was roughly ten kilobytes of ISO catalogue metadata.
Every one of its 544 known-bad fixtures fails by construction, on demand, for a declared reason —
which is excellent negative testing and is not the same thing as a hypothesis being wrong.

The governance layer had outgrown the science it governed. This repository exists to take the
first measurement.

## 4. What was found, and what was killed

**Killed:** the original framing was "nobody has measured the independence coefficient `c` that
RSS Definition 32 assumes and Corollary 3 uses to cut validation evidence from 10^9 to 10^5
examples." A novelty check found Minhao Qiu's open-access 2024 FAU dissertation, which measured
camera-lidar error correlation on nuScenes and KITTI conditioned on night and rain (rho_FN
0.43-0.53; `c` near 2.9 is derivable from the KITTI table). **Never claim first-to-measure.**
That claim would have been demolished on contact.

**What survives, and is stronger:**

1. **The censored denominator.** `loaders.py:231` deletes every ground-truth object with zero
   lidar and zero radar returns before scoring. Computed at 9.43% of the evaluated validation
   set. This is a correction to published work, including plausibly Qiu's own estimate, since a
   dependence estimate computed through that pipeline is biased toward independence.
2. **The missing bridge.** Of 875 papers citing RSS, zero mention Definition 32, Corollary 3, or
   c-approximate independence. Qiu's thesis contains zero occurrences of "Shalev". The field's
   own authoritative survey (Hoss et al.) contains zero occurrences of "correlat", "common cause"
   or "copula". The measurement literature and the safety-argument literature that depends on it
   have never met.
3. **Class-conditioned dependence.** Nobody has conditioned the coefficient on object class.
   Not on pedestrians, not on children, not on vulnerable road users.

## 5. Exact state right now

| Item | State |
|---|---|
| Result A | **measured.** All ten audits passed, transcript at `results/audit_result_a.txt` |
| Headline | 12,694 of 134,565 (9.43%) removed by the point filter |
| External validation | A3 reproduces nuScenes' published val sample count of 6,019 exactly |
| Analysed bytes | SHA-256 `db48746b10e3544d5ef619eaa3d687e3960626fe1b4422ed856711da5aa7325b` |
| Corrected errors | 3D distance replaced by 2D per `data_classes.py:54-56` (47 of ~53,000 objects, headline unchanged); three corrupted transfers, one caught only by CRC32C |
| Reiyah repository | **untouched.** Its 1.2.1 work in flight belongs to another workstream |

## 5b. Results B and C, same day

**Result B (measured, analytic).** The removal criterion is defined on range-sensor returns
alone, so it correlates with lidar failure by construction and not with camera failure. Lidar-only
recall inflation `N_full / N_eval` is **x1.1042 overall and x1.2461 at 40-50 m**, against x1.0421
within 20 m. By class: traffic cone x1.1817, bicycle x1.1232, car x1.1221, pedestrian x1.0927,
bus x1.0112.

The caveat was found by pressure-testing our own claim and is stated in the README rather than
buried: `num_lidar_pts` counts the **keyframe sweep only**, while production detectors accumulate
around ten sweeps. So the factor is an **upper bound**, not a point estimate. Direction of the
bias is assumption-free; magnitude is not.

**Result C (hypothesis rejected).** We expected Qiu's dependence estimate to have inherited the
filter. It did not. Qiu uses an independent pipeline — front-facing ROI 30 m by 50 m split at
30 m, Hungarian assignment on GIoU — and the only ground-truth filter described is spatial. The
terms `num_lidar_pts`, `num_pts`, devkit and zero-point appear nowhere in the dissertation.

The replacement is stronger. Two communities measure on two different denominators and neither
has noticed: Qiu measured dependence on an uncensored set and found false-negative correlation
of 0.43 to 0.53, while the benchmark the field optimises against removes a range-sensor-selected
9.43% of its ground truth. The phenomenon has been measured and the leaderboard cannot see it.
**Say this in a way that strengthens Qiu's work, because it does.**

## 6. The next smallest action

Results A, B and C are settled. The open gap is Result B's upper bound, and only a detector can
close it.

**Run one camera-only and one lidar-only detector over the validation set twice — with the
zero-point filter and without it — and report the delta.** That converts the x1.1042 bound into a
measurement, and it directly answers the question a reviewer will ask first.

Stack, already verified: nuScenes is the only dataset where both arms exist as downloadable
weights. Camera arm PETR, lidar arm BEVFusion-lidar or CenterPoint, **both from MMDetection3D
v1.4.0** so one environment and one metric path serves both. Torch 2.1 with CUDA 12.1, mmcv 2.1.0
prebuilt wheel, Python 3.10.

### The compute is already built — do not rebuild it

`gcloud` is authenticated as `dev@alfred-ai.app` on project `sunlit-unison-487018-b0`.

| Resource | State |
|---|---|
| `sentinel-gpu`, zone `us-west1-a` | `g2-standard-8`, **NVIDIA L4 24 GB**, driver 580, currently TERMINATED |
| `sentinel-nuscenes-data-1tb` | 1 TB disk, attached, mounted `/datasets/nuscenes-full` |
| Dataset on that disk | **complete trainval**: `samples` 53 GB, `sweeps` 342 GB, `v1.0-trainval` metadata 2.5 GB, `maps`, plus 294 GB of original archives |

Start with `gcloud compute instances start sentinel-gpu --zone us-west1-a`, reach it with
`gcloud compute ssh sentinel-gpu --zone us-west1-a --tunnel-through-iap`. Roughly $0.85-1.00/hour
while running, near zero while stopped. **Stop it when not actively computing.**

### The one real obstacle, and how to get round it

The box carries **torch 2.9.1 + CUDA 12.9**. mmcv 2.1.0, which MMDetection3D v1.4.0 requires, has
prebuilt wheels only up to cu121/torch2.1.0. So a native install means either downgrading torch —
which would disturb the Sentinel stack that owns this machine — or building mmcv from source
against cu129, which is the multi-week failure mode. Root has only 30 GB free, which is tight for
a second environment plus weights.

**Use a container.** containerd is present at `/opt/containerd`. A pinned image carrying
torch 2.1 + cu121 + mmcv 2.1.0 + mmdet3d v1.4.0 isolates the toolchain completely, leaves
Sentinel's environment untouched, and makes the run reproducible by digest — which this program
should want anyway. Mount `/datasets/nuscenes-full` read-only into it.

Do not install mmcv into the host Python. That machine belongs to another mission.

The per-object matcher is the one piece that must be written: the devkit's `accumulate()` keeps
its match set in a local variable named `taken` and discards it on return, so per-object
true-positive and false-negative outcomes are not exposed. Re-implement it keeping `taken`, then
validate by re-aggregating your per-object table back to the official mAP and NDS. **Do not skip
that validation step** — it is the only proof the matcher is the official one.

## 7. Then, in order

1. Determine whether Qiu's pipeline inherited the zero-point filter. If it did, their dependence
   estimate is biased and we say so carefully and generously — it strengthens their conclusion.
2. Re-run one published camera-only detector with and without the filter and report the delta in
   its headline numbers. This needs a GPU and the 370 GB sensor blobs; the host machine currently
   has under 3 GB free, so it belongs in GCP where the data already sits.
3. Only then, the dependence coefficient itself, stratified, with the worst-group rule enforced
   so a thin class resolves to `insufficient` rather than to a number the data cannot carry.

## 8. Traps already identified

| Trap | Why it bites |
|---|---|
| Effective N | 2 Hz annotation over 20 s scenes gives ~40 near-identical boxes per object. Cluster on `instance_token` or intervals shrink by roughly sqrt(30) and manufacture significance. |
| Shared difficulty | Marginal dependence is guaranteed by range and occlusion. The estimand is *conditional* independence. |
| Operating point | "Missed" is undefined until a score threshold is chosen, and two detectors' confidences are not mutually calibrated. Match at equal recall and show the result does not flip. |
| Reference contamination | nuScenes ground truth is annotated with lidar in the loop, so the reference shares a modality with one channel. Declare it. |
| Bike-rack filter | Runs *after* the point filter, so it does not change this statistic — but it does shrink the final evaluation set. |
| GPU generation | mmcv 2.1.0 prebuilt wheels stop at CUDA 12.1. A Blackwell card turns a two-day setup into two weeks. |

## 9. Standards this work is held to

Plain reviewable Markdown, JSON and deterministic scripts. Normative requirements separate from
rationale. Every claim carries the epistemic state of its evidence. A computed number is not a
measurement; a passing validator is not acceptance; a checksum is not truth; generated prose is
not evidence.

Failures are information. Preserve them as diagnostics, known-bad fixtures, open findings,
contradictions or retractions. Never weaken a check to make a run pass.

## 10. Required closeout for the next session

State, separately and from exact records: repository root, branch and commit; worktree
cleanliness and every uncommitted path; the audit result for every check in
`tools/audit_result_a.py`; whether Result A is computed or measured; what remains unverified; and
the next smallest authorized action.
