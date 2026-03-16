import random

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

LOL_ROLE_EMOJIS = {
    'Fighter': '⚔️',
    'Tank': '🛡️',
    'Mage': '🔮',
    'Assassin': '🗡️',
    'Marksman': '🏹',
    'Support': '💚',
}

DDRAGON_VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'
DDRAGON_CHAMPIONS_URL = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/champion.json'
DDRAGON_SPLASH_URL = (
    'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion_id}_0.jpg'
)


class LeagueOfLegendsCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='lol', flags=['show', 'dm'], category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Receba um campeão aleatório de League of Legends.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            version_resp = await HttpClient.get(DDRAGON_VERSIONS_URL)
            version_resp.raise_for_status()
            version = version_resp.json()[0]

            champs_resp = await HttpClient.get(DDRAGON_CHAMPIONS_URL.format(version=version))
            champs_resp.raise_for_status()
            champions = champs_resp.json()['data']

            champion = random.choice(list(champions.values()))  # noqa: S311
            splash_url = DDRAGON_SPLASH_URL.format(champion_id=champion['id'])

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
                f'⚔️ Ataque: {info["attack"]}/10',
                f'🛡️ Defesa: {info["defense"]}/10',
                f'🔮 Magia: {info["magic"]}/10',
                f'🎯 Dificuldade: {info["difficulty"]}/10',
                '',
                f'> {champion["blurb"]}',
            ]

            return [Reply.to(data).image(splash_url, '\n'.join(lines))]
        except Exception:
            logger.exception('lol_fetch_error')
            return [
                Reply.to(data).text('Erro ao buscar campeão de LoL. Tente novamente mais tarde! 🎮')
            ]
