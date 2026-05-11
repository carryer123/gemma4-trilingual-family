| Adapter | Scalar selector status | G2-52 | G2 state | G3 source | G3 state | Pipeline action |
|---|---|---:|---:|---:|---:|---|
| `stock` | baseline | 51/52 | **GREEN** | 78/80 | **GREEN** | GREEN: eligible, log audit artifacts |
| `lora_v1` | loss/BLEU-attractive historical candidate | 36/52 | **RED** | 52/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `lora_v2` | controlled comparison candidate | 52/52 | **GREEN** | 73/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |
| `L_v1_recreate` | controlled comparison candidate | 49/52 | **AMBER** | 72/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |
| `v1ra_r64_a128` | controlled comparison candidate | 44/52 | **RED** | 63/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `v1ra_r08_a16` | controlled comparison candidate | 52/52 | **GREEN** | 66/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `v1ra_r08_a64` | controlled comparison candidate | 48/52 | **AMBER** | 73/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |
| `v1ra_r16_a32` | controlled comparison candidate | 51/52 | **GREEN** | 76/80 | **GREEN** | GREEN: eligible, log audit artifacts |
| `v1ra_r16_a64` | controlled comparison candidate | 49/52 | **AMBER** | 75/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |
| `v1ra_r64_a16` | controlled comparison candidate | 52/52 | **GREEN** | 68/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `v1ra_r64_a64` | controlled comparison candidate | 51/52 | **GREEN** | 72/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `v1seed_1234` | controlled comparison candidate | 52/52 | **GREEN** | 79/80 | **GREEN** | GREEN: eligible, log audit artifacts |
| `v1seed_2026` | controlled comparison candidate | 52/52 | **GREEN** | 71/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |
| `v1seed_42` | controlled comparison candidate | 51/52 | **GREEN** | 77/80 | **GREEN** | GREEN: eligible, log audit artifacts |
| `v1seed_7777` | controlled comparison candidate | 51/52 | **GREEN** | 45/80 | **RED** | RED: block promotion; retrain/repair then rerun full failed gate |
| `v1seed_99999` | controlled comparison candidate | 51/52 | **GREEN** | 73/80 | **AMBER** | AMBER: inspect raw outputs; targeted repair or scoped waiver; rerun failed gate |

This is a promotion-decision audit trace, not a selector benchmark: it does not estimate false-positive or false-negative rates.
