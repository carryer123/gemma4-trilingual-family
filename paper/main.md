# State-Gated Audit for Niche-Population LoRA Fine-Tuning: A Trilingual Case Study

**Authors.** Byoungsang Lee^1,2^, Yunchul Kim^1^, Youmin Shim^1^, Chaewon Kwak^1^, Jung Heon Lee^1,3,*^

^1^ School of Advanced Materials Science and Engineering, Sungkyunkwan University (SKKU), Suwon 16419, Korea
^2^ MoonTechnology, 3F, 29-5, World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea
^3^ Department of MetaBioHealth, Sungkyunkwan University (SKKU), Suwon 16419, Korea

^*^ Correspondence: Jung Heon Lee (jhlee7@skku.edu)

**ORCID iDs.** Byoungsang Lee, 0000-0001-6874-0935; Yunchul Kim, 0000-0002-7278-1411; Youmin Shim, 0009-0006-6900-1628; Chaewon Kwak, 0000-0001-7762-8435; Jung Heon Lee, 0000-0003-4790-3525.

---

## Abstract

Held-out loss and task metrics are useful for selecting LoRA adapters, but
they do not certify deployment-specific behavior. We present a trilingual
KO/RU/EN case study in which one loss-attractive Gemma 4 E2B LoRA trajectory
failed a deployment-critical cross-script gate while scalar metrics remained
acceptable. The finding is deliberately narrow: the failure occurs in one
historical training trajectory and is not reproduced in 13 controlled
retrainings. We therefore do not claim a reproducible cliff law, a calibrated
detector, or a population failure rate. The contribution is a conservative
**state-gated audit** workflow for niche-population adapter promotion. The
workflow names deployment gates, records raw generations, separates
GREEN/AMBER/RED audit states, and maps those states to actions. In an audit
atlas of 176 dependent artifacts, the original trajectory remains the most
severe G2 script-state failure under an expanded 52-probe rerun (36/52; worst
direction 6/13) and is also RED under an expanded 80-probe G3 schema audit
(52/80). Several controls are threshold-sensitive or blocked by independent
G2/G3 debt. This is an audit case study, not a benchmark.

---

## Section index

1. [Introduction — state-gated audit for niche LoRA deployment](sections/01_introduction.md)
2. [Related Work](sections/02_related_work.md)
3. [State-Gated Audit: Method](sections/03_method.md)
4. [Behavioral Gate Suite and Audit Protocol](sections/04_family_as_evaluator.md)
5. [Experiments — disagreement on every variant that can disagree](sections/05_experiments.md)
6. [Discussion — claim boundaries and limitations](sections/06_discussion.md)
7. [Future Work and Scaling Plan](sections/07_future_work.md)
8. [Conclusion](sections/08_conclusion.md)

**Appendices**:

- [Appendix A — Dataset construction details](sections/appendix_A_dataset.md)
- [Appendix B — LoRA hyperparameters and training setup](sections/appendix_B_hparams.md)
- [Appendix C — probe sets](data_release/family_as_evaluator_probes_v1.jsonl)
- [Appendix D — Failure case gallery (raw outputs)](sections/appendix_D_failure_gallery.md)
- [Appendix E — Reproducibility](sections/appendix_E_repro.md)
- [Appendix F — FaE protocol specification](sections/appendix_F_protocol.md)

**References**: [references.bib](references.bib)

---

## Acknowledgements

We are grateful to the SKKU School of Advanced Materials Science and
Engineering and MoonTechnology for protected research time. The 4× A100
80GB cluster used for training and distillation is part of the KISTI HPC
infrastructure. We thank the Gemma 4, Unsloth, Tatoeba, and Ollama
communities for the open-source substrate this work is built on.
