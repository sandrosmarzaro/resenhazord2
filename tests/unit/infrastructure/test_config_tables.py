from bot.infrastructure.config_tables import BlockedUserRow, ChatRow, CommandOverrideRow


class TestRepr:
    def test_chat_row_repr_shows_platform_and_native_id(self):
        row = ChatRow(platform='whatsapp', native_id='120@g.us')

        assert repr(row) == "ChatRow(platform='whatsapp', native_id='120@g.us')"

    def test_command_override_repr_shows_command_and_state(self):
        row = CommandOverrideRow(command_name='hentai', enabled=False)

        assert repr(row) == "CommandOverrideRow(command_name='hentai', enabled=False)"

    def test_blocked_user_repr_shows_both_keys(self):
        row = BlockedUserRow(user_key='55@s.whatsapp.net', alt_key='1@lid')

        assert repr(row) == "BlockedUserRow(user_key='55@s.whatsapp.net', alt_key='1@lid')"
