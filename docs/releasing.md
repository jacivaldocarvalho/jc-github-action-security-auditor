# Release Preparation and Publication

This guide describes a future release process. It does not indicate that a
release, tag, publishing workflow, or Trusted Publisher already exists. Obtain
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

## TestPyPI and PyPI publication

TestPyPI and PyPI are separate services with separate project and publisher
configuration. After explicit approval for the destination and scope:

1. Configure a Trusted Publisher for the exact repository, publishing workflow,
   and protected environment on the target index. For a new project, use a
   pending publisher where appropriate. This repository has no publishing
   workflow configured by this guide.
2. Prefer PyPI Trusted Publishing with OIDC and the PyPA publishing action;
   avoid storing long-lived PyPI API tokens. Review and pin any action used in
   a future workflow to a full commit SHA. Protect the publishing environment
   with required reviewers and limit who can change the workflow and publisher.
3. Give only the publishing job `id-token: write`, required for OIDC. Grant
   other permissions only as needed; keep build and test jobs read-only. This
   permission allows requesting an OIDC token and is distinct from repository
   content write access.
4. First publish the reviewed artifacts to TestPyPI using its configured
   Trusted Publisher and TestPyPI repository URL. Verify the uploaded version,
   metadata, and installation in a clean environment. TestPyPI is separate
   from PyPI and may not contain all runtime dependencies; install trusted
   dependencies separately rather than relying on a mixed-index resolution.
5. After separate explicit approval for PyPI, publish the same reviewed
   artifacts using the PyPI Trusted Publisher, then verify the project page and
   installation in a clean environment.

Follow the [PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/)
for current service-specific setup. A manually authenticated upload is a
separate fallback requiring an approved credential and operation; never commit
credentials or place them in command history.

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
