"""Simple sentence splitter for japanese text."""

import re
from typing import Generator, Iterator, List, Match, Union, overload

BETWEEN_QUOTE_JA_REGEX = r"「[^「」]*」"
BETWEEN_PARENS_JA_REGEX = r"\([^()]*\)"
ESCAPE_CHAR = "∯"
DEFAULT_PUNCTUATION_REGEX = r"。!?"


def __split_newline_iter(texts: Iterator[str]) -> Generator[str, None, None]:
    for text in texts:
        for line in text.splitlines():
            yield line


@overload
def split_newline(arg: str) -> Generator[str, None, None]:
    ...


@overload
def split_newline(arg: List[str]) -> Generator[str, None, None]:
    ...


@overload
def split_newline(arg: Iterator[str]) -> Generator[str, None, None]:
    ...


def split_newline(arg: Union[str, List[str], Iterator[str]]) -> Generator[str, None, None]:
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
        escapeRegex = rf"(?<!{ESCAPE_CHAR})([{punctuations}])(?!{ESCAPE_CHAR})"
        result = re.sub(escapeRegex, rf"{ESCAPE_CHAR}\1{ESCAPE_CHAR}", text)
        return result

    def escape_between_quote(text: str) -> str:
        result = re.sub(BETWEEN_QUOTE_JA_REGEX, escape_between_punctuation, text)
        return result

    def escape_between_parens(text: str) -> str:
        result = re.sub(BETWEEN_PARENS_JA_REGEX, escape_between_punctuation, text)
        return result

    def sub_split_punctuation(text: str) -> List[str]:
        splitRegex = rf"(?<!{ESCAPE_CHAR})([{punctuations}])(?!{ESCAPE_CHAR})"
        result = re.sub(splitRegex, "\\1\n", text)
        unescapeRegex = rf"({ESCAPE_CHAR})([{punctuations}])({ESCAPE_CHAR})"
        result = re.sub(unescapeRegex, "\\2", result)
        return result.splitlines()

    for text in texts:
        temp = text
        if not split_between_quote:
            temp = escape_between_quote(temp)
        if not split_between_parens:
            temp = escape_between_parens(temp)
        sentences = sub_split_punctuation(temp)
        for sentence in sentences:
            yield sentence


@overload
def split_punctuation(
    arg: str, punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]:
    ...


@overload
def split_punctuation(
    arg: List[str], punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]:
    ...


@overload
def split_punctuation(
    arg: Iterator[str], punctuations: str = DEFAULT_PUNCTUATION_REGEX, split_between_quote: bool = False, split_between_parens: bool = False
) -> Generator[str, None, None]:
    ...


def split_punctuation(
    arg: Union[str, List[str], Iterator[str]],
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
    """
    if isinstance(arg, str):
        yield from __split_punctuation_iter(iter([arg]), punctuations, split_between_quote, split_between_parens)
    elif isinstance(arg, list):
        yield from __split_punctuation_iter(iter(arg), punctuations, split_between_quote, split_between_parens)
    elif isinstance(arg, Iterator):
        yield from __split_punctuation_iter(arg, punctuations, split_between_quote, split_between_parens)
