# concatenate_matching のアルゴリズム的 DoS 対策と str 入力の修正

- 日付: 2026-07-25
- 対象: `ja_sentence_segmenter/concatenate/simple_concatenator.py`
- 起点: `CLAUDE-SECURITY-20260724-162943/CLAUDE-SECURITY-RESULTS.md` の F1
- ベースリビジョン: `3b3a516`（スキャン時点 `9a15236` の子孫。ロジックは無変更）

## 背景

> このセクションと次の「スコープ」の行番号は、いずれも**ベースリビジョン `3b3a516`（修正前）**の位置を指す。修正後のファイルでは行が動いているので、`git show 3b3a516:<path>` で参照すること。

Claude Security の全リポジトリスキャンで、検証パネルを通過した指摘は F1 の1件だけだった（9件中8件は 0-3 で否決）。F1 は `__concatenate_matching_iter` のアルゴリズム的 DoS である。

`former` は `former_matching_rule` を満たした連続行の累積結合である。修正前の `simple_concatenator.py:15` はその正規表現を累積バッファ全体に対して毎ループ再実行し、21/24/27 行目は毎回バッファを新しい文字列として作り直す。どちらも1行あたり O(len(former)) なので、総計は入力長に対して二次となる。バッファ長にも吸収行数にも上限がない。

ベースリビジョンで実測した（`former_matching_rule=r"^(?P<result>.+)(の)$"`, `remove_former_matched=False`, 入力は `あの` の繰り返し）。

| 入力 | 所要時間 |
| --- | --- |
| 0.45 MB | 2.51 s |
| 0.90 MB | 7.07 s |
| 1.80 MB | 30.13 s |

入力2倍で時間4倍、二次であることが確認できる。README のパイプライン（`make_pipeline(normalize, split_newline, concat_tail_no, split_punc2)`）をそのまま Web API に載せた場合、1.80 MB の投稿1件で CPU コア1本を30秒占有できる。10 MB なら数時間規模になる。

精査の過程で、F1 とは独立した2つ目の問題も見つかった。`concatenate_matching` のシグネチャと docstring は `arg: Union[str, list[str], Iterator[str]]` を宣言しているが、修正前の `simple_concatenator.py:90-93` の分岐は `list` と `Iterator` の2つしかない。`str` はどちらにも該当せず（`isinstance("abc", Iterator)` は `False`）、例外もなく空ジェネレータになる。

```
concatenate_matching('私の願いは', former_matching_rule=r'^(?P<result>.+)(の)$')  ->  []
concatenate_matching(['私の願いは'], former_matching_rule=r'^(?P<result>.+)(の)$')  ->  ['私の願いは']
```

これは他の3つの公開関数からの逸脱である。

以下はいずれも修正前（`3b3a516`）の状態である。

| 関数 | `Union` に `str` | `@overload` | `isinstance` 分岐 |
| --- | --- | --- | --- |
| `normalize` | あり | 3 | 3（`neologd_normalizer.py:102,104,106`） |
| `split_newline` | あり | 3 | 3（`simple_splitter.py:45,47,49`） |
| `split_punctuation` | あり | 3 | 3（`simple_splitter.py:127,129,131`） |
| `concatenate_matching` | あり | **2** | **2**（`simple_concatenator.py:90,92`） |

3箇所で不整合である。実行時シグネチャは `str` を受けると宣言し、`@overload` は `str` を拒否し（mypy はエラーにする）、実装は受け取って黙って何も返さない。README のパイプラインでは `normalize` が先頭で `str` を受けるため `concatenate_matching` には常にジェネレータが渡り、この経路は表に出ない。単体で使うと沈黙する失敗になる。

## スコープ

含むもの。

