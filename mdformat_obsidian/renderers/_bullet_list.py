from __future__ import annotations

from typing import TYPE_CHECKING

from mdformat.renderer._util import get_list_marker_type, is_tight_list

if TYPE_CHECKING:
    from mdformat.renderer import RenderContext, RenderTreeNode


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
