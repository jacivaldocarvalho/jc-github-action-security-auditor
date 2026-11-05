# ADR 0001: Python Version Support

## Status

Accepted.

## Context

The CLI needs a maintained Python baseline and repeatable compatibility checks.
The package uses Python 3.11 language features and modern packaging.

## Decision

Declare Python 3.11 or newer in package metadata. Configure CI to test Python
3.11 and 3.12 on GitHub-hosted runners.

## Consequences

Python versions below 3.11 are excluded. The declared range also permits newer
versions, but the matrix does not explicitly test them. A configured matrix is
not evidence that either GitHub-hosted job has passed; actual run results are
needed to establish that.

## Alternatives considered

- Support older Python releases: would require maintaining compatibility with
  an older language and dependency baseline.
- Test only one Python version: would leave the other matrix target unchecked.

## References

- [Package metadata](../../pyproject.toml)
- [CI workflow](../../.github/workflows/ci.yml)
