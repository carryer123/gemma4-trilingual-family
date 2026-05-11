#!/usr/bin/env python3
"""Build the EMNLP submission PDFs from real LaTeX sources.

This is intentionally separate from the Markdown/ReportLab fallback builder.
It mirrors the Paper5 submission practice: source/*.tex + style files +
compiled PDFs + README with exact build commands.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path


PROJ = Path("/scratch/hpc198a01/젬마4해커톤")
OUT_ROOT = PROJ / "submissions"
PKG = OUT_ROOT / "EMNLP2026_StateGated_LoRA_submission"
SUBMIT = PKG / "emnlp_submission"
SOURCE = SUBMIT / "source"
ZIP_PATH = OUT_ROOT / "EMNLP2026_StateGated_LoRA_submission.zip"
ANON_PKG = OUT_ROOT / "EMNLP2026_StateGated_LoRA_review_anon"
ANON_ZIP_PATH = OUT_ROOT / "EMNLP2026_StateGated_LoRA_review_anon.zip"
TECTONIC = Path("/scratch/hpc198a01/.conda/envs/texbuild/bin/tectonic")
ACL_STYLE_SRC = Path("/scratch/hpc198a01/tmp/acl_style")


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


def g2_table_rows() -> str:
    data = json.loads((PROJ / "paper/figures/g2_extended_scores.json").read_text())
    names = ["stock", "lora_v1", "lora_v2", "L_v1_recreate", "v1ra_r64_a128"]
    rows = []
    for name in names:
        r = data["variants"][name]
        worst = min(d["correct"] for d in r["by_direction"].values())
        band = g2_band(r["g2_score"], worst)
        rows.append(
            f"\\texttt{{{tex_escape(name)}}} & {r['g2_score']}/52 & "
            f"{worst}/13 & {band} \\\\"
        )
    return "\n".join(rows)


def g3_table_rows() -> str:
    data = json.loads((PROJ / "paper/figures/g3_extended_scores.json").read_text())
    names = ["stock", "lora_v1", "lora_v2", "L_v1_recreate", "v1seed_7777", "v1ra_r64_a128"]
    rows = []
    for name in names:
        r = data["variants"][name]
        groups = r["by_group"]
        worst_name, worst_score = min(((k, v["correct"]) for k, v in groups.items()), key=lambda kv: kv[1])
        band = g3_band(r["g3_score"], worst_score)
        rows.append(
            f"\\texttt{{{tex_escape(name)}}} & {r['g3_score']}/80 & "
            f"{worst_score}/20 \\texttt{{{tex_escape(worst_name)}}} & "
            f"{band} \\\\"
        )
    return "\n".join(rows)


def g2_band(total: int, worst_direction: int) -> str:
    if total >= 50 and worst_direction >= 12:
        return "GREEN"
    if total >= 48 and worst_direction >= 10:
        return "AMBER"
    return "RED"


def g3_band(total: int, worst_group: int) -> str:
    if total >= 72 and worst_group >= 18:
        return "GREEN"
    if total >= 64 and worst_group >= 15:
        return "AMBER"
    return "RED"


def trace_rows() -> str:
    rows = []
    # Fixed order copied from the audited selector trace for stable paper layout.
    order = [
        ("stock", "baseline", "GREEN", "GREEN", "eligible; log audit artifacts"),
        ("lora_v1", "loss-attractive candidate", "RED", "RED", "block promotion; retrain/repair"),
        ("lora_v2", "comparison candidate", "GREEN", "AMBER", "repair/rerun G3"),
        ("L_v1_recreate", "same-config retrain", "AMBER", "AMBER", "inspect; repair or scoped waiver"),
        ("v1ra_r64_a128", "capacity arm", "RED", "RED", "block; not boundary waiver"),
        ("v1ra_r16_a32", "capacity arm", "GREEN", "GREEN", "eligible; log artifacts"),
        ("v1seed_1234", "seed arm", "GREEN", "GREEN", "eligible; log artifacts"),
        ("v1seed_7777", "seed arm", "GREEN", "RED", "block on schema debt"),
    ]
    for name, status, g2, g3, action in order:
        rows.append(
            f"\\texttt{{{tex_escape(name)}}} & {tex_escape(status)} & {g2} & {g3} & {tex_escape(action)} \\\\"
        )
    return "\n".join(rows)


def scalar_state_rows() -> str:
    return "\n".join(
        [
            "stock & -- & baseline & 51/52 & 78/80 & eligible baseline \\\\",
            "\\texttt{lora\\_v1} & 0.5316; BLEU 31.4 & scalar-eligible candidate & 36/52 & 52/80 & block \\\\",
            "\\texttt{lora\\_v2} & not used for scalar claim & comparison candidate & 52/52 & 73/80 & repair/rerun G3 \\\\",
            "\\texttt{L\\_v1\\_recreate} & same-config control & control & 49/52 & 72/80 & inspect/rerun \\\\",
        ]
    )


def main_tex() -> str:
    template = r"""
\documentclass[11pt]{{article}}
\usepackage{{acl}}
\usepackage{{times}}
\usepackage{{latexsym}}
\usepackage{{booktabs}}
\usepackage{{array}}
\usepackage{{multirow}}
\usepackage{{amsmath}}
\usepackage{{microtype}}
\usepackage{{graphicx}}
\usepackage{{url}}
\usepackage{{xcolor}}
\usepackage{{pifont}}
\usepackage{{xspace}}
\newcommand{{\green}}{{\textsc{{Green}}\xspace}}
\newcommand{{\amber}}{{\textsc{{Amber}}\xspace}}
\newcommand{{\red}}{{\textsc{{Red}}\xspace}}
\newcommand{{\cmark}}{{\ding{{51}}}}
\newcommand{{\xmark}}{{\ding{{55}}}}
\title{{State-Gated Audit for Niche-Population LoRA Fine-Tuning: A Trilingual Case Study}}
\author{{
Byoungsang Lee$^{{1,2}}$ \quad
Yunchul Kim$^{{1}}$ \quad
Youmin Shim$^{{1}}$ \quad
Chaewon Kwak$^{{1}}$ \quad
Jung Heon Lee$^{{1,3}}$\\
$^{{1}}$School of Advanced Materials Science and Engineering, Sungkyunkwan University (SKKU), Suwon 16419, Korea\\
$^{{2}}$MoonTechnology, 3F, 29-5, World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea\\
$^{{3}}$Department of MetaBioHealth, Sungkyunkwan University (SKKU), Suwon 16419, Korea\\
\texttt{{jhlee7@skku.edu}}
}}
\begin{{document}}
\maketitle
\begin{{abstract}}
Adapter selection is often driven by held-out loss or aggregate task metrics, but small deployments may depend on behavioral states that those metrics do not name.
We study this mismatch in a trilingual KO/RU/EN LoRA audit and propose a state-gated promotion workflow: deployment states are specified before promotion, probes and scorers are versioned, raw generations are retained, and each gate maps to a \green/\amber/\red pipeline action.
The empirical case is deliberately bounded.
One loss-attractive Gemma 4 E2B adapter, \texttt{lora\_v1}, would remain a candidate under scalar screening but fails a deployment-critical script-state gate and a structured-output gate.
In an expanded rerun, it scores 36/52 on G2 script-state compliance, with the worst direction at 6/13, and 52/80 on G3 schema compliance, with tool-call JSON at 3/20.
A same-configuration retrain, five seed retrainings, and seven capacity arms do not reproduce the original 1/4 discovery failure, so we do not claim a deterministic cliff, calibrated detector, or population failure rate.
The contribution is therefore not a new training method or benchmark, but an auditable promotion trace for niche-population adapters.
The case shows why scalar screening should be paired with explicit state gates, and why non-reproduction should narrow mechanism claims rather than erase the deployment decision.
\end{{abstract}}

