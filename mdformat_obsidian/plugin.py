"""Public Extension."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer.typing import Render
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

from ._normalize_list import normalize_list as unbounded_normalize_list
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
    import argparse
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


# ================================================================================
# End Dollar Math
# ================================================================================

# A mapping from syntax tree node type to a function that renders it.
# This can be used to overwrite renderer functions of existing syntax
# or add support for new syntax.
RENDERERS: Mapping[str, Render] = {
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


def add_cli_options(parser: argparse.ArgumentParser) -> None:
    """Force numbering."""
    for a in parser._actions:
        if a.option_strings != ["--number"]:
            continue
        a.default = True


# A mapping from `RenderTreeNode.type` to a `Postprocess` that does
# postprocessing for the output of the `Render` function. Unlike
# `Render` funcs, `Postprocess` funcs are collaborative: any number of
# plugins can define a postprocessor for a syntax type and all of them
# will run in series.
POSTPROCESSORS: Mapping[str, Postprocess] = {
    "bullet_list": unbounded_normalize_list,
    "ordered_list": unbounded_normalize_list,
}
