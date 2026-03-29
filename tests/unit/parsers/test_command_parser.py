import pytest

from bot.domain.commands.base import ArgType, CommandConfig, OptionDef
from bot.domain.parsers.command_parser import CommandParser


class TestSimpleCommand:
    def setup_method(self):
        self.parser = CommandParser(CommandConfig(name='oi'))

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', oi', True),
            (',oi', True),
            (', OI', True),
            ('  , oi  ', True),
            ('\t,\toi\t', True),
            ('oi', False),
            (', oi test', False),
            (', oie', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_simple(self):
        result = self.parser.parse(', oi')
        assert result.command_name == 'oi'
        assert len(result.flags) == 0
        assert len(result.options) == 0
        assert result.rest == ''


class TestCommandWithDiacritics:
    def setup_method(self):
        self.parser = CommandParser(CommandConfig(name='pokémon', flags=['team', 'show', 'dm']))

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',pokémon', True),
            (',pokemon', True),
            (',pokémon team', True),
            (',pokémon show dm', True),
            (',pokémon dm show', True),
            (',pokémon team show dm', True),
            (',pokémon dm team show', True),
            (',pokemon team show dm', True),
            (',pokémon hello', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_flags(self):
        result = self.parser.parse(',pokémon team show dm')
        assert result.command_name == 'pokémon'
        assert result.flags == {'team', 'show', 'dm'}
        assert result.rest == ''

    def test_parse_partial_flags(self):
        result = self.parser.parse(',pokémon show')
        assert result.flags == {'show'}

    def test_parse_no_flags(self):
        result = self.parser.parse(',pokémon')
        assert len(result.flags) == 0


class TestCommandWithAliases:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(name='anime', aliases=['manga'], flags=['show', 'dm'])
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',anime', True),
            (',manga', True),
            (',anime show', True),
            (',manga dm', True),
            (',anime show dm', True),
            (',animee', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_anime(self):
        result = self.parser.parse(',anime show')
        assert result.command_name == 'anime'
        assert result.flags == {'show'}

    def test_parse_manga(self):
        result = self.parser.parse(',manga dm')
        assert result.command_name == 'manga'
        assert result.flags == {'dm'}


class TestCommandWithOptions:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='stic',
                options=[OptionDef(name='type', values=['crop', 'full', 'circle', 'rounded'])],
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',stic', True),
            (',stic crop', True),
            (',stic full', True),
            (',stic circle', True),
            (',stic rounded', True),
            (',stic hello', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_option_value(self):
        result = self.parser.parse(',stic crop')
        assert result.options.get('type') == 'crop'

    def test_parse_no_option(self):
        result = self.parser.parse(',stic')
        assert len(result.options) == 0


class TestCommandWithOptionsAndFlagsAndArgs:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='img',
                options=[
                    OptionDef(name='resolution', values=['sd', 'hd', 'fhd', 'qhd', '4k']),
                    OptionDef(
                        name='model',
                        values=[
                            'flux-pro',
                            'flux-realism',
                            'flux-anime',
                            'flux-3d',
                            'flux',
                            'cablyai',
                            'turbo',
                        ],
                    ),
                ],
                flags=['show', 'dm'],
                args=ArgType.OPTIONAL,
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',img', True),
            (',img hd', True),
            (',img hd flux-pro a cat', True),
            (',img show dm a cat', True),
            (',img 4k turbo show dm a beautiful sunset', True),
            # order-independent: flags before options
            (',img show hd a cat', True),
            (',img dm show turbo 4k a sunset', True),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_options_flags_rest(self):
        result = self.parser.parse(',img hd flux-pro show dm a beautiful cat')
        assert result.options.get('resolution') == 'hd'
        assert result.options.get('model') == 'flux-pro'
        assert result.flags == {'show', 'dm'}
        assert result.rest == 'a beautiful cat'

    def test_parse_only_prompt(self):
        result = self.parser.parse(',img a beautiful cat')
        assert len(result.options) == 0
        assert len(result.flags) == 0
        assert result.rest == 'a beautiful cat'

    def test_parse_no_args(self):
        result = self.parser.parse(',img')
        assert result.rest == ''


class TestCommandWithPatternOption:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='áudio',
                options=[OptionDef(name='lang', pattern=r'[A-Za-z]{2}-[A-Za-z]{2}')],
                flags=['show', 'dm'],
                args=ArgType.OPTIONAL,
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',áudio', True),
            (',audio', True),
            (',áudio pt-BR hello', True),
            (',audio en-US show dm hello', True),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_pattern_option(self):
        result = self.parser.parse(',áudio pt-BR hello world')
        assert result.options.get('lang') == 'pt-BR'
        assert result.rest == 'hello world'

    def test_parse_no_lang(self):
        result = self.parser.parse(',áudio hello world')
        assert len(result.options) == 0
        assert result.rest == 'hello world'


class TestCommandWithNameContainingSpace:
    def setup_method(self):
        self.parser = CommandParser(CommandConfig(name='rule 34', flags=['show', 'dm']))

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',rule 34', True),
            (',rule 34 show', True),
            (',rule 34 show dm', True),
            (', rule 34', True),
            (',rule34', True),
            (',rule', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse(self):
        result = self.parser.parse(',rule 34 show dm')
        assert result.command_name == 'rule 34'
        assert result.flags == {'show', 'dm'}


class TestCommandWithArgsPattern:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='ban',
                args=ArgType.OPTIONAL,
                args_pattern=r'^(?:@\d+(?:\s+@\d+)*)?$',
                group_only=True,
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',ban', True),
            (',ban @123', True),
            (',ban @123 @456', True),
            (',ban hello', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected


class TestCommandGroupOnly:
    def setup_method(self):
        self.parser = CommandParser(CommandConfig(name='adm', group_only=True))

    def test_still_matches(self):
        assert self.parser.matches(',adm') is True


class TestCommandWithRequiredArgs:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='fuck',
                args=ArgType.REQUIRED,
                args_pattern=r'^@\d+\s*$',
                group_only=True,
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',fuck @123', True),
            (',fuck', False),
            (',fuck hello', False),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected


class TestCommandWithMultipleOptions:
    def setup_method(self):
        self.parser = CommandParser(
            CommandConfig(
                name='bíblia',
                options=[
                    OptionDef(name='lang', values=['pt', 'en']),
                    OptionDef(
                        name='version',
                        values=['nvi', 'ra', 'acf', 'kjv', 'bbe', 'apee', 'rvr'],
                    ),
                ],
                args=ArgType.OPTIONAL,
            )
        )

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',bíblia', True),
            (',biblia', True),
            (',bíblia pt nvi', True),
            (',biblia en kjv Genesis 1:1', True),
            # order-independent: version before lang
            (',bíblia nvi pt Genesis 1:1', True),
        ],
    )
    def test_matches(self, text, expected):
        assert self.parser.matches(text) == expected

    def test_parse_options_and_rest(self):
        result = self.parser.parse(',bíblia pt nvi Genesis 1:1')
        assert result.options.get('lang') == 'pt'
        assert result.options.get('version') == 'nvi'
        assert result.rest == 'Genesis 1:1'

    def test_parse_no_options(self):
        result = self.parser.parse(',bíblia')
        assert len(result.options) == 0
        assert result.rest == ''
