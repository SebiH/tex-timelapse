"""Single source of truth for the compile pipeline's ordered stages.

Previously this ordered list of five actions was duplicated in
tex-timelapse.py and three times in webserver.py - one copy of which had
already drifted (a hardcoded stage list omitted 'Replace Text'). Adding,
removing or reordering a stage now means editing ACTION_CLASSES here, and
nowhere else.
"""

from typing import List, Type

from tex_timelapse.actions.action import Action
from tex_timelapse.actions.init_repo import InitRepoAction
from tex_timelapse.actions.replace_text import ReplaceTextAction
from tex_timelapse.actions.compile_latex import CompileLatexAction
from tex_timelapse.actions.pdf_to_image import PdfToImageAction
from tex_timelapse.actions.assemble_image import AssembleImageAction

ACTION_CLASSES: List[Type[Action]] = [
    InitRepoAction,
    ReplaceTextAction,
    CompileLatexAction,
    PdfToImageAction,
    AssembleImageAction,
]


def create_actions() -> List[Action]:
    """Fresh, *uninitialised* action instances in pipeline order.

    Each call returns brand-new instances - never a shared module-level
    list - so callers can safely mutate/init their own copy without
    stepping on anyone else's.
    """
    return [cls() for cls in ACTION_CLASSES]


def get_stage_names() -> List[str]:
    """Ordered stage names, e.g. for matching a --stage/<stage> argument
    against `Action.getName()` without hardcoding the list a second time."""
    return [action.getName() for action in create_actions()]
