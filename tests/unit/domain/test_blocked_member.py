from bot.domain.models.blocked_member import BlockedMember
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

PN = '5527900000003@s.whatsapp.net'
LID = '123456789012345@lid'


class TestOfParticipant:
    def test_a_lid_entry_keys_by_its_phone_number(self):
        member = BlockedMember.of_participant({'id': LID, 'phoneNumber': PN})

        assert member == BlockedMember(key=PN, alt_key=LID)

    def test_a_phone_number_entry_keeps_its_lid_aside(self):
        member = BlockedMember.of_participant({'id': PN, 'lid': LID, 'admin': None})

        assert member == BlockedMember(key=PN, alt_key=LID)

    def test_a_lid_entry_without_phone_number_keys_by_the_lid(self):
        member = BlockedMember.of_participant({'id': LID})

        assert member == BlockedMember(key=LID)

    def test_drops_the_device_suffix(self):
        member = BlockedMember.of_participant({'id': '5527900000003:2@s.whatsapp.net'})

        assert member == BlockedMember(key=PN)


class TestOfSender:
    def test_a_lid_addressed_sender_carries_both_forms(self):
        data = GroupCommandDataFactory(platform='whatsapp', sender_jid=PN, participant=LID)

        assert BlockedMember.of_sender(data).keys == {PN, LID}

    def test_a_private_sender_is_its_jid(self):
        data = PrivateCommandDataFactory(platform='whatsapp', jid=PN)

        assert BlockedMember.of_sender(data).keys == {PN}

    def test_a_discord_sender_is_namespaced(self):
        data = GroupCommandDataFactory(platform='discord', sender_jid='42', participant=None)

        assert BlockedMember.of_sender(data).keys == {'discord:42'}