- `max_concatenate_length` 引数の追加によるオプトインの累積量上限（既定 `None`）
- 各累積が上限で打ち切られる前に必ず1回は `former_matching_rule` の評価を受けることの保証
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
    max_concatenate_length: Optional[int] = None,
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
    max_concatenate_length: Optional[int] = None,
) -> Generator[str, None, None]:
```

既定値は `None`（上限なし）とする。オプトインなので既存の呼び出しの振る舞いは完全に不変であり、上限を設定した呼び出しだけが後述の副作用を引き受ける。「推奨値」の定数は公開しない。適切な値は呼び出し側のデータ次第であり、`DEFAULT_` を冠した定数が既定でないのは名前が嘘になるため。

`max_concatenate_length` は末尾のキーワード引数なので、既存の位置引数呼び出しはすべて無影響。

`str` の `@overload` を先頭に置く。`list[str]` や `Iterator[str]` より先に評価させるためではなく（`str` はどちらにも該当しない）、他3関数の並び順に合わせるため。

型は `Optional[int]`。`pyproject.toml` の `requires-python = ">=3.9"` により `int | None` は実行時の注釈として使えず、既存コードも `Optional` / `Union` を用いている。

`None` は上限なしを意味する。`0` 以下は `ValueError` を送出する。`0` を黙って上限なしとして扱うと、上限を無効化したつもりのない呼び出しが無防備になるため。

検証は公開関数の本体の先頭、`isinstance` によるディスパッチより前に置く。ただし `concatenate_matching` は `yield from` を含むジェネレータ関数なので、**`ValueError` は呼び出し時点ではなく最初の `next()` の時点で送出される**。呼び出し時点で送出させるには、ジェネレータを返す非ジェネレータのラッパーに分割する必要があるが、他の3つの公開関数の構造から外れるため採らない。既存の流儀を優先し、遅延送出を受け入れる。テストは `list(...)` で消費して検証する。

プライベート関数 `__concatenate_matching_iter` にも同じ引数を末尾に追加する。既定値は持たせない（呼び出し元は公開関数のみ）。

### アルゴリズム

`__concatenate_matching_iter` のループ先頭、正規表現マッチより前にチェックを1つ挿入する。あわせて「現在の累積で結合が起きたか」を表すフラグ `concatenated` を導入する。

```python
former = next(texts)
concatenated = False

for latter in texts:
    if concatenated and max_concatenate_length is not None and len(former) >= max_concatenate_length:
        yield former
        former = latter
        concatenated = False
        continue

    former_match_obj = re.match(former_matching_rule, former) if former_matching_rule else None
    # 以降のマッチ処理は現行のまま。
    # 3つの結合分岐では concatenated = True、else 分岐では concatenated = False を立てる。
