# Section 5.3 — 4-arm bridge-pivot ablation

| Arm | Base | Empty | JSON parse | Translit script | tok/s |
|---|---|---|---|---|---|
| **stock** | E2B | 0/30 | 10/14 | 4/4 | 16.56 |
| **L_direct** | E2B | 0/30 | 9/14 | 4/4 | 11.47 |
| **L_pivot_only** | E2B | 0/30 | 9/14 | 4/4 | 11.34 |
| **L_pivot_filtered** | E2B | 0/30 | 9/14 | 4/4 | 11.57 |
| **lora_v2** | E2B | 0/30 | 7/14 | 4/4 | 11.04 |
| **L_multilingual** | E2B | 0/30 | 8/14 | 4/4 | 11.52 |
| **E4B_L_direct** | E4B | 0/30 | 11/14 | 4/4 | 8.48 |
| **E4B_L_pivot_only** | E4B | 0/30 | 10/14 | 4/4 | 8.5 |
| **E4B_L_pivot_filtered** | E4B | 0/30 | 9/14 | 4/4 | 8.68 |
| **E4B_L_multilingual** | E4B | 0/30 | 10/14 | 4/4 | 9.01 |

# Section 5.4 — policy-frequency curve (E2B)

| Variant | translit% | translit/4 | json/14 |
|---|---|---|---|
| L_pf_00p0 | 0.0% (step 2500) | 4/4 | 10/14 |
| L_policy_00 | 0.0% (step 1500) | 4/4 | 10/14 |
| L_step_dense_p0 | 0.0% (step 5000) | 4/4 | 9/14 |
| L_step_dense_p0_step00250 | 0.0% (step 250) | 4/4 | 9/14 |
| L_step_dense_p0_step00500 | 0.0% (step 500) | 4/4 | 9/14 |
| L_step_dense_p0_step00750 | 0.0% (step 750) | 4/4 | 8/14 |
| L_step_dense_p0_step01000 | 0.0% (step 1000) | 3/4 | 9/14 |
| L_step_dense_p0_step01250 | 0.0% (step 1250) | 4/4 | 9/14 |
| L_step_dense_p0_step01500 | 0.0% (step 1500) | 4/4 | 9/14 |
| L_step_dense_p0_step01750 | 0.0% (step 1750) | 3/4 | 7/14 |
| L_step_dense_p0_step02000 | 0.0% (step 2000) | 3/4 | 11/14 |
| L_step_dense_p0_step02250 | 0.0% (step 2250) | 3/4 | 6/14 |
| L_step_dense_p0_step02500 | 0.0% (step 2500) | 3/4 | 5/14 |
| L_step_dense_p0_step02750 | 0.0% (step 2750) | 4/4 | 6/14 |
| L_step_dense_p0_step03000 | 0.0% (step 3000) | 3/4 | 7/14 |
| L_step_dense_p0_step03250 | 0.0% (step 3250) | 4/4 | 8/14 |
| L_step_dense_p0_step03500 | 0.0% (step 3500) | 3/4 | 7/14 |
| L_step_dense_p0_step03750 | 0.0% (step 3750) | 3/4 | 6/14 |
| L_step_dense_p0_step04000 | 0.0% (step 4000) | 3/4 | 6/14 |
| L_step_dense_p0_step04250 | 0.0% (step 4250) | 4/4 | 9/14 |
| L_step_dense_p0_step04500 | 0.0% (step 4500) | 4/4 | 9/14 |
| L_step_dense_p0_step04750 | 0.0% (step 4750) | 4/4 | 9/14 |
| L_step_dense_p0_step05000 | 0.0% (step 5000) | 4/4 | 9/14 |
| lora_v1 | 0.0% (step 4512) | 1/4 | 7/14 |
| lora_v1_step4000 | 0.0% (step 4000) | 1/4 | 8/14 |
| L_pf_00p5 | 0.5% (step 2500) | 4/4 | 9/14 |
| L_policy_01 | 0.95% (step 1500) | 4/4 | 9/14 |
| L_pf_01p0 | 1.0% (step 2500) | 4/4 | 9/14 |
| L_multilingual | 1.4% (step 1500) | 4/4 | 8/14 |
| lora_v2 | 1.46% (step 5130) | 4/4 | 7/14 |
| lora_v2_step4500 | 1.46% (step 4500) | 4/4 | 7/14 |
| lora_v2_step5000 | 1.46% (step 5000) | 4/4 | 8/14 |
| L_direct | 1.5% (step 1500) | 4/4 | 9/14 |
| L_pivot_filtered | 1.5% (step 1500) | 4/4 | 9/14 |
| L_pivot_only | 1.5% (step 1500) | 4/4 | 9/14 |
| L_step_dense_p1_5 | 1.5% (step 5000) | 3/4 | 7/14 |
| L_step_dense_p1_5_step00250 | 1.5% (step 250) | 4/4 | 10/14 |
| L_step_dense_p1_5_step00500 | 1.5% (step 500) | 3/4 | 9/14 |
| L_step_dense_p1_5_step00750 | 1.5% (step 750) | 4/4 | 9/14 |
| L_step_dense_p1_5_step01000 | 1.5% (step 1000) | 3/4 | 10/14 |
| L_step_dense_p1_5_step01250 | 1.5% (step 1250) | 2/4 | 6/14 |
| L_step_dense_p1_5_step01500 | 1.5% (step 1500) | 2/4 | 8/14 |
| L_step_dense_p1_5_step01750 | 1.5% (step 1750) | 2/4 | 9/14 |
| L_step_dense_p1_5_step02000 | 1.5% (step 2000) | 2/4 | 9/14 |
| L_step_dense_p1_5_step02250 | 1.5% (step 2250) | 2/4 | 8/14 |
| L_step_dense_p1_5_step02500 | 1.5% (step 2500) | 3/4 | 7/14 |
| L_step_dense_p1_5_step02750 | 1.5% (step 2750) | 2/4 | 7/14 |
| L_step_dense_p1_5_step03000 | 1.5% (step 3000) | 4/4 | 7/14 |
| L_step_dense_p1_5_step03250 | 1.5% (step 3250) | 2/4 | 6/14 |
| L_step_dense_p1_5_step03500 | 1.5% (step 3500) | 2/4 | 7/14 |
| L_step_dense_p1_5_step03750 | 1.5% (step 3750) | 2/4 | 6/14 |
| L_step_dense_p1_5_step04000 | 1.5% (step 4000) | 3/4 | 7/14 |
| L_step_dense_p1_5_step04250 | 1.5% (step 4250) | 3/4 | 8/14 |
| L_step_dense_p1_5_step04500 | 1.5% (step 4500) | 3/4 | 7/14 |
| L_step_dense_p1_5_step04750 | 1.5% (step 4750) | 3/4 | 8/14 |
| L_step_dense_p1_5_step05000 | 1.5% (step 5000) | 3/4 | 7/14 |
| L_policy_03 | 1.84% (step 600) | 4/4 | 10/14 |
| L_policy_05 | 1.84% (step 600) | 4/4 | 10/14 |
| L_policy_10 | 1.84% (step 600) | 4/4 | 10/14 |
| L_pf_02p0 | 2.0% (step 2500) | 4/4 | 8/14 |
| L_pf_03p0 | 3.0% (step 2500) | 4/4 | 9/14 |
| L_pf_05p0 | 5.0% (step 2500) | 4/4 | 9/14 |
| L_pf_08p0 | 8.0% (step 2500) | 4/4 | 7/14 |
| L_pf_10p0 | 10.0% (step 2500) | 4/4 | 9/14 |

