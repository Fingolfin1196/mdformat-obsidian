"""General Helpers."""

from __future__ import annotations

import re

from . import __plugin_name__


def separate_indent(line: str) -> tuple[str, str]:
    """Separate leading indent from content. Also used by the test suite.

    Returns:
        tuple[str, str]: separate indent and content

    """
    re_indent = re.compile(r"(?P<indent>\s*)(?P<content>[^\s]?.*)")
    match = re_indent.match(line)
    assert match  # for pyright
    return (match["indent"], match["content"])
