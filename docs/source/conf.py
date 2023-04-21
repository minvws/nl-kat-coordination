# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import subprocess

branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8")
commit_date = subprocess.check_output(["git", "log", "--format=#%h %cs", "-n 1"]).decode("utf-8")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "OpenKAT"
copyright = "Ministerie van Volksgezondheid, Welzijn en Sport (European Union Public License 1.2)"
author = "The OpenKAT team"
version = branch + commit_date
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosectionlabel",
    "sphinx_rtd_theme",
    "myst_parser",
    "sphinxcontrib.mermaid",
    "sphinx_multiversion",
]

myst_enable_extensions = ["tasklist"]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"

html_logo = "_static/keiko-hero.jpg"
html_favicon = "_static/favicon.svg"

html_theme_options = {
    "collapse_navigation": False,
    "style_nav_header_background": "#ca005d",
}

html_context = {
    "display_github": True,
    "github_user": "minvws",
    "github_repo": "nl-kat-coordination",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

html_static_path = ["_static"]
html_css_files = [
    "openkat.css",
]

mermaid_version = ""  # Do not fetch from the CDN
html_js_files = [
    "mermaid-9.4.3.min.js",
]


# Whitelist pattern for tags (set to None to ignore all tags)
smv_tag_whitelist = r"^.*$"

# Whitelist pattern for branches (set to None to ignore all branches)
smv_branch_whitelist = None

# Whitelist pattern for remotes (set to None to use local branches only)
smv_remote_whitelist = r"^.*$"

# Pattern for released versions
smv_released_pattern = r"^tags/.*$"

# Determines whether remote or local git branches/tags are preferred if their output dirs conflict
smv_prefer_remote_refs = True
