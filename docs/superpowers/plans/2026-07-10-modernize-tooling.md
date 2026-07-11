# ツーリング・CI モダン化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ja_sentence_segmenter の開発ツーリング(Poetry/black/flake8/mypy0.931/tox3)を 2026 年標準(uv/Ruff/mypy最新/tox4+tox-uv)に刷新し、テスト CI・PyPI 自動リリース・Dependabot を整備する。

**Architecture:** pyproject.toml を PEP 621 + uv_build に全面書き換えし、全ツール設定を pyproject.toml に集約する。コード側はフォーマッタ/リンターによる機械的変換のみ許容し、既存テストスイートを回帰の砦とする。CI は lint ジョブ + Python 3.9〜3.14 マトリクス(tox-uv 経由)で構成する。

**Tech Stack:** uv / uv_build / Ruff / mypy / bandit / pytest / tox 4 + tox-uv / poethepoet / pdoc / GitHub Actions / PyPI Trusted Publishing / Dependabot

**Spec:** `docs/superpowers/specs/2026-07-10-modernize-tooling-design.md`

## Global Constraints

- ライブラリ本体(`ja_sentence_segmenter/` 配下)の**挙動は変更しない**。機械的変換(ruff format / ruff --fix / pyupgrade)のみ許容し、変換後は必ず `uv run pytest` で全テスト成功を確認する。テストコードの期待値は変更しない
- `requires-python = ">=3.9"`、対象 Python は 3.9〜3.14
- バージョンは `0.1.0`
- `line-length = 160`(Ruff)
- ディレクトリ構成(フラットレイアウト)は変更しない
- 作業ブランチ: `feature-modernize-tooling`(作成済み。設計書コミットあり)
- コミットメッセージ末尾に `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` を付ける

---

### Task 1: pyproject.toml の PEP 621 化と uv 移行

**Files:**
- Modify: `pyproject.toml`(全面書き換え)
- Delete: `poetry.lock`, `setup.cfg`, `tox.ini`
- Create: `uv.lock`(`uv lock` で生成)

**Interfaces:**
- Consumes: なし(最初のタスク)
- Produces:
  - dependency group `test`(pytest, pytest-cov)と `dev`(test を include + ruff/mypy/bandit/tox/tox-uv/poethepoet/pdoc)
  - poe タスク: `lint` / `fmt` / `typecheck` / `test` / `bandit` / `pdoc`(Task 2, 5 が使用)
  - `[tool.tox]` env_list py39〜py314、runner = uv-venv-lock-runner(Task 3 の CI が使用)

- [ ] **Step 1: pyproject.toml を以下の内容に全面書き換え**

