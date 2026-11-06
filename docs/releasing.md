# Release Preparation and Publication

This guide describes a future release process and a prepared publishing workflow.
It does not indicate that a release, tag, or Trusted Publisher already exists. Obtain
explicit, operation-specific approval before publishing to TestPyPI or PyPI,
creating a tag or release, or changing publishing infrastructure or credentials.

## Prerequisites

Review the intended commit and ensure the working tree and release inputs are
understood. Confirm the version in [pyproject.toml](../pyproject.toml), the
[changelog](../CHANGELOG.md), intended tag, release notes, and built metadata
agree. The current metadata version is `0.1.0`; verify the intended version and
its availability on each target index before publication. Do not assume it has
already been published. Review dependencies, distribution contents, and changes
to the [CI workflow](../.github/workflows/ci.yml).

Run the checks below in an isolated development environment, preferably on both
Python 3.11 and 3.12. Record actual results; a configured matrix alone does not
prove a hosted run passed.

```bash
python -m pytest --cov=jc_github_action_security_auditor --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
jc-gha-audit scan .
```

Investigate findings and errors before release. The auditor is not a complete
security assessment. See the [contribution guide](../CONTRIBUTING.md) and
[README](../README.md) for setup and limitations.

## Build and inspect

Install `build` and `twine` in a temporary tooling environment; they are not
project runtime dependencies. Build from the reviewed commit using build's
default isolated backend environment. The temporary directory keeps prior
artifacts out of this build:

```bash
python -m pip install build twine
release_dist_dir=$(mktemp -d)
python -m build --outdir "$release_dist_dir"
python -m twine check "$release_dist_dir"/*
```

Inspect both archive file lists and their contents, including package metadata,
entry points, dependencies, README, secrets, generated files, and unintended
instructions. Confirm all expected package modules are present. For example:

```bash
python -m zipfile -l "$release_dist_dir"/*.whl
tar -tzf "$release_dist_dir"/*.tar.gz
```

Rebuild a wheel from the extracted sdist in a separate directory with build
isolation, and check the resulting wheel. Review and retain the exact artifacts
and hashes selected for publication; do not silently substitute later builds.
Build isolation creates an environment for build dependencies; it does not by
itself guarantee reproducibility or provenance.

Create separate clean Python 3.11 and 3.12 environments. Install the built
wheel in each and verify `jc-gha-audit --help`, `jc-gha-audit --version`, a
clean workflow scan, and a scan producing a known finding. Repeat installation
from the sdist to verify it can build and install independently. Run these tests
outside the source checkout so imports come from the installed distribution.

## PyPI Trusted Publishing setup

The prepared [publishing workflow](../.github/workflows/publish.yml) is manually
triggered only on `main`. Its build job builds and checks the distributions;
the separate publishing job downloads those artifacts, checks their hashes, and
uses PyPI Trusted Publishing via OIDC. It does not use a PyPI API token or
username and password. The hash check detects transfer corruption; it does not
establish independent trust in a compromised build job.

Before the first upload, verify that the project name is available on PyPI and
create a **pending publisher** there with these exact values:

- PyPI project name: `jc-github-action-security-auditor`
- GitHub owner: `jacivaldocarvalho`
- Repository: `jc-github-action-security-auditor`
- Workflow filename: `publish.yml`
- GitHub Environment: `pypi`

If the project already exists, an authorized project owner must configure an
existing project's Trusted Publisher instead. See the [PyPI pending publisher
guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
PyPI and TestPyPI have separate publisher configurations; this workflow targets
PyPI only.

In GitHub repository settings, create the `pypi` environment **before running
the workflow**, require an independent reviewer where available, prevent
self-review where supported, and restrict deployment branches to `main`. Confirm
that the repository's plan and visibility support the desired protection rules;
if required review is unavailable, do not rely on it as a release gate. Restrict
who can change the workflow, `main`, environment rules, and PyPI publisher. GitHub
may otherwise create an unprotected environment when a workflow references a
missing one. See [GitHub deployment environment documentation](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

After the reviewed workflow is committed to `main`, validate the release commit,
CI, version availability, artifact contents and hashes. Obtain explicit approval
for the exact PyPI publication before manually dispatching `publish.yml` on
`main`. The `pypi` environment reviewer must inspect the build run and artifacts
before approving the publishing job. No ordinary push or pull request publishes.
Verify the PyPI project page and installation after the approved upload.

Follow the [PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [GitHub security guidance](https://docs.github.com/en/actions/reference/security/secure-use).
Do not configure long-lived PyPI credentials for this workflow.

## Tag, release notes, and recovery

After explicit approval, create the intended Git tag for the reviewed commit
and prepare release notes from the changelog. Record the tag, artifact hashes,
validation results, and publication outcome. Create a GitHub release only when
its scope is approved; do not claim a release was published before verification.

If an artifact is faulty, stop further promotion, communicate the issue through
the project's established channels, and assess whether to yank the affected
release and publish a corrected version. Package index uploads are not generally
reversible replacements: do not assume an uploaded filename or version can be
reused. Review the index's current recovery rules and obtain explicit approval
before yanking, deleting, or publishing a correction.
