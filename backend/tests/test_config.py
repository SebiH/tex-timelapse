"""Tests for tex_timelapse.config: the Config dataclass coercion rules."""

import pytest

from tex_timelapse.config import (
    Config,
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_str,
    coerce_text_replacements,
)


# ---------------------------------------------------------------------------
# coerce_bool - the documented rule
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('value', ['false', 'False', '0', ''])
def test_coerce_bool_documented_false_strings(value):
    assert coerce_bool(value) is False


@pytest.mark.parametrize('value', [
    # the implementation normalises via .strip().lower() before comparing,
    # so case/whitespace variants of the documented false strings are also
    # false - broader than, but consistent with, the documented rule.
    'FALSE', 'FaLsE', ' false ', '0 ', ' 0', '   ',
])
def test_coerce_bool_false_strings_are_normalised_first(value):
    assert coerce_bool(value) is False


@pytest.mark.parametrize('value', [
    'true', 'True', '1', 'yes', 'no', 'anything-else', 'FALSEY',
])
def test_coerce_bool_every_other_nonempty_string_is_true(value):
    # 'no'/'anything-else' aren't in the false-list either - the rule only
    # special-cases 'false'/'0'/'' (and their case/whitespace variants), not
    # a broader falsy-word list. 'FALSEY' also isn't 'false' after
    # stripping/lowering, so it stays true.
    assert coerce_bool(value) is True


def test_coerce_bool_plain_bool_passthrough():
    assert coerce_bool(True) is True
    assert coerce_bool(False) is False


def test_coerce_bool_none_is_false():
    assert coerce_bool(None) is False


def test_coerce_bool_non_string_falls_back_to_python_bool():
    assert coerce_bool(0) is False
    assert coerce_bool(1) is True
    assert coerce_bool([]) is False
    assert coerce_bool([1]) is True


def test_coerce_bool_would_be_wrong_with_plain_bool_builtin():
    # The whole reason coerce_bool exists: bool('false') is True in Python.
    assert bool('false') is True
    assert coerce_bool('false') is False


# ---------------------------------------------------------------------------
# coerce_int / coerce_float
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('value,expected', [
    ('3', 3),
    ('-1', -1),
    (3, 3),
    (3.9, 3),
    ('3.9', 3),  # falls back to float parse then int()
    (True, 1),   # bool is an int subclass; coerce_int special-cases it explicitly
    (False, 0),
])
def test_coerce_int_valid_values(value, expected):
    assert coerce_int(value) == expected


@pytest.mark.parametrize('value', [None, ''])
def test_coerce_int_none_or_empty_uses_default(value):
    assert coerce_int(value, default=42) == 42
    assert coerce_int(value) == 0


def test_coerce_int_unparseable_uses_default():
    assert coerce_int('not-a-number', default=7) == 7
    assert coerce_int(object(), default=7) == 7


@pytest.mark.parametrize('value,expected', [
    ('3.5', 3.5),
    ('3', 3.0),
    (3, 3.0),
    (-0.25, -0.25),
])
def test_coerce_float_valid_values(value, expected):
    assert coerce_float(value) == expected


@pytest.mark.parametrize('value', [None, ''])
def test_coerce_float_none_or_empty_uses_default(value):
    assert coerce_float(value, default=1.5) == 1.5


def test_coerce_float_unparseable_uses_default():
    assert coerce_float('not-a-float', default=2.0) == 2.0


def test_coerce_str_none_uses_default():
    assert coerce_str(None, default='fallback') == 'fallback'


def test_coerce_str_stringifies_non_string():
    assert coerce_str(3) == '3'
    assert coerce_str(3.5) == '3.5'


def test_coerce_text_replacements_drops_malformed_entries():
    value = [
        {'old': 'a', 'new': 'b'},
        {'old': 'x'},  # missing 'new' -> dropped
        'not-a-dict',  # dropped
        {'old': 1, 'new': 2},  # coerced to strings
    ]
    assert coerce_text_replacements(value) == [
        {'old': 'a', 'new': 'b'},
        {'old': '1', 'new': '2'},
    ]


def test_coerce_text_replacements_non_list_returns_empty():
    assert coerce_text_replacements(None) == []
    assert coerce_text_replacements('not-a-list') == []


# ---------------------------------------------------------------------------
# Config.from_dict / to_dict
# ---------------------------------------------------------------------------

def test_from_dict_coerces_string_values_from_yaml_or_web_ui():
    config = Config.from_dict({
        'rows': '4',
        'columns': '8',
        'blur': '2.5',
        'highlightChanges': 'false',
        'crop': '1',
        'concatCommits': '3',
    })
    assert config.rows == 4 and isinstance(config.rows, int)
    assert config.columns == 8 and isinstance(config.columns, int)
    assert config.blur == 2.5 and isinstance(config.blur, float)
    assert config.highlightChanges is False
    assert config.crop is True
    assert config.concatCommits == 3


def test_from_dict_missing_fields_fall_back_to_defaults_dict():
    defaults = {'rows': 9, 'columns': 2}
    config = Config.from_dict({'columns': 5}, defaults=defaults)
    # 'rows' missing from data -> falls back to defaults
    assert config.rows == 9
    # 'columns' present in data -> data wins over defaults
    assert config.columns == 5


def test_from_dict_missing_everywhere_falls_back_to_dataclass_default():
    config = Config.from_dict({}, defaults={})
    assert config.rows == Config.rows  # dataclass field default (3)
    assert config.latexCmd == Config.latexCmd


def test_from_dict_handles_none_data_and_defaults():
    config = Config.from_dict(None, defaults=None)
    assert config.rows == 3
    assert config.columns == 6


def test_from_dict_ignores_unknown_keys():
    config = Config.from_dict({'startDate': '2024-01-01', 'rows': 5})
    assert config.rows == 5
    assert not hasattr(config, 'startDate')


def test_to_dict_round_trip():
    config = Config.from_dict({'rows': 4, 'highlightChanges': 'false'})
    as_dict = config.to_dict()
    assert as_dict['rows'] == 4
    assert as_dict['highlightChanges'] is False

    round_tripped = Config.from_dict(as_dict)
    assert round_tripped == config


def test_to_dict_has_no_underscore_keys():
    config = Config()
    assert all(not k.startswith('_') for k in config.to_dict())
