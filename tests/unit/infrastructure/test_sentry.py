from collections.abc import Callable

from bot.infrastructure.sentry import init_sentry


class RateLimitError(Exception):
    pass


class AMQPConnectionError(Exception):
    pass


def _before_send(mocker) -> Callable:
    init = mocker.patch('bot.infrastructure.sentry.sentry_sdk.init')

    init_sentry('https://public@o0.ingest.sentry.io/1')

    return init.call_args.kwargs['before_send']


class TestDropsExpectedNoise:
    def test_drops_absorbed_provider_rate_limit(self, mocker):
        before_send = _before_send(mocker)
        hint = {'exc_info': (RateLimitError, RateLimitError('Too many requests'), None)}

        assert before_send({}, hint) is None

    def test_drops_broker_refusal_as_log_message(self, mocker):
        before_send = _before_send(mocker)
        event = {
            'logentry': {
                'message': 'error when creating transport: '
                "<AMQPConnectionError: (111, 'Connection refused')>",
            },
        }

        assert before_send(event, {}) is None

    def test_drops_broker_refusal_as_exception(self, mocker):
        before_send = _before_send(mocker)
        error = AMQPConnectionError("(111, 'Connection refused')")
        hint = {'exc_info': (AMQPConnectionError, error, None)}

        assert before_send({}, hint) is None


class TestKeepsRealErrors:
    def test_keeps_unrelated_exception(self, mocker):
        before_send = _before_send(mocker)
        event = {'message': 'boom'}
        hint = {'exc_info': (ValueError, ValueError('boom'), None)}

        assert before_send(event, hint) == event

    def test_keeps_unrelated_log_message(self, mocker):
        before_send = _before_send(mocker)
        event = {'logentry': {'message': 'database write failed'}}

        assert before_send(event, {}) == event

    def test_keeps_broker_close_that_is_not_a_refusal(self, mocker):
        before_send = _before_send(mocker)
        event = {'message': 'AMQPConnectionError: authentication failure'}

        assert before_send(event, {}) == event
