"""An mdformat plugin for `obsidian`."""

__version__ = "0.1.0"

__plugin_name__ = "obsidian"

# FYI see source code for available interfaces:
#   https://github.com/executablebooks/mdformat/blob/5d9b573ce33bae219087984dd148894c774f41d4/src/mdformat/plugins.py
from .plugin import POSTPROCESSORS, RENDERERS, update_mdit

__all__ = ("POSTPROCESSORS", "RENDERERS", "update_mdit")
