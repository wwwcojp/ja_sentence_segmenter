# concatenate_matching のアルゴリズム的 DoS 対策と str 入力の修正

- 日付: 2026-07-25
- 対象: `ja_sentence_segmenter/concatenate/simple_concatenator.py`
- 起点: `CLAUDE-SECURITY-20260724-162943/CLAUDE-SECURITY-RESULTS.md` の F1
- ベースリビジョン: `3b3a516`（スキャン時点 `9a15236` の子孫。ロジックは無変更）

## 背景

Claude Security の全リポジトリスキャンで、検証パネルを通過した指摘は F1 の1件だけだった（9件中8件は 0-3 で否決）。F1 は `__concatenate_matching_iter` のアルゴリズム的 DoS である。

`former` は `former_matching_rule` を満たした連続行の累積結合である。`simple_concatenator.py:15` はその正規表現を累積バッファ全体に対して毎ループ再実行し、21/24/27 行目は毎回バッファを新しい文字列として作り直す。どちらも1行あたり O(len(former)) なので、総計は入力長に対して二次となる。バッファ長にも吸収行数にも上限がない。

現 HEAD で実測した（`former_matching_rule=r"^(?P<result>.+)(の)$"`, `remove_former_matched=False`, 入力は `あの` の繰り返し）。

| 入力 | 所要時間 |
| --- | --- |
| 225 KB | 2.51 s |
| 450 KB | 7.07 s |
| 900 KB | 30.13 s |

入力2倍で時間4倍、二次であることが確認できる。README のパイプライン（`make_pipeline(normalize, split_newline, concat_tail_no, split_punc2)`）をそのまま Web API に載せた場合、900 KB の投稿1件で CPU コア1本を30秒占有できる。10 MB なら数時間規模になる。

精査の過程で、F1 とは独立した2つ目の問題も見つかった。`concatenate_matching` のシグネチャと docstring は `arg: Union[str, list[str], Iterator[str]]` を宣言しているが、`simple_concatenator.py:90-93` の分岐は `list` と `Iterator` の2つしかない。`str` はどちらにも該当せず（`isinstance("abc", Iterator)` は `False`）、例外もなく空ジェネレータになる。

```
concatenate_matching('私の願いは', former_matching_rule=r'^(?P<result>.+)(の)$')  ->  []
concatenate_matching(['私の願いは'], former_matching_rule=r'^(?P<result>.+)(の)$')  ->  ['私の願いは']
```

これは他の3つの公開関数からの逸脱である。

| 関数 | `Union` に `str` | `@overload` | `isinstance` 分岐 |
| --- | --- | --- | --- |
| `normalize` | あり | 3 | 3（`neologd_normalizer.py:102,104,106`） |
| `split_newline` | あり | 3 | 3（`simple_splitter.py:45,47,49`） |
| `split_punctuation` | あり | 3 | 3（`simple_splitter.py:127,129,131`） |
| `concatenate_matching` | あり | **2** | **2**（`simple_concatenator.py:90,92`） |

3箇所で不整合である。実行時シグネチャは `str` を受けると宣言し、`@overload` は `str` を拒否し（mypy はエラーにする）、実装は受け取って黙って何も返さない。README のパイプラインでは `normalize` が先頭で `str` を受けるため `concatenate_matching` には常にジェネレータが渡り、この経路は表に出ない。単体で使うと沈黙する失敗になる。

## スコープ

含むもの。

- `max_concatenate_length` 引数の追加による累積量の上限
- `str` 入力の分岐と `str` 用 `@overload` の追加
- 上記に伴う docstring、テスト、CHANGELOG、バージョンの更新

含まないもの。

- `former` / `latter` のマッチ意味論の変更（後述）
- 他モジュールの変更
- 依存関係の脆弱性スキャン（スキャン対象外。Dependabot の担当）

変更は `simple_concatenator.py` 1ファイルと、そのテスト・CHANGELOG・`pyproject.toml` のバージョンに限る。

## 設計

### API

```python
@overload
def concatenate_matching(
    arg: str,
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = 10000,
) -> Generator[str, None, None]: ...


@overload
def concatenate_matching(arg: list[str], ...) -> Generator[str, None, None]: ...


@overload
def concatenate_matching(arg: Iterator[str], ...) -> Generator[str, None, None]: ...


def concatenate_matching(
    arg: Union[str, list[str], Iterator[str]],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = 10000,
) -> Generator[str, None, None]:
```

`max_concatenate_length` は末尾のキーワード引数なので、既存の位置引数呼び出しはすべて無影響。