\section{{Introduction}}
LoRA fine-tuning pipelines commonly promote adapters by validation loss, BLEU, chrF, or a small task-specific metric set.
Those signals are necessary but incomplete when deployment depends on narrow behavioral requirements: script direction, schema validity, tool-call arguments, refusal language, or age/register constraints.
A scalar metric can look acceptable while a named deployment state regresses.
This paper studies that risk in one trilingual KO/RU/EN adapter audit.
The scope is intentionally small.
We do not introduce a new model architecture, a general multilingual benchmark, or a universal detector.
We ask a narrower engineering question: when a niche deployment has non-negotiable behavioral states, what should the adapter promotion pipeline record and do before deployment?

We propose \emph{state-gated audit}.
Candidate adapters are still trained and screened with ordinary scalar metrics, but promotion additionally requires a versioned gate suite:
\[
\operatorname{{audit}}(a)=\{{L(a),Q(a),G_1(a),\ldots,G_8(a),R(a),A(a)\}},
\]
where $L$ is loss, $Q$ is an optional task metric, $G_i$ are deployment gates, $R$ stores raw generations and scorer versions, and $A$ is the resulting pipeline action.
The important design choice is that gates are not collapsed into a single leaderboard score.
They route artifacts into \green, \amber, or \red states.
\green admits with logging, \amber blocks automatic deployment and triggers review or repair, and \red blocks promotion unless the deployment specification itself changes and the audit is rerun.

The empirical case motivating the protocol is a single historical adapter, \texttt{{lora\_v1}}.
It remains attractive under held-out loss (\texttt{{eval\_loss=0.531}}) and task metrics, but its discovery G2 script-state smoke test falls to 1/4.
This is not a reproducible law.
A same-mix same-hyperparameter retrain, five seed retrainings, and seven capacity arms all fail to reproduce the 1/4 outcome.
The honest conclusion is therefore selector disagreement plus negative mechanism evidence.
The contribution is not ``we discovered a cliff law''; it is that explicit deployment gates made a false-green candidate visible before promotion.

The practical question is not whether the failed trajectory is common.
It is whether a promotion pipeline can detect and act on such a trajectory before release.
We therefore treat the adapter as an audit object rather than as a sample from a population of failures.
This paper contributes: (i) a state-gated promotion contract that maps named deployment gates to \green/\amber/\red actions; (ii) a reproducible audit capsule with frozen G2/G3 probes, scorers, raw generations, and artifact-level decision traces; and (iii) a bounded case study showing scalar-state disagreement, independent G2/G3 debt, and negative controlled reproduction evidence.
The expanded reruns show that \texttt{{lora\_v1}} is not merely a four-prompt artifact, while also showing that other adapters carry boundary or independent debt.

\section{{Positioning}}
This work sits closest to adapter selection, behavioral evaluation, and structured-output reliability.
LoRA and other PEFT methods make it cheap to train many candidate adapters \citep{{hu2022lora,houlsby2019adapter,liu2022ia3,dettmers2023qlora}}, but that convenience shifts the deployment problem from ``can we fine-tune?'' to ``which fine-tuned artifact is eligible to promote?''
Standard selection signals such as held-out cross-entropy, BLEU \citep{{papineni2002bleu}}, chrF \citep{{popovic2015chrf}}, and sacreBLEU-style reproducible metric wrappers \citep{{post2018sacrebleu}} summarize broad task behavior.
They do not name deployment states such as script discipline, exact JSON structure, tool-call validity, refusal language, or age/register constraints.
This paper therefore treats scalar metrics as useful first-stage filters, not as deployment certificates.

Behavioral evaluation work has long argued that aggregate scores can hide subgroup or task-state failures \citep{{ribeiro2020checklist,gebru2021datasheets,bender2018datastatements}}.
Our case study is narrower: it does not build a general multilingual benchmark.
Instead, it asks how a small team should document promotion decisions when a deployment has explicit non-negotiable states.
The audit is operational.
It records raw generations, scorer versions, gate states, and the action triggered by each state.
This differs from leaderboard-style evaluation because the primary output is not a rank; it is a pipeline decision: eligible, inspect/repair, or block.

The structured-output side connects to JSON validity, function calling, and constrained decoding \citep{{bray2017json,scholak2021picard}}.
Here G3 is not a semantic task score.
It is an interface-discipline gate: the model must emit parseable JSON with required keys, correct types, allowed enum values, and no forbidden extra keys.
A model can be semantically helpful yet fail G3 if a downstream parser cannot consume the output.
Conversely, passing G3 does not certify semantic correctness.
This claim boundary is central to the paper's framing.

\section{{State-Gated Audit Protocol}}
The audit uses eight deployment gates.
The 30-probe discovery set maps to seven released categories: translation (6), grammar (4), phonetic/script transfer (4), family scenario (4), function call (4), age band (4), and safety (4).
The paper groups these categories into eight deployment states because persona-bridge and L1-aware grammar are separate rubric dimensions inside the human-rated portion.
We report this mapping explicitly to avoid treating the 30 probes as independent iid samples.

