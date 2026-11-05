import pytest

from bot.domain.services.minors_filter import MinorsFilter


@pytest.fixture
def dropped(mocker):
    return mocker.patch('bot.infrastructure.metrics._minors_dropped')


class TestFlags:
    def test_flags_a_label_holding_a_minor_term(self, dropped):
        assert MinorsFilter.flags('redgifs', ['Teen', 'Feet']) is True

    def test_matches_inside_a_longer_label_whatever_the_case(self, dropped):
        assert MinorsFilter.flags('rule34', ['schoolGIRL_uniform']) is True

    def test_lets_clean_labels_through(self, dropped):
        assert MinorsFilter.flags('redgifs', ['Feet', 'Redhead']) is False


class TestCompliance:
    def test_counts_each_drop_by_source(self, dropped):
        MinorsFilter.flags('hentai', ['loli'])

        dropped.add.assert_called_once_with(1, {'source': 'hentai'})

    def test_clean_labels_count_nothing(self, dropped):
        MinorsFilter.flags('hentai', ['vanilla'])

        dropped.add.assert_not_called()
