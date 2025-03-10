"""Public Extension."""

from __future__ import annotations

import re
from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from markdown_it.rules_block.html_block import HTML_SEQUENCES
from mdformat import codepoints
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer._context import _wrap
from mdformat.renderer._util import (
    decimalify_leading,
    decimalify_trailing,
    get_list_marker_type,
    is_tight_list,
)
from mdformat.renderer.typing import Render
from mdit_py_plugins.tasklists import tasklists_plugin

from mdformat_obsidian._helpers import separate_indent

from .mdit_plugins import (
    INLINE_SEP,
    OBSIDIAN_CALLOUT_PREFIX,
    dollarmath_plugin,
    footnote_plugin,
    format_footnote,
    format_footnote_block,
    format_footnote_ref,
    obsidian_callout_plugin,
    obsidian_links_plugin,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown_it import MarkdownIt
    from mdformat.renderer.typing import Render


def update_mdit(mdit: MarkdownIt) -> None:
    """Update the parser to identify Alerts."""
    mdit.use(partial(dollarmath_plugin, double_inline=True))
    mdit.use(footnote_plugin)
    mdit.use(obsidian_callout_plugin)
    mdit.use(tasklists_plugin)
    mdit.use(obsidian_links_plugin)


def _render_obsidian_callout(node: RenderTreeNode, context: RenderContext) -> str:
    """Render a `RenderTreeNode`."""
    title_line = node.markup.replace(INLINE_SEP, "")
    elements = [render for child in node.children if (render := child.render(context))]
    # Do not separate the title line from the first row
    return "\n".join([title_line, "\n\n".join(elements)]).rstrip()


def _no_render(node: RenderTreeNode, context: RenderContext) -> str:
    """Skip rendering when handled separately."""
    return ""


def _recursive_render(
    node: RenderTreeNode,
    context: RenderContext,
) -> str:
    elements = [render for child in node.children if (render := child.render(context))]
    # Do not separate the title line from the first row
    return "\n\n".join(elements).rstrip()


def paragraph(node: RenderTreeNode, context: RenderContext) -> str:  # noqa: C901
    inline_node = node.children[0]
    text = inline_node.render(context)

    if context.do_wrap:
        wrap_mode = context.options["mdformat"]["wrap"]
        if isinstance(wrap_mode, int):
            wrap_mode -= context.env["indent_width"]
            wrap_mode = max(1, wrap_mode)
        # Newlines should be mostly WRAP_POINTs by now, but there are
        # exceptional newlines that need to be preserved:
        # - hard breaks: newline defines the hard break
        # - html inline: newline vs space can be the difference between
        #                html block and html inline
        # Split the text and word wrap each section separately.
        sections = text.split("\n")
        text = "\n".join(_wrap(s, width=wrap_mode) for s in sections)

    # A paragraph can start or end in whitespace e.g. if the whitespace was
    # in decimal representation form. We need to re-decimalify it, one reason being
    # to enable "empty" paragraphs with whitespace only.
    text = decimalify_leading(codepoints.UNICODE_WHITESPACE, text)
    text = decimalify_trailing(codepoints.UNICODE_WHITESPACE, text)

    lines = text.split("\n")
    for i in range(len(lines)):
        # Strip whitespace to prevent issues like a line starting tab that is
        # interpreted as start of a code block.
        lines[i] = lines[i].rstrip()
        lindent, lstrip = separate_indent(lines[i])
        lines[i] = lstrip

        # If a line looks like an ATX heading, escape the first hash.
        if re.match(r"#{1,6}( |\t|$)", lines[i]):
            lines[i] = f"\\{lines[i]}"

        # Make sure a paragraph line does not start with ">"
        # (otherwise it will be interpreted as a block quote).
        if lines[i].startswith(">"):
            lines[i] = f"\\{lines[i]}"

        # Make sure a paragraph line does not start with "*", "-" or "+"
        # followed by a space, tab, or end of line.
        # (otherwise it will be interpreted as list item).
        if re.match(r"[-*+]( |\t|$)", lines[i]):
            lines[i] = f"\\{lines[i]}"

        # If a line starts with a number followed by "." or ")" followed by
        # a space, tab or end of line, escape the "." or ")" or it will be
        # interpreted as ordered list item.
        if re.match(r"[0-9]+\)( |\t|$)", lines[i]):
            lines[i] = lines[i].replace(")", "\\)", 1)
        if re.match(r"[0-9]+\.( |\t|$)", lines[i]):
            lines[i] = lines[i].replace(".", "\\.", 1)

        # Consecutive "-", "*" or "_" sequences can be interpreted as thematic
        # break. Escape them.
        space_removed = lines[i].replace(" ", "").replace("\t", "")
        if len(space_removed) >= 3:
            if all(c == "*" for c in space_removed):
                lines[i] = lines[i].replace("*", "\\*", 1)  # pragma: no cover
            elif all(c == "-" for c in space_removed):
                lines[i] = lines[i].replace("-", "\\-", 1)
            elif all(c == "_" for c in space_removed):
                lines[i] = lines[i].replace("_", "\\_", 1)  # pragma: no cover

        # A stripped line where all characters are "=" or "-" will be
        # interpreted as a setext heading. Escape.
        stripped = lines[i].strip(" \t")
        if all(c == "-" for c in stripped):
            lines[i] = lines[i].replace("-", "\\-", 1)
        elif all(c == "=" for c in stripped):
            lines[i] = lines[i].replace("=", "\\=", 1)

        # Check if the line could be interpreted as an HTML block.
        # If yes, prefix it with 4 spaces to prevent this.
        for html_seq_tuple in HTML_SEQUENCES:
            can_break_paragraph = html_seq_tuple[2]
            opening_re = html_seq_tuple[0]
            if can_break_paragraph and opening_re.search(lines[i]):
                lines[i] = f"    {lines[i]}"
                break

        lines[i] = lindent + lines[i]

    text = "\n".join(lines)

    return text


def bullet_list(node: RenderTreeNode, context: RenderContext) -> str:
    pre_indent = " " * (2 * int(node.level > 0))
    marker_type = pre_indent + get_list_marker_type(node)
    first_line_indent = " "
    indent = " " * len(marker_type + first_line_indent)
    block_separator = "\n" if is_tight_list(node) else "\n\n"

    with context.indented(len(indent)):
        text = ""
        for child_idx, child in enumerate(node.children):
            list_item = child.render(context)
            formatted_lines = []
            line_iterator = iter(list_item.split("\n"))
            first_line = next(line_iterator)
            formatted_lines.append(
                f"{marker_type}{first_line_indent}{first_line}"
                if first_line
                else marker_type
            )
            for line in line_iterator:
                formatted_lines.append(f"{indent}{line}" if line else "")

            text += "\n".join(formatted_lines)
            if child_idx != len(node.children) - 1:
                text += block_separator

        return text


def ordered_list(node: RenderTreeNode, context: RenderContext) -> str:
    pre_indent = " " * (2 * int(node.level > 0))
    marker_type = get_list_marker_type(node)
    first_line_indent = " "
    block_separator = "\n" if is_tight_list(node) else "\n\n"
    list_len = len(node.children)

    starting_number = node.attrs.get("start")
    if starting_number is None:
        starting_number = 1
    assert isinstance(starting_number, int)

    indent_width = len(
        f"{list_len + starting_number - 1}{marker_type}{first_line_indent}"
    )

    text = ""
    with context.indented(indent_width):
        for list_item_index, list_item in enumerate(node.children):
            list_item_text = list_item.render(context)
            formatted_lines = []
            line_iterator = iter(list_item_text.split("\n"))
            first_line = next(line_iterator)

            # Prefix first line of the list item with consecutive numbering,
            # padded with zeros to make all markers of even length.
            # E.g.
            #   002. This is the first list item
            #   003. Second item
            #   ...
            #   112. Last item
            number = starting_number + list_item_index
            pad = len(str(list_len + starting_number - 1))
            number_str = pre_indent + str(number).rjust(pad, "0")
            formatted_lines.append(
                f"{number_str}{marker_type}{first_line_indent}{first_line}"
                if first_line
                else f"{number_str}{marker_type}"
            )

            for line in line_iterator:
                formatted_lines.append(" " * indent_width + line if line else "")

            text += "\n".join(formatted_lines)
            if list_item_index != len(node.children) - 1:
                text += block_separator

        return text


# A mapping from syntax tree node type to a function that renders it.
# This can be used to overwrite renderer functions of existing syntax
# or add support for new syntax.
RENDERERS: Mapping[str, Render] = {
    "paragraph": paragraph,
    "bullet_list": bullet_list,
    "ordered_list": ordered_list,
    "footnote": format_footnote,
    "footnote_block": format_footnote_block,
    "footnote_ref": format_footnote_ref,
    "hr": (lambda node, context: "---"),
    "embed_file": lambda node, context: f"![[{node.content}]]",
    "internal_link": lambda node, context: f"[[{node.content}]]",
    "math_block": (lambda node, context: f"$${node.content}$$"),
    "math_block_label": (lambda node, context: f"$${node.content}$$ ({node.info})"),
    "math_inline": (lambda node, context: f"${node.content}$"),
    "math_inline_double": (lambda node, context: f"$${node.content}$$"),
    OBSIDIAN_CALLOUT_PREFIX: _render_obsidian_callout,
    f"{OBSIDIAN_CALLOUT_PREFIX}_title": _no_render,
    f"{OBSIDIAN_CALLOUT_PREFIX}_title_inner": _no_render,
    f"{OBSIDIAN_CALLOUT_PREFIX}_collapsed": _no_render,
    # FIXME: can I add divs without introducing new blocks?
    f"{OBSIDIAN_CALLOUT_PREFIX}_content": _recursive_render,
}
