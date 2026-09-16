from bot.infrastructure.metrics import record_dlq, record_retry


class TestRetryAndDlq:
    def test_record_retry_increments_retry_counter(self, mocker):
        retries = mocker.patch('bot.infrastructure.metrics._retries')

        record_retry()

        retries.add.assert_called_once_with(1)

    def test_record_dlq_increments_dlq_counter(self, mocker):
        dlq = mocker.patch('bot.infrastructure.metrics._dlq')

        record_dlq()

        dlq.add.assert_called_once_with(1)
