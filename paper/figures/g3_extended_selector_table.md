| Variant | G3-80 | Worst group | G3 band | Main failure reason |
|---|---:|---:|---:|---|
| `L_v1_recreate` | 72/80 | 16/20 `router` | **AMBER** | schema_violation |
| `lora_v1` | 52/80 | 3/20 `tool_call` | **RED** | schema_violation |
| `lora_v2` | 73/80 | 16/20 `router` | **AMBER** | schema_violation |
| `stock` | 78/80 | 18/20 `router` | **GREEN** | schema_violation |
| `v1ra_r08_a16` | 66/80 | 13/20 `tool_call` | **RED** | schema_violation |
| `v1ra_r08_a64` | 73/80 | 15/20 `age_register` | **AMBER** | schema_violation |
| `v1ra_r16_a32` | 76/80 | 18/20 `router` | **GREEN** | schema_violation |
| `v1ra_r16_a64` | 75/80 | 16/20 `tool_call` | **AMBER** | json_parse_error:JSONDecodeError |
| `v1ra_r64_a128` | 63/80 | 12/20 `tool_call` | **RED** | schema_violation |
| `v1ra_r64_a16` | 68/80 | 10/20 `age_register` | **RED** | schema_violation |
| `v1ra_r64_a64` | 72/80 | 14/20 `tool_call` | **RED** | schema_violation |
| `v1seed_1234` | 79/80 | 19/20 `router` | **GREEN** | schema_violation |
| `v1seed_2026` | 71/80 | 15/20 `age_register` | **AMBER** | schema_violation |
| `v1seed_42` | 77/80 | 18/20 `router` | **GREEN** | schema_violation |
| `v1seed_7777` | 45/80 | 2/20 `router` | **RED** | json_parse_error:JSONDecodeError |
| `v1seed_99999` | 73/80 | 16/20 `tool_call` | **AMBER** | schema_violation |

G3-80 bands are triage heuristics: GREEN means >=72/80 and every 20-probe group >=18/20; AMBER means >=64/80 and every group >=15/20; RED is below that floor. These thresholds are not calibrated precision/recall estimates.
