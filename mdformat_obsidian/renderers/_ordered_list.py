from __future__ import annotations

from typing import TYPE_CHECKING

from mdformat.renderer._util import get_list_marker_type, is_tight_list

if TYPE_CHECKING:
    from mdformat.renderer import RenderContext, RenderTreeNode


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
