# ja_sentence_segmenter
日本語のテキストに対して、ルールベースによる文区切り（sentence segmentation）を行います。

## Getting Started

### Prerequisites
* Python 3.6+

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
