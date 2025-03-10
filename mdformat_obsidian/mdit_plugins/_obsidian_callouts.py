"""Obsidian Callouts. Adapted from mdformat-gfm-alerts."""

from __future__ import annotations

import re
from contextlib import contextmanager, suppress
from typing import Generator, NamedTuple

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from mdit_py_plugins.utils import is_code_block

OBSIDIAN_CALLOUT_PREFIX = "obsidian_callout"
"""Prefix used to differentiate the parsed output."""

INLINE_SEP = "\n\n"
"""Optional separator to differentiate the title and, if present, inline content."""

PATTERN = r"^\\?\[!(?P<title>[^\]]+)\\?\](?P<fold>[\-\+]?)"
"""Regular expression to match Obsidian Alerts."""


# FYI: copied from mdformat_admon.factories
@contextmanager
def new_token(
    state: StateBlock | StateInline,
    name: str,
    kind: str,
) -> Generator[Token, None, None]:
    """Create scoped token."""
    yield state.push(f"{name}_open", kind, 1)
    state.push(f"{name}_close", kind, -1)


# FYI: Adapted from mdformat_admon.factories
class CalloutState(NamedTuple):
    """Frozen state."""

    parentType: str
    lineMax: int


class CalloutData(NamedTuple):
    """CalloutData data for rendering."""

    old_state: CalloutState
    meta_text: str
    fold: str
    custom_title: str
    next_line: int


def format_obsidian_callout_markup(
    state: StateBlock,
    start_line: int,
    admonition: CalloutData,
) -> None:
    """Format markup."""
    tag = admonition.meta_text.lower()
    folded = bool(admonition.fold)
    custom_title = admonition.custom_title
    title_line = f"[!{tag}]{admonition.fold}{INLINE_SEP}{custom_title}"

    with new_token(state, OBSIDIAN_CALLOUT_PREFIX, "div") as token:
        token.attrs = {
            "data-callout-metadata": "",
            "data-callout-fold": "",
            "data-callout": admonition.meta_text.lower(),
            "class": "callout",
        }
        if folded:
            token.attrs["data-callout-fold"] = "-"
            token.attrs["class"] = "callout is-collapsible is-collapsed"
        token.block = True
        token.map = [start_line, admonition.next_line]
        token.markup = title_line
        with new_token(state, f"{OBSIDIAN_CALLOUT_PREFIX}_title", "div") as tkn_title:
            tkn_title.attrs = {"class": "callout-title"}

            title_inner = f"{OBSIDIAN_CALLOUT_PREFIX}_title_inner"
            with new_token(state, title_inner, "div") as tkn_title_inner:
                tkn_title_inner.attrs = {"class": "callout-title-inner"}

                tkn_title_txt = state.push("inline", "", 0)
                tkn_title_txt.content = admonition.custom_title.strip()
            if folded:
                collapsed = f"{OBSIDIAN_CALLOUT_PREFIX}_collapsed"
                with new_token(state, collapsed, "div") as tkn_collapsed:
                    tkn_collapsed.attrs = {"class": "callout-fold is-collapsed"}

        content = f"{OBSIDIAN_CALLOUT_PREFIX}_content"
        with new_token(state, content, "div") as tkn_content:
            tkn_content.attrs = {"class": "callout-content"}
            if folded:
                tkn_content.attrs["style"] = "display: none;"

            state.md.block.tokenize(state, start_line + 1, admonition.next_line)

    # FIXME: this isn't actually replacing the block quote outer div?
    #
    # Render as a div for accessibility rather than block quote
    #   Which is because '>' is being misused (https://github.com/orgs/community/discussions/16925#discussioncomment-8729846)
    state.parentType = "div"  # admonition.old_state.parentType
    state.lineMax = admonition.old_state.lineMax
    state.line = admonition.next_line


def parse_possible_blockquote_admon(
    state: StateBlock,
    start_line: int,
    end_line: int,
    silent: bool,
) -> CalloutData | bool:
    if is_code_block(state, start_line):
        return False

    start = state.bMarks[start_line] + state.tShift[start_line]

    # Exit if no match for any pattern
    text = state.src[start:]
    regex = re.compile(rf"{PATTERN}(?P<custom_title>(?: |<br>)[^\n]+)?", re.IGNORECASE)
    match = regex.match(text)
    if not match:
        return False

    # Since start is found, we can report success here in validation mode
    if silent:
        return True

    old_state = CalloutState(
        parentType=state.parentType,
        lineMax=state.lineMax,
    )
    state.parentType = OBSIDIAN_CALLOUT_PREFIX

    fold = ""
    with suppress(IndexError):
        fold = match["fold"]
    return CalloutData(
        old_state=old_state,
        meta_text=match["title"],
        fold=fold,
        custom_title=match["custom_title"] or "",
        next_line=end_line,
    )


def alert_logic(
    state: StateBlock,
    startLine: int,
    endLine: int,
    silent: bool,
) -> bool:
    """Parse Obsidian Alerts."""
    result = parse_possible_blockquote_admon(state, startLine, endLine, silent)
    if isinstance(result, CalloutData):
        format_obsidian_callout_markup(state, startLine, admonition=result)
        return True
    return result


def obsidian_callout_plugin(md: MarkdownIt) -> None:
    md.block.ruler.before("blockquote", OBSIDIAN_CALLOUT_PREFIX, alert_logic)
