import json

import httpx

from bot.infrastructure.failure_snapshot import FailureSnapshot


def _caught(action) -> BaseException:
    try:
        action()
    except Exception as error:  # noqa: BLE001
        return error
    raise AssertionError


def _bad_json() -> None:
    json.loads('{')


def _server_error() -> None:
    httpx.Response(500, request=httpx.Request('GET', 'https://a.io')).raise_for_status()


def _wrapped() -> None:
    try:
        _bad_json()
    except ValueError:
        raise RuntimeError from None


def _while_handling() -> None:
    try:
        _bad_json()
    except ValueError:
        raise RuntimeError  # noqa: B904


class TestStackPaths:
    def test_a_standard_library_frame_shows_its_file_name(self):
        stack = FailureSnapshot.of(_caught(_bad_json))['stack']

        assert '  decoder.py:' in stack

    def test_a_package_frame_shows_its_path_inside_the_package(self):
        stack = FailureSnapshot.of(_caught(_server_error))['stack']

        assert '  httpx/' in stack

    def test_a_test_frame_outside_the_bot_is_no_bot_frame(self):
        assert FailureSnapshot.of(_caught(_bad_json))['frame'] is None


class TestChain:
    def test_an_implicit_context_is_listed_first(self):
        stack = FailureSnapshot.of(_caught(_while_handling))['stack']

        assert stack.index('JSONDecodeError') < stack.index('RuntimeError')

    def test_a_suppressed_context_is_left_out(self):
        stack = FailureSnapshot.of(_caught(_wrapped))['stack']

        assert 'JSONDecodeError' not in stack
