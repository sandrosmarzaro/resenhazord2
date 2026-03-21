from datetime import UTC, datetime

import structlog
from bs4 import BeautifulSoup

from bot.data.bicho import ANIMAL_EMOJIS, ARG_TO_DRAW_ID, DRAWS, PRIZE_EMOJIS
from bot.data.browser_headers import BROWSER_HEADERS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class BichoCommand(Command):
    BICHO_URL = 'https://www.eojogodobicho.com/deu-no-poste.html'
    MIN_COLUMNS = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bicho',
            args=ArgType.OPTIONAL,
            args_pattern=r'^(?:ppt|ptm|pt|ptv|ptn|cor)?$',
            category='outras',
        )

    @property
    def menu_description(self) -> str:
        return 'Exibe os resultados do Jogo do Bicho do dia.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            draws = await self._fetch_draws()
            arg = parsed.rest.lower().strip()

            if arg:
                draw_id = ARG_TO_DRAW_ID.get(arg)
                draw = next((d for d in draws if d['id'] == draw_id), None)
            else:
                published = [d for d in draws if d['published']]
                draw = published[-1] if published else None

            if not draw:
                return [Reply.to(data).text('Nenhum sorteio publicado ainda hoje. 🎲')]

            if not draw['published']:
                return [Reply.to(data).text(f'Sorteio {draw["label"]} ainda não foi publicado. ⏳')]

            now = datetime.now(tz=UTC)
            date_str = now.strftime('%d/%m/%Y')
            lines = [
                f'🎲 *Jogo do Bicho — {draw["label"]}*',
                f'📅 {date_str}',
                '',
            ]
            for i, prize in enumerate(draw['prizes']):
                emoji = PRIZE_EMOJIS[i] if i < len(PRIZE_EMOJIS) else f'{i + 1}:'
                lines.append(
                    f'{emoji}  {prize["milhar"]} · {prize["emoji"]} *{prize["animal"]}* '
                    f'(grupo {prize["group"]})'
                )

            return [Reply.to(data).text('\n'.join(lines))]
        except Exception:
            logger.exception('bicho_fetch_error')
            return [
                Reply.to(data).text(
                    'Erro ao buscar resultados do Jogo do Bicho. Tente novamente! 🎲'
                )
            ]

    @staticmethod
    def _parse_prize_row(row) -> dict | None:  # type: ignore[no-untyped-def]
        cols = row.find_all('td')
        milhar_td = row.find('td', class_='dnp-milhar')
        milhar = milhar_td.get_text(strip=True) if milhar_td else ''
        group_a = cols[2].find('a') if len(cols) >= BichoCommand.MIN_COLUMNS else None
        group_text = group_a.get_text(strip=True) if group_a else ''
        animal_a = cols[-1].find('a') if cols else None
        animal = animal_a.get_text(strip=True) if animal_a else ''

        if not (milhar and animal and group_text.isdigit()):
            return None

        return {
            'milhar': milhar,
            'animal': animal,
            'group': int(group_text),
            'emoji': ANIMAL_EMOJIS.get(animal, '🐾'),
        }

    @staticmethod
    def _parse_prizes(block) -> list[dict]:  # type: ignore[no-untyped-def]
        table = block.find('table', class_='dnp-table')
        if not table:
            return []
        prizes = []
        for row in table.find('tbody').find_all('tr'):  # type: ignore[union-attr]
            prize = BichoCommand._parse_prize_row(row)
            if prize:
                prizes.append(prize)
        return prizes

    @classmethod
    async def _fetch_draws(cls) -> list[dict]:
        response = await HttpClient.get(cls.BICHO_URL, headers=BROWSER_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        results: list[dict] = []
        for draw_info in DRAWS:
            block = soup.find(id=f'bloco-{draw_info["id"]}')
            published = bool(block and block.find(class_='status-publicado'))
            prizes = cls._parse_prizes(block) if published and block else []
            results.append(
                {
                    'id': draw_info['id'],
                    'label': draw_info['label'],
                    'published': published,
                    'prizes': prizes,
                }
            )

        return results
