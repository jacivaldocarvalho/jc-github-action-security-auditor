# ADR 0002: Full SHA Pinning

## Status

Accepted.

## Context

Remote GitHub Actions and reusable workflows are supply-chain dependencies.
Tags and branches can move, changing the code used by a workflow without a
change to the workflow reference.

## Decision

Pin remote actions and reusable workflows to reviewed, full 40-character commit
SHAs. The CI workflow pins its actions this way. GHA005 flags non-SHA remote
step actions, and GHA006 flags non-SHA remote reusable workflows for review.

## Consequences

Pins make changes to the selected commit explicit in the workflow, but require
deliberate updates. The offline checks validate reference shape only: they do
not resolve a SHA, verify its provenance or contents, or establish that it is
safe. Local references and Docker image pinning are outside these checks.

## Alternatives considered

- Use tags or branches: easier to update, but their targets can change.
- Resolve references online: could add context, but conflicts with the current
  offline scanner design.

## References

- [Pinning rules](../../src/jc_github_action_security_auditor/rules/action_pinning.py)
- [CI workflow](../../.github/workflows/ci.yml)
- [Project README](../../README.md)
