"""Simple sentence concatenator for japanese text."""

import re
from collections.abc import Generator, Iterator
from typing import Optional, Union, overload


def __concatenate_matching_iter(
    texts: Iterator[str],
    former_matching_rule: Optional[str],
    latter_matching_rule: Optional[str],
    remove_former_matched: bool,
    remove_latter_matched: bool,
    max_concatenate_length: Optional[int],
) -> Generator[str, None, None]:
    # 累積は入力1行ごとに再走査されるので、パターンのコンパイルはループの外で1度だけ行う。
    former_pattern = re.compile(former_matching_rule) if former_matching_rule else None
    latter_pattern = re.compile(latter_matching_rule) if latter_matching_rule else None

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

            former_match_obj = former_pattern.match(former) if former_pattern else None
            latter_match_obj = latter_pattern.match(latter) if latter_pattern else None

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
    except StopIteration:
        pass


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
def concatenate_matching(
    arg: list[str],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = None,
) -> Generator[str, None, None]: ...


@overload
def concatenate_matching(
    arg: Iterator[str],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = None,
) -> Generator[str, None, None]: ...


def concatenate_matching(
    arg: Union[str, list[str], Iterator[str]],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
    max_concatenate_length: Optional[int] = None,
) -> Generator[str, None, None]:
    r"""Concatenate two lines with regular expression rule.

    Parameters
    ----------
    arg : Union[str, list[str], Iterator[str]]
        texts you want to concatenate.
        a str is treated as one indivisible line and is never split, so it has
        nothing to be concatenated with and comes back unchanged. split it into
        lines yourself first -- `split_newline` does this -- and pass the
        result here.
    former_matching_rule : Optional[str], optional
        regular expression for former line, by default None
    latter_matching_rule : Optional[str], optional
        regular expression for latter line, by default None
    remove_former_matched : bool, optional
        whether to remove matched place of former line, by default True.
        if this is True, former_matching_rule must contain named group 'result',
        only that group remains.
        e.g. r"^(\s*[>]+\s*)(?P<result>.+)$"
    remove_latter_matched : bool, optional
        whether to remove matched place of latter line, by default True.
        if this is True, latter_matching_rule must contain named group 'result',
        only that group remains.
        e.g. r"^(\s*[>]+\s*)(?P<result>.+)$"
    max_concatenate_length : Optional[int], optional
        soft upper bound on the length of an accumulation, by default None,
        meaning no bound. must be positive if not None.
        set it when segmenting untrusted text, and see the notes below for
        what it costs. leaving it None keeps the unbounded behaviour.

    Yields
    ------
    Generator[str, None, None]
        concatenated texts.

    Raises
    ------
    TypeError
        if arg is not a str, a list or an Iterator.
    ValueError
        if max_concatenate_length is not None and not positive.
        both are raised on the first iteration rather than at call time,
        because this is a generator function.

    Notes
    -----
    Why max_concatenate_length exists: without a bound, former_matching_rule
    is re-applied to an ever growing accumulation and the accumulation itself
    is rebuilt on every input line. both costs grow with the accumulated
    length, so the total work is quadratic in the size of the input.

    What setting it costs: once an accumulation reaches the bound it is
    yielded as is and a new accumulation starts. no text is lost and no
    exception is raised, but the output differs from an unbounded run by more
    than where it is split.

    - the bound is soft. it is only checked after an accumulation has been
      concatenated at least once, so former_matching_rule is applied at least
      once per accumulation even when the first line already exceeds the
      bound. an accumulation may therefore exceed the bound by the length of
      the line that started it plus one more line.
    - neither matching rule is evaluated at a bound boundary, so text that
      remove_former_matched or remove_latter_matched would have stripped
      survives into the output there.
    - an accumulation may be broken between an opening bracket and its
      closing one, which stops split_punctuation from protecting the
      punctuation inside it.
    """
    if max_concatenate_length is not None and max_concatenate_length <= 0:
        msg = f"max_concatenate_length must be positive or None, got {max_concatenate_length}"
        raise ValueError(msg)

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
    else:
        # 静的には到達しないが、型注釈のない呼び出しが tuple や set を渡したときに
        # 黙って空を返さないための実行時ガード。
        msg = f"arg must be a str, a list or an Iterator, got {type(arg).__name__}"  # type: ignore[unreachable]
        raise TypeError(msg)
