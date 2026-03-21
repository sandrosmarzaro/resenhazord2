import pytest

from bot.domain.jid import strip_jid


class TestStripJid:
    @pytest.mark.parametrize(
        ('jid', 'expected'),
        [
            ('5511999990000@s.whatsapp.net', '5511999990000'),
            ('5511999990000@S.WHATSAPP.NET', '5511999990000'),
            ('5511999990000@lid', '5511999990000'),
            ('5511999990000@LID', '5511999990000'),
            ('5511999990000', '5511999990000'),
            ('', ''),
        ],
    )
    def test_strip_jid(self, jid, expected):
        assert strip_jid(jid) == expected