```

チェックをマッチより前に置くことが要件である。マッチの後に置くと、上限を超えた回のスキャンコストがすでに発生してしまう。

このチェックにより `re.match` に渡る `former` の長さが上限で頭打ちになり、全体が O(n × 上限) すなわち入力長に対して線形になる。3つの結合分岐での文字列再結合コストも同時に頭打ちになる。

チェックは4分岐すべての手前にあるので、`latter_matching_rule` のみを指定した経路（`former += tmp_latter` の分岐、こちらも無制限に伸びる）も同じ1箇所で塞げる。

`max_concatenate_length is not None` と明示比較する。`if max_concatenate_length and ...` と書くと `0` が上限なしに落ちてしまい、`ValueError` を送出する設計と矛盾する。

### concatenated フラグが必要な理由

フラグなしで無条件にチェックすると、**累積の最初の行がすでに上限以上の長さだった場合、`former_matching_rule` が一度も評価されないまま素通りする**。`remove_former_matched` による除去も起きない。これは「余分に分割されるだけ」では済まない振る舞いの変更である。

実測で確認した。`former_matching_rule=r"^(?P<result>.+)(の)$"`, `remove_former_matched=True`, 上限 10000、入力の1行目が 20000 文字（末尾が `の`）の場合。

| 実装 | 出力チャンク数 | 1件目の末尾 | `の` の除去 |
| --- | --- | --- | --- |
| 現行 | 1 | `あああ願いは` | される |
| フラグなし | 2 | `あああああの` | **されない** |
| フラグあり | 1 | `あああ願いは` | される |

フラグを入れることで **各累積は上限で打ち切られる前に必ず1回は `former_matching_rule` の評価を受ける**ことが保証され、現行の振る舞いが完全に保存される。

フラグは線形性を損なわない。各累積に「上限を超えた1回ぶんのスキャン」を許すことになるが、その行は入力から1度しか消費されないため、無制限スキャンのコストの総和は入力長で頭打ちになる。「短行を大量に」「上限ちょうどの長さの行を連打」「巨大行と短行の交互」の3パターンで、いずれも入力2倍に対して時間約2倍であることを実測した。

この保証の対象は `former_matching_rule` のみである。上限チェックで飛ばされた `latter` は `latter_matching_rule` の評価を受けずに次の `former` になるが、これは結合が起きなかったときの既存の else 分岐とまったく同じ構造であり、「除去は結合が発生したときのみ働く」という既存仕様と整合する。

### 意味論

上限に達しない限り、実行されるコードパスは現行と同一である。したがって次の仕様はすべて保持される。

- `former` は「結合しようとしている前の行」であり、結合結果がそのまま次の「前の行」になる。`former_matching_rule` が累積バッファ全体に当たるのはこの仕様の帰結である
- `latter` は「結合しようとしている後の行」である。イテレータの先頭行には前の行が存在しないため `latter_matching_rule` の対象にならない
- `remove_former_matched` / `remove_latter_matched` による除去は結合が発生したときのみ働く。結合が起きなければ除去すべきものはない

加えて、上限の導入により次の不変条件を保証する。

- **各累積は、上限で打ち切られる前に必ず1回は `former_matching_rule` の評価を受ける。** 上限は累積の伸びを止めるものであって、まだ一度も処理されていない行の処理を拒否するものではない

上限はソフト上限である。次の行を読んだ時点で `len(former) >= max_concatenate_length` を判定すること、および上記の不変条件により初回の評価が免除されることから、バッファは上限を超え得る。厳密な上限ではないことを docstring に明記する。

テキストの欠落はない。上限到達時は現在のバッファを `yield` してから `latter` で仕切り直すので、入力の全文字がどこかの出力チャンクに必ず現れる。

### 上限を設定したときの副作用

**当初この設計は「上限に達した場合の影響は余分な分割のみ」と記述していたが、これは誤りだった。** 上限分岐の `continue` はマッチ処理のブロック全体を飛ばすため、分割位置だけでなく**出力されるテキストの中身が変わる**。副作用は3つあり、いずれもコードレビューで実際に再現された。

**1. 除去ルールが境界で効かない。** 上限境界では `former_matching_rule` も `latter_matching_rule` も評価されないので、`remove_former_matched` / `remove_latter_matched` が剥がすはずだった文字が出力に残る。

```
上限あり: ['あああああああああの', 'あああの']    ← の が2個
上限なし: ['ああああああああああああの']          ← の が1個
```

**2. 鉤括弧が分断され、句点の保護が壊れる。** これが最も影響が深刻である。`split_punctuation` の `split_between_quote=False`（既定）は `BETWEEN_QUOTE_JA_REGEX = r"「[^「」]*」"` で鉤括弧内の句点を保護するが、開き括弧と閉じ括弧が同じ文字列にないと機能しない。上限が途中で切ると保護が無効化され、鉤括弧内の `。` が文の切れ目として扱われる。文区切りという本業の品質そのものの劣化である。

```
上限なし: 1件 / 「」不整合 0件
既定10000: 3件 / 「」不整合 2件 ← 鉤括弧内の 。 で文が切れる
```

**3. 上限がソフトである。** 前述の初回評価の保証により、累積は「開始した行の長さ + もう1行」ぶん上限を超え得る。

いずれも上限を設ける以上、避けられない帰結である（境界では結合が起きないので、除去すべきものが存在しない）。したがってコードで修正するのではなく、docstring・README・CHANGELOG に明記して、上限を設定する呼び出し側が引き受ける前提とする。

### 既定値を None とする根拠

上記の副作用は、既定で有効にしてよいものではない。特に鉤括弧の分断は、このライブラリの本業である文区切りの品質を、利用者に無断で劣化させる。README のパイプラインをそのまま使っているだけの利用者が、アップグレードだけで句点で終わらない文の断片を受け取ることになる。

したがって既定は `None`（上限なし）とし、**上限はオプトイン**とする。既存の呼び出しの振る舞いは完全に不変になる。

代償として、**上限を設定しない利用者の DoS は塞がらない**。これは承知の上での判断である。README に「信頼できない入力を扱う場合は `max_concatenate_length` を設定する」節を設けて周知する。

### マッチを速くすれば上限が不要になるか

ならない。二次コストの発生源は正規表現だけではないため。

正規表現を一切使わず、実コードと同じ形（`tmp_former = former` でエイリアスを作ってから結合）で文字列連結だけを測った結果：

| 行数 | 所要時間 | 前回比 |
| --- | --- | --- |
| 50,000 | 0.37 s | — |
| 100,000 | 1.95 s | 5.2x |
| 200,000 | 8.78 s | 4.5x |

**文字列の再結合だけで二次**である。`tmp_former = former` がエイリアスを作るため CPython の in-place 最適化（`x = x + y` で `x` の参照カウントが1のときのみ有効）が効かず、毎回バッファ全体をコピーする。したがって正規表現のコストをゼロにしても DoS は残り、バッファ長そのものを頭打ちにする以外に手はない。

同じ理由で「`former_matching_rule` の評価を累積ごとに1回だけにする」案も採らない。これは性能上無意味なだけでなく、既存7ケース中3ケースの出力を壊す。このマッチは「この累積はもう1行受け入れてよいか」という**停止条件**であり、バッファが伸びると答えが変わるためである（`私の` は `の` で終わるので結合するが、結合後の `私の願いは` は `は` で終わるので結合しない）。

### str 入力の修正

他3関数と同じ3分岐の規約に揃える。

```python
if isinstance(arg, str):
    yield from __concatenate_matching_iter(iter([arg]), ...)
