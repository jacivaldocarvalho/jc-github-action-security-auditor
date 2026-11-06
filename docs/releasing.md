# Release Preparation and Publication

Version 0.1.0 was published to PyPI using GitHub Actions Trusted Publishing.
This guide describes subsequent releases and how to restore the publishing setup.
Obtain explicit, operation-specific approval before publishing, creating or
pushing a tag, creating a GitHub Release, or changing publishing infrastructure.

## One-time publishing setup

The PyPI Trusted Publisher and GitHub Environment `pypi` are normally configured
once and reused. Before each release, confirm that they still match the workflow
and that their protections remain effective. To recreate the configuration, an
authorized project owner configures the existing PyPI project's Trusted Publisher:

- Project: `jc-github-action-security-auditor`
- GitHub owner: `jacivaldocarvalho`
- Repository: `jc-github-action-security-auditor`
- Workflow filename: `publish.yml`
- GitHub Environment: `pypi`

For a new project, PyPI offers a pending publisher; the project name must match
the distribution metadata. PyPI and TestPyPI have separate publisher settings;
the current workflow targets official PyPI only. See the [PyPI setup guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
and [pending publisher guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

Create the `pypi` environment in GitHub before running the workflow. Restrict
deployments to `main`, require an independent reviewer where available, and
prevent self-review where supported. Check that the repository's plan and
visibility support these protections; do not rely on required review if it is
unavailable. Restrict who can change `main`, the workflow, environment rules,
and PyPI publisher. GitHub can otherwise create a missing environment without
protection rules. See [GitHub environment documentation](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

## Prepare the version

Update `project.version` in [pyproject.toml](../pyproject.toml), the authoritative
package metadata, and update [CHANGELOG.md](../CHANGELOG.md) with the intended
release date and actual changes. Check that the version, release notes, and
planned `v<version>` tag agree. Confirm on the [official PyPI project page](https://pypi.org/project/jc-github-action-security-auditor/)
that the target version is not already published; investigate any existing files
before proceeding. Review dependencies, the working tree, and release inputs.

## Validate before release

In an isolated development environment, preferably on both supported Python
versions in the [CI matrix](../.github/workflows/ci.yml), run:

```bash
python -m pytest --cov=jc_github_action_security_auditor --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
jc-gha-audit scan .
```

Investigate scan findings and errors; the auditor is not a complete security
assessment. The publishing workflow's `id-token: write` produces a GHA004 review
finding and is required for OIDC. See the [README](../README.md) for limitations.

Install `build` and `twine` in a temporary tooling environment. Build with the
default isolated backend environment into a fresh temporary directory:

```bash
python -m pip install build twine
release_dist_dir=$(mktemp -d)
python -m build --outdir "$release_dist_dir"
python -m twine check --strict "$release_dist_dir"/*
python -m zipfile -l "$release_dist_dir"/*.whl
tar -tzf "$release_dist_dir"/*.tar.gz
```

Inspect wheel and sdist contents and metadata, including name, version, Python
requirement, license, entry points, dependencies, README rendering, links,
secrets, and unexpected files. Rebuild a wheel from the extracted sdist in a
separate isolated build and check it. In clean Python 3.11 and 3.12 environments,
install each distribution outside the checkout and test CLI help, version,
a clean scan, and a scan with a known finding. Record results and hashes.
`twine check --strict` checks the long description but is not a substitute for
reviewing its rendered appearance and linked assets.

## Integrate the release commit

After the required approval, commit and push the reviewed preparation changes to
`main`. Require the CI workflow to pass for the exact commit, including its Python
3.11 and 3.12 jobs. Record that commit SHA, confirm it is the intended source
revision and the current remote `main`, and check that the intended version and
artifacts have not appeared on PyPI in the meantime. The publishing workflow
builds its own artifacts from the dispatched revision; local builds and CI do
not automatically gate it or guarantee identical bytes.

## Publish with OIDC

After explicit approval for the exact version and destination, manually run
[Publish to PyPI](../.github/workflows/publish.yml) from GitHub Actions using
**Run workflow**, selecting `main`, or run `gh workflow run publish.yml --ref main`.
The workflow is triggered by `workflow_dispatch`; ordinary pushes and pull
requests do not publish. The build job is restricted to `refs/heads/main`.
Immediately verify that the run's head SHA is the reviewed release commit; do
not approve or proceed with a different revision. If environment approval is
configured, an authorized reviewer inspects the run and its artifacts before
approving the `pypi` job. The workflow itself does not enforce CI success or
check a specified expected SHA; protect `main` and coordinate dispatch and review.

The build job has `contents: read`, builds wheel and sdist in an isolated build,
runs `twine check --strict`, and uploads them with SHA-256 checksums. The separate
publishing job downloads the artifacts, verifies the checksums, removes the
checksum file, and invokes the PyPA publishing action. Its only GitHub token
permission is `id-token: write`, used for OIDC; it has no checkout step. Use
Trusted Publishing exclusively, without permanent PyPI tokens or passwords.

## Verify the publication

Check the [PyPI project page](https://pypi.org/project/jc-github-action-security-auditor/)
for the intended version and both wheel and sdist. In a fresh environment outside
the checkout, install that exact version from official PyPI and check the CLI:

```bash
python -m venv /tmp/jc-auditor-release-verify
/tmp/jc-auditor-release-verify/bin/python -m pip install --index-url https://pypi.org/simple 'jc-github-action-security-auditor==<version>'
/tmp/jc-auditor-release-verify/bin/jc-gha-audit --version
/tmp/jc-auditor-release-verify/bin/jc-gha-audit --help
```

Replace `<version>` with the released version and use a fresh environment path.
Confirm the reported version, and record the workflow URL, source SHA, artifacts,
and hashes. Do not rerun a successful publication.

## Tag and create the GitHub Release

After separate explicit approval and successful PyPI verification, check for an
existing local and remote `v<version>` tag and GitHub Release. Stop on a conflict;
never move or overwrite a tag. Create an annotated tag at the exact published
source commit, verify its target, and push only that tag. Publish the matching
GitHub Release with accurate notes based on the changelog, and verify its status
and tag target. Do not assert that unpublished features are present.

## Failure handling and security limits

If OIDC authentication or upload fails, stop and inspect the workflow logs and
PyPI Trusted Publisher configuration. Do not fall back to long-lived tokens or
password authentication. Check the official PyPI version page and its files for
partial publication before considering a retry; resolve the cause and obtain
specific approval. Never retry blindly. PyPI does not permit replacing an
uploaded distribution file, even after deletion; a partial or incorrect release
may require a new version. Assess yanking or a corrected release separately and
obtain explicit approval before taking those actions.

All external actions in the current workflows are pinned to full commit SHAs;
verify upstream ownership and review pins when updating them. Permissions are
limited per job, and the publishing job is separated from the build. The checksum
check detects transfer corruption, but a compromised build can alter both files
and checksums. Build tools and backend dependencies are installed from package
indexes without pinned versions, so dependency compromise and non-reproducible
builds remain risks. Review the build run, dependencies, artifacts and hashes;
build isolation alone does not establish provenance or guarantee reproducibility.
See [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [GitHub's secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use).