`str` の `@overload` を先頭に置く。`list[str]` や `Iterator[str]` より先に評価させるためではなく（`str` はどちらにも該当しない）、他3関数の並び順に合わせるため。

型は `Optional[int]`。`pyproject.toml` の `requires-python = ">=3.9"` により `int | None` は実行時の注釈として使えず、既存コードも `Optional` / `Union` を用いている。

`None` は上限なしを意味する。`0` 以下は `ValueError` を送出する。`0` を黙って上限なしとして扱うと、上限を無効化したつもりのない呼び出しが無防備になるため。検証は公開関数側で行う。ジェネレータ本体で送出すると最初の `next()` まで遅延するので、引数の妥当性は呼び出し時点で判定する。

プライベート関数 `__concatenate_matching_iter` にも同じ引数を末尾に追加する。既定値は持たせない（呼び出し元は公開関数のみ）。

### アルゴリズム

`__concatenate_matching_iter` のループ先頭、正規表現マッチより前にチェックを1つ挿入する。

```python
for latter in texts:
    if max_concatenate_length is not None and len(former) >= max_concatenate_length:
        yield former
        former = latter
        continue

    former_match_obj = re.match(former_matching_rule, former) if former_matching_rule else None
    # 以降は現行のまま
```

マッチより前に置くことが要件である。マッチの後に置くと、上限を超えた回のスキャンコストがすでに発生してしまう。

このチェックにより `re.match` に渡る `former` の長さが上限で頭打ちになり、全体が O(n × 上限) すなわち入力長に対して線形になる。21/24/27 行目の文字列再結合コストも同時に頭打ちになる。

チェックは4分岐すべての手前にあるので、`latter_matching_rule` のみを指定した経路（27 行目の `former += tmp_latter`、こちらも無制限に伸びる）も同じ1箇所で塞げる。

`max_concatenate_length is not None` と明示比較する。`if max_concatenate_length and ...` と書くと `0` が上限なしに落ちてしまい、`ValueError` を送出する設計と矛盾する。

### 意味論

上限に達しない限り、実行されるコードパスは現行と同一である。したがって次の仕様はすべて保持される。

- `former` は「結合しようとしている前の行」であり、結合結果がそのまま次の「前の行」になる。`former_matching_rule` が累積バッファ全体に当たるのはこの仕様の帰結である
- `latter` は「結合しようとしている後の行」である。イテレータの先頭行には前の行が存在しないため `latter_matching_rule` の対象にならない
- `remove_former_matched` / `remove_latter_matched` による除去は結合が発生したときのみ働く。結合が起きなければ除去すべきものはない

上限はソフト上限である。次の行を読んだ時点で `len(former) >= max_concatenate_length` を判定するため、バッファは最大で `max_concatenate_length + 直近1行の長さ` まで伸び得る。厳密な上限ではないことを docstring に明記する。

テキストの欠落はない。上限到達時は現在のバッファを `yield` してから `latter` で仕切り直すので、入力の全文字がどこかの出力チャンクに必ず現れる。

### 既定値 10000 文字の根拠

日本語の1文は通常数十から数百文字であり、`concat_tail_no` のような結合ルールを適用しても実文書なら数文が繋がる程度である。10000 文字（原稿用紙25枚相当）に達する連結は正常な文章ではまず起きない。一方、悪意ある入力に対しては 10000 × n で線形に抑え込める。

これは本変更で唯一、実文書の振る舞いが変わり得る箇所である。上限に達した場合の影響は「長すぎる連結が余分に分割される」ことのみで、例外もテキストの欠落も起きない。

### str 入力の修正

他3関数と同じ3分岐の規約に揃える。

```python
if isinstance(arg, str):
    yield from __concatenate_matching_iter(iter([arg]), ...)
elif isinstance(arg, list):
    ...
elif isinstance(arg, Iterator):
    ...
```

`str` 1本は結合相手が存在しないので、`next(texts)` の後にループが回らず終端の `yield former` でそのまま1件返る。現行の「黙って空」から「入力をそのまま1件返す」に変わる。空を期待して書かれた呼び出しは存在し得ないため、実害のある破壊的変更にはならない。

## 採用しなかった案

セキュリティレポートは、上限に加えて「`former_matching_rule` を累積全体ではなく最後に追加されたセグメントまたは有界の接尾辞に対して評価する」「`+` の繰り返しではなくリストに貯めて yield 時に一度だけ join する」ことを提案していた。どちらも採用しない。

