# Section 5.3 fill — 4-arm bridge-pivot ablation

| Arm | Empty | JSON parse | Translit script | tok/s |
|---|---|---|---|---|
| **stock** | 0/30 | 10/14 (71%) | 4/4 (100%) | 16.56 |
| **L_direct** | 0/30 | 9/14 (64%) | 4/4 (100%) | 11.47 |
| **L_pivot_only** | 0/30 | 9/14 (64%) | 4/4 (100%) | 11.34 |
| **L_pivot_filtered** | 0/30 | 9/14 (64%) | 4/4 (100%) | 11.57 |
| **lora_v2** | 0/30 | 7/14 (50%) | 4/4 (100%) | 11.04 |
| **L_multilingual** | 0/30 | 8/14 (57%) | 4/4 (100%) | 11.52 |

# Section 5.4 fill — policy-frequency curve
(translit_share_actual_pct from ablation builder)
| Variant | Translit share % | Translit script-correct | JSON parse |
|---|---|---|---|
| **stock** | nan | 4/4 (100%) | 10/14 |
| **L_policy_00** | 0.0 | 4/4 (100%) | 10/14 |
| **lora_v2** | 1.46 | 4/4 (100%) | 7/14 |
