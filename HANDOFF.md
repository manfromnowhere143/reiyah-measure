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
| Result A | **computed, audit incomplete** — see README "Audit status" |
| Headline | 12,694 of 134,565 (9.43%) removed by the point filter |
| Corrected error | 3D distance replaced by 2D per `data_classes.py:54-56`; headline unchanged |
| Audit runs | two terminated by network truncation; one transfer rejected by CRC32C integrity check |
| Reiyah repository | **untouched.** Its 1.2.1 work in flight belongs to another workstream |

## 6. The next smallest action

Complete the audit on a checksum-verified local copy:

```sh
cd ~/workspace/reiyah-measure
gsutil cp gs://sunlit-unison-487018-b0-sentinel/nuscenes/v1.0-trainval_meta.tgz /tmp/meta.tgz
shasum -a 256 /tmp/meta.tgz          # record this digest in the README provenance table
python3 tools/audit_result_a.py < /tmp/meta.tgz
```

`gsutil cp` verifies CRC32C and will delete a corrupted transfer; a plain pipe will not. On an
unreliable connection this distinction has already produced one silently corrupted download.

If every audit passes, Result A becomes a measurement and the README status table changes. If any
audit fails, **the finding is withdrawn, not weakened.**

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
