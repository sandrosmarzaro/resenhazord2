import pytest

from bot.domain.services.team_name_matcher import TeamNameMatcher


class TestBest:
    def test_picks_the_closest_name(self):
        assert TeamNameMatcher.best('Fluminense', ['Palmeiras', 'Fluminense']) == 'Fluminense'

    def test_returns_none_without_a_good_match(self):
        assert TeamNameMatcher.best('Fluminense', ['Completely Different FC']) is None

    def test_returns_none_without_candidates(self):
        assert TeamNameMatcher.best('Flamengo', []) is None


class TestPair:
    @pytest.mark.parametrize(
        ('official', 'short'),
        [
            ('Società Sportiva Lazio S.p.A.', 'Lazio'),
            ('Grêmio Foot-Ball Porto Alegrense', 'Grêmio'),
            ('Instituto Atlético Central Córdoba', 'Instituto (Córdoba)'),
            ('Racing Club Asociación Civil de Avellaneda', 'Racing Club'),
            ('Sociedade Esportiva Palmeiras', 'Palmeiras'),
        ],
    )
    def test_official_names_contain_the_short_ones(self, official, short):
        assert TeamNameMatcher.pair([official], ['Flamengo', short]) == {official: short}

    def test_each_candidate_is_used_once(self):
        pairs = TeamNameMatcher.pair(
            ['West Ham United', 'Leeds United', 'Inter Milan', 'AC Milan'],
            ['Leeds United', 'AC Milan', 'Internazionale'],
        )

        assert pairs == {
            'Leeds United': 'Leeds United',
            'AC Milan': 'AC Milan',
            'Inter Milan': 'Internazionale',
        }
