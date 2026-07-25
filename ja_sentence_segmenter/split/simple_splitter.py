"""Simple sentence splitter for japanese text."""

import re
from collections.abc import Generator, Iterator
from re import Match
from typing import Union, overload

BETWEEN_QUOTE_JA_REGEX = r"「[^「」]*」"
"""japanese quotation, whose punctuation is protected from splitting."""

BETWEEN_PARENS_JA_REGEX = r"\([^()]*\)"
"""parentheses, whose punctuation is protected from splitting."""

ESCAPE_CHAR = "∯"
"""sentinel wrapped around punctuation that must not split a sentence.

it is stripped again once splitting is done. that final strip cannot tell a
sentinel apart from the same character in the input, so any U+222F already
present in the text is silently removed. remove it beforehand if your text
may contain it.
"""

DEFAULT_PUNCTUATION_REGEX = r"。!?"
"""default punctuation characters for splitting."""


def __split_newline_iter(texts: Iterator[str]) -> Generator[str, None, None]:
    for text in texts:
        yield from text.splitlines()


@overload
def split_newline(arg: str) -> Generator[str, None, None]: ...


@overload
def split_newline(arg: list[str]) -> Generator[str, None, None]: ...


@overload
def split_newline(arg: Iterator[str]) -> Generator[str, None, None]: ...


def split_newline(arg: Union[str, list[str], Iterator[str]]) -> Generator[str, None, None]:
    """Split text with line boundaries.

    Parameters
    ----------
    arg : Union[str, List[str], Iterator[str]]
        texts you want to split.

    Yields
    ------
    Generator[str, None, None]
        texts splitted with line boundaries.
    """
    if isinstance(arg, str):
        yield from __split_newline_iter(iter([arg]))
    elif isinstance(arg, list):
        yield from __split_newline_iter(iter(arg))
    elif isinstance(arg, Iterator):
        yield from __split_newline_iter(arg)


def __split_punctuation_iter(texts: Iterator[str], punctuations: str, split_between_quote: bool, split_between_parens: bool) -> Generator[str, None, None]:
    def escape_between_punctuation(match: Match[str]) -> str:
        text = match.group()
        escape_regex = rf"(?<!{ESCAPE_CHAR})([{punctuations}])(?!{ESCAPE_CHAR})"
        result = re.sub(escape_regex, rf"{ESCAPE_CHAR}\1{ESCAPE_CHAR}", text)
        return result

    def escape_between_quote(text: str) -> str:
        result = re.sub(BETWEEN_QUOTE_JA_REGEX, escape_between_punctuation, text)
        return result

    def escape_between_parens(text: str) -> str:
        result = re.sub(BETWEEN_PARENS_JA_REGEX, escape_between_punctuation, text)
        return result

    def sub_split_punctuation(text: str) -> list[str]:
        split_regex = rf"(?<!{ESCAPE_CHAR})([{punctuations}])(?!{ESCAPE_CHAR})"
        result = re.sub(split_regex, "\\1\n", text)
        unescape_regex = rf"({ESCAPE_CHAR})([{punctuations}])({ESCAPE_CHAR})"
        result = re.sub(unescape_regex, "\\2", result)
        return result.splitlines()

    for text in texts:
        temp = text
        if not split_between_quote:
            temp = escape_between_quote(temp)
        if not split_between_parens:
            temp = escape_between_parens(temp)
        sentences = sub_split_punctuation(temp)
        yield from sentences


@overload
def split_punctuation(
    arg: str, punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]: ...


@overload
def split_punctuation(
    arg: list[str], punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]: ...


@overload
def split_punctuation(
    arg: Iterator[str], punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]: ...


def split_punctuation(
    arg: Union[str, list[str], Iterator[str]],
    punctuations: str = DEFAULT_PUNCTUATION_REGEX,
    split_between_quote: bool = False,
    split_between_parens: bool = False,
) -> Generator[str, None, None]:
    """Split text with puctuations.

    Parameters
    ----------
    arg : Union[str, List[str], Iterator[str]]
        texts you want to split
    punctuations : str, optional
        regular expression for puctuations, by default DEFAULT_PUNCTUATION_REGEX
    split_between_quote : bool, optional
        split if punctuation between quotes, by default False
    split_between_parens : bool, optional
        split if punctuation between parentheses, by default False

    Yields
    ------
    Generator[str, None, None]
        texts splitted with puctuations.

    Notes
    -----
    protecting punctuation inside quotes and parentheses is implemented by
    wrapping it in ESCAPE_CHAR (U+222F) and stripping that again afterwards.
    the strip cannot tell a sentinel apart from the same character in the
    input, so any U+222F already present in the text is silently removed.
    """
    if isinstance(arg, str):
        yield from __split_punctuation_iter(iter([arg]), punctuations, split_between_quote, split_between_parens)
    elif isinstance(arg, list):
        yield from __split_punctuation_iter(iter(arg), punctuations, split_between_quote, split_between_parens)
    elif isinstance(arg, Iterator):
        yield from __split_punctuation_iter(arg, punctuations, split_between_quote, split_between_parens)
