from bot.domain.models.blocked_member import BlockedMember
from bot.domain.models.chat_config import ChatConfig

PN = '5527900000003@s.whatsapp.net'
LID = '123456789012345@lid'


class TestBlocks:
    def test_matches_a_member_by_the_alternate_form(self):
        config = ChatConfig(blocked=(BlockedMember(key=PN, alt_key=LID),))

        assert config.blocks(BlockedMember(key=LID)) is True

    def test_matches_a_sender_carrying_the_stored_form(self):
        config = ChatConfig(blocked=(BlockedMember(key=LID),))

        assert config.blocks(BlockedMember(key=PN, alt_key=LID)) is True

    def test_lets_anyone_else_through(self):
        config = ChatConfig(blocked=(BlockedMember(key=PN, alt_key=LID),))

        assert config.blocks(BlockedMember(key='5527900000004@s.whatsapp.net')) is False
