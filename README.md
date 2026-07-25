# ja_sentence_segmenter

[![Test](https://github.com/wwwcojp/ja_sentence_segmenter/actions/workflows/test.yml/badge.svg)](https://github.com/wwwcojp/ja_sentence_segmenter/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/ja-sentence-segmenter)](https://pypi.org/project/ja-sentence-segmenter/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ja-sentence-segmenter)](https://pypi.org/project/ja-sentence-segmenter/)

日本語のテキストに対して、ルールベースによる文区切り（sentence segmentation）を行います。

## Getting Started

### Prerequisites
* Python 3.9+

### Installing
`pip install ja_sentence_segmenter`

### Usage
```Python
import functools

from ja_sentence_segmenter.common.pipeline import make_pipeline
from ja_sentence_segmenter.concatenate.simple_concatenator import concatenate_matching
from ja_sentence_segmenter.normalize.neologd_normalizer import normalize
from ja_sentence_segmenter.split.simple_splitter import split_newline, split_punctuation

split_punc2 = functools.partial(split_punctuation, punctuations=r"。!?")
concat_tail_no = functools.partial(concatenate_matching, former_matching_rule=r"^(?P<result>.+)(の)$", remove_former_matched=False)
segmenter = make_pipeline(normalize, split_newline, concat_tail_no, split_punc2)

# Golden Rule: Simple period to end sentence #001 (from https://github.com/diasks2/pragmatic_segmenter/blob/master/spec/pragmatic_segmenter/languages/japanese_spec.rb#L6)
text1 = "これはペンです。それはマーカーです。"
print(list(segmenter(text1)))
```

```
> ["これはペンです。", "それはマーカーです。"]
```

### 信頼できない入力を扱う場合

`concatenate_matching` は、結合ルールを満たす行が続くかぎり累積を伸ばし続けます。このとき結合ルールは伸び続けた累積全体に対して毎行再適用され、累積そのものも毎行作り直されるため、**処理量は入力サイズの2乗に比例します**。ルールに合う行だけでできた 1.8MB のテキストで CPU コアを30秒占有でき、入力が大きくなるほど2乗で悪化します。

外部から与えられたテキストを区切る場合は、`max_concatenate_length` に上限を設定してください。既定は `None`（上限なし）です。

```Python
concat_tail_no = functools.partial(
    concatenate_matching,
    former_matching_rule=r"^(?P<result>.+)(の)$",
    remove_former_matched=False,
    max_concatenate_length=10000,  # 累積の上限（文字数）
)
```

上限を設定すると、区切り位置が変わるだけでなく出力されるテキスト自体も変わります。上限に達した箇所では結合ルールが評価されないため、`remove_former_matched` / `remove_latter_matched` が剥がすはずだった文字が残ります。また `「` と `」` の間で累積が切れると、`split_punctuation` による鉤括弧内の句点の保護が効かなくなります。詳細は `concatenate_matching` の docstring を参照してください。

## API

公開しているのは次の5つです。引数の詳細は [API ドキュメント](https://wwwcojp.github.io/ja_sentence_segmenter/ja_sentence_segmenter.html) にあります。

| 関数 | 役割 |
| --- | --- |
| `normalize` | 表記を揃える（半角カナ→全角、全角英数→半角、連続空白の圧縮など） |
| `split_newline` | 改行で行に分割する |
| `concatenate_matching` | 正規表現ルールに従って隣り合う行を結合する |
| `split_punctuation` | 句点で文に分割する |
| `make_pipeline` | 上記を合成して1つの segmenter にする |

いずれも `str` / `list[str]` / `Iterator[str]` を受け取り、ジェネレータを返します。ただし **`concatenate_matching` だけは `str` を「1行」として扱い、改行で分割しません。** 先に `split_newline` を通してください。

### パイプラインの順序

`make_pipeline` は左から順に適用します。`concatenate_matching` は行を単位に動くので、`split_newline` より後、`split_punctuation` より前に置きます。

```Python
make_pipeline(normalize, split_newline, concat_tail_no, split_punc2)
#             ①表記を揃える ②行に分割  ③行を結合    ④文に分割
```

### 主なオプション

```Python
normalize(text, remove_tildes=True)
# 'それは〜ペンです～。' -> 'それはペンです。'    既定(False)なら波ダッシュは残る

split_punctuation(text, punctuations=r"。!?")
# 文末とみなす文字を変える

split_punctuation(text, split_between_quote=True)
# '彼は「そうだ。だから行く」と言った。'
#   既定(False) -> ['彼は「そうだ。だから行く」と言った。']       鉤括弧内では切らない
#   True        -> ['彼は「そうだ。', 'だから行く」と言った。']
# split_between_parens は (…) について同じことをする

concatenate_matching(lines, latter_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$")
# 「後の行」側のルール。引用記号の除去などに使う。
# former_matching_rule は「前の行」側で、末尾の助詞などを見るのに向く
```

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

## Versioning
We use SemVer for versioning. For the versions available, see the tags on this repository.

## Contributing
TODO

## License
MIT

## Acknowledgments

### テキストの正規化処理
テキスト正規化のコードは、[mecab-ipadic-NEologd](https://github.com/neologd/mecab-ipadic-neologd)の以下のWIKIを参考に一部修正を加えています。

サンプルコードの提供者であるhideaki-t氏とoverlast氏に感謝します。

https://github.com/neologd/mecab-ipadic-neologd/wiki/Regexp.ja#python-written-by-hideaki-t--overlast

### 文区切り（sentence segmentation）のルール
文区切りのルールとして、[Pragmatic Segmenter](https://github.com/diasks2/pragmatic_segmenter)の日本語ルールを参考にしました。

https://github.com/diasks2/pragmatic_segmenter#golden-rules-japanese

また、以下のテストコード中で用いられているテストデータを、本PJのテストコードで利用しました。

https://github.com/diasks2/pragmatic_segmenter/blob/master/spec/pragmatic_segmenter/languages/japanese_spec.rb

作者のKevin S. Dias氏と[コントリビュータの方々](https://github.com/diasks2/pragmatic_segmenter/graphs/contributors)に感謝します。

Thanks to Kevin S. Dias and [contributors](https://github.com/diasks2/pragmatic_segmenter/graphs/contributors).
