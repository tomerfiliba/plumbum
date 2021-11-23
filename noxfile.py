# -*- coding: utf-8 -*-
from __future__ import annotations

import nox

ALL_PYTHONS = ["2.7", "3.5", "3.6", "3.7", "3.8", "3.9"]

nox.options.sessions = ["lint", "tests"]


@nox.session(reuse_venv=True)
def lint(session):
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(python=ALL_PYTHONS, reuse_venv=True)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(reuse_venv=True)
def docs(session):
    """
    Build the docs. Pass "serve" to serve.
    """

    session.install("-e", ".[docs]")
    session.chdir("docs")
    session.run("sphinx-build", "-M", "html", ".", "_build")

    if session.posargs:
        if "serve" in session.posargs:
            print("Launching docs at http://localhost:8000/ - use Ctrl-C to quit")
            session.run("python", "-m", "http.server", "8000", "-d", "_build/html")
        else:
            print("Unsupported argument to docs")


@nox.session
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")
