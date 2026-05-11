# 7. Future Work

The present paper stops at Tier 1: a selector disagreement and a
negative mechanism result in one language triple. The next experiments
needed for a stronger submission are straightforward.

First, rerun the protocol on an external household panel. A Tier 2 claim
requires at least 10 households using the same probe-set hash, declared
evaluator roles, and inter-evaluator agreement reporting. The immediate
target is N=20 households across three months, which would let us
separate idiosyncratic household effects from reproducible gate failures.

Second, extend the language triples beyond KO/RU/EN. The bridge-pivot
pipeline is language-agnostic; the most informative next triples are
KO+Vietnamese+EN, KO+Mandarin+EN, and KO+Mongolian with RU/EN bridges.
The key question is whether the same gate failures recur when the
low-resource pair, scripts, and family language roles change.

Third, evaluate speech. The current work is text-only, while the target
deployment includes child and parent speech. A small hand-transcribed
child-speech set would test whether the same state-gated audit rule
is needed for audio input and speech-to-text-to-action pipelines.

Finally, compare selectors against stronger baselines. This paper uses
loss-only, task-metric, random-checkpoint, and state-gated selectors. A
future study should add targeted spot-check selectors and learned
failure predictors, then report false-positive and false-negative rates
against human-reviewed deployment decisions.
