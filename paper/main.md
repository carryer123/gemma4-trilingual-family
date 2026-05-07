# Beyond BLEU: Family-as-Evaluator for Trilingual L1-Aware On-Device Tutoring with Gemma 4

**Authors**: Byoungsang Lee^1,2,*^, Jung Heon Lee^1,3,†^

^1^ School of Advanced Materials Science and Engineering, Sungkyunkwan University (SKKU), Suwon 16419, Korea
^2^ MoonTechnology, 3F, 29-5, World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea
^3^ Department of MetaBioHealth, Sungkyunkwan University (SKKU), Suwon 16419, Korea

^*^ First author. ^†^ Correspondence: Prof. Jung Heon Lee (jhlee7@skku.edu)

**ORCID**: Byoungsang Lee 0000-0001-6874-0935 · Jung Heon Lee 0000-0003-4790-3525

**Code & data**: https://github.com/[author]/gemma4-trilingual-family
(Apache 2.0)

---

## Abstract

Multicultural families with two parental L1s and a child growing up
trilingual are a fast-growing demographic, yet existing language-tutoring
products treat each user as a monolingual literate single learner. We
present a trilingual KO + RU + EN co-learning system built around
Gemma 4 E2B running entirely on a phone, with a moon1-hosted Gemma 4 26B
+ MTP-drafter + SoulX-FlashHead avatar premium tier. Three contributions:
(1) a 50× English-pivot data augmentation taking 247 direct KO-RU pairs
to 12,408 trilingual triples, plus a Gemma 4 E4B-distilled 2,300-card
synthetic learning corpus produced at 0.87 cards/s with `think:False` +
4-GPU round-robin (a 22× systems speedup over the naive baseline);
(2) a Family-as-Evaluator protocol — a 30-probe rubric scored by an
actual KO-L1 / RU-L1 / EN-bridge multicultural household with a
21-month-old child — that surfaces failure modes invisible to BLEU,
COMET, and JSON-schema parse rate; (3) an empirical demonstration that
LoRA fine-tuning, even when it descends loss cleanly to 0.15 in two
hours, can *regress* on under-represented policies (transliteration
script-direction: 100% → 25%) while improving on family-context realism,
L1-aware refusals, and empty-response rate. We document the regression,
trace it to data-policy frequency, and fix it in LoRA-v2 with 300
explicit transliteration pairs. We release the LoRA adapter, the
trilingual dataset, and the 30-probe Family-as-Evaluator set under
Apache 2.0 + CC-BY. The work was submitted to the 2026 Kaggle Gemma 4
Good Hackathon and is part of a publicly-funded Sejong regional content
program scaling to N=20 multicultural households in late 2026.

---

## Section index

The full paper assembles in this order. Each section is a separate file
under `paper/sections/`:

1. [Introduction](sections/01_introduction.md)
2. [Related Work](sections/02_related_work.md)
3. [Method](sections/03_method.md)
4. [Family-as-Evaluator](sections/04_family_as_evaluator.md)
5. [Experiments](sections/05_experiments.md)
6. [Discussion and Limitations](sections/06_discussion.md)
7. [Future Work and the Sejong Pipeline](sections/07_future_work.md)
8. [Conclusion](sections/08_conclusion.md)

**Appendices**:

- [Appendix A — Dataset construction details](sections/appendix_A_dataset.md)
- [Appendix B — LoRA hyperparameters and training setup](sections/appendix_B_hparams.md)
- [Appendix C — Family-as-Evaluator probe set (30 probes)](data_release/family_as_evaluator_probes_v1.jsonl)
- [Appendix D — Failure case gallery (LoRA-v1 vs. stock E2B)](sections/appendix_D_failure_gallery.md)
- [Appendix E — Reproducibility](sections/appendix_E_repro.md)
- [Appendix F — FaE protocol specification (mirrored at `tools/fae_protocol/SPEC.md`)](sections/appendix_F_protocol.md)

**References**: [references.bib](references.bib)

---

## How to read this paper

* **For ML reviewers**: §3 (Method) and §5 (Experiments) are the
  technical core. §5.2 reports the LoRA-v1 vs. stock auto-judge with
  the script-direction regression in detail. Appendix B covers
  hyperparameters, Appendix D shows raw failure cases.
* **For HCI reviewers**: §4 (Family-as-Evaluator) is the methodological
  core. §6.1 addresses the N=1 critique head-on. §7.2 commits to the
  N=20 panel via the Sejong family-center program.
* **For practitioners**: §3.2 (data) and Appendix A (schemas) are a
  recipe for replicating the trilingual dataset for any other language
  triple. The released LoRA adapter and dataset card are linked at the
  top.

---

## Submission timeline

| Version | Target venue | Date | New material vs. prior |
|---|---|---|---|
| v1 | arXiv preprint + Kaggle Gemma 4 Good Hackathon | **2026-05-17** | base paper |
| v2 | LoResMT or MRL workshop @ ACL/EMNLP | 2026-06 | LoRA-v2 + family human-eval |
| v3 | ACL Findings 2027 or CHI 2027 | 2026-12 | Sejong N=20 panel + 3 more language triples + child-speech eval |
| v4 | journal (Computer Speech & Language or similar) | 2027 spring | 6-month longitudinal, IRB clear, full power analysis |

---

## Acknowledgements

This work began in the home of the first author. The 21-month-old
participant is the first author's child; the RU-L1 evaluator is the
first author's spouse. We are grateful to MoonTechnology and the SKKU
School of Advanced Materials Science and Engineering for protected
research time, and to the Sejong Regional Specialized Content
Development support program (administered by Sejong Cultural
Industries Promotion Foundation) for the funding pipeline that makes
the N=20 family-center scaling milestone in §7 financially feasible.
The 4× A100 80GB cluster used for training and distillation is part
of the KISTI HPC infrastructure. We thank the Gemma 4, Unsloth,
SoulX-FlashHead, Tatoeba, and Ollama communities for the open-source
substrate this work is built on.