\begin{{table*}}[t]
\centering
\small
\begin{{tabular}}{{p{{0.08\linewidth}}p{{0.36\linewidth}}p{{0.48\linewidth}}}}
\toprule
Gate & Deployment state & Evidence in this paper \\
\midrule
G1 & Translation/task behavior & 6 discovery probes plus held-out task metrics. \\
G2 & Cross-script state discipline & 4 discovery probes; 52-probe automatic rerun for 16 key adapters. \\
G3 & JSON/schema validity & 14 discovery checks; 80-probe automatic schema rerun for 16 key adapters. \\
G4 & Function-call validity & 4 discovery prompts; reported as diagnostic. \\
G5 & L1-aware grammar explanation & Human-rated rubric dimension; not used for population claims. \\
G6 & Age-banded vocabulary/register & Human-rated rubric dimension; not used for population claims. \\
G7 & Persona-bridge consistency & Human-rated rubric dimension; not used for population claims. \\
G8 & Safety/refusal behavior & 4 discovery prompts plus rubric notes. \\
\bottomrule
\end{{tabular}}
\caption{{Gate mapping and claim boundary. G2 and G3 carry the main empirical load; human-tier gates motivate the deployment state vector but do not support prevalence claims.}}
\label{{tab:gates}}
\end{{table*}}

Only G2 and G3 carry the main empirical load.
G2 is a Unicode-block script-state check, not a phonetic transliteration-quality metric.
The expanded G2 audit uses 52 prompts: four directions (KO$\rightarrow$Cyrillic, RU$\rightarrow$Hangul, KO$\rightarrow$Latin, RU$\rightarrow$Latin), 13 lexical surfaces each.
A response passes a prompt when the target script ratio is at least 85\% and no other tracked script exceeds 10\%.
This check intentionally asks a shallow but deployment-critical question: is the adapter in the requested script state at all?

The expanded G3 audit uses 80 automatic schema prompts across four groups: object cards, intent routing, age/register rewrites, and tool-call JSON.
A response must parse as JSON and satisfy required-key, type, enum, and no-extra-key constraints where declared.
G3 checks schema discipline, not semantic correctness.

\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lp{{0.60\linewidth}}}}
\toprule
State & Pipeline action \\
\midrule
\green & Eligible for deployment candidate status; log raw outputs, scorer version, gate version, and selected artifact hash. \\
\amber & Automatic deployment is blocked; inspect raw outputs, label errors, add a minimal targeted repair slice or document a scoped waiver, then rerun failed gates. \\
\red & Promotion is blocked; rollback, retrain, or change deployment specification. A \red state cannot be silently waived. \\
\bottomrule
\end{{tabular}}
\caption{{Audit states are actions, not just labels. AMBER and RED are not overrides: AMBER permits documented repair or scoped waiver plus failed-gate rerun; RED requires rollback or retraining unless the deployment specification itself changes and the full audit is rerun.}}
\label{{tab:actions}}
\end{{table}}

For G2-52 we report threshold sensitivity rather than a single calibrated cutoff.
\green requires total $\geq$50/52 and every direction $\geq$12/13.
\amber requires total $\geq$48/52 and every direction $\geq$10/13.
\red is below the \amber floor.
For G3-80, \green requires total $\geq$72/80 and every 20-probe group $\geq$18/20; \amber requires total $\geq$64/80 and every group $\geq$15/20; \red is below that floor.
These thresholds are engineering triage rules.
They are deliberately reported with sensitivity and caveats rather than as calibrated precision/recall cutoffs.
The deployment owner may choose stricter or looser thresholds, but the paper requires that the threshold version, raw outputs, and resulting action state be logged.

\section{{Experimental Setup}}
We audit Gemma 4 E2B/E4B LoRA adapters trained on KO/RU/EN mixtures built from direct translation data, English-pivot triples, synthetic object cards, family-scenario dialogs, function-call examples, and targeted script-transfer pairs.
The audit atlas contains 176 evaluated artifacts: one stock baseline, final adapters, and intermediate checkpoints.
These artifacts are dependent; many are checkpoints from the same run.
We use the atlas to document what happened, not to estimate prevalence.

The key trajectory is \texttt{{lora\_v1}}: Gemma 4 E2B, LoRA $r=32$, $\alpha=64$, bf16, AdamW-8bit, cosine learning rate $2\cdot10^{-4}$, no explicit script-transfer injection.
Controlled retrainings include a same-mix same-hyperparameter dense retrain, five seed resamples, and seven LoRA capacity arms.
The later \texttt{{lora\_v2}} run adds targeted script-transfer data; it is a comparison candidate, not a controlled causal intervention, because the run differs in more than one way.

\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lrr}}
\toprule
Audit set & Size & Purpose \\
\midrule
Discovery atlas & 176 & Historical gate outcomes and retraining trace \\
G2-52 rerun & 16 & Larger cross-script state audit \\
G3-80 rerun & 16 & Larger structured-output audit \\
\bottomrule
\end{{tabular}}
\caption{{Nested artifact sets. The 176 artifacts are an audit atlas, not iid samples.}}
\label{{tab:sets}}
\end{{table}}

\section{{Case Observation: G2 and G3 Debt}}
The stock E2B baseline passes the discovery G2 smoke set at 4/4 and G3 at 10/14.
The historical \texttt{{lora\_v1}} final adapter remains loss-attractive (\texttt{{eval\_loss=0.531}}) but falls to G2=1/4 and G3=7/14.
Its step-4000 checkpoint shows the same G2=1/4 outcome.
These two artifacts are adjacent checkpoints of one training trajectory, so the independent-run count is one.

Adding 300 script-transfer examples in a later run (\texttt{{lora\_v2}}) repairs G2 on the discovery probes (4/4) and reaches 52/52 on G2-52, but it remains \amber on G3-80 (73/80; worst group 16/20).
We therefore do not claim that data injection solves the adapter.
It repairs one audit state while leaving independent schema debt.

\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lrrl}}
\toprule
Adapter & G2-52 & Worst dir. & Band \\
\midrule
{g2_table_rows()}
\bottomrule
\end{{tabular}}
\caption{{Expanded G2 script-state audit. \texttt{{lora\_v1}} remains RED at 36/52 and worst direction 6/13, so the original finding is not merely a four-prompt artifact.}}
\label{{tab:g2}}
\end{{table}}

\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lrrl}}
\toprule
Adapter & G3-80 & Worst group & Band \\
\midrule
{g3_table_rows()}
\bottomrule
\end{{tabular}}
\caption{{Expanded G3 schema audit. G3 is independent debt: \texttt{{lora\_v2}} is G2-clean but still AMBER on schema discipline.}}
\label{{tab:g3}}
\end{{table}}

