# concatenate_matching の DoS 対策と str 入力修正 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `concatenate_matching` の累積結合に上限を設けて二次時間の DoS を解消し、あわせて `str` 入力が黙って空を返す不整合を直す。

**Architecture:** `__concatenate_matching_iter` のループ先頭、正規表現マッチより前に上限チェックを1つ挿入する。「現在の累積で結合が起きたか」を表す `concatenated` フラグを併用し、各累積が上限で打ち切られる前に必ず1回は `former_matching_rule` の評価を受けることを保証する。マッチの意味論そのものには一切手を触れないため、既存テストは無改変で通る。

**Tech Stack:** Python 3.9+ / uv / Ruff / mypy (strict) / pytest

設計の根拠、採用しなかった案、実測値は `docs/superpowers/specs/2026-07-25-concatenator-dos-fix-design.md` にある。

## Global Constraints

- 対象ファイルは `ja_sentence_segmenter/concatenate/simple_concatenator.py` とそのテストのみ。他モジュールには触れない
- **既存テストのアサーションは1文字も変更しない。** 無変更で通ることが「意味論を壊していない」証拠になる
- `requires-python = ">=3.9"` のため `int | None` は使えない。`Optional[int]` / `Union[...]` を使う
- 行長は 160（`[tool.ruff] line-length = 160`）
- 循環的複雑度は 10 まで（`[tool.ruff.lint.mccabe] max-complexity = 10`）
- mypy は `strict = true` かつ `warn_unreachable = true`。**ディスパッチを1つの `yield from` にまとめて `else: return` を書くと `warn_unreachable` に弾かれる。** 他3関数と同じく3分岐それぞれに `yield from` を書く
- docstring は numpy convention（`[tool.ruff.lint.pydocstyle] convention = "numpy"`）。`tests/**` は D ルール免除
- 各タスクの最後に `uv run poe lint`、`uv run poe typecheck`、`uv run poe test` がすべて通ること

## File Structure

| ファイル | 役割 | 操作 |
| --- | --- | --- |
| `ja_sentence_segmenter/concatenate/simple_concatenator.py` | 上限機構と `str` ディスパッチの追加 | 変更 |
| `tests/concatenate/test_simple_concatenator.py` | 新規テスト関数の追加（既存関数は無変更） | 変更 |
| `CHANGELOG.md` | `[Unreleased]` への追記 | 変更 |
| `pyproject.toml` | `[project]` の `version` | 変更 |

新規ファイルはない。`simple_concatenator.py` は変更後も 156 行程度で、分割は不要。

## タスク一覧

| # | 内容 | 完了時に落ちるテスト |
| --- | --- | --- |
| 1 | 上限機構の導入 | Task 2・3 のテストが落ちる（想定どおり） |
| 2 | 初回評価の保証（`concatenated` フラグ） | Task 3 のテストが落ちる |
| 3 | `str` 入力への対応 | なし |
| 4 | CHANGELOG とバージョン | なし |

---

### Task 1: 上限機構の導入

**Files:**
- Modify: `ja_sentence_segmenter/concatenate/simple_concatenator.py`
- Test: `tests/concatenate/test_simple_concatenator.py`

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces:
  - `DEFAULT_MAX_CONCATENATE_LENGTH: int` = `10000`（モジュール定数）
  - `concatenate_matching(..., max_concatenate_length: Optional[int] = DEFAULT_MAX_CONCATENATE_LENGTH) -> Generator[str, None, None]`
  - `__concatenate_matching_iter(texts, former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length)` — 第6引数を末尾に追加、既定値なし

- [ ] **Step 1: テストファイルの先頭に pytest の import を追加する**

`tests/concatenate/test_simple_concatenator.py` の1行目を次に差し替える。現在は `from ja_sentence_segmenter.concatenate import simple_concatenator` の1行だけである。

```python
import pytest

from ja_sentence_segmenter.concatenate import simple_concatenator

RULE_NO = r"^(?P<result>.+)(の)$"
```

`RULE_NO` は既存の `test_concatenate_matching` では使わない。既存のアサーションは正規表現をリテラルで書いたまま変更しない。

- [ ] **Step 2: 失敗するテストを書く**

`tests/concatenate/test_simple_concatenator.py` の末尾に追記する。

