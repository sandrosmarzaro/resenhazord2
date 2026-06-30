from bot.infrastructure.database import Database


class TestEngine:
    def test_configures_pool_to_survive_neon_idle_disconnects(self, mocker):
        create_engine = mocker.patch('bot.infrastructure.database.create_async_engine')
        Database.configure('postgresql+asyncpg://localhost/test')

        Database.engine()

        _, kwargs = create_engine.call_args
        assert kwargs['pool_pre_ping'] is True
        assert kwargs['pool_recycle'] == 300
