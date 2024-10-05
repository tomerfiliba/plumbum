from __future__ import annotations

import nox

nox.needs_version = ">=2024.4.15"
nox.options.default_venv_backend = "uv|virtualenv"

ALL_PYTHONS = [
    c.split()[-1]
    for c in nox.project.load_toml("pyproject.toml")["project"]["classifiers"]
    if c.startswith("Programming Language :: Python :: 3.")
]


@nox.session(reuse_venv=True)
def lint(session):
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session
def pylint(session):
    """
    Run pylint.
    """

    session.install(".", "paramiko", "ipython", "pylint")
    session.run("pylint", "plumbum", *session.posargs)


@nox.session(python=ALL_PYTHONS, reuse_venv=True)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install("-e", ".[test]")
    session.run("pytest", *session.posargs, env={"PYTHONTRACEMALLOC": "5"})


@nox.session(reuse_venv=True, default=False)
def docs(session):
    """
    Build the docs. Pass "serve" to serve.
    """

    session.install("-e", ".[docs]")
    session.chdir("docs")
    session.run("sphinx-build", "-M", "html", ".", "_build")

    if session.posargs:
        if "serve" in session.posargs:
            session.log("Launching docs at http://localhost:8000/ - use Ctrl-C to quit")
            session.run("python", "-m", "http.server", "8000", "-d", "_build/html")
        else:
            session.log("Unsupported argument to docs")


@nox.session(default=False)
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")
