# 8. Conclusion

We argued that for a multicultural family with three live languages and
a pre-literate child, the right primary metric is not BLEU or
perplexity but a small, stratified rubric scored by the family itself.
We built a trilingual KO + RU + EN co-learning system on Gemma 4 E2B
running entirely on-device under Apache 2.0, augmented by a 76M MTP-
drafter accelerated 26B premium tier with a SoulX-FlashHead L1-aware
avatar. We expanded a 247-pair direct KO-RU resource into 12,408
trilingual triples via English-pivot, distilled 1,500 trilingual object
cards and 1,000 family scenarios from Gemma 4 E4B, and trained a 32-rank
LoRA in two hours on a single A100 80GB.

We then ran a 30-probe Family-as-Evaluator audit with one household
(KO L1 + RU L1 + EN bridge + 21-month-old) and found, against our own
expectation, that the LoRA *regressed* on transliteration script
correctness (100% → 25%) while improving on family-context realism, L1-
aware refusals, and empty-response rate. The regression was invisible
to BLEU and JSON-parse metrics. We diagnosed it as policy-frequency
overfitting (too few transliteration examples in v1), corrected it
with 300 explicit transliteration pairs (LoRA-v2), and committed to
scaling the family-evaluator panel to 20 multicultural households via
the Sejong Multicultural Family Center program in late 2026.

The methodological point — *observable benchmark success ≠ task-real
success; instrument the parity that matters* — is inherited from our
group's Paper 1 on AI-native DFT engines [bnml-paper1]. There, hidden
cancellations between separately-broken normalizations let an engine
appear to pass lattice-constant benchmarks while its wavefunctions
silently disagreed with QE. Here, hidden translate-instead-of-
transliterate behavior let a LoRA pass schema parsers and BLEU while
silently betraying the tutoring task. The cross-domain pattern is the
same; the fix is the same; and, we believe, the protocol of demanding
*parity-with-the-task-as-actually-used* before declaring progress is
the same.

The system, dataset, LoRA adapter, evaluation probes, and reproducibility
artifacts are released under Apache 2.0 + CC-BY at [repo]. The hackathon
demonstration video accompanies the submission [demo-video]. We hope
that other multicultural families, particularly those at the
intersection of low-resource language pairs and pre-literate child
users, find this useful as a starting point — and we explicitly invite
them to break it, document the failure modes their household surfaces,
and contribute back to the protocol.

> 이 작업은 우리 가족의 일상에서 시작되었습니다.
> *— Это работа началась с нашей семьи.*
> *— This work began with our family.*