**接尾辞マッチへの変更**は仕様違反である。`former` は「前の行」であり、結合結果が次の「前の行」になるのが仕様なので、ルールは累積全体に当たるのが正しい。この案を実装して `tests/concatenate/test_simple_concatenator.py:49` のケースにかけると期待値と食い違う。

```
期待: [..., '> 私はあなたがきらいです。でも実は', ...]
実際: [..., '> 私はあなたがきらいです。', ' >でも実は', ...]
```

**リストに貯めて join する変更**は `remove_former_matched=True` と両立しない。この経路では `former_match_obj.group("result")` が累積バッファ全体を書き換えるため（`["私の", "願いは"]` が `"私願いは"` になる）、追記のみのリストでは表現できない。

**上限だけでは不十分**というレポートの評価も誤りである。「全バッファ再走査が残る」のは事実だが、上限 C を導入すればバッファ長が C で頭打ちになるため総計は O(n × C) すなわち線形になる。実測でも確認済み（後述）。二次爆発の解消に接尾辞マッチもリスト化も必要ない。

**上限到達時に例外を送出する案**も採らない。文分割器としては、途中で落ちるより余分に分割された結果を返すほうが呼び出し側にとって扱いやすい。既定値を持たせる以上、既存の長文処理バッチが突然落ちるリスクも避けたい。

## テスト計画

`tests/concatenate/test_simple_concatenator.py` に追加する。既存のアサーションは1文字も変更しない。無変更で通ること自体が「意味論を壊していない」証拠になる。

1. 回帰: 既定値のまま既存の全ケースが従来どおりの結果を返す
2. 上限到達: 小さい上限（例 `max_concatenate_length=10`）で、全チャンクが `上限 + 最大行長` 以下に収まる
3. 欠落なし: 上限到達を伴う入力について、出力の連結が入力の連結と一致する
4. 上限なし: `max_concatenate_length=None` で従来の無制限動作になる
5. 引数検証: `0` および負値で `ValueError` が送出される
6. `str` 入力: `concatenate_matching('...')` が `concatenate_matching(['...'])` と同じ結果を返す
7. 二次爆発の回帰防止: 一定行数の入力が既定値で現実的な時間内に完走する

7 は時間ではなくチャンク数で検証する。実時間のアサーションは CI の負荷変動で不安定になるため使わない。二次爆発が復活すればテスト自体がタイムアウトするので、検出には十分である。

## ドキュメントとバージョン

- docstring に `max_concatenate_length` を numpy スタイルで追記する。ソフト上限であること、`None` で無制限になること、`0` 以下で `ValueError` になることを明記する。`Raises` セクションを新設する
- `CHANGELOG.md` の `[Unreleased]` に Added / Fixed / Security を追記する
- `pyproject.toml` の `[project]` の `version` を `0.1.0` から `0.2.0` に上げる。引数追加と `str` 対応は加算的だが、10000 文字を超える連結で挙動が変わるため minor 相当と判断する
- README は変更しない。既定値で保護されるため利用者側の対応は不要である

## 検証済みの事実

設計内容をプロトタイプで実装し、プロジェクトの実設定で確認した結果を記録する。

品質ゲートはすべて通過した。`ruff check` は All checks passed、`ruff format --check` は already formatted、`mypy`（strict）は Success、`pytest` は既存テスト無変更で 5 passed。C901（`max-complexity = 10`）は発火しない。

性能は線形になった。

| 入力 | 修正前 | 修正後 |
| --- | --- | --- |
| 900 KB | 30.13 s | 0.58 s |
| 3.6 MB | 未測定（二次から約8分と推定） | 2.35 s |
| 14.4 MB | 未測定（二次から約2時間と推定） | 9.44 s |

修正後は入力4倍で時間ちょうど4倍であり、線形であることが確認できる。

動作も設計どおりだった。入力の連結と出力の連結が一致（欠落なし）、最大チャンク長が上限内、`str` 入力が `[str]` 入力と一致、`0` と負値で `ValueError`、`None` で従来動作。

## リスク

**既定値 10000 に達する実文書が存在した場合、出力の分割位置が変わる。** 影響は余分な分割のみで、テキストの欠落も例外も起きない。`max_concatenate_length=None` で従来の動作に戻せる。

**`str` 入力の戻り値が空から1件に変わる。** 空を期待した呼び出しは考えにくいが、厳密には振る舞いの変更である。CHANGELOG に記載する。

**テスト 7 が時間依存になる。** 閾値を緩く取るか、チャンク数による間接検証に切り替えて CI の不安定化を避ける。

**このスキャンは依存関係の脆弱性を検査していない。** `.venv` は対象外であり、依存の脆弱性は Dependabot の担当である。本設計の範囲外。