elif isinstance(arg, list):
    ...
elif isinstance(arg, Iterator):
    ...
else:
    msg = f"arg must be a str, a list or an Iterator, got {type(arg).__name__}"  # type: ignore[unreachable]
    raise TypeError(msg)
```

`str` 1本は結合相手が存在しないので、`next(texts)` の後にループが回らず終端の `yield former` でそのまま1件返る。現行の「黙って空」から「入力をそのまま1件返す」に変わる。空を期待して書かれた呼び出しは存在し得ないため、実害のある破壊的変更にはならない。

`str` は**1行として扱い、改行では分割しない**。`split_newline` の仕事だからである。ただし新設した `str` オーバーロードを見て複数行の文書を渡すと入力がそのまま返ってくるので、docstring に「先に行へ分割してから渡すこと」を明記する。

終端の `else` は静的には到達しない（`Union` が網羅されている）ので `warn_unreachable` に弾かれる。`# type: ignore[unreachable]` で明示的に抑止する。型注釈のない呼び出しが tuple や set を渡したときに入力を丸ごと黙って捨てるのを防ぐための実行時ガードであり、静的に到達しないことは抑止する理由にならない。

## 採用しなかった案

セキュリティレポートは、上限に加えて「`former_matching_rule` を累積全体ではなく最後に追加されたセグメントまたは有界の接尾辞に対して評価する」「`+` の繰り返しではなくリストに貯めて yield 時に一度だけ join する」ことを提案していた。どちらも採用しない。

**接尾辞マッチへの変更**は仕様違反である。`former` は「前の行」であり、結合結果が次の「前の行」になるのが仕様なので、ルールは累積全体に当たるのが正しい。この案を実装して `test_concatenate_matching` の `texts3`（両ルールに行頭アンカーを指定するケース）にかけると期待値と食い違う。

