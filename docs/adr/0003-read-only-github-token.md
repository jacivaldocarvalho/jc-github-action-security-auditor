# ADR 0003: Read-Only GitHub Token

## Status

Accepted.

## Context

GitHub Actions workflows can access a `GITHUB_TOKEN`. Granting only the
permissions needed by a workflow reduces the potential impact of misuse.

## Decision

Apply least privilege to token permissions. The project's CI declares
`contents: read`. GHA003 reports explicit `write-all` declarations, and GHA004
reports explicit write scopes for review at workflow and job level.

## Consequences

Jobs requiring additional access must explicitly justify and grant it. A write
finding indicates a review opportunity, not a confirmed vulnerability. The
checks inspect declarations; they do not infer effective permissions from
repository settings or event context.

## Alternatives considered

- Grant broad write access: simpler for write operations, but increases access
  beyond the current CI job's needs.
- Rely solely on repository defaults: leaves the workflow's intended permission
  boundary less explicit.

## References

- [CI workflow](../../.github/workflows/ci.yml)
- [Permission rules](../../src/jc_github_action_security_auditor/rules/permissions.py)
- [Project README](../../README.md)
