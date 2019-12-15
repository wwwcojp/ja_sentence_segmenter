"""Simple sentence concatenator for japanese text."""
import re
from typing import Generator, Iterator, List, Optional, Union, overload


def __concatenate_matching_iter(
    texts: Iterator[str], former_matching_rule: Optional[str], latter_matching_rule: Optional[str], remove_former_matched: bool, remove_latter_matched: bool
) -> Generator[str, None, None]:
    try:
        former = next(texts)

        for latter in texts:
            former_match_obj = re.match(former_matching_rule, former) if former_matching_rule else None
            latter_match_obj = re.match(latter_matching_rule, latter) if latter_matching_rule else None

            if former_matching_rule and latter_matching_rule and former_match_obj and latter_match_obj:
                tmp_former = former_match_obj.group("result") if remove_former_matched else former
                tmp_latter = latter_match_obj.group("result") if remove_latter_matched else latter
                former = tmp_former + tmp_latter
            elif former_matching_rule and not latter_matching_rule and former_match_obj:
                tmp_former = former_match_obj.group("result") if remove_former_matched else former
                former = tmp_former + latter
            elif not former_matching_rule and latter_matching_rule and latter_match_obj:
                tmp_latter = latter_match_obj.group("result") if remove_latter_matched else latter
                former += tmp_latter
            else:
                yield former
                former = latter

        yield former
    except StopIteration:
        pass


@overload
def concatenate_matching(
    arg: List[str],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
) -> Generator[str, None, None]:
    ...


@overload
def concatenate_matching(
    arg: Iterator[str],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
) -> Generator[str, None, None]:
    ...


def concatenate_matching(
    arg: Union[str, List[str], Iterator[str]],
    former_matching_rule: Optional[str] = None,
    latter_matching_rule: Optional[str] = None,
    remove_former_matched: bool = True,
    remove_latter_matched: bool = True,
) -> Generator[str, None, None]:
    r"""Concatenate two lines with regular expression rule.

    Parameters
    ----------
    arg : Union[str, List[str], Iterator[str]]
        texts you want to concatenate.
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

    Yields
    ------
    Generator[str, None, None]
        concatenated texts.
    """
    if isinstance(arg, list):
        yield from __concatenate_matching_iter(iter(arg), former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched)
    elif isinstance(arg, Iterator):
        yield from __concatenate_matching_iter(arg, former_matching_rule, latter_matching_rule, remove_former_matched, remove_latter_matched)
