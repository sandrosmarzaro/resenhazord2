import random

import structlog

from bot.data.league_of_legends import LOL_ROLE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class LeagueOfLegendsCommand(Command):
    VERSIONS_URL = 'https://ddragon.leagueoflegends.com/api/versions.json'
    CHAMPIONS_URL = 'https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/champion.json'
    SPLASH_URL = 'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion_id}_0.jpg'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='lol', flags=['show', 'dm'], category='random')

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
                f'> {champion["blurb"]}',
            ]

            return [Reply.to(data).image(splash_url, '\n'.join(lines))]
        except Exception:
            logger.exception('lol_fetch_error')
            return [
                Reply.to(data).text('Erro ao buscar campeão de LoL. Tente novamente mais tarde! 🎮')
            ]
