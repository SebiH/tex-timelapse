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
from tex_timelapse.project import Project

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


def create_and_init_actions(project: Project) -> List[Action]:
    """Build a fresh pipeline and call init() on every stage exactly once,
    in the calling thread.

    Action.init() sets per-instance attributes from project.config (e.g.
    AssembleImageAction's self.rows/self.blur), and AssembleImageAction's
    init also has the os.makedirs side effect for the frames dir. Calling
    init() once per snapshot - as compileSnapshot used to, inside a worker
    thread pool - means every worker races to rewrite the same instance's
    attributes. It was only ever benign because every thread happened to
    write identical values; it was a data race by construction.

    The fix is procedural: build and init the pipeline exactly once, here,
    before any work is fanned out to a thread pool, then treat the
    returned actions as read-only. Both entry points into the pipeline -
    compileProject's worker pool, and a direct single-snapshot
    compileSnapshot() call (as webserver.py makes for a recompile) - must
    go through this helper rather than calling action.init() themselves.
    """
    actions = create_actions()
    for action in actions:
        action.init(project)
    return actions
