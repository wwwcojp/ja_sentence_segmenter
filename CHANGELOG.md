# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] 2026-07-25
### Added
- `concatenate_matching`: new `max_concatenate_length` parameter, an opt-in bound on the accumulated concatenation. It defaults to `None`, so **existing behaviour is unchanged unless you set it**.

  Without a bound, `former_matching_rule` is re-applied to an ever growing accumulation and the accumulation is rebuilt on every input line; both costs grow with the accumulated length, so the total work is quadratic in the input size — a 1.8MB input pins a CPU core for 30 seconds, and larger inputs scale as the square. Set this parameter when segmenting untrusted text.

  Setting it changes the output by more than split positions. At a bound boundary neither matching rule is evaluated, so text that `remove_former_matched` or `remove_latter_matched` would have stripped survives into the output there, and an accumulation may be broken between an opening bracket and its closing one, which stops `split_punctuation` from protecting the punctuation inside it. The bound is also soft: it is only checked after an accumulation has been concatenated at least once, so an accumulation may exceed it by the length of the line that started it plus one more line. See the docstring for details.

### Fixed
- `concatenate_matching`: accept `str` input. The signature declared it but the dispatch had no `str` branch, so a `str` argument silently yielded nothing. A `str` is treated as one indivisible line and is never split — split it into lines first, e.g. with `split_newline`.
- `concatenate_matching`: raise `TypeError` instead of silently yielding nothing when `arg` is neither a `str`, a `list` nor an `Iterator`. Passing a tuple, a set or `dict.keys()` previously discarded the entire input with no error.

### Changed
- `concatenate_matching`: compile the matching rules once per call instead of on every input line (about 17% faster on large inputs).

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
