# GitHub Action Security Auditor

This project aims to provide an offline CLI for identifying potentially insecure
GitHub Actions workflow configurations, without GitHub credentials or API access.
The CLI discovers and parses local workflow files and runs a small set of
review-oriented security checks.

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

The checks report:

- `GHA001` (MEDIUM): `pull_request_target` trigger.
- `GHA002` (MEDIUM): `workflow_run` trigger.
- `GHA003` (HIGH): explicit `permissions: write-all`.
- `GHA004` (MEDIUM): explicit write permissions requiring review.
- `GHA005` (MEDIUM): a remote step action not pinned to a full commit SHA.
- `GHA006` (MEDIUM): a remote reusable workflow not pinned to a full commit SHA.

These findings identify configurations to review, not confirmed vulnerabilities.
The checks do not evaluate exploitability, effective permissions from repository
settings or event context, or the full GitHub Actions schema. A scan without
findings is not a guarantee of security.
Pinning checks do not resolve references or verify the referenced commit online.
Local actions and local reusable workflows are excluded; Docker image pinning is
not checked.

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
