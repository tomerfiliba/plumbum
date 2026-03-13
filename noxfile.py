#!/usr/bin/env -S uv run

# /// script
# dependencies = ["nox>=2025.2.9"]
# ///

from __future__ import annotations

import argparse

import nox

nox.needs_version = ">=2025.2.9"
nox.options.default_venv_backend = "uv|virtualenv"

PYPROJECT = nox.project.load_toml()
ALL_PYTHONS = nox.project.python_versions(PYPROJECT)


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

    session.install("-e.", "paramiko", "ipython", "pylint")
    session.run("pylint", "plumbum", *session.posargs)


@nox.session(python=ALL_PYTHONS, reuse_venv=True)
def tests(session):
    """
    Run the unit and regular tests.
    """
    test_deps = nox.project.dependency_groups(PYPROJECT, "test")
    session.install("-e.", *test_deps, "pytest-cov")
    session.run("pytest", "--cov", *session.posargs, env={"PYTHONTRACEMALLOC": "5"})


@nox.session(reuse_venv=True, default=False)
def docs(session):
    """
    Build the docs. Use "--non-interactive" to avoid serving. Pass "-b linkcheck" to check links.
    """

    uv_pip = ["uv", "pip"] if session.venv_backend == "uv" else ["pip"]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", dest="builder", default="html", help="Build target (default: html)"
    )
    args, posargs = parser.parse_known_args(session.posargs)

    serve = args.builder == "html" and session.interactive
    extra_installs = ["sphinx-autobuild"] if serve else []
    session.install("-e.", "--group=docs", *extra_installs)
    session.run(*uv_pip, "list")

    session.chdir("docs")

    shared_args = (
        "-n",  # nitpicky mode
        "-T",  # full tracebacks
        f"-b={args.builder}",
        ".",
        f"_build/{args.builder}",
        *posargs,
    )

    if serve:
        session.run("sphinx-autobuild", "--open-browser", *shared_args)
    else:
        session.run("sphinx-build", "--keep-going", *shared_args)


@nox.session(default=False)
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")


if __name__ == "__main__":
    nox.main()