```toml
[project]
name = "ja_sentence_segmenter"
version = "0.1.0"
description = "sentence segmenter for japanese text"
authors = [{ name = "wwwcojp" }]
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.9"
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Text Processing",
    "Topic :: Text Processing :: General",
]
dependencies = []

[project.urls]
Homepage = "https://wwwcojp.github.io/ja_sentence_segmenter/ja_sentence_segmenter.html"
Repository = "https://github.com/wwwcojp/ja_sentence_segmenter"

[dependency-groups]
test = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
]
dev = [
    { include-group = "test" },
    "bandit>=1.8",
    "mypy>=1.15",
    "pdoc>=15.0",
    "poethepoet>=0.30",
    "ruff>=0.13",
    "tox>=4.21",
    "tox-uv>=1.25",
]

[build-system]
requires = ["uv_build>=0.11,<0.13"]
build-backend = "uv_build"

# フラットレイアウト(src/ なし)のため module-root を空にする
[tool.uv.build-backend]
module-root = ""

[tool.ruff]
line-length = 160

[tool.ruff.lint]
select = ["A", "B", "C4", "C90", "D", "E", "F", "I", "N", "RUF", "SIM", "UP", "W"]
# 日本語テキストを扱うライブラリのため、全角文字を「紛らわしい文字」として
# 検出する RUF001/002/003 は無効化する
ignore = ["RUF001", "RUF002", "RUF003"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pydocstyle]
convention = "numpy"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]

[tool.mypy]
files = ["ja_sentence_segmenter/**/*.py"]
strict = true
warn_unreachable = true
disallow_any_unimported = true
pretty = true
show_column_numbers = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test_"]
python_functions = ["test_*"]
addopts = "--strict-markers --strict-config --cov-report xml:cov.xml --cov ja_sentence_segmenter -vv"

[tool.coverage.run]
branch = true
omit = ["tests/*", "**/__init__.py"]

[tool.coverage.report]
skip_covered = false

[tool.tox]
requires = ["tox>=4.21", "tox-uv>=1.25"]
env_list = ["py39", "py310", "py311", "py312", "py313", "py314"]

[tool.tox.env_run_base]
description = "run unit tests"
runner = "uv-venv-lock-runner"
dependency_groups = ["test"]
commands = [["pytest"]]

[tool.poe.tasks]
lint = { shell = "ruff check . && ruff format --check .", help = "lint and check formatting with ruff" }
fmt = { shell = "ruff format . && ruff check --fix .", help = "format code and autofix lint issues" }
typecheck = { cmd = "mypy", help = "type check with mypy" }
test = { cmd = "pytest", help = "run tests with pytest" }
bandit = { cmd = "bandit -r ja_sentence_segmenter/", help = "analyze code using bandit" }
pdoc = { cmd = "pdoc -d numpy -o docs -t theme/ ja_sentence_segmenter/", help = "generate api documents using pdoc" }
```

補足(実装者向け):
- `License :: OSI Approved :: MIT License` classifier は意図的に削除している。PEP 639 の SPDX 式(`license = "MIT"`)と license classifier の併用は非推奨のため
- 実行時依存はゼロ(`dependencies = []`)。これは現状と同じ

- [ ] **Step 2: 旧ツールのファイルを削除**

```bash
git rm poetry.lock setup.cfg tox.ini
```

- [ ] **Step 3: ロックファイル生成と同期**

Run: `uv lock && uv sync`
Expected: `uv.lock` が生成され、`Resolved N packages` / `Installed N packages` で成功終了。エラーが出る場合は依存のバージョン floor が Python 3.9 で解決不能な可能性が高い(floor を1段下げて再試行)

- [ ] **Step 4: 既存テストが通ることを確認**

Run: `uv run pytest`
Expected: 全テスト PASS(既存 4 テストファイル)。カバレッジレポート `cov.xml` が生成される

- [ ] **Step 5: ビルドと py.typed 同梱確認**

Run:
```bash
uv build
uv run python -m zipfile -l dist/ja_sentence_segmenter-0.1.0-py3-none-any.whl | grep py.typed
```
Expected: sdist と wheel が `dist/` に生成され、grep が `ja_sentence_segmenter/py.typed` を出力する。**py.typed が含まれない場合は失敗** — `[tool.uv.build-backend]` の設定を確認すること

- [ ] **Step 6: tox のスモークテスト(1環境)**

Run: `uv run tox run -e py310`
Expected: uv が Python 3.10 を自動取得して環境構築し、pytest が PASS する

- [ ] **Step 7: コミット**