```
期待: [..., '> 私はあなたがきらいです。でも実は', ...]
実際: [..., '> 私はあなたがきらいです。', ' >でも実は', ...]
```

**リストに貯めて join する変更**は `remove_former_matched=True` と両立しない。この経路では `former_match_obj.group("result")` が累積バッファ全体を書き換えるため（`["私の", "願いは"]` が `"私願いは"` になる）、追記のみのリストでは表現できない。

**上限だけでは不十分**というレポートの評価も誤りである。「全バッファ再走査が残る」のは事実だが、上限 C を導入すればバッファ長が C で頭打ちになるため総計は O(n × C) すなわち線形になる。実測でも確認済み（後述）。二次爆発の解消に接尾辞マッチもリスト化も必要ない。

**上限到達時に例外を送出する案**も採らない。文分割器としては、途中で落ちるより分割された結果を返すほうが呼び出し側にとって扱いやすい。

**「上限を設定したときの副作用をコードで直す」案**も採らない。境界では結合が起きないので、除去すべきものがそもそも存在しない。除去を起こすには結合を起こすしかなく、それは上限を設けないということである。文書化して呼び出し側に引き受けてもらうのが唯一筋の通る扱いになる。

## テスト計画

`tests/concatenate/test_simple_concatenator.py` に追加する。既存のアサーションは1文字も変更しない。無変更で通ること自体が「意味論を壊していない」証拠になる。

1. 回帰: 既定（`None`）のまま既存の全ケースが従来どおりの結果を返す
2. 上限到達: 短い行と小さい上限（例 `max_concatenate_length=10`）で、全チャンクが `上限 + 最大行長` 以下に収まる
3. 欠落なし: 上限到達を伴う入力について、出力の連結が入力の連結と一致する
4. **初回評価の保証**: 1行目が単独で上限を超える入力に対し、`former_matching_rule` が評価されること。`remove_former_matched=True` で除去が起き、上限なしの場合と同じ結果になることで検証する
5. 上限なし: `max_concatenate_length=None` で従来の無制限動作になる
6. 引数検証: `0` および負値で `ValueError` が送出される
7. `str` 入力: 1件返ること、および改行を含んでいても分割されないこと
8. 非対応型: tuple / set / int で `TypeError` が送出される
9. 上限境界の副作用: `latter_matching_rule` を指定した場合、境界で剥がされなかった接頭辞が残ることを固定する
10. 二次爆発の回帰防止: 上限を設定した入力が完走し、期待どおりのチャンク数になる

4 が初回評価の保証の要である。フラグを外すと落ちるテストであり、意図しない退行を検出する。

9 は docstring に明記した副作用そのものを固定するテストである。上限チェックが正規表現マッチより後ろに移るなどの変更で挙動が変わったときに検出する。当初これが欠けており、コードレビューで指摘された。

10 は時間ではなくチャンク数で検証する。実時間のアサーションは CI の負荷変動で不安定になるため使わない。入力は3万行で足りる（30万行でも検出内容は同じで、CI 時間だけが10倍かかる）。**「二次時間が復活すればテストがタイムアウトする」とは書かない** — `pytest-timeout` は依存に入っておらず GitHub Actions にも `timeout-minutes` がないので、存在しない仕組みを説明することになる。実際の検出器はチャンク数のアサーションである。

2 のアサーションは「短い行」に限定する。初回評価の保証により、1行目が上限を超える場合はチャンクが上限を超え得るため、無条件の上界にはならない。

## ドキュメントとバージョン

