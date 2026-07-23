"""Tests for tex_timelapse.actions' registry: the single source of truth for
the pipeline's ordered stages (see the module docstring - this used to be
duplicated four times and drifted)."""

from tex_timelapse.actions import (
    ACTION_CLASSES,
    create_actions,
    create_and_init_actions,
    get_stage_names,
)
from tex_timelapse.actions.assemble_image import AssembleImageAction
from tex_timelapse.actions.compile_latex import CompileLatexAction
from tex_timelapse.actions.init_repo import InitRepoAction
from tex_timelapse.actions.pdf_to_image import PdfToImageAction
from tex_timelapse.actions.replace_text import ReplaceTextAction


def test_action_classes_order():
    assert ACTION_CLASSES == [
        InitRepoAction,
        ReplaceTextAction,
        CompileLatexAction,
        PdfToImageAction,
        AssembleImageAction,
    ]


def test_get_stage_names_matches_action_classes_order():
    expected = [cls().getName() for cls in ACTION_CLASSES]
    assert get_stage_names() == expected
    # and, concretely, the exact stage names/order the rest of the codebase
    # (CLI --stage, webserver reset/<stage>) depends on:
    assert get_stage_names() == [
        'Init Repository',
        'Replace Text',
        'Compile LaTeX',
        'PDF to Image',
        'Assemble Image',
    ]


def test_create_actions_returns_fresh_instances_each_call():
    first = create_actions()
    second = create_actions()

    assert len(first) == len(ACTION_CLASSES)
    assert [type(a) for a in first] == ACTION_CLASSES

    # different call -> different instances, not a shared module-level list
    assert first is not second
    for a, b in zip(first, second):
        assert a is not b


def test_create_and_init_actions_initialises_every_stage(project_factory):
    project = project_factory()
    actions = create_and_init_actions(project)

    assert [type(a) for a in actions] == ACTION_CLASSES

    # init() ran and pulled config values onto the instance (spot-check one
    # attribute per action that only exists post-init())
    assemble_action = next(a for a in actions if isinstance(a, AssembleImageAction))
    assert assemble_action.rows == project.config.rows
    assert assemble_action.columns == project.config.columns

    init_repo_action = next(a for a in actions if isinstance(a, InitRepoAction))
    assert init_repo_action.concatCommits == project.config.concatCommits

    replace_text_action = next(a for a in actions if isinstance(a, ReplaceTextAction))
    assert replace_text_action.text_replacements == project.config.text_replacements