# Step-axis cliff (0% policy data)

| variant | step | translit/4 |
|---|---|---|
| L_step_dense_p0_step00250 | 250 | 4/4 |
| L_step_dense_p0_step00500 | 500 | 4/4 |
| L_step_dense_p0_step00750 | 750 | 4/4 |
| L_step_dense_p0_step01000 | 1000 | 3/4 |
| L_step_dense_p0_step01250 | 1250 | 4/4 |
| E4B_L_policy_00 | 1500 | 4/4 |
| L_policy_00 | 1500 | 4/4 |
| L_step_dense_p0_step01500 | 1500 | 4/4 |
| L_step_dense_p0_step01750 | 1750 | 3/4 |
| L_step_dense_p0_step02000 | 2000 | 3/4 |
| L_step_dense_p0_step02250 | 2250 | 3/4 |
| L_pf_00p0 | 2500 | 4/4 |
| L_step_dense_p0_step02500 | 2500 | 3/4 |
| L_step_dense_p0_step02750 | 2750 | 4/4 |
| L_step_dense_p0_step03000 | 3000 | 3/4 |
| L_step_dense_p0_step03250 | 3250 | 4/4 |
| L_step_dense_p0_step03500 | 3500 | 3/4 |
| L_step_dense_p0_step03750 | 3750 | 3/4 |
| L_step_dense_p0_step04000 | 4000 | 3/4 |
| lora_v1_step4000 | 4000 | 1/4 |
| L_step_dense_p0_step04250 | 4250 | 4/4 |
| L_step_dense_p0_step04500 | 4500 | 4/4 |
| lora_v1 | 4512 | 1/4 |
| L_step_dense_p0_step04750 | 4750 | 4/4 |
| L_step_dense_p0 | 5000 | 4/4 |
| L_step_dense_p0_step05000 | 5000 | 4/4 |