- docstring に `max_concatenate_length` を numpy スタイルで追記する。既定が `None` であること、設定した場合の3つの副作用、`0` 以下で `ValueError` になることを明記する。`arg` の説明に「`str` は1行として扱い分割しないので、先に行へ分割してから渡すこと」を追記する。`Raises` セクションを新設し `TypeError` と `ValueError` を記載する
- `CHANGELOG.md` に Added / Fixed / Changed を追記する。既定が `None` で既存の振る舞いが不変であることを最初に述べ、設定した場合の副作用を続ける
- `pyproject.toml` の `[project]` の `version` を `0.1.0` から `0.2.0` に上げる。既定 `None` により既存の振る舞いは不変だが、引数の追加は新機能なので SemVer 上 minor が適切である
- **README に「信頼できない入力を扱う場合」節を追加する。** 既定が `None` である以上、上限は利用者が自分で設定しなければ効かない。ここに書かなければ誰も気づかない

## 検証済みの事実

設計内容をプロトタイプで実装し、プロジェクトの実設定で確認した結果を記録する。

品質ゲートはすべて通過した。`ruff check` は All checks passed、`ruff format --check` は already formatted、`mypy`（strict）は Success、`pytest` は既存テスト無変更で 8 passed。C901（`max-complexity = 10`）は発火しない。

実装上の注意点が1つ見つかった。ディスパッチを `texts` 変数に一本化して末尾で `yield from` を1回だけ呼ぶ形に整理すると、`Union` が網羅されているため `else: return` が `warn_unreachable = true` に弾かれる。他3関数と同じく `yield from` を3分岐それぞれに書く形にする必要がある。終端の `else` で `TypeError` を送出する場合も同じ理由で `# type: ignore[unreachable]` が要る。

性能は線形になった（以下はいずれも上限 10000 を設定した場合）。

| 入力 | 上限なし（既定） | 上限 10000 |
| --- | --- | --- |
| 1.80 MB | 27.32 s | 0.49 s |
| 7.20 MB | 未測定（二次から約7分と推定） | 1.92 s |
| 28.80 MB | 未測定（二次から約2時間と推定） | 7.74 s |

上限を設定すると入力4倍で時間ちょうど4倍であり、線形であることが確認できる。`concatenated` フラグ導入後も、3種類の攻撃パターン（短行の大量投入、上限ちょうどの長さの行の連打、巨大行と短行の交互）すべてで入力2倍に対して時間約2倍を維持した。

パターンをループ外で1度だけコンパイルする変更により、上限ありの 1.80 MB は 0.58 s から 0.49 s に短縮した（約16%）。上限なしの 1.80 MB も 30.13 s から 27.32 s になっている。

動作も設計どおりだった。1行目が上限を超える場合でも `former_matching_rule` が評価されて除去が起きること、入力の連結と出力の連結が一致すること（欠落なし）、短い行では最大チャンク長が上限内に収まること、`str` 入力が `[str]` 入力と一致すること、`0` と負値で `ValueError` になること、`None` で従来動作になることを確認した。

## リスク

**上限を設定しない利用者の DoS は塞がらない。** 既定を `None` にした以上、これは設計上の選択である。README の「信頼できない入力を扱う場合」節が唯一の周知手段なので、削られないようにする。

**上限を設定した利用者は3つの副作用を引き受ける。** 除去ルールが境界で効かない、鉤括弧が分断されて句点保護が壊れる、上限がソフトである。docstring・README・CHANGELOG の3か所に記載した。いずれか1か所だけに書くと見落とされる。

**`str` 入力の戻り値が空から1件に変わる。** 空を期待した呼び出しは考えにくいが、厳密には振る舞いの変更である。CHANGELOG に記載する。

**tuple / set / `dict.keys()` が `TypeError` になる。** 従来は黙って空を返していた。静かなデータ消失を診断可能なエラーに変える意図的な変更だが、これらを渡していたコードは動かなくなる。CHANGELOG に記載する。

**`concatenated` フラグを外すと初回評価の保証が失われる。** リファクタリングで「フラグは冗長」と判断されると、1行目が上限を超える入力で `former_matching_rule` が適用されなくなる。テスト 4 がこれを検出する。フラグの意図をコード上のコメントと docstring の両方に残す。

**このスキャンは依存関係の脆弱性を検査していない。** `.venv` は対象外であり、依存の脆弱性は Dependabot の担当である。本設計の範囲外。
