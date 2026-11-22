# 0008. The copilot narrates tool results

- Status: accepted
- Date: 2026-11-22

## Context

Investigators ask questions in ordinary language. A model that can see case
text can also invent a transfer, follow instructions hidden in a narration, or
sound certain about a hypothesis. The product already has deterministic
operations that answer the questions the milestone cares about: trace, shared
accounts, indicators, observations.

A large agent framework would move tool routing into configuration that is
harder to audit. The tool list is short.

## Decision

The copilot is a tool runner with a fixed allow-list. Deterministic mode is
the default and does not contact a model. Assisted mode, later, may phrase the
tool bundle. A citation check drops any claim that references evidence the
tools did not return. The model is not given a query language. Case text is
not sent anywhere while the provider is `none`.

No model vendor is selected. The port can be bound later. The milestone does
not depend on a key.

## Consequences

- Answers are only as good as the tools. That is the point.
- Phrase coverage of the first router is limited. Unrecognised questions get a
  case summary rather than a guessed narrative.
- Provider outages do not take the feature down.

## Alternatives

- A chat model with direct database access. Rejected. It can answer anything,
  including things that are not in the case.
- A vector database of narrations in Phase 1. Extra store, extra copies of
  sensitive text, no milestone question that requires it. Reconsider only for
  a stated similarity feature.
- Requiring a model for the demo. Rejected so the demonstration stays
  reproducible offline.