```bash
git add pyproject.toml uv.lock
git commit -m "build: migrate packaging from Poetry to uv (PEP 621, uv_build)

- rewrite pyproject.toml with PEP 621 [project] metadata, version 0.1.0
- requires-python >=3.9, classifiers 3.9-3.14
- dev deps as PEP 735 dependency groups; drop black/flake8/isort/dlint/safety/pip-licenses
- tox 4 + tox-uv config in [tool.tox] (native TOML); delete tox.ini
- delete poetry.lock (replaced by uv.lock) and empty setup.cfg

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Ruff / mypy / bandit を通す(コードの機械的現代化)

**Files:**
- Modify: `ja_sentence_segmenter/**/*.py`, `tests/**/*.py`(自動修正・再フォーマットのみ)

**Interfaces:**
- Consumes: Task 1 の poe タスク(`lint` / `typecheck` / `bandit` / `test`)と Ruff/mypy 設定
- Produces: `uv run poe lint` / `uv run poe typecheck` / `uv run poe bandit` がすべて成功する状態(Task 3 の CI lint ジョブ、Task 5 の統合検証が前提とする)

- [ ] **Step 1: 現状の違反を確認**

Run: `uv run ruff check .`
Expected: いくつかの違反が報告される(UP 系の古い typing 構文などが典型)。件数と内容を控えておく

- [ ] **Step 2: 自動修正と再フォーマットを適用**

```bash
uv run ruff check --fix .
uv run ruff format .
```
Expected: UP 系(`typing.List` → `list` 等)や import 整列が自動修正される。line-length 160 のためフォーマット差分は小さいはず

- [ ] **Step 3: 残った違反を手動で解消**

Run: `uv run ruff check .` を再実行し、残件があれば以下の決定ルールで対応する:

| ルール | 対応 |
|---|---|
| `D`(docstring) | 不足していれば処理内容を1行で説明する docstring を追加(挙動に影響なし) |
| `B` / `SIM` / `C4` | 提案どおりの書き換えが**明らかに等価**な場合のみ適用。等価性に少しでも疑いがあれば、書き換えずに行末へ `# noqa: <ルールID>` を付け、その行の直前に理由コメントを書く |
| `N`(命名) | 公開 API の名前は**変更しない**(破壊的変更になる)。該当したら `# noqa: N###` + 理由コメント |
| その他 | 機械的に直せるものは直す。挙動が変わりうるものは `# noqa` + 理由コメント |

Expected: 最終的に `uv run ruff check .` と `uv run ruff format --check .` がともにエラーゼロ

- [ ] **Step 4: mypy を通す**

Run: `uv run poe typecheck`
Expected: エラーゼロ。旧設定は strict 相当だったため大きな問題は出ない見込み。エラーが出た場合は型注釈の追加・修正のみで対応する(実行時の挙動を変える修正は不可。どうしても必要なら `# type: ignore[<code>]` + 理由コメント)

- [ ] **Step 5: bandit を通す**

Run: `uv run poe bandit`
Expected: `No issues identified.`(旧 bandit でも通っていたコードのため)

- [ ] **Step 6: 回帰がないことを確認**

Run: `uv run poe test`
Expected: 全テスト PASS。**1件でも失敗したら Step 2〜4 の変更のどれかが挙動を変えている** — `git diff` で該当箇所を特定し、その変更を元に戻して `# noqa` 対応に切り替える

- [ ] **Step 7: コミット**

```bash
git add ja_sentence_segmenter/ tests/
git commit -m "style: apply ruff autofixes and formatting, satisfy mypy strict

Mechanical modernization only (pyupgrade rewrites, import sorting,
formatting). No behavior change; verified by existing test suite.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(コード変更が一切発生しなかった場合はこのコミットは不要。Step 6 まで確認できていればタスク完了とする)

---

### Task 3: GitHub Actions と Dependabot の整備

**Files:**
- Create: `.github/workflows/test.yml`
- Modify: `.github/workflows/gh-pages.yml`(全面書き換え)
- Create: `.github/workflows/release.yml`
- Create: `.github/dependabot.yml`
- Modify: `.gitignore`(`/_site` を追加)

**Interfaces:**
- Consumes: Task 1 の `[tool.tox]` 設定(test ジョブが `tox run -e py` で使用)、dependency group `dev`(lint ジョブが使用)
- Produces: PR で lint + 3.9〜3.14 マトリクスが走る CI、`v*` タグで PyPI 公開する release ワークフロー

- [ ] **Step 1: `.github/workflows/test.yml` を作成**

```yaml
name: Test

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.13"
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Ruff lint
        run: uv run ruff check .
      - name: Ruff format check
        run: uv run ruff format --check .
      - name: Type check
        run: uv run mypy
      - name: Bandit
        run: uv run bandit -r ja_sentence_segmenter/

  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: ${{ matrix.python-version }}
          enable-cache: true
      - name: Run tests via tox
        run: uvx --with tox-uv tox run -e py
