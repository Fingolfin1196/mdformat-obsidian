"""Public Extension."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING

# from mdit_py_plugins.dollarmath import dollarmath_plugin
from markdown_it import MarkdownIt
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer._util import get_list_marker_type, is_tight_list
from mdformat.renderer.typing import Render
from mdit_py_plugins.tasklists import tasklists_plugin

from ._dollarmath import dollarmath_plugin
from .mdit_plugins import (
    INLINE_SEP,
    OBSIDIAN_CALLOUT_PREFIX,
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
    from mdformat.renderer.typing import Postprocess, Render


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


# A mapping from `RenderTreeNode.type` to a `Postprocess` that does
# postprocessing for the output of the `Render` function. Unlike
# `Render` funcs, `Postprocess` funcs are collaborative: any number of
# plugins can define a postprocessor for a syntax type and all of them
# will run in series.
POSTPROCESSORS: Mapping[str, Postprocess] = {
    # "bullet_list": unbounded_normalize_list,
    # "ordered_list": unbounded_normalize_list,
}
