# Family-as-Evaluator (FaE) Protocol — Specification v1.0

**License**: CC-BY 4.0
**Status**: v1.0
**Companion paper**: a paper documenting the gate suite and curriculum is
currently under double-blind review at a peer-reviewed venue; a full citation
will be added here after the review outcome.

This document is the canonical specification of the FaE protocol.

## Files in this directory

| File | Purpose |
|---|---|
| `SPEC.md` | this specification (= paper Appendix F) |
| `probes_v1.jsonl` | the 30-probe v1 set referenced by the spec |
| `probes_v1.sha256` | SHA-256 of probes_v1.jsonl (pin in pre-registrations) |
| `preregistration_template.yaml` | YAML template to fork |
| `scoring_template.csv` | CSV header for evaluator scoring |
| `taxonomy_v1.txt` | failure-mode tag list |
| `examples/run_2026.yaml` | the pre-registration of our N=1 case study |

## Protocol versioning

* `probes_v1.0.0.jsonl` (this release) — first stable
* Future versions follow semver; tag sets are append-only within a major
  version.

## How to adopt FaE for your population

1. **Pick your language triple** (or pair). The triple form is for
   households with two distinct parental L1s + a bridge; the pair form
   is for households where both parents share L1.
2. **Localize the probe surfaces**. Translate the *input texts* of the
   v1 probes into your language triple. Keep the rubric identical.
   File a pull request to add your localization.
3. **Pre-register** (`preregistration_template.yaml`). Pin the SHA-256
   of the probe set you will use.
4. **Recruit evaluators** following §F.2 (two adult L1 evaluators +
   child observer if applicable).
5. **Score** following §F.3 with mandatory free-text on every score ≤ 3.
6. **Tag failure modes** from `taxonomy_v1.txt` and propose new tags as
   needed (open-coded; we will fold them into v2 of the taxonomy).
7. **Report** following §F.4.
8. **Promote claim tier** following §F.5 if you have N ≥ 10 households.

## Citation

A citation will be added here after the companion paper's review outcome.
Until then, please cite the spec by its version (`FaE v1.0`) and the
repository commit hash.