The raw G2 examples show why this matters.
For KO to Cyrillic prompts, \texttt{{lora\_v1}} often echoes Hangul instead of emitting Cyrillic.
For RU to Hangul, it sometimes translates rather than transliterates.
These outputs are fluent and can look superficially useful, which is why scalar task metrics do not capture the deployment violation.
The expanded G2-52 rerun confirms that the observation is not a four-prompt artifact.

G3-80 adds a second independent debt signal.
\texttt{{lora\_v1}} scores 52/80, with its tool-call group falling to 3/20.
\texttt{{lora\_v2}} repairs G2 but remains \amber on G3-80.
This prevents the paper from telling an overly simple repair story.
The targeted script-transfer injection fixes the script-state gate in one run; it does not make the adapter generally deployment-ready.

\section{{Controlled Non-Reproduction}}
We tested whether the G2=1/4 outcome follows from training duration, data mix, seed, or LoRA capacity.
It does not reproduce in the controlled set.

\begin{{table}}[t]
\centering
\small
\begin{{tabular}}{{lrr}}
\toprule
Controlled retraining & $n$ & G2=1/4 outcomes \\
\midrule
Same-mix same-hp dense retrain & 1 & 0 \\
Seed sweep & 5 & 0 \\
$r/\alpha$ capacity sweep & 7 & 0 \\
\midrule
Total & 13 & 0 \\
\bottomrule
\end{{tabular}}
\caption{{Controlled retrainings fail to reproduce the discovery G2=1/4 outcome. This is negative mechanism evidence, not evidence that the event is impossible.}}
\label{{tab:retrain}}
\end{{table}}

For 0/13, the one-sided 95\% Clopper--Pearson upper bound is $1-0.05^{{1/13}}\approx0.21$.
The point estimate is zero, but the interval admits a moderate seed-stochastic phenomenon.
We therefore do not claim the failure is rare.
We claim only that the deterministic mechanisms we tested are not supported by the controlled retrainings.

The same-mix retrain also lands far from the original adapter in LoRA-weight space: across 353 matched modules, the median relative Frobenius distance is 1.29.
This is a diagnostic consistent with different stochastic endpoints, not causal proof.
The negative result is not a footnote; it is part of the claim.
If the original trajectory cannot be reproduced as a deterministic law, the paper should not claim a deterministic law.
The remaining contribution is still useful but more modest: scalar metrics did not certify the deployment state of a candidate adapter, and an explicit gate suite produced an actionable audit state before promotion.

\section{{Promotion-Decision Audit Trace}}
We evaluate scalar screening and state-gated screening as different decision rules, not as competing estimators of a hidden ground truth.
A scalar selector keeps an adapter eligible when its held-out loss and task metrics are within the candidate band used by the deployment team.
A state-gated selector additionally requires every deployment-critical gate to be \green under the current gate version.
The claim is therefore procedural: if an adapter is scalar-eligible but gate-\red, automatic promotion is unjustified until the failed gate is repaired, explicitly scoped out of the deployment specification, and rerun.

\begin{{table*}}[t]
\centering
\small
\begin{{tabular}}{{p{{0.18\linewidth}}p{{0.21\linewidth}}p{{0.20\linewidth}}p{{0.08\linewidth}}p{{0.08\linewidth}}p{{0.18\linewidth}}}}
\toprule
Adapter & Scalar evidence & Scalar status & G2-52 & G3-80 & State-gated action \\
\midrule
{scalar_state_rows()}
\bottomrule
\end{{tabular}}
\caption{{Scalar-state decision table. The scalar claim is intentionally limited: \texttt{{lora\_v1}} was eligible under the pre-gate scalar screening rule (eval loss 0.5316; BLEU 31.4, within 0.6 of the best held-out BLEU reported in the audit), but state-gated promotion blocks it. Missing scalar rows are not used to claim scalar superiority.}}
\label{{tab:scalar-state}}
\end{{table*}}

We also trace four promotion rules: loss-only, task-metric, random final checkpoint, and state-gated audit.
This is a decision trace, not a selector benchmark.
On \texttt{{lora\_v1}}, scalar rules would keep the adapter under consideration: held-out loss is acceptable, task metrics remain competitive, and the final checkpoint exists.
State-gated audit blocks it because G2 is \red and G3 is \red.

\begin{{table*}}[t]
\centering
\small
\begin{{tabular}}{{p{{0.18\linewidth}}p{{0.22\linewidth}}p{{0.09\linewidth}}p{{0.09\linewidth}}p{{0.31\linewidth}}}}
\toprule
Adapter & Scalar selector status & G2 & G3 & Pipeline action \\
\midrule
{trace_rows()}
\bottomrule
\end{{tabular}}
\caption{{Promotion-decision audit trace for representative adapters. The trace does not estimate selector precision or recall. It shows what the pipeline would do once explicit deployment gates are attached to ordinary scalar screening.}}
\label{{tab:trace}}
\end{{table*}}

Threshold sensitivity confirms the narrow claim.
Under the relaxed G2 rule (total $\geq$48/52 and each direction $\geq$10/13), 14/16 adapters pass G2, but \texttt{{lora\_v1}} and \texttt{{v1ra\_r64\_a128}} remain stable failures.
Under the default rule (total $\geq$50/52 and each direction $\geq$12/13), 11/16 pass G2.
Under a perfect 52/52 rule, 5/16 pass G2.
Only 4/16 are \green on both default G2 and G3-80.
Thus \texttt{{lora\_v1}} is not an artifact of the current 50/52 cutoff; the threshold mainly changes how boundary controls are routed to review.

The combined audit trace is more informative than any single gate.
Some adapters are G2-clean but blocked by G3.
Some are boundary cases on both gates.
A few pass both expanded automatic gates.
The protocol does not claim that all rejected adapters are unusable.
It claims that automatic promotion is not justified until the failed gate is repaired, waived by a changed deployment specification, and rerun.

\section{Raw-Output Audit Examples}
The audit stores raw generations because a scalar gate score alone is not enough for debugging.
For G2, the most useful diagnostic is often not the total score but the exact failure surface: wrong script, mixed script, or translation instead of transliteration.
For G3, the raw output distinguishes parser failure from a schema-level violation such as missing keys or forbidden extra keys.
Table~\ref{tab:raw} shows representative examples from the exported audit logs.
The examples are shortened for space, but the source package contains the full raw generations.

