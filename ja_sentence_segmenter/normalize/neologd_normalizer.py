"""テキストの正規化処理.

正規化のコードは以下を参考に一部修正を加えています。
https://github.com/neologd/mecab-ipadic-neologd/wiki/Regexp.ja#python-written-by-hideaki-t--overlast
"""
from __future__ import unicode_literals

import re
import unicodedata
from typing import Dict, Generator, Iterator, List, Union, overload


def __unicode_normalize(cls: str, s: str) -> str:
    pt = re.compile("([{}]+)".format(cls))

    def norm(c: str) -> str:
        return unicodedata.normalize("NFKC", c) if pt.match(c) else c

    s = "".join(norm(x) for x in re.split(pt, s))
    s = re.sub("－", "-", s)
    return s


def __remove_extra_spaces(s: str) -> str:
    s = re.sub("[ 　]+", " ", s)
    blocks = "".join(
        (
            "\u4E00-\u9FFF",  # CJK UNIFIED IDEOGRAPHS
            "\u3040-\u309F",  # HIRAGANA
            "\u30A0-\u30FF",  # KATAKANA
            "\u3000-\u303F",  # CJK SYMBOLS AND PUNCTUATION
            "\uFF00-\uFFEF",  # HALFWIDTH AND FULLWIDTH FORMS
        )
    )
    basic_latin = "\u0000-\u007F"

    def remove_space_between(cls1: str, cls2: str, s: str) -> str:
        p = re.compile("([{}]) ([{}])".format(cls1, cls2))
        while p.search(s):
            s = p.sub(r"\1\2", s)
        return s

    s = remove_space_between(blocks, blocks, s)
    s = remove_space_between(blocks, basic_latin, s)
    s = remove_space_between(basic_latin, blocks, s)
    return s


def __normalize_neologd(s: str, remove_tildes: bool) -> str:
    s = s.strip()
    s = __unicode_normalize("０-９Ａ-Ｚａ-ｚ｡-ﾟ", s)

    def maketrans(f: str, t: str) -> Dict[int, int]:
        return {ord(x): ord(y) for x, y in zip(f, t)}

    s = re.sub("[˗֊‐‑‒–⁃⁻₋−]+", "-", s)  # normalize hyphens
    s = re.sub("[﹣－ｰ—―─━ー]+", "ー", s)  # normalize choonpus
    if remove_tildes:
        s = re.sub("[~∼∾〜〰～]", "", s)  # remove tildes (original)
    else:
        s = re.sub("[~∼∾〜〰～]", "～", s)  # normalize tildes (modified by wwwcojp)

    s = s.translate(maketrans("!\"#$%&'()*+,-./:;<=>?@[¥]^_`{|}~｡､･｢｣", "！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝〜。、・「」"))

    s = __remove_extra_spaces(s)
    s = __unicode_normalize("！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝〜", s)  # keep ＝,・,「,」
    s = re.sub("[’]", "'", s)
    s = re.sub("[”]", '"', s)
    return s


def __normalize_iter(texts: Iterator[str], remove_tildes: bool) -> Generator[str, None, None]:
    for text in texts:
        yield __normalize_neologd(text, remove_tildes)


@overload
def normalize(arg: str, remove_tildes: bool = False) -> Generator[str, None, None]:
    ...


@overload
def normalize(arg: List[str], remove_tildes: bool = False) -> Generator[str, None, None]:
    ...


@overload
def normalize(arg: Iterator[str], remove_tildes: bool = False) -> Generator[str, None, None]:
    ...


def normalize(arg: Union[str, List[str], Iterator[str]], remove_tildes: bool = False) -> Generator[str, None, None]:
    """Normalize text with mecab-ipadic-neologd rules.

    Parameters
    ----------
    arg : Union[str, List[str], Iterator[str]]
        texts you want to normalize.
    remove_tildes : bool, optional
        whether to remove tildes, by default False

    Yields
    ------
    Generator[str, None, None]
        normalized texts.
    """
    if isinstance(arg, str):
        yield from __normalize_iter(iter([arg]), remove_tildes)
    elif isinstance(arg, list):
        yield from __normalize_iter(iter(arg), remove_tildes)
    elif isinstance(arg, Iterator):
        yield from __normalize_iter(arg, remove_tildes)
