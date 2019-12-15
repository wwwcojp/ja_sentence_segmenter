"""simple pipeline generator."""
import functools
from typing import Callable, Generator


def make_pipeline(*funcs: Callable[..., Generator[str, None, None]]) -> Callable[..., Generator[str, None, None]]:
    """Make pipeline of generators.

    Parameters
    ----------
    *funcs : Callable[..., Generator[str, None, None]]
        generator you want to add pipeline.

    Returns
    -------
    Callable[..., Generator[str, None, None]]
        pipeline of generators.
    """

    def composite(
        func1: Callable[..., Generator[str, None, None]], func2: Callable[..., Generator[str, None, None]]
    ) -> Callable[..., Generator[str, None, None]]:
        return lambda x: func2(func1(x))

    return functools.reduce(composite, funcs)