```python
def test_concatenate_matching_max_concatenate_length() -> None:
    texts = ["あの"] * 100

    # 上限に達したら打ち切って次の累積を始める
    result = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False, max_concatenate_length=10)
    )
    assert len(result) == 20
    assert max(len(chunk) for chunk in result) == 10
    # テキストの欠落がない
    assert "".join(result) == "".join(texts)

    # None を渡すと従来どおり無制限
    assert list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False, max_concatenate_length=None)
    ) == ["".join(texts)]


def test_concatenate_matching_max_concatenate_length_validation() -> None:
    # concatenate_matching はジェネレータ関数なので、ValueError は呼び出し時点ではなく
    # 最初の next() で送出される。list() で消費して検証する。
    for invalid in (0, -1):
        with pytest.raises(ValueError, match="max_concatenate_length must be positive or None"):
            list(simple_concatenator.concatenate_matching(["あの"], max_concatenate_length=invalid))


def test_concatenate_matching_does_not_blow_up_on_large_input() -> None:
    # 上限がないと再帰的な再走査で二次時間になり、この入力で30秒かかる。
    # 実時間ではなくチャンク数で検証する（CI の負荷変動に左右されないため）。
    # 二次時間が復活した場合はテスト自体がタイムアウトして検出される。
    texts = ["あの"] * 300000
    result = list(simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False))
    assert len(result) == 60
    assert "".join(result) == "".join(texts)
```

- [ ] **Step 3: テストが失敗することを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py -v --no-cov
```

期待: 新規3件が `TypeError: concatenate_matching() got an unexpected keyword argument 'max_concatenate_length'` で FAIL。既存の `test_concatenate_matching` は PASS。

- [ ] **Step 4: モジュール定数を追加する**

`ja_sentence_segmenter/concatenate/simple_concatenator.py` の import 直後（5行目 `from typing import Optional, Union, overload` の次）に空行を挟んで追加する。

```python
DEFAULT_MAX_CONCATENATE_LENGTH = 10000
"""default soft upper bound on the accumulated length."""
```

`simple_splitter.py` の `DEFAULT_PUNCTUATION_REGEX` と同じ流儀である。

- [ ] **Step 5: プライベート関数のシグネチャに引数を追加する**

現在の定義（1行にまとまっている）を次の複数行の形に差し替える。引数追加で 160 文字を超えるため `ruff format` が折り返す形に合わせる。

```python
def __concatenate_matching_iter(
    texts: Iterator[str],
    former_matching_rule: Optional[str],
    latter_matching_rule: Optional[str],
    remove_former_matched: bool,
    remove_latter_matched: bool,
    max_concatenate_length: Optional[int],
) -> Generator[str, None, None]:
```

- [ ] **Step 6: 上限チェックをループ先頭に挿入する**

`for latter in texts:` の直後、`former_match_obj = ...` の直前に挿入する。

```python
        for latter in texts:
            if max_concatenate_length is not None and len(former) >= max_concatenate_length:
                yield former
                former = latter
                continue

            former_match_obj = re.match(former_matching_rule, former) if former_matching_rule else None
