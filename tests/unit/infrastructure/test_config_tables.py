from bot.infrastructure.config_tables import ChatRow, CommandOverrideRow


class TestRepr:
    def test_chat_row_repr_shows_platform_and_native_id(self):
        row = ChatRow(platform='whatsapp', native_id='120@g.us')

        assert repr(row) == "ChatRow(platform='whatsapp', native_id='120@g.us')"

    def test_command_override_repr_shows_command_and_state(self):
        row = CommandOverrideRow(command_name='hentai', enabled=False)

        assert repr(row) == "CommandOverrideRow(command_name='hentai', enabled=False)"
