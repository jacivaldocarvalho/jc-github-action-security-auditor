# GitHub Action Security Auditor

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![CI](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/actions/workflows/ci.yml)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-Ruff-261230)](https://docs.astral.sh/ruff/)
[![License](https://img.shields.io/github/license/jacivaldocarvalho/jc-github-action-security-auditor)](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/blob/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/LICENSE)

## Overview

This project provides an offline CLI for identifying potentially insecure
GitHub Actions workflow configurations, without GitHub credentials or API access.
The CLI discovers and parses local workflow files and runs a small set of
review-oriented security checks.

## The Problem

GitHub Actions workflows can have excessive `GITHUB_TOKEN` permissions or use
privileged triggers that make untrusted code or inputs especially risky. Third-party
actions referenced by mutable tags and remote reusable workflows without immutable
references can change after review, with supply-chain implications for the code that
runs in CI. Reviewing workflow YAML before execution helps identify configurations
that warrant closer scrutiny before they can affect a repository or its automation.

## Why This Project?

The auditor is a lightweight Python CLI for offline static analysis of local
workflow files. It requires no GitHub credentials or API access and produces
deterministic, review-oriented findings. Rules can be disabled through a local
configuration file, and text, JSON, and Markdown reports support both local
development and CI automation.

## Requirements and installation

Python 3.11 or later is required. For local development, install the package and
development tools from the repository root:

```bash
python -m pip install -e ".[dev]"
```

## Usage

```bash
jc-gha-audit --help
jc-gha-audit --version
jc-gha-audit scan .
jc-gha-audit scan . --config audit.yml
jc-gha-audit scan . --format json
jc-gha-audit scan . --format markdown --config audit.yml
```

The `scan` command discovers `.yml` and `.yaml` regular files directly inside the
repository's `.github/workflows/` directory in sorted order and reports `OK` or
`ERROR` for each file's parsing result. It continues after parsing errors and
exits with status 1 if any finding is reported, parsing fails, or discovery
fails. It exits with status 0 if all files parse without findings. If no workflows are
found, it prints a message and exits successfully. Nested directories and
symbolic-link workflow files are ignored; symbolic-link `.github` or
`.github/workflows` directories are rejected. `OK` means parsing succeeded; it
does not mean that a workflow is valid for GitHub Actions or secure.

The default `text` format prints parsing status and findings. Use `--format json`
for a structured summary, findings, and workflow errors, or `--format markdown`
for a readable report with the same information. Reports go to standard output;
configuration and discovery failures go to standard error. Findings and scanning
errors produce exit status 1 in every format.

## Example: Detecting Insecure Workflows

![Terminal demonstration of the auditor detecting three workflow security findings](https://raw.githubusercontent.com/jacivaldocarvalho/jc-github-action-security-auditor/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/docs/assets/security-demo.gif)

This workflow is **intentionally insecure and for demonstration only**. Create it
in a temporary directory, then scan that directory:

```bash
example_repo=$(mktemp -d)
mkdir -p "$example_repo/.github/workflows"
cat > "$example_repo/.github/workflows/insecure.yml" <<'YAML'
name: Insecure example
on: pull_request_target
permissions: write-all
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
YAML
jc-gha-audit scan "$example_repo" --format json
```

The resulting JSON is:

```json
{
  "summary": {
    "workflows_analyzed": 1,
    "findings": 3,
    "errors": 0
  },
  "findings": [
    {
      "rule_id": "GHA001",
      "severity": "MEDIUM",
      "message": "The pull_request_target trigger warrants a security review.",
      "file_path": ".github/workflows/insecure.yml",
      "line": null,
      "recommendation": "Review token permissions and secrets; avoid executing untrusted pull request code in a privileged context."
    },
    {
      "rule_id": "GHA003",
      "severity": "HIGH",
      "message": "Workflow declares write-all token permissions.",
      "file_path": ".github/workflows/insecure.yml",
      "line": null,
      "recommendation": "Replace write-all with only the permissions required by this workflow or job, following least privilege."
    },
    {
      "rule_id": "GHA005",
      "severity": "MEDIUM",
      "message": "Job 'build', step 1 uses an unpinned remote action: actions/checkout@v4.",
      "file_path": ".github/workflows/insecure.yml",
      "line": null,
      "recommendation": "Pin the action to a reviewed full 40-character commit SHA."
    }
  ],
  "errors": []
}
```

GHA001 flags the `pull_request_target` trigger for review. GHA003 flags the
explicit `write-all` token permissions. GHA005 flags `actions/checkout@v4`
because its ref is not a full commit SHA. The CLI exits with status 1 because
it reported findings. These are configurations requiring review, not confirmed
exploitable vulnerabilities.

## Security Checks

| Rule ID | Severity | Detection | Security rationale |
| --- | --- | --- | --- |
| GHA001 | MEDIUM | `pull_request_target` in `on` (string, list, or mapping). | Privileged pull request contexts require care with untrusted code, tokens, and secrets. |
| GHA002 | MEDIUM | `workflow_run` in `on` (string, list, or mapping). | Artifacts and other inputs from the triggering workflow require validation in a privileged context. |
| GHA003 | HIGH | Explicit `permissions: write-all` at workflow or job level. | Broad write access can exceed the permissions a workflow needs. |
| GHA004 | MEDIUM | Explicit permission mapping with one or more `write` values at workflow or job level. | Write access should be reviewed against the permissions actually required. |
| GHA005 | MEDIUM | Remote step action reference with a nonempty ref that is not a full 40-character hexadecimal commit SHA. | Mutable or abbreviated references can change or be ambiguous after review. |
| GHA006 | MEDIUM | Remote job reusable workflow reference in `owner/repo/.github/workflows/file.yml` or `.yaml` form with a nonempty ref that is not a full 40-character hexadecimal commit SHA. | Mutable or abbreviated references can change or be ambiguous after review. |

The pinning checks skip malformed references, including missing or empty refs.
These findings identify configurations to review, not confirmed vulnerabilities.
The checks do not evaluate exploitability, effective permissions from repository
settings or event context, or the full GitHub Actions schema. A scan without
findings is not a guarantee of security.
Pinning checks do not resolve references or verify the referenced commit online.
Local actions and local reusable workflows are excluded; Docker image pinning is
not checked.

## Rule configuration

All rules are enabled by default. Pass `--config PATH` to select a local UTF-8
YAML file that disables specific rules, for example:

```yaml
disabled_rules:
  - GHA001
  - GHA005
```

Only `disabled_rules` is supported; it must contain unique, known rule IDs.
An empty file or mapping leaves all rules enabled. Invalid or unreadable
configuration produces an error and exit status 1. No configuration file is
discovered automatically. The file is limited to 1 MiB and YAML aliases,
merge keys, and explicit tags are rejected.

## YAML parsing library

`parse_workflow(path)` in `jc_github_action_security_auditor.parser` reads a
UTF-8 workflow file and returns its top-level mapping. It uses a custom safe
loader and raises `WorkflowParseError` for invalid or unsupported input. The
unquoted `on` key and boolean-like words such as `yes`, `no`, `on`, and `off`
remain strings; `true` and `false` (including their usual YAML capitalizations)
are booleans. Mapping keys must be strings, and duplicate keys, YAML merge keys,
and aliases are rejected. An empty document is rejected; an empty mapping is
accepted. No GitHub Actions schema validation is performed.

Input is limited to 1 MiB. The parser does not execute workflow contents, but
the size limit alone does not prevent all resource exhaustion. It is not a
sandbox for files controlled by a concurrently changing filesystem.

## Tests

```bash
python -m pytest -q
```

To measure coverage, including CLI subprocesses, run:

```bash
python -m pytest --cov=jc_github_action_security_auditor --cov-report=term-missing
```

Coverage measures executed statements, not whether every branch or security
scenario was tested. Subprocess coverage requires the development dependencies
and normal process termination to save measurements.

## Roadmap (Planned)

The following are proposed future improvements and are not implemented:

**Short-term priorities**

- SARIF output for GitHub Code Scanning and GitHub Actions annotations.
- Expression injection detection and credential persistence checks.
- Reduced false positives.

**Longer-term priorities**

- Self-hosted runner security checks and context-aware permission analysis.
- A reusable GitHub Action for this auditor.
- Benchmarking against established tools and real repositories.

## Documentation

See the [documentation index](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/blob/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/docs/index.md) for architecture decisions and
diagrams, the [contribution guide](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/blob/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/CONTRIBUTING.md) for development practices,
and the [changelog](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/blob/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/CHANGELOG.md) for project history.

## License

Distributed under the MIT License. See [LICENSE](https://github.com/jacivaldocarvalho/jc-github-action-security-auditor/blob/2f984f95cb34c657cfd3dfd3ecc41174a2cbc7a4/LICENSE) for more information.

## Author

**Jacivaldo Carvalho**

Telecommunications Engineer | DevOps Engineer | SRE | Networking

[GitHub](https://github.com/jacivaldocarvalho) | [LinkedIn](https://www.linkedin.com/in/jacivaldocarvalho) | [Website](https://www.jacivaldocarvalho.com/)