\begin{table*}[t]
\centering
\small
\begin{tabular}{p{0.13\linewidth}p{0.15\linewidth}p{0.27\linewidth}p{0.34\linewidth}}}
\toprule
Adapter & Gate & Requested state & Observed failure mode \\
\midrule
\texttt{lora\_v1} & G2 & KO phrase $\rightarrow$ Cyrillic script-state & Emits Hangul for prompts that require Cyrillic; the output may be fluent but violates the requested script state. \\
\texttt{lora\_v1} & G2 & RU phrase $\rightarrow$ Hangul script-state & Often produces Hangul, but several outputs are translations or mixed-script responses rather than script-state-preserving transliterations. \\
\texttt{lora\_v1} & G3 & Tool-call JSON & Tool-call group falls to 3/20; common failures include non-JSON prose, missing required keys, and wrong field types. \\
\texttt{lora\_v2} & G3 & Router or age/register JSON & G2 is clean, but G3 remains AMBER; failures are schema discipline errors rather than cross-script errors. \\
\bottomrule
\end{tabular}
\caption{Representative raw-output diagnostics. The paper does not ask the reader to trust only aggregate gate scores; it keeps raw generations as part of the audit trail.}
\label{tab:raw}
\end{table*}

These raw examples also explain why the paper avoids the term ``transliteration quality'' for G2.
The automatic scorer cannot decide whether a Cyrillic rendering is phonetically ideal.
It can decide whether the adapter obeyed the requested script state.
That weaker check is still deployment-relevant in the motivating setting because the user explicitly requests cross-script output.
The same distinction applies to G3: passing the schema gate does not prove that the answer is semantically correct, but failing it is enough to block automatic promotion when the downstream interface requires parseable JSON.

\section{Reproducibility Package}
The submission package is organized so that the paper's claims are traceable to released artifacts rather than to prose alone.
The review source folder includes the G2 and G3 probe files, scorer implementations, merged JSON result files, and table-generation scripts.
The main paper PDF is compiled from \texttt{source/lora\_state\_gated\_main.tex} with ACL review style.
The package also includes a README with exact build commands and a SHA-256 manifest for the files in the bundle.

The reproducibility design follows the claim boundary.
For Tier 1 existence claims, the relevant evidence is a named artifact, a prompt, a raw generation, a scorer version, and a gate result.
For negative retraining claims, the relevant evidence is the controlled-run list and the observed absence of G2=1/4 outcomes in the thirteen retrainings.
For threshold-sensitivity claims, the relevant evidence is the same merged G2-52 result table evaluated under relaxed, default, and strict cutoffs.
The package deliberately does not present the 176-artifact atlas as a prevalence dataset, so it does not include code that estimates population failure rates from that dependent collection.

This organization is useful for review because the strongest possible criticism of the paper is not that the case study is small; the paper already states that.
The stronger criticism would be that the small case is not auditable.
The package addresses that risk by tying each central number to a machine-readable artifact:
\begin{itemize}
\item G2-52: \texttt{g2\_extended\_scores.json} and raw generations for the rechecked key adapters.
\item G3-80: \texttt{g3\_extended\_scores.json} and the schema scorer.
\item Promotion trace: deterministic table generation from the merged G2/G3 JSON summaries.
\item Manuscript: ACL-style LaTeX source with the exact title, author block, bibliography, and style files.
\end{itemize}

The package is still not a full public benchmark.
It is a reproducible audit capsule for a case study.
That is the intended level of evidence.
Future work can turn the same state/action format into a broader benchmark by adding independent deployments, independent raters, and more language pairs.

\section{Practical Use Pattern}
The intended user of the protocol is not a leaderboard organizer.
It is a small deployment team that trains several adapters and must decide whether any candidate can be promoted.
In that setting the protocol is lightweight:
\begin{enumerate}
\item Write the deployment states before model selection.
\item Freeze the probe files and scorer versions.
\item Run scalar metrics to remove clearly bad adapters.
\item Run state gates on remaining candidates.
\item Promote only \green candidates; route \amber candidates to documented repair or scoped waiver; block \red candidates.
\end{enumerate}
This sequence matters because it prevents the gate suite from becoming a post-hoc explanation for a preferred adapter.
The gate files and thresholds should exist before the final promotion decision.
If the deployment owner later changes a threshold, the change is recorded as a new audit version and the affected adapters are rerun.

The protocol also clarifies what an \amber waiver means.
It is not permission to ignore a failure.
It is a documented statement that the failed gate is outside the current deployment scope.
For example, if an adapter is used only in a text-only tutoring path, a tool-call JSON gate might be waived for that deployment, but the waiver changes the deployment specification and must be attached to the release record.
If the tool-call path is later enabled, the waiver no longer applies and G3 must be rerun.
This is a more conservative workflow than simply choosing the lowest-loss checkpoint and writing a limitation paragraph after the fact.