```

補足: `tox run -e py` は「実行中のインタプリタに一致する環境」を選ぶため、matrix の Python がそのまま使われる。tox 定義(pyproject.toml の `[tool.tox]`)がローカルと CI の単一ソースになる

- [ ] **Step 2: `.github/workflows/gh-pages.yml` を以下に全面書き換え**

```yaml
name: GitHub Pages

on:
  push:
    branches:
      - main
  pull_request:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.13"
      - name: Build API docs
        run: uvx pdoc -d numpy -o _site -t theme/ ja_sentence_segmenter/
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

補足: 出力先を `docs/` ではなく `_site/` にするのは意図的(`docs/superpowers/` の設計文書を公開サイトに含めないため)。ローカルの `poe pdoc` タスクは従来どおり `docs/` に出力するが、そちらは gitignore 済み

- [ ] **Step 3: `.github/workflows/release.yml` を作成**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Build distributions
        run: uv build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

補足: API トークンは不要(Trusted Publishing / OIDC)。PyPI 側での trusted publisher 登録が別途必要(Task 5 の PR 本文に手順を記載する)

- [ ] **Step 4: `.github/dependabot.yml` を作成**

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

- [ ] **Step 5: `.gitignore` に `_site` を追加**

`.gitignore` の以下の箇所:

```
# generated documentation (pdoc output), except committed specs
/docs/*
!/docs/superpowers/
```

を次のように変更:

```
# generated documentation (pdoc output), except committed specs
/docs/*
!/docs/superpowers/
/_site
```

- [ ] **Step 6: ワークフローの検証(ローカルでできる範囲)**

```bash
uvx yamllint -d relaxed .github/workflows/ .github/dependabot.yml
uvx pdoc -d numpy -o _site -t theme/ ja_sentence_segmenter/
ls _site/ja_sentence_segmenter.html
rm -rf _site
```
Expected: yamllint がエラーゼロ(warning は許容)、pdoc が `_site/ja_sentence_segmenter.html` を生成する

- [ ] **Step 7: コミット**

```bash
git add .github/ .gitignore
git commit -m "ci: add test/release workflows, modernize gh-pages, add dependabot

- test.yml: ruff/mypy/bandit lint job + tox matrix on Python 3.9-3.14
- gh-pages.yml: ubuntu-latest, official Pages actions, pdoc via uvx
- release.yml: publish to PyPI via trusted publishing on v* tags
- dependabot: weekly updates for uv.lock and GitHub Actions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: README / CHANGELOG の更新

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 の poe タスク名(`lint` / `typecheck` / `test`)、Task 3 のワークフロー名(バッジ URL)
- Produces: なし(最終成果物)

- [ ] **Step 1: README にバッジを追加**

`README.md` の先頭行:

```markdown
# ja_sentence_segmenter
```

を次のように変更:

```markdown
# ja_sentence_segmenter

