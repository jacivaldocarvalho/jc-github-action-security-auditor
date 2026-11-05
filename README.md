# GitHub Action Security Auditor

This project aims to provide an offline CLI for identifying potentially insecure
GitHub Actions workflow configurations, without GitHub credentials or API access.
The CLI currently discovers and parses local workflow files. Security checks are
not implemented.

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
exits with status 1 if any file fails or discovery fails. If no workflows are
found, it prints a message and exits successfully. Nested directories and
symbolic-link workflow files are ignored; symbolic-link `.github` or
`.github/workflows` directories are rejected. Parsing success does not mean that
a workflow is valid for GitHub Actions or secure: schema validation and security
analysis are not implemented.

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
