| Rule | G2 criterion | G2-pass variants | G2+G3 strict-pass variants | Always-rejected examples |
|---|---|---:|---:|---|
| Relaxed G2 | total ≥48/52 and every direction ≥10/13 | 14/16 | 6/16 | `lora_v1`, `v1ra_r64_a128` |
| Current green G2 | total ≥50/52 and every direction ≥12/13 | 11/16 | 5/16 | `L_v1_recreate`, `lora_v1`, `v1ra_r64_a128` |
| Perfect G2 | total ≥52/52 and every direction ≥13/13 | 5/16 | 2/16 | `L_v1_recreate`, `lora_v1`, `v1ra_r64_a128` |

| Variant | 48/52 + dir≥10 | 50/52 + dir≥12 | 52/52 + dir=13 | G3 | Interpretation |
|---|---:|---:|---:|---:|---|
| `stock` | PASS | PASS | FAIL | 10/14 | stable positive control |
| `lora_v1` | FAIL | FAIL | FAIL | 7/14 | rejected under every G2 cutoff |
| `lora_v2` | PASS | PASS | PASS | 7/14 | G2-clean but blocked by G3 |
| `L_v1_recreate` | PASS | FAIL | FAIL | 7/14 | threshold-sensitive G2 boundary case |
| `v1ra_r64_a128` | FAIL | FAIL | FAIL | 6/14 | rejected under every G2 cutoff |
| `v1ra_r16_a64` | PASS | FAIL | FAIL | 9/14 | relaxed-only G2 boundary case |
| `v1seed_42` | PASS | PASS | FAIL | 8/14 | passes current G2 and G3 |
| `v1seed_2026` | PASS | PASS | PASS | 10/14 | passes perfect G2 and G3 |

The sensitivity check supports two claims only: `lora_v1` is not an artifact of the current 50/52 cutoff, and several controls are threshold-sensitive or blocked by the independent G3 gate. It does not calibrate G2 precision/recall.
