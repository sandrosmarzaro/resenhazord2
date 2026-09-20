from bot.infrastructure.metrics import record_agent_mapping, record_dlq, record_retry


class TestRetryAndDlq:
    def test_record_retry_increments_retry_counter(self, mocker):
        retries = mocker.patch('bot.infrastructure.metrics._retries')

        record_retry()

        retries.add.assert_called_once_with(1)

    def test_record_dlq_increments_dlq_counter(self, mocker):
        dlq = mocker.patch('bot.infrastructure.metrics._dlq')

        record_dlq()

        dlq.add.assert_called_once_with(1)


class TestAgentMapping:
    def test_record_agent_mapping_carries_outcome_provider_and_version(self, mocker):
        mappings = mocker.patch('bot.infrastructure.metrics._agent_mappings')

        record_agent_mapping('command', 'github', 'c0ffee')

        mappings.add.assert_called_once_with(
            1,
            {
                'agent.outcome': 'command',
                'agent.provider': 'github',
                'agent.prompt.version': 'c0ffee',
            },
        )
