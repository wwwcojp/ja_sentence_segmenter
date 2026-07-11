# ja_sentence_segmenter ツーリング・CI モダン化 設計書

作成日: 2026-07-10

## 背景と目的

本リポジトリは 2020〜2022 年ごろのツールセット(Poetry 旧形式、black + flake8 プラグイン群、
mypy 0.931、tox 3、非推奨ランナー/アクションを使う CI)で構成されている。
これを 2026 年時点の標準的なツールセットに刷新し、開発・テスト・リリースの体験を現代化する。

**ライブラリ本体(`ja_sentence_segmenter/` 配下)のコードの挙動は変更しない。**
変更はツーリング、設定、CI、ドキュメントに限定する。
ただしフォーマッタ・リンター(pyupgrade 等)による機械的なコード変換は許容する
(挙動が変わらないことをテストで確認する)。

## スコープ

- 対象: パッケージ管理、リンター/フォーマッター、型チェック、テスト環境、
  GitHub Actions(テスト CI 新設・gh-pages 更新・PyPI リリース自動化新設)、
  Dependabot、README/CHANGELOG/.gitignore
- 対象外: ライブラリの機能追加・仕様変更、pre-commit の導入、docs テーマ(`theme/`)の変更

## 決定事項サマリ

| 項目 | 現行 | 移行後 |
|---|---|---|
| Python サポート | ^3.6.2 | >=3.9(3.9〜3.14) |
| パッケージ管理 | Poetry(旧形式) | uv |
| ビルドバックエンド | poetry.masonry.api | uv_build |
| メタデータ | [tool.poetry] | PEP 621 [project] |
| 開発依存 | [tool.poetry.group.dev] | [dependency-groups] dev(PEP 735) |
| ロックファイル | poetry.lock | uv.lock |
| フォーマッター | black | ruff format |
| リンター | flake8 + プラグイン5種 + flake518 + isort + pep8-naming + dlint | Ruff |
| セキュリティ静的解析 | bandit 1.7 | bandit 最新(維持) |
| 型チェック | mypy 0.931(個別フラグ) | mypy 最新(strict = true) |
| マルチバージョンテスト | tox 3(tox.ini) | tox 4 + tox-uv(pyproject.toml 内 [tool.tox]) |
| 脆弱性スキャン | safety | GitHub Dependabot |
| ライセンス一覧 | pip-licenses | 廃止(実行時依存ゼロのため) |
| タスクランナー | poethepoet | poethepoet(維持) |
| API ドキュメント | pdoc | pdoc(維持、uvx 実行) |
| テスト CI | なし | test.yml 新設(lint + 3.9〜3.14 マトリクス) |
| gh-pages CI | ubuntu-20.04 / actions v2 / peaceiris | ubuntu-latest / actions v4 系 / GitHub 公式 Pages アクション |
| PyPI リリース | 手動 | release.yml(v* タグ → Trusted Publishing) |
| バージョン | 0.0.2 | 0.1.0(3.6〜3.8 サポート終了を含むため) |

## セクション1: パッケージ管理・プロジェクト定義

### pyproject.toml の PEP 621 化

- `[project]` テーブルに name / version = "0.1.0" / description / authors / readme /
  license = "MIT"(SPDX 式)/ urls(homepage, repository)を移行
- `requires-python = ">=3.9"`
- classifiers を Python 3.9〜3.14 に更新。`Development Status :: 4 - Beta` は維持
- `py.typed` の同梱を維持(uv_build はパッケージ内の py.typed を自動で含めるため、
  追加設定なしで PEP 561 対応が保たれることをビルド成果物で確認する)
- `[build-system]` は `uv_build` に変更。uv_build のデフォルトは src レイアウトのため、
  現行のフラットレイアウトを維持する設定(`[tool.uv.build-backend] module-root = ""`)を入れる
  (ディレクトリ構成は変更しない)
- `poetry.lock` を削除し `uv.lock` を生成・コミット
- 空ファイルの `setup.cfg` を削除

### 開発依存([dependency-groups] dev)

ruff / mypy / bandit / pytest / pytest-cov / tox / tox-uv / poethepoet / pdoc をいずれも最新版で指定。
black, flake8 系一式, flake518, isort, pep8-naming, dlint, safety, pip-licenses は削除。

## セクション2: リント・型チェック・テスト

### Ruff([tool.ruff])

- `line-length = 160`(現行踏襲。日本語テキストや正規表現を多用するため意図的に広くする)
- `[tool.ruff.lint]` select:
  - `E, W, F`(pycodestyle / pyflakes)
  - `I`(isort 相当)
  - `N`(pep8-naming 相当)
  - `D`(pydocstyle。`[tool.ruff.lint.pydocstyle] convention = "numpy"`)
  - `A`(flake8-builtins 相当)
  - `C90`(mccabe。max-complexity = 10)
  - `UP`(pyupgrade。requires-python 3.9 準拠の構文へ現代化)
  - `B`(bugbear)
  - `C4`(comprehensions)
  - `SIM`(simplify)
  - `RUF`(Ruff 固有)
- `tests/` は per-file-ignores で `D`(docstring 必須)を除外(現行 flake8 の exclude 踏襲)
- フォーマットは `ruff format`(black 互換)

### mypy([tool.mypy])