\begin{table}[t]
\centering
\small
\begin{tabular}{p{0.22\linewidth}p{0.66\linewidth}}}
\toprule
Question & Audit answer \\
\midrule
Can we deploy? & Only if all deployment-critical gates are \green under the current specification. \\
Can we inspect? & Yes. \amber is designed for raw-output review, error labeling, repair, and rerun. \\
Can we waive? & Only by documenting that the failed gate is outside deployment scope; no silent override. \\
Can we rank? & Not directly. The protocol is a promotion trace, not a calibrated benchmark. \\
\bottomrule
\end{tabular}
\caption{Operational interpretation of audit states. This table is intentionally procedural because the paper's claim is a promotion workflow, not a new model score.}
\label{tab:workflow}
\end{table}

The case study shows why this procedural view is useful.
\texttt{lora\_v2} is not simply ``better'' or ``worse'' than \texttt{lora\_v1}.
It is G2-clean but G3-\amber.
That state suggests a specific next step: inspect schema failures, try constrained decoding or a small schema-repair slice, and rerun G3.
\texttt{lora\_v1}, by contrast, is G2-\red and G3-\red.
That state suggests rollback or retraining rather than boundary review.
The labels therefore reduce ambiguity in the deployment pipeline even when they do not produce a calibrated estimate of future user harm.

\section{Ethical and Deployment Scope}
The motivating deployment is family-centered, multilingual, and potentially child-facing.
That context is exactly why the paper takes a conservative promotion stance.
The study does not use child behavior to train a model, does not release private household conversations, and does not claim population-level conclusions from household observation.
The household setting is used to define a deployment specification: scripts must be obeyed, JSON must be parseable, register must be age-appropriate, and refusal language must remain safe.
The automatic results in this paper concern adapter artifacts and prompt outputs, not human-subject inference.

The protocol is also designed to reduce a common risk in small deployments: informal override.
In many prototype pipelines, a developer sees a low validation loss, tries a few prompts, and ships the checkpoint.
If later failures appear, they are explained as edge cases.
State-gated audit reverses that burden.
Before promotion, the deployment states are named, the probes are versioned, and the raw outputs are retained.
When a failure appears, the pipeline has to choose an explicit action.
This does not make the deployment safe by itself, but it makes the decision auditable.

There is a second ethical reason to keep the claim narrow.
A paper about a small family-centered deployment could easily overstate cultural or linguistic generality.
We avoid that.
KO/RU/EN is a concrete case, not a proxy for all multilingual families.
G2 script-state discipline is not transliteration quality.
G3 schema discipline is not semantic correctness.
Human-tier observations are not prevalence estimates.
These boundaries are not rhetorical hedges; they are part of the reproducibility contract.
The reader should be able to tell exactly which claims are supported by automatic probes, which claims are negative retraining results, and which claims remain future work.

For deployment, the practical implication is simple.
If an adapter fails a state that is critical to the current user path, the adapter is not automatically promoted.
If the state is not relevant to the current user path, the waiver must change the deployment specification and be logged.
This distinction matters most in niche deployments because the user group may be too small for broad aggregate metrics to reveal failures early.
The audit state is therefore a guardrail against silent assumptions, not a replacement for broader evaluation.

\section{{Discussion}}
Three claims survive the audit.
First, loss does not certify deployment state in this case study.
A loss-attractive adapter can fail an explicit gate.
Second, gates are non-redundant.
\texttt{{lora\_v2}} repairs G2 but remains \amber on G3-80; schema discipline requires a separate recovery strategy such as constrained decoding or schema-guided generation.
Third, mechanism claims must be weaker than audit claims.
We observed one training trajectory that scalar metrics would not flag, but we did not reproduce the original 1/4 G2 outcome under controlled retraining.

The protocol is useful precisely because it is conservative.
It is not a calibrated detector and it does not certify semantic quality.
It makes hidden behavioral debt visible before automatic promotion.
For small deployments this distinction matters.
The deployment owner may decide that an \amber gate is outside the current requirement scope, but that is a documented change in deployment specification, not a silent override.
The same rule applies to \red artifacts: promotion can resume only after rollback, repair, retraining, or a changed deployment requirement followed by audit rerun.

\section{{Limitations}}
The evidence supports an audit claim, not a prevalence claim.
The central failure is one independent trajectory; the 176-artifact atlas is dependent; G2 checks script-state compliance rather than phonetic quality; G3 checks schema shape rather than semantic correctness; and the child-facing motivation defines deployment requirements rather than human-subject prevalence.
These limits are why the protocol records actions and raw outputs instead of reporting a calibrated failure rate.

The gate thresholds are also heuristics.
We report sensitivity, but we do not calibrate precision or recall against a ground-truth deployment success label.
The 20-example repair slice mentioned in the protocol is a minimal operational unit, not a statistically optimized number.
The right repair budget depends on deployment risk and gate type.
Finally, this work does not propose a new LoRA training objective.
That is a deliberate scope choice: the main failure mode was not stable enough to justify a new training algorithm.

\section{{Conclusion}}
This case study argues for a modest practice: when fine-tuning adapters for a niche deployment, record explicit behavioral gates before promotion and map audit states to pipeline actions.
In our KO/RU/EN LoRA audit, one loss-attractive trajectory fails a cross-script state gate and is not reproduced in 13 controlled retrainings.
That negative result is part of the claim boundary.
The useful contribution is not a new failure law, but a conservative audit workflow that makes hidden behavioral debt visible before adapter deployment.

\bibliography{{lora_state_gated}}
\end{{document}}
"""
    return (
        template.replace("{g2_table_rows()}", g2_table_rows())
        .replace("{g3_table_rows()}", g3_table_rows())
        .replace("{trace_rows()}", trace_rows())
        .replace("{scalar_state_rows()}", scalar_state_rows())
        .replace("{{", "{")
        .replace("}}", "}")
    )


def supplement_tex() -> str:
    return r"""
\documentclass[11pt]{article}
\usepackage{acl}
\usepackage{times}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{microtype}
\title{Supplementary Material: State-Gated Audit for Niche-Population LoRA Fine-Tuning}
\author{
Byoungsang Lee$^{1,2}$ \quad
Yunchul Kim$^{1}$ \quad
Youmin Shim$^{1}$ \quad
Chaewon Kwak$^{1}$ \quad
Jung Heon Lee$^{1,3}$\\
$^{1}$School of Advanced Materials Science and Engineering, Sungkyunkwan University (SKKU), Suwon 16419, Korea\\
$^{2}$MoonTechnology, 3F, 29-5, World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea\\
$^{3}$Department of MetaBioHealth, Sungkyunkwan University (SKKU), Suwon 16419, Korea\\
\texttt{jhlee7@skku.edu}
}
\begin{document}
\maketitle
\section{Released Audit Assets}
The submission source includes the versioned probe files, automatic scorers, raw audit tables, and reproduction scripts needed to regenerate the G2-52 and G3-80 audit summaries. The released source tree contains:
\begin{itemize}
\item \texttt{fae\_protocol/probes\_v2\_translit.jsonl}: 52 G2 script-state prompts.
\item \texttt{fae\_protocol/probes\_v3\_schema.jsonl}: 80 G3 structured-output prompts.
\item \texttt{fae\_protocol/score\_translit\_auto.py}: Unicode-block script-state scorer.
\item \texttt{fae\_protocol/score\_schema\_auto.py}: JSON/schema scorer.
\item \texttt{figures/g2\_extended\_scores.json} and \texttt{figures/g3\_extended\_scores.json}: merged audit results.
\end{itemize}
\section{Claim-Tier Policy}
The paper separates three claim tiers. Tier 1 existence claims identify a concrete failure in a named artifact. Tier 2 predictability claims require controlled reproduction under a specified training factor. Tier 3 prevalence claims require an independent population sample. The present submission makes Tier 1 audit claims and negative Tier 2 evidence; it does not make Tier 3 prevalence claims.
\section{Anonymity and Submission Hygiene}
The review package suppresses author names, affiliations, ORCIDs, e-mail addresses, hostnames, and local paths. Camera-ready author ordering can be restored after review without adding equal-contribution wording.
\section{Build Note}
The main paper PDF is compiled from \texttt{source/lora\_state\_gated\_main.tex} with the ACL review style. The fallback Markdown and ReportLab PDFs are retained only as non-authoritative development artifacts.
\end{document}
"""


def bib() -> str:
    return r"""
@inproceedings{hu2022lora,
  title={LoRA: Low-Rank Adaptation of Large Language Models},
  author={Hu, Edward J. and Shen, Yelong and Wallis, Phillip and Allen-Zhu, Zeyuan and Li, Yuanzhi and Wang, Shean and Wang, Lu and Chen, Weizhu},
  booktitle={International Conference on Learning Representations},
  year={2022}
}

@inproceedings{houlsby2019adapter,
  title={Parameter-Efficient Transfer Learning for NLP},
  author={Houlsby, Neil and Giurgiu, Andrei and Jastrzebski, Stanislaw and Morrone, Bruna and de Laroussilhe, Quentin and Gesmundo, Andrea and Attariyan, Mona and Gelly, Sylvain},
  booktitle={International Conference on Machine Learning},
  year={2019}
}

@inproceedings{liu2022ia3,
  title={Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context Learning},
  author={Liu, Haokun and Tam, Derek and Muqeeth, Mohammed and Mohta, Jay and Huang, Tenghao and Bansal, Mohit and Raffel, Colin},
  booktitle={Advances in Neural Information Processing Systems},
  year={2022}
}

@inproceedings{dettmers2023qlora,
  title={QLoRA: Efficient Finetuning of Quantized LLMs},
  author={Dettmers, Tim and Pagnoni, Artidoro and Holtzman, Ari and Zettlemoyer, Luke},
  booktitle={Advances in Neural Information Processing Systems},
  year={2023}
}

@inproceedings{papineni2002bleu,
  title={BLEU: a Method for Automatic Evaluation of Machine Translation},
  author={Papineni, Kishore and Roukos, Salim and Ward, Todd and Zhu, Wei-Jing},
  booktitle={Proceedings of ACL},
  year={2002}
}

@inproceedings{popovic2015chrf,
  title={chrF: character n-gram F-score for automatic MT evaluation},
  author={Popovi{\'c}, Maja},
  booktitle={Proceedings of the Tenth Workshop on Statistical Machine Translation},
  year={2015}
}

@inproceedings{post2018sacrebleu,
  title={A Call for Clarity in Reporting BLEU Scores},
  author={Post, Matt},
  booktitle={Proceedings of the Third Conference on Machine Translation: Research Papers},
  year={2018}
}

@inproceedings{ribeiro2020checklist,
  title={Beyond Accuracy: Behavioral Testing of NLP Models with CheckList},
  author={Ribeiro, Marco Tulio and Wu, Tongshuang and Guestrin, Carlos and Singh, Sameer},
  booktitle={Proceedings of ACL},
  year={2020}
}

@article{bender2018datastatements,
  title={Data Statements for Natural Language Processing: Toward Mitigating System Bias and Enabling Better Science},
  author={Bender, Emily M. and Friedman, Batya},
  journal={Transactions of the Association for Computational Linguistics},
  volume={6},
  pages={587--604},
  year={2018}
}

@article{gebru2021datasheets,
  title={Datasheets for Datasets},
  author={Gebru, Timnit and Morgenstern, Jamie and Vecchione, Briana and Vaughan, Jennifer Wortman and Wallach, Hanna and Daum{\'e} III, Hal and Crawford, Kate},
  journal={Communications of the ACM},
  volume={64},
  number={12},
  pages={86--92},
  year={2021}
}

@techreport{bray2017json,
  title={The JavaScript Object Notation (JSON) Data Interchange Format},
  author={Bray, Tim},
  institution={RFC Editor},
  number={8259},
  year={2017}
}

@inproceedings{scholak2021picard,
  title={PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models},
  author={Scholak, Torsten and Schucher, Nathan and Bahdanau, Dzmitry},
  booktitle={Proceedings of EMNLP},
  year={2021}
}
"""


def write_readme() -> None:
    readme = """# EMNLP/ARR LaTeX Submission Source

This folder now follows the Paper5-style traceable build pattern:

- Main source: `source/lora_state_gated_main.tex`
- Supplement source: `source/lora_state_gated_supplement.tex`
- Style: `source/acl.sty` with `\\usepackage{acl}`
- Bibliography style: `source/acl_natbib.bst`
- Bibliography: `source/lora_state_gated.bib`
- Compiled outputs:
  - `01_main_paper_8p.pdf`
  - `02_supplement.pdf`

Build commands used on this machine:

```bash
cd emnlp_submission/source
tectonic lora_state_gated_main.tex
tectonic lora_state_gated_supplement.tex
cp lora_state_gated_main.pdf ../01_main_paper_8p.pdf
cp lora_state_gated_supplement.pdf ../02_supplement.pdf
```

The TeX engine used here was Tectonic 0.16.9. The source uses the official ACL
style file retrieved from `acl-org/acl-style-files`. This build includes the
author block and omits equal-contribution wording.
"""
    write(SUBMIT / "README.md", readme)


def compile_tex(tex_name: str) -> Path:
    run([str(TECTONIC), tex_name], SOURCE)
    return SOURCE / tex_name.replace(".tex", ".pdf")


def update_manifest() -> None:
    rows: list[str] = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and p.name != "manifest_sha256.txt":
            rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}")
    write(PKG / "manifest_sha256.txt", "\n".join(rows) + "\n")


def rebuild_zip() -> str:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PKG.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(PKG.parent))
    return hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()


def sanitize_review_text(text: str) -> str:
    replacements = {
        "Byoungsang Lee": "Anonymous Author",
        "Lee, Byoungsang": "Anonymous",
        "Yunchul Kim": "Anonymous Author",
        "Kim, Yunchul": "Anonymous",
        "Youmin Shim": "Anonymous Author",
        "Shim, Youmin": "Anonymous",
        "Chaewon Kwak": "Anonymous Author",
        "Kwak, Chaewon": "Anonymous",
        "Jung Heon Lee": "Anonymous Author",
        "Lee, Jung Heon": "Anonymous",
        "Sungkyunkwan University": "Anonymous Institution",
        "SKKU": "Anonymous Institution",
        "MoonTechnology": "Anonymous Organization",
        "World Cup Buk-ro 48-gil, Mapo-gu, Seoul 03927, Korea": "Anonymous address",
        "Suwon 16419, Korea": "Anonymous address",
        "School of Advanced Materials Science and Engineering": "Anonymous Department",
        "Department of MetaBioHealth": "Anonymous Department",
        "jhlee7@skku.edu": "anonymous@example.com",
        "NON-ANONYMOUS AUTHOR VERSION": "PASS",
        "non-anonymous author version": "anonymous review version",
        "author block and omits equal-contribution wording": "anonymous review author block",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def anonymize_tex_author(tex: str) -> str:
    tex = tex.replace(r"\usepackage{acl}", r"\usepackage[review]{acl}")
    tex = re.sub(r"\\author\{.*?\n\}\n\\begin\{document\}", "\\\\author{Anonymous ACL submission}\n\\\\begin{document}", tex, flags=re.S)
    return sanitize_review_text(tex)


def build_review_anon_package() -> str:
    if ANON_PKG.exists():
        shutil.rmtree(ANON_PKG)
    shutil.copytree(PKG, ANON_PKG)
    anon_submit = ANON_PKG / "emnlp_submission"
    anon_source = anon_submit / "source"

    for name in ["lora_state_gated_main.tex", "lora_state_gated_supplement.tex"]:
        p = anon_source / name
        p.write_text(anonymize_tex_author(p.read_text(encoding="utf-8")), encoding="utf-8")

    # Sanitize non-authoritative fallback/source text files too; review packages
    # should not leak names even in files that are not used for compilation.
    for p in anon_submit.rglob("*"):
        if not p.is_file() or p.name in {"acl.sty", "acl_natbib.bst"}:
            continue
        if p.suffix.lower() not in {".md", ".tex", ".bib", ".txt", ".yaml", ".jsonl", ".csv"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        p.write_text(sanitize_review_text(text), encoding="utf-8")

    # Compile review-mode PDFs from sanitized TeX.
    run([str(TECTONIC), "lora_state_gated_main.tex"], anon_source)
    run([str(TECTONIC), "lora_state_gated_supplement.tex"], anon_source)
    shutil.copy2(anon_source / "lora_state_gated_main.pdf", anon_submit / "01_main_paper_8p.pdf")
    shutil.copy2(anon_source / "lora_state_gated_supplement.pdf", anon_submit / "02_supplement.pdf")

    # Scan only for project-identifying strings. Common words in ACL style files
    # such as "Anonymous ACL submission" are expected.
    bad_patterns = [
        "Byoungsang", "Yunchul", "Youmin", "Chaewon", "Jung Heon",
        "Sungkyunkwan", "SKKU", "MoonTechnology", "jhlee7",
        "World Cup Buk-ro", "/scratch/hpc198a01",
    ]
    hits = []
    for p in anon_submit.rglob("*"):
        if not p.is_file() or p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for pat in bad_patterns:
            if pat in txt:
                hits.append(f"{p.relative_to(ANON_PKG)}: {pat}")
    (ANON_PKG / "anonymity_scan.txt").write_text("PASS\n" if not hits else "\n".join(hits) + "\n", encoding="utf-8")
    if hits:
        raise SystemExit("Anonymous package scan failed:\n" + "\n".join(hits))

    rows = []
    for p in sorted(ANON_PKG.rglob("*")):
        if p.is_file() and p.name != "manifest_sha256.txt":
            rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ANON_PKG).as_posix()}")
    write(ANON_PKG / "manifest_sha256.txt", "\n".join(rows) + "\n")

    if ANON_ZIP_PATH.exists():
        ANON_ZIP_PATH.unlink()
    with zipfile.ZipFile(ANON_ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(ANON_PKG.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(ANON_PKG.parent))
    return hashlib.sha256(ANON_ZIP_PATH.read_bytes()).hexdigest()


def convert_leftover_text_to_author_version() -> None:
    """Patch Markdown fallback/source files left by the anonymous fallback builder."""
    replacements = {
        "Anonymous N=20 panel": "N=20 panel",
        "[Anonymous N=20 panel]": "N=20 panel",
        "Anonymous Authors": "Lee et al.",
        "Anonymous supplementary material": "Supplementary material",
        "Anonymous minimal bibliography": "Non-anonymous bibliography",
        "anonymous submission source": "submission source",
        "Anonymous submission source": "Submission source",
        "anonymous author block": "author block",
        "Anonymous Author, Anonymous Author": "Byoungsang Lee, Yunchul Kim, Youmin Shim, Chaewon Kwak, Jung Heon Lee",
        "author = {Anonymous and Anonymous}": "author = {Lee, Byoungsang and Kim, Yunchul and Shim, Youmin and Kwak, Chaewon and Lee, Jung Heon}",
    }
    for p in SUBMIT.rglob("*"):
        if not p.is_file():
            continue
        if p.name in {"acl.sty", "acl_natbib.bst"}:
            continue
        if p.suffix.lower() not in {".md", ".tex", ".bib", ".txt", ".yaml", ".jsonl", ".csv"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, repl in replacements.items():
            new = new.replace(old, repl)
        if new != text:
            p.write_text(new, encoding="utf-8")


def main() -> None:
    if not TECTONIC.exists():
        raise SystemExit(f"Tectonic not found: {TECTONIC}")
    if not (ACL_STYLE_SRC / "acl.sty").exists():
        raise SystemExit(f"ACL style missing: {ACL_STYLE_SRC / 'acl.sty'}")
    SOURCE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ACL_STYLE_SRC / "acl.sty", SOURCE / "acl.sty")
    shutil.copy2(ACL_STYLE_SRC / "acl_natbib.bst", SOURCE / "acl_natbib.bst")
    write(SOURCE / "lora_state_gated_main.tex", textwrap.dedent(main_tex()).strip() + "\n")
    write(SOURCE / "lora_state_gated_supplement.tex", textwrap.dedent(supplement_tex()).strip() + "\n")
    write(SOURCE / "lora_state_gated.bib", bib().strip() + "\n")
    main_pdf = compile_tex("lora_state_gated_main.tex")
    supp_pdf = compile_tex("lora_state_gated_supplement.tex")
    shutil.copy2(main_pdf, SUBMIT / "01_main_paper_8p.pdf")
    shutil.copy2(supp_pdf, SUBMIT / "02_supplement.pdf")
    write_readme()
    write(PKG / "anonymity_scan.txt", "NON-ANONYMOUS AUTHOR VERSION\n")
    convert_leftover_text_to_author_version()
    update_manifest()
    sha = rebuild_zip()
    anon_sha = build_review_anon_package()
    print(f"[ok] compiled main: {SUBMIT / '01_main_paper_8p.pdf'}")
    print(f"[ok] compiled supplement: {SUBMIT / '02_supplement.pdf'}")
    print(f"[ok] zip: {ZIP_PATH}")
    print(f"[ok] sha256: {sha}")
    print(f"[ok] anonymous review zip: {ANON_ZIP_PATH}")
    print(f"[ok] anonymous review sha256: {anon_sha}")


if __name__ == "__main__":
    main()
