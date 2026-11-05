# Testing Layers

The [test suite](../../tests/) exercises individual components and the CLI.
Coverage includes subprocess instrumentation for CLI tests; it measures executed
statements rather than proving security or branch completeness.

```mermaid
flowchart TD
    Tests[Pytest suite] --> Unit[Component tests]
    Unit --> Models[Models and reporting]
    Unit --> Input[Discovery, parser, and configuration]
    Unit --> Rules[Security rules]
    Tests --> Integration[CLI integration tests]
    Tests --> Edge[Security edge-case tests]
    Tests --> Coverage[pytest-cov and coverage.py]
    Integration --> Subprocess[CLI subprocess instrumentation]
    Subprocess --> Coverage
```

Coverage settings are in [pyproject.toml](../../pyproject.toml).
