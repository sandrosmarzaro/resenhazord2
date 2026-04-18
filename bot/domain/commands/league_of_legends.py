import random

import structlog

from bot.data.league_of_legends import (
    LOL_ITEM_EMOJIS,
    LOL_ROLE_EMOJIS,
    LOL_SPELL_BY_ID,
    LOL_SPELL_EMOJIS,
    LOL_VALID_SPELLS,
)
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient
from bot.infrastructure.opgg_client import OpggMcpError, opgg_client

logger = structlog.get_logger()


class LeagueOfLegendsCommand(Command):
    VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'
    CHAMPIONS_URL = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/champion.json'
    SPELLS_URL = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/summoner.json'
    SPLASH_URL = 'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion_id}_0.jpg'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='lol',
            flags=[Flag.SHOW, Flag.DM, 'build'],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD, Platform.TELEGRAM],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um campeão aleatório de League of Legends.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            version_resp = await HttpClient.get(self.VERSIONS_URL)
            version_resp.raise_for_status()
            version = version_resp.json()[0]

            champs_resp = await HttpClient.get(self.CHAMPIONS_URL.format(version=version))
            champs_resp.raise_for_status()
            champions = champs_resp.json()['data']

            champion = random.choice(list(champions.values()))  # noqa: S311
            splash_url = self.SPLASH_URL.format(champion_id=champion['id'])

            roles_line = '  '.join(
                f'{LOL_ROLE_EMOJIS.get(tag, "❓")} {tag}' for tag in champion['tags']
            )
            info = champion['info']
            lines = [
                f'*{champion["name"]}*',
                f'_{champion["title"]}_',
                '',
                roles_line,
                '',
                f'⚔️ {info["attack"]}/10   🛡️ {info["defense"]}/10',
                f'🔮 {info["magic"]}/10   🎯 {info["difficulty"]}/10',
                '',
            ]

            has_build = 'build' in parsed.flags
            if has_build:
                build_info = await self._fetch_opgg_build(champion['name'])
                if build_info:
                    lines.extend(build_info)
                    lines.append('')
                else:
                    spells_resp = await HttpClient.get(self.SPELLS_URL.format(version=version))
                    spells_resp.raise_for_status()
                    spells_data = spells_resp.json()['data']

                    valid_spell_names = [
                        name
                        for name, spell in spells_data.items()
                        if spell['name'] in LOL_VALID_SPELLS
                    ]
                    chosen_spells = random.sample(valid_spell_names, 2)

                    spell_emoji = LOL_SPELL_EMOJIS.get
                    spells_line = '  '.join(
                        f'{spell_emoji(spells_data[key]["name"], "❓")} {spells_data[key]["name"]}'
                        for key in chosen_spells
                    )
                    lines.extend([f'🧙‍♂️ {spells_line}', ''])

            lines.append(f'> {champion["blurb"]}')

            return [Reply.to(data).image(splash_url, '\n'.join(lines))]
        except Exception:
            logger.exception('lol_fetch_error')
            return [
                Reply.to(data).text('Erro ao buscar campeão de LoL. Tente novamente mais tarde! 🎮')
            ]

    async def _fetch_opgg_build(self, champion_name: str) -> list[str] | None:
        try:
            analysis = await opgg_client.get_champion_analysis(champion_name=champion_name)
            data = analysis.get('lolgetchampionanalysis', {}).get('data', {})
        except OpggMcpError:
            logger.warning('opgg_build_fetch_failed', champion=champion_name)
            return None
        except Exception:
            logger.exception('opgg_unexpected_error', champion=champion_name)
            return None
        else:
            if not data:
                return None

            lines: list[str] = []
            self._add_items_to_lines(data, lines)
            self._add_boots_to_lines(data, lines)
            self._add_runes_to_lines(data, lines)
            self._add_spells_to_lines(data, lines)

            if lines:
                return lines
            return None

    def _add_items_to_lines(self, data: dict, lines: list[str]) -> None:
        core_items = data.get('core_items', {})
        item_names = core_items.get('ids_names', [])
        if item_names:
            win_rate = core_items.get('win', 0)
            item_icons = '  '.join(
                f'{LOL_ITEM_EMOJIS.get(name, "📦")} {name}' for name in item_names[:4]
            )
            lines.append(f'🛡️ Build ({win_rate} jogos):')
            lines.append(item_icons)

    def _add_boots_to_lines(self, data: dict, lines: list[str]) -> None:
        boots = data.get('boots', {})
        boot_names = boots.get('ids_names', [])
        if boot_names:
            lines.append(f'👟 {boot_names[0]}')

    def _add_runes_to_lines(self, data: dict, lines: list[str]) -> None:
        runes = data.get('runes', {})
        primary = runes.get('primary_page_name', '')
        primary_runes = runes.get('primary_rune_names', [])
        secondary = runes.get('secondary_page_name', '')
        secondary_runes = runes.get('secondary_rune_names', [])

        if not primary or not primary_runes:
            return

        rune_line = f'{primary}: {", ".join(primary_runes[:2])}'
        if secondary and secondary_runes:
            rune_line += f'  •  {secondary}: {", ".join(secondary_runes[:2])}'
        lines.append(f'🏆 Runes: {rune_line}')

    def _add_spells_to_lines(self, data: dict, lines: list[str]) -> None:
        spells = data.get('summoner_spells', {})
        spell_ids = spells.get('ids', [])
        if not spell_ids:
            return

        spell_names = [LOL_SPELL_BY_ID.get(sid, f'Spell {sid}') for sid in spell_ids[:2]]
        filtered = [s for s in spell_names if s in LOL_VALID_SPELLS]
        if filtered:
            spell_line = '  '.join(f'{LOL_SPELL_EMOJIS.get(s, "❓")} {s}' for s in filtered)
            lines.append(f'🧙‍♂️ {spell_line}')
