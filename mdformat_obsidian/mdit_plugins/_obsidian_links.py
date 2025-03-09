from __future__ import annotations

from typing import Callable

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline


def obsidian_links_plugin(md: MarkdownIt) -> None:
    md.inline.ruler.before("escape", "obsidian_links", obsidian_links())


def is_escaped(state: StateInline, back_pos: int, mod: int = 0) -> bool:
    """Test if bracket is escaped."""
    # count how many \ are before the current position
    backslashes = 0
    while back_pos >= 0:
        back_pos = back_pos - 1
        if state.src[back_pos] == "\\":
            backslashes += 1
        else:
            break

    if not backslashes:
        return False

    # if an odd number of \ then ignore
    if (backslashes % 2) != mod:
        return True

    return False


def obsidian_links() -> Callable[[StateInline, bool], bool]:
    def _obsidian_links(state: StateInline, silent: bool) -> bool:
        src_part = state.src[state.pos :]
        if not any(src_part.startswith(s) for s in ("[[", "![[")):
            return False
        pre_len = 2 + int(src_part[0] == "!")

        if is_escaped(state, state.pos):
            return False

        # find closing ]]
        pos = state.pos + pre_len
        found_closing = False
        end = -1
        while not found_closing:
            try:
                end = state.src.index("]]", pos)
            except ValueError:
                return False

            if is_escaped(state, end):
                pos = end + 2
                continue

            found_closing = True

        if not found_closing:
            return False

        text = state.src[state.pos + pre_len : end]

        if not silent:
            ttype = "embed_file" if src_part[0] == "!" else "internal_link"
            token = state.push(ttype, "", 0)
            token.content = text

        state.pos = end + 2

        return True

    return _obsidian_links
