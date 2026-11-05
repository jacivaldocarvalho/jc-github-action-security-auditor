# CI Pipeline

The configured [CI workflow](../../.github/workflows/ci.yml) runs on push and
pull requests with read-only contents permission. Checkout and Python setup use
full SHA pins. The diagram describes configuration, not hosted run results.

```mermaid
flowchart TD
    Push[Push] --> Job[CI job]
    PR[Pull request] --> Job
    Permissions[Token: contents read] -.-> Job
    Job --> Matrix[Python 3.11 and 3.12 matrix]
    Matrix --> Checkout[SHA-pinned checkout]
    Checkout --> Python[SHA-pinned Python setup]
    Python --> Install[Install project and development dependencies]
    Install --> Tests[Pytest with coverage]
    Tests --> Lint[Ruff lint]
    Lint --> Format[Ruff format check]
```
