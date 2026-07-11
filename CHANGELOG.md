# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] 2026-07-10
### Changed
- Drop support for Python 3.6-3.8 (minimum supported version is now 3.9); add support for Python 3.11-3.14
- Migrate packaging from Poetry to [uv](https://docs.astral.sh/uv/) (PEP 621 metadata, uv_build backend)
- Replace black/flake8/isort/pep8-naming/dlint with [Ruff](https://docs.astral.sh/ruff/); update mypy/bandit/pytest to latest
- Migrate to tox 4 + tox-uv (config in pyproject.toml)

### Added
- CI workflow: lint + test matrix on Python 3.9-3.14
- Automated PyPI release via trusted publishing on version tags
- Dependabot for dependency and GitHub Actions updates

### Removed
- safety (replaced by Dependabot) and pip-licenses

## [0.0.2] 2020-02-23
### Added
- add py.typed for [PEP 561](https://www.python.org/dev/peps/pep-0561/#id18)

## [0.0.1] 2019-12-15
Initial Release
