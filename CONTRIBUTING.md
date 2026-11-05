# Contributing

## Development setup

Use Python 3.11 or newer. From the repository root, create and activate a virtual
environment, then install the project and development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Validation

Run the same test coverage and Ruff checks configured in CI:

```bash
python -m pytest --cov=jc_github_action_security_auditor --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
```

Run the local security auditor against the repository:

```bash
jc-gha-audit scan .
```

The scanner exits with status 1 for findings or scanning errors. Findings are
review prompts, not proof of exploitation. See the [README](README.md) for
configuration, report formats, and current limitations.

## Contribution workflow

1. Create a branch for a focused change.
2. Make the change and add or update tests for affected behavior and risks.
3. Run the validation commands above and document relevant limitations.
4. Open a pull request describing the change and validation, then respond to
   review feedback.

Treat workflow YAML and configuration as untrusted input. Avoid introducing
secrets, unnecessary permissions, network access to the offline scanner, or
unreviewed dependencies. Pin remote CI actions to reviewed full commit SHAs;
consider compatibility and resource limits when handling untrusted data.

## Design documentation

- [Python support decision](docs/adr/0001-python-version-support.md)
- [Full SHA pinning decision](docs/adr/0002-full-sha-pinning.md)
- [Token permissions decision](docs/adr/0003-read-only-github-token.md)
- [Architecture diagram](docs/diagrams/architecture.md)
- [CI and testing diagrams](docs/diagrams/ci-pipeline.md)
- [Testing layers](docs/diagrams/testing-layers.md)
