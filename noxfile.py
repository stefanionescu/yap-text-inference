"""Python-native task runner for linting, hooks, security, and coverage."""

from __future__ import annotations

import nox

nox.options.default_venv_backend = "none"
nox.options.sessions = ["lint", "test"]


def _run(session: nox.Session, *args: str) -> None:
    session.run(*args, external=True)


@nox.session(name="lint")
def lint(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh")


@nox.session(name="lint_fast")
def lint_fast(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--fast")


@nox.session(name="lint_code")
def lint_code(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--only", "code")


@nox.session(name="lint_shell")
def lint_shell(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--only", "shell")


@nox.session(name="lint_docs")
def lint_docs(session: nox.Session) -> None:
    _run(session, "bash", "linting/docs/run.sh")


@nox.session(name="lint_docker")
def lint_docker(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--only", "docker")


@nox.session(name="quality")
def quality(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--only", "quality")


@nox.session(name="security")
def security(session: nox.Session) -> None:
    _run(session, "bash", "linting/security/run.sh")


@nox.session(name="hooks")
def hooks(session: nox.Session) -> None:
    _run(session, "bash", "linting/lint.sh", "--only", "hooks")


@nox.session(name="test")
def test(session: nox.Session) -> None:
    _run(session, "python", "-m", "pytest", "-q")


@nox.session(name="coverage")
def coverage(session: nox.Session) -> None:
    _run(session, "bash", "scripts/coverage.sh")


@nox.session(name="sonar")
def sonar(session: nox.Session) -> None:
    _run(session, "bash", "linting/security/sonarqube/run.sh")


@nox.session(name="codeql")
def codeql(session: nox.Session) -> None:
    _run(session, "bash", "linting/security/codeql/run.sh")
