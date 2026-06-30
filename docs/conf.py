"""Sphinx configuration for the aws-stepfunctions-toolkit documentation.

Markdown-first: pages are authored in Markdown and parsed by MyST. The API
reference is generated from docstrings by autodoc. Built locally with
``make docs`` and on Read the Docs via ``.readthedocs.yaml``.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

# -- Project information -----------------------------------------------------

project = "AWS Step Functions Toolkit"
author = "Roy Assis, Compugen"
copyright = "2026, Compugen"  # noqa: A001 - Sphinx requires this exact name

# Single source of truth for the version is the installed package metadata
# (which setuptools-scm derives from the git tag). Mirrors the package's own
# __version__ logic so the docs never drift from what was built.
try:
    release = _pkg_version("aws-stepfunctions-toolkit")
except PackageNotFoundError:
    release = "0.0.0"
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",  # author pages in Markdown
    "sphinx.ext.autodoc",  # pull API docs from docstrings
    "sphinx.ext.napoleon",  # Google / NumPy docstring styles
    "sphinx.ext.viewcode",  # add [source] links to the API reference
    "sphinx.ext.intersphinx",  # link stdlib types in signatures
    "sphinx_copybutton",  # copy button on code blocks
]

# Autodoc: document members in definition order; fold type hints into the
# parameter descriptions for a cleaner signature line.
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Only the stdlib inventory — reliable and resolves types like pathlib.Path.
# nitpicky stays off (default), so unresolved third-party types (boto3,
# pydantic) are silently left unlinked rather than failing the strict build.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# MyST: enable the extensions the existing Markdown relies on, and generate
# anchors for headings up to h4 so in-page links like `strategies.md#image-sources`
# resolve under the strict (-W) build.
myst_enable_extensions = ["colon_fence", "deflist", "fieldlist", "tasklist"]
myst_heading_anchors = 4

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"{project} {release}"
