"""Public Extension."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer.typing import Render
from mdit_py_plugins.tasklists import tasklists_plugin

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
from .renderers import bullet_list, ordered_list, paragraph

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


def _recursive_render(
    node: RenderTreeNode,
    context: RenderContext,
) -> str:
    elements = [render for child in node.children if (render := child.render(context))]
    # Do not separate the title line from the first row
    return "\n\n".join(elements).rstrip()


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
    "hr": (lambda node, ctx: "---"),
    "embed_file": lambda node, ctx: f"![[{node.content}]]",
    "internal_link": lambda node, ctx: f"[[{node.content}]]",
    "math_block": (lambda node, ctx: f"$${node.content}$$"),
    "math_block_label": (lambda node, ctx: f"$${node.content}$$ ({node.info})"),
    "math_inline": (lambda node, ctx: f"${node.content}$"),
    "math_inline_double": (lambda node, ctx: f"$${node.content}$$"),
    OBSIDIAN_CALLOUT_PREFIX: _render_obsidian_callout,
    f"{OBSIDIAN_CALLOUT_PREFIX}_title": (lambda node, ctx: ""),
    f"{OBSIDIAN_CALLOUT_PREFIX}_title_inner": (lambda node, ctx: ""),
    f"{OBSIDIAN_CALLOUT_PREFIX}_collapsed": (lambda node, ctx: ""),
    # FIXME: can I add divs without introducing new blocks?
    f"{OBSIDIAN_CALLOUT_PREFIX}_content": _recursive_render,
}