```

マッチより **前** に置くことが要件である。マッチの後に置くと、上限を超えた回のスキャンコストがすでに発生してしまう。

`max_concatenate_length is not None` と明示比較する。`if max_concatenate_length and ...` と書くと `0` が「上限なし」に落ちてしまい、Step 8 の `ValueError` と矛盾する。

- [ ] **Step 7: 2つの `@overload` と公開関数のシグネチャに引数を追加する**

`@overload` は2つ（`list[str]` と `Iterator[str]`）ある。両方と、実体の `def concatenate_matching(` の3箇所すべてで、`remove_latter_matched: bool = True,` の次の行に追加する。

```python
    max_concatenate_length: Optional[int] = DEFAULT_MAX_CONCATENATE_LENGTH,
```

- [ ] **Step 8: docstring に引数と Raises を追記する**

`remove_latter_matched` の説明の最後（2つ目の `e.g. r"^(\s*[>]+\s*)(?P<result>.+)$"` の行）の直後、`Yields` セクションの前に挿入する。

```
    max_concatenate_length : Optional[int], optional
        soft upper bound on the length of an accumulation,
        by default DEFAULT_MAX_CONCATENATE_LENGTH.
        without a bound the matching rule is re-applied to an ever growing
        accumulation, which costs quadratic time in the size of the input.
        once an accumulation reaches this length it is yielded as is and a new
        accumulation starts, so no text is lost and no exception is raised.
        None disables the bound. must be positive if not None.

    Raises
    ------
    ValueError
        if max_concatenate_length is not None and not positive.
        raised on the first iteration, not at call time, because this is a
        generator function.
```

- [ ] **Step 9: 引数の検証とディスパッチへの受け渡しを実装する**

docstring 直後の本体を次に差し替える。

```python
    if max_concatenate_length is not None and max_concatenate_length <= 0:
        msg = f"max_concatenate_length must be positive or None, got {max_concatenate_length}"
        raise ValueError(msg)

    if isinstance(arg, list):
        yield from __concatenate_matching_iter(
            iter(arg), former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length
        )
    elif isinstance(arg, Iterator):
        yield from __concatenate_matching_iter(
            arg, former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length
        )
```

`else: return` を足してはいけない。`Union` が網羅されているため `warn_unreachable = true` に弾かれる。

- [ ] **Step 10: テストが通ることを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py -v --no-cov
```

期待: 4件すべて PASS。`test_concatenate_matching_does_not_blow_up_on_large_input` は 1 秒前後で完走する（修正前は30秒かかっていた）。

- [ ] **Step 11: 品質ゲートを通す**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

期待: `All checks passed!` / `already formatted` / `Success: no issues found in 9 source files` / 全テスト PASS。

- [ ] **Step 12: コミット**

```bash
git add ja_sentence_segmenter/concatenate/simple_concatenator.py tests/concatenate/test_simple_concatenator.py
git commit -m "fix: bound the accumulation in concatenate_matching

The former matching rule was re-run over an unboundedly accumulated
buffer once per input line, making the loop quadratic in the input size.
A 900KB input pinned a CPU core for 30 seconds.

Add max_concatenate_length, checked before the regex runs so the buffer
handed to re.match is bounded. Total work becomes linear in the input."
```

---

### Task 2: 初回評価の保証

**Files:**
- Modify: `ja_sentence_segmenter/concatenate/simple_concatenator.py`
- Test: `tests/concatenate/test_simple_concatenator.py`

**Interfaces:**
- Consumes: Task 1 の `DEFAULT_MAX_CONCATENATE_LENGTH`、`max_concatenate_length` 引数、`__concatenate_matching_iter` の6引数シグネチャ
- Produces: シグネチャの変更なし。振る舞いの不変条件のみ追加

Task 1 の上限チェックには穴がある。**累積の最初の行がすでに上限以上の長さだった場合、`former_matching_rule` が一度も評価されないまま素通りする。** `remove_former_matched` による除去も起きない。これは「余分に分割されるだけ」では済まない振る舞いの変更である。

- [ ] **Step 1: 失敗するテストを書く**

`tests/concatenate/test_simple_concatenator.py` の末尾に追記する。

```python
def test_concatenate_matching_applies_former_rule_to_oversized_first_line() -> None:
    # 1行目が単独で上限を超えていても former_matching_rule は評価されなければならない。
    # 上限は累積の伸びを止めるものであって、まだ一度も処理されていない行の処理を
    # 拒否するものではない。
    texts = ["あ" * 19999 + "の", "願いは"]

    bounded = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=True, max_concatenate_length=10000)
    )
    unbounded = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=True, max_concatenate_length=None)
    )

    assert bounded == unbounded
    assert bounded == ["あ" * 19999 + "願いは"]
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py::test_concatenate_matching_applies_former_rule_to_oversized_first_line -v --no-cov
```

期待: FAIL。`bounded` が 2 要素になり、1件目の末尾の `の` が除去されずに残る。

- [ ] **Step 3: `concatenated` フラグを導入する**

`__concatenate_matching_iter` の本体を次に差し替える。`try:` から `except StopIteration:` の直前までが対象。

```python
    try:
        former = next(texts)
        # 上限は「現在の累積で1回以上結合が起きた後」にのみ確認する。
        # そうしないと、1行目が単独で上限を超えている場合に
        # former_matching_rule が一度も評価されないまま素通りしてしまう。
        concatenated = False

        for latter in texts:
            if concatenated and max_concatenate_length is not None and len(former) >= max_concatenate_length:
                yield former
                former = latter
                concatenated = False
                continue

            former_match_obj = re.match(former_matching_rule, former) if former_matching_rule else None
            latter_match_obj = re.match(latter_matching_rule, latter) if latter_matching_rule else None

            if former_matching_rule and latter_matching_rule and former_match_obj and latter_match_obj:
                tmp_former = former_match_obj.group("result") if remove_former_matched else former
                tmp_latter = latter_match_obj.group("result") if remove_latter_matched else latter
                former = tmp_former + tmp_latter
                concatenated = True
            elif former_matching_rule and not latter_matching_rule and former_match_obj:
                tmp_former = former_match_obj.group("result") if remove_former_matched else former
                former = tmp_former + latter
                concatenated = True
            elif not former_matching_rule and latter_matching_rule and latter_match_obj:
                tmp_latter = latter_match_obj.group("result") if remove_latter_matched else latter
                former += tmp_latter
                concatenated = True
            else:
                yield former
                former = latter
                concatenated = False

        yield former
```

3つの結合分岐で `concatenated = True`、`else` 分岐と上限分岐で `concatenated = False` を立てる。

このフラグは線形性を損なわない。各累積に「上限を超えた1回ぶんのスキャン」を許すことになるが、その行は入力から1度しか消費されないため、無制限スキャンのコストの総和は入力長で頭打ちになる。

- [ ] **Step 4: docstring にこの保証を追記する**

Task 1 Step 8 で追加した `max_concatenate_length` の説明のうち、`None disables the bound.` の行の **前** に2文を挿入する。

```
        the bound is only checked after the accumulation has been concatenated
        at least once, so former_matching_rule is always applied at least once
        per accumulation even if the first line already exceeds the bound.
        that also means an accumulation may exceed the bound by up to the
        length of a single line.
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py -v --no-cov
```

期待: 5件すべて PASS。特に Task 1 で書いた `test_concatenate_matching_max_concatenate_length`（チャンク数 20、最大長 10）と `test_concatenate_matching_does_not_blow_up_on_large_input`（チャンク数 60）が値を変えずに通ること。入力行が2文字と短いためフラグの影響を受けない。

- [ ] **Step 6: 品質ゲートを通す**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

期待: すべて PASS。C901 は発火しない（複雑度は上限 10 に収まる）。

- [ ] **Step 7: コミット**

```bash
git add ja_sentence_segmenter/concatenate/simple_concatenator.py tests/concatenate/test_simple_concatenator.py
git commit -m "fix: run the former rule at least once per accumulation

Checking the cap unconditionally meant an accumulation whose first line
already exceeded the cap was yielded without former_matching_rule ever
being evaluated, so remove_former_matched stripped nothing.

Gate the check on a concatenated flag. The free scan stays bounded by
the input size because each line is consumed once, so this keeps the
loop linear."
```

---

### Task 3: str 入力への対応

**Files:**
- Modify: `ja_sentence_segmenter/concatenate/simple_concatenator.py`
- Test: `tests/concatenate/test_simple_concatenator.py`

**Interfaces:**
- Consumes: Task 1 の `DEFAULT_MAX_CONCATENATE_LENGTH` と `max_concatenate_length` 引数
- Produces: `str` を受ける `@overload`（3つ目）。実行時の振る舞いが「空を返す」から「入力をそのまま1件返す」に変わる

`concatenate_matching` のシグネチャと docstring は `arg: Union[str, list[str], Iterator[str]]` を宣言しているが、分岐は `list` と `Iterator` の2つしかない。`str` はどちらにも該当せず（`isinstance("abc", Iterator)` は `False`）、例外もなく空ジェネレータになる。`normalize` / `split_newline` / `split_punctuation` はいずれも3分岐と3つの `@overload` を持っており、この関数だけが逸脱している。

- [ ] **Step 1: 失敗するテストを書く**

`tests/concatenate/test_simple_concatenator.py` の末尾に追記する。

```python
def test_concatenate_matching_str_input() -> None:
    # str は結合相手がないのでそのまま1件返る。他の3つの公開関数と同じ規約。
    result = list(simple_concatenator.concatenate_matching("私の願いは", former_matching_rule=RULE_NO))
    assert result == ["私の願いは"]
    assert result == list(simple_concatenator.concatenate_matching(["私の願いは"], former_matching_rule=RULE_NO))
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py::test_concatenate_matching_str_input -v --no-cov
```

期待: FAIL。`assert [] == ['私の願いは']`。

- [ ] **Step 3: `str` の `@overload` を追加する**

既存の2つの `@overload` の **前**（`list[str]` の `@overload` の直前）に挿入する。`normalize` / `split_newline` / `split_punctuation` と同じ並び順である。

```python
@overload
def concatenate_matching(
    arg: str,
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = DEFAULT_MAX_CONCATENATE_LENGTH,
) -> Generator[str, None, None]: ...
```

- [ ] **Step 4: `str` の分岐を追加する**

Task 1 Step 9 で書いた `if isinstance(arg, list):` を `elif` に変え、その前に `str` の分岐を足す。

```python
    if isinstance(arg, str):
        yield from __concatenate_matching_iter(
            iter([arg]), former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length
        )
    elif isinstance(arg, list):
        yield from __concatenate_matching_iter(
            iter(arg), former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length
        )
    elif isinstance(arg, Iterator):
        yield from __concatenate_matching_iter(
            arg, former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched, max_concatenate_length
        )
```

`str` 1本は結合相手が存在しないので、`next(texts)` の後にループが回らず終端の `yield former` でそのまま1件返る。

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/concatenate/test_simple_concatenator.py -v --no-cov
```

期待: 6件すべて PASS。

- [ ] **Step 6: 品質ゲートを通す**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test
```

期待: すべて PASS。`@overload` が3つになっても mypy は追加のエラーを出さない。

- [ ] **Step 7: コミット**

```bash
git add ja_sentence_segmenter/concatenate/simple_concatenator.py tests/concatenate/test_simple_concatenator.py
git commit -m "fix: accept str input in concatenate_matching

The signature and docstring declared str in the Union, but the dispatch
had no str branch, so str input silently yielded nothing. The other
three public functions all dispatch on three types.

Add the str branch and the matching overload."
```

---

### Task 4: CHANGELOG とバージョン

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Task 1〜3 の変更内容
- Produces: リリース可能な状態

- [ ] **Step 1: CHANGELOG に追記する**

`CHANGELOG.md` の `## [Unreleased]` の行の直後に、新しい `## [0.2.0]` セクションを挿入する。`## [Unreleased]` の見出し自体は空のまま残す（既存の `## [0.1.0] 2026-07-10` と同じ構造）。

```markdown
## [Unreleased]

## [0.2.0] 2026-07-25
### Security
- `concatenate_matching`: bound the accumulated concatenation with the new `max_concatenate_length` parameter (default 10000). Without a bound, `former_matching_rule` was re-applied to an ever growing buffer once per input line, which is quadratic in the input size — a 900KB input pinned a CPU core for 30 seconds. Pass `None` to restore the previous unbounded behaviour.

### Fixed
- `concatenate_matching`: accept `str` input. The signature declared it but the dispatch had no `str` branch, so a `str` argument silently yielded nothing.

### Added
- `DEFAULT_MAX_CONCATENATE_LENGTH` constant in `ja_sentence_segmenter.concatenate.simple_concatenator`.
```

- [ ] **Step 2: バージョンを上げる**

`pyproject.toml` の `[project]` セクション、3行目を差し替える。

```toml
version = "0.2.0"
```

引数追加と `str` 対応は加算的だが、10000 文字を超える連結で挙動が変わるため minor 相当と判断する。

- [ ] **Step 3: 全体の品質ゲートを通す**

```bash
uv run poe lint && uv run poe typecheck && uv run poe test && uv run poe bandit
```

期待: すべて PASS。

- [ ] **Step 4: コミット**

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore: release 0.2.0"
```

---

## 完了条件

- [ ] `uv run poe lint` が `All checks passed!` と `already formatted` を返す
- [ ] `uv run poe typecheck` が `Success: no issues found in 9 source files` を返す
- [ ] `uv run poe test` で全テストが PASS する
- [ ] 既存の `test_concatenate_matching` が1文字も変更されていない（`git diff` で確認）
- [ ] 900KB 相当の入力（`["あの"] * 300000`）が1秒前後で完走する