[![Test](https://github.com/wwwcojp/ja_sentence_segmenter/actions/workflows/test.yml/badge.svg)](https://github.com/wwwcojp/ja_sentence_segmenter/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/ja-sentence-segmenter)](https://pypi.org/project/ja-sentence-segmenter/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ja-sentence-segmenter)](https://pypi.org/project/ja-sentence-segmenter/)
```

- [ ] **Step 2: Prerequisites を更新**

`README.md` の:

```markdown
### Prerequisites
* Python 3.6+
```

を次のように変更:

```markdown
### Prerequisites
* Python 3.9+
```

- [ ] **Step 3: Development セクションを追加**

`README.md` の `## Versioning` セクションの直前に以下を挿入:

```markdown
## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
git clone https://github.com/wwwcojp/ja_sentence_segmenter.git
cd ja_sentence_segmenter
uv sync

uv run poe lint       # lint and format check (ruff)
uv run poe typecheck  # type check (mypy)
uv run poe test       # run tests (pytest)
uv run tox            # run tests on all supported Python versions
```
```

- [ ] **Step 4: CHANGELOG に 0.1.0 エントリを追加**

`CHANGELOG.md` の:

```markdown
## [Unreleased]
```

の直後に以下を挿入:

```markdown

## [0.1.0] 2026-07-10
### Changed
- Drop support for Python 3.6-3.8 (minimum supported version is now 3.9); add support for Python 3.10-3.14
- Migrate packaging from Poetry to [uv](https://docs.astral.sh/uv/) (PEP 621 metadata, uv_build backend)
- Replace black/flake8/isort/pep8-naming/dlint with [Ruff](https://docs.astral.sh/ruff/); update mypy/bandit/pytest to latest
- Migrate to tox 4 + tox-uv (config in pyproject.toml)

### Added
- CI workflow: lint + test matrix on Python 3.9-3.14
- Automated PyPI release via trusted publishing on version tags
- Dependabot for dependency and GitHub Actions updates

### Removed
- safety (replaced by Dependabot) and pip-licenses
```

- [ ] **Step 5: コミット**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: update README and CHANGELOG for tooling modernization

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: 統合検証と PR 作成

**Files:**
- なし(検証と PR 作成のみ)

**Interfaces:**
- Consumes: Task 1〜4 のすべての成果物
- Produces: レビュー可能な PR(検証基準をすべて満たした状態)

- [ ] **Step 1: 検証基準(スペックの「完了の定義」)を全件実行**

```bash
uv sync
uv run poe lint
uv run poe typecheck
uv run poe bandit
uv run poe test
rm -rf dist && uv build
uv run python -m zipfile -l dist/ja_sentence_segmenter-0.1.0-py3-none-any.whl | grep py.typed
uvx pdoc -d numpy -o _site -t theme/ ja_sentence_segmenter/ && rm -rf _site
```
Expected: すべて成功。1つでも失敗したら該当タスクに戻って修正してから再実行

- [ ] **Step 2: tox 全環境の実行**

Run: `uv run tox`
Expected: py39〜py314 の全環境で PASS(uv が各 Python を自動取得する。ネットワーク制約等で一部バージョンが取得できない場合は、取得できた環境がすべて PASS していることを確認し、PR 本文にその旨を記載する)

- [ ] **Step 3: push して PR 作成**

```bash
git push -u origin feature-modernize-tooling
gh pr create --title "Modernize tooling and CI (uv / Ruff / tox 4 / trusted publishing)" --body "$(cat <<'EOF'
## Summary
- Poetry → uv(PEP 621 / uv_build / uv.lock)、Python サポートを 3.9〜3.14 に更新(3.6〜3.8 は終了)、バージョン 0.1.0
- black + flake8 プラグイン群 + isort + dlint → Ruff に集約(bandit は継続)、mypy を最新化(strict)
- tox 4 + tox-uv(設定は pyproject.toml に集約)
- CI 新設: lint + Python 3.9〜3.14 マトリクス。gh-pages を公式 Pages アクション方式に更新。v* タグで PyPI へ trusted publishing する release ワークフローを追加。Dependabot 導入(safety の代替)
- ライブラリ本体の挙動は不変(機械的変換のみ、既存テストで確認済み)

詳細設計: docs/superpowers/specs/2026-07-10-modernize-tooling-design.md

## マージ後に必要な手動作業
1. **PyPI Trusted Publisher 登録**: PyPI の ja-sentence-segmenter プロジェクト設定 → Publishing → GitHub リポジトリ `wwwcojp/ja_sentence_segmenter`、workflow `release.yml`、environment `pypi` で登録
2. **GitHub Pages のソース変更**: Settings → Pages → Source を「GitHub Actions」に変更

## Test plan
- [ ] CI の lint ジョブが green
- [ ] CI の test マトリクス(3.9〜3.14)が全 green
- [ ] gh-pages の build ジョブが green

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: PR が作成され URL が表示される

- [ ] **Step 4: CI の結果を確認**

Run: `gh pr checks --watch`
Expected: 全ジョブ green。落ちたジョブがあればログを確認し(`gh run view <id> --log-failed`)、該当タスクの修正 → push → 再確認
