# Family-as-Evaluator (FaE) Protocol — Specification v1.0

**Authors**: Byoungsang Lee, Jung Heon Lee
**License**: CC-BY 4.0
**Status**: v1.0

This document is the canonical specification of the FaE protocol.
Appendix F of the companion paper is a copy of this file. If they ever
diverge, this file is the authority.

---

See `SPEC.md` rendered into the paper at `paper/sections/appendix_F_protocol.md`.

## Files in this directory

| File | Purpose |
|---|---|
| `SPEC.md` | this specification (= paper Appendix F) |
| `probes_v1.jsonl` | the 30-probe v1 set referenced by the spec |
| `probes_v1.sha256` | SHA-256 of probes_v1.jsonl (pin in pre-registrations) |
| `preregistration_template.yaml` | YAML template to fork |
| `scoring_template.csv` | CSV header for evaluator scoring |
| `taxonomy_v1.txt` | failure-mode tag list |
| `examples/run_lee2026.yaml` | the pre-registration of our N=1 case study |

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

```bibtex
@misc{lee2026fae,
  title  = {Family-as-Evaluator: A Protocol Specification for Niche-Population LLM Evaluation},
  author = {Lee, Byoungsang and Lee, Jung Heon},
  year   = {2026},
  howpublished = {Version 1.0, CC-BY 4.0,
                  \url{https://github.com/[author]/gemma4-trilingual-family/blob/main/tools/fae_protocol/SPEC.md}}
}
```
