# Reference Audit Notes

Date: 2026-05-09

Checked and normalized high-risk references:

| Key | Status | Evidence |
|---|---|---|
| `gemma1` | verified | arXiv 2403.08295, "Gemma: Open Models Based on Gemini Research and Technology" |
| `gemma3` | verified | arXiv 2503.19786, "Gemma 3 Technical Report" |
| `gemma4` | verified | official Google DeepMind Gemma 4 model page |
| `labse` | verified | ACL Anthology 2022.acl-long.62 |
| `kalajdzievski-scaling-law` | verified | arXiv 2401.05605 |
| `biderman-lora-forgets` | verified | TMLR 2024 / arXiv 2405.09673 |
| `gaussian-splatting` | verified | ACM TOG 2023, DOI 10.1145/3592433 |

Cleaned or isolated risky references:

* Removed active citations to placeholder/local references such as
  `bridge-corpus`, `coco-learning-2023`, `soulx-fh`, `gaussian-avatars`,
  `bnml-paper1`, and `statedgs` from the EMNLP-facing body.
* The bibliography may still contain unused planning references for the
  arXiv/hackathon build; the anonymized build script strips identifying
  names and region-specific strings from `paper_anon/references.bib`.
* Remaining cited references should still be checked once against the final
  ACL/ARR bibliography style before submission.