- `strict = true` に集約し、strict に含まれない現行の `warn_unreachable = true` と
  `disallow_any_unimported = true` は明示的に維持
- `pretty = true` を追加
- 対象は現行同様 `ja_sentence_segmenter/**/*.py` のみ

### bandit

- 最新版に更新。poe タスク `bandit -r ja_sentence_segmenter/` を維持

### pytest([tool.pytest.ini_options])

- testpaths / python_files / python_classes / python_functions / カバレッジ出力(cov.xml)は現行踏襲
- `-p no:cacheprovider` を削除(キャッシュ有効化)
- `--strict-markers --strict-config` を追加
- `[tool.coverage]` 設定は現行踏襲

### tox([tool.tox] を pyproject.toml 内に記述)

- tox 4(4.21+ のネイティブ TOML 形式)+ tox-uv
- `env_list = py39, py310, py311, py312, py313, py314`
- 各環境で dev グループの pytest / pytest-cov を使いテスト実行
- `tox.ini` は削除

### poe タスク([tool.poe.tasks])

- `lint`: ruff check + ruff format --check
- `fmt`: ruff format + ruff check --fix
- `typecheck`: mypy
- `test`: pytest
- `bandit`: 現行踏襲
- `pdoc`: 現行踏襲(`pdoc -d numpy -o docs -t theme/ ja_sentence_segmenter/`)
- `safety` タスクは削除

## セクション3: CI・リリース・ドキュメント

### .github/workflows/test.yml(新設)

- トリガー: main への push、および PR
- **lint ジョブ**: `astral-sh/setup-uv` → `uv sync` → ruff check / ruff format --check /
  mypy / bandit を実行
- **test ジョブ**: matrix で Python 3.9〜3.14。各ランナーで tox(tox-uv 経由)の
  該当環境を実行し、ローカルと CI のテスト定義を一元化する

### .github/workflows/gh-pages.yml(更新)

- `ubuntu-latest` / `actions/checkout@v4` 系に更新
- pdoc は `uvx pdoc` で実行(ビルド内容は現行と同一)。ただし出力先は `docs/` ではなく
  ワークフロー内の一時ディレクトリ(例: `_site/`)にし、`docs/superpowers/` の設計書が
  公開サイトに混入しないようにする
- デプロイを peaceiris/actions-gh-pages から GitHub 公式方式
  (`actions/upload-pages-artifact` + `actions/deploy-pages`)へ変更
- 現行同様、ビルドは PR でも実行し、デプロイは main への push 時のみ

### .github/workflows/release.yml(新設)

- トリガー: `v*` タグの push
- `uv build` で sdist / wheel を作成 → `pypa/gh-action-pypi-publish` で PyPI へ公開
- 認証は Trusted Publishing(OIDC、`permissions: id-token: write`)。API トークン不要

### .github/dependabot.yml(新設)

- `uv` エコシステム(uv.lock の依存更新)と `github-actions` を週次でチェック
- safety の代替として機能する

### ドキュメント・その他

- README: Prerequisites を「Python 3.9+」に更新、開発手順を uv ベースに記載、
  CI ステータスバッジと PyPI バージョンバッジを追加
- CHANGELOG: `[0.1.0]` として今回の変更(ツーリング刷新、Python 3.6〜3.8 サポート終了)を記載
- .gitignore: `.ruff_cache/` を追加。`docs/` の ignore を `/docs/*` + `!/docs/superpowers/` に
  変更し、pdoc 生成物は除外しつつ本設計書をコミット可能にする(実施済み)

## 手動作業(ユーザーによる1回限りの設定)

1. **PyPI Trusted Publisher 登録**: PyPI の ja_sentence_segmenter プロジェクト設定 →
   Publishing → GitHub リポジトリ `wwwcojp/ja_sentence_segmenter`、
   ワークフロー `release.yml` を trusted publisher として登録
2. **GitHub Pages のソース変更**: リポジトリ Settings → Pages → Source を
   「GitHub Actions」に変更(公式 Pages アクション方式への切り替えに伴う)

## 移行手順(一括移行・単一ブランチ)

`feature-modernize-tooling` ブランチ上で以下の順にコミットし、1つの PR でマージする。

1. pyproject.toml の PEP 621 化 + uv 移行(poetry.lock / setup.cfg 削除、uv.lock 生成)
2. Ruff 導入(旧リンター群の設定・依存を削除、自動修正・再フォーマット適用)
3. mypy 最新化(strict 化、エラーが出れば型注釈を修正)
4. tox 4 + tox-uv(pyproject 内 [tool.tox]、tox.ini 削除)
5. CI ワークフロー(test.yml 新設、gh-pages.yml 更新、release.yml 新設、dependabot.yml 新設)
6. README / CHANGELOG 更新

## 検証基準(完了の定義)

- `uv sync` が成功し、`uv.lock` がコミットされている
- `uv run poe lint` / `uv run poe typecheck` / `uv run poe bandit` がすべて成功する
- `uv run poe test` で既存テストが全件成功する(テストコードの期待値は変更しない)
- `uv run tox`(ローカルにあるバージョンのみでも可)が成功する
- `uv build` で sdist / wheel が作成でき、wheel に `py.typed` が含まれている
- `uvx pdoc -d numpy -o docs -t theme/ ja_sentence_segmenter/` が成功する
- PR 上で test.yml の全ジョブ(lint + 3.9〜3.14)が green になる
