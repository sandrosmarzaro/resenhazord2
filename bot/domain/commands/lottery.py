from datetime import UTC, datetime, timedelta

import httpx
import structlog
from bs4 import BeautifulSoup

from bot.data.bicho import ANIMAL_EMOJIS, ARG_TO_DRAW_ID, DRAWS, PRIZE_EMOJIS
from bot.data.browser_headers import BROWSER_HEADERS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class LotteryCommand(Command):
    BICHO_URL = 'https://www.eojogodobicho.com/deu-no-poste.html'
    YESTERDAY_URL = (
        'https://www.eojogodobicho.com/resultados/{region}/resultados-do-bicho-{date}.html'
    )
    DEFAULT_REGION = 'rio'
    MIN_COLUMNS = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bicho',
            args=ArgType.OPTIONAL,
            args_pattern=r'^(?:ppt|ptm|pt|ptv|ptn|cor)?$',
            args_label='sorteio',
            options=[OptionDef(name='regiao', values=['rio', 'sp', 'mg', 'ba', 'go', 'ce'])],
            category='other',
        )

    @property
    def menu_description(self) -> str:
        return 'Exibe os resultados do Jogo do Bicho do dia.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            region = parsed.options.get('regiao', self.DEFAULT_REGION)
            draws = await self._fetch_draws(self.BICHO_URL)
            arg = parsed.rest.lower().strip()

            if arg:
                draw_id = ARG_TO_DRAW_ID.get(arg)
                draw = next((d for d in draws if d['id'] == draw_id), None)
                if not draw:
                    return [Reply.to(data).text('Nenhum sorteio publicado ainda hoje. 🎲')]
                if not draw['published']:
                    return [
                        Reply.to(data).text(f'Sorteio {draw["label"]} ainda não foi publicado. ⏳')
                    ]
                return [self._format_draw(data, draw)]
            published = [d for d in draws if d['published']]
            if published:
                return [self._format_draw(data, published[-1])]

            return await self._fallback_yesterday(data, region)
        except Exception:
            logger.exception('bicho_fetch_error')
            return [
                Reply.to(data).text(
                    'Erro ao buscar resultados do Jogo do Bicho. Tente novamente! 🎲'
                )
            ]

    async def _fallback_yesterday(
        self, data: CommandData, region: str = 'rio'
    ) -> list[BotMessage]:
        yesterday = datetime.now(tz=UTC) - timedelta(days=1)
        date_str = yesterday.strftime('%d-%m-%Y')
        url = self.YESTERDAY_URL.format(region=region, date=date_str)
        try:
            draws = await self._fetch_draws(url)
            published = [d for d in draws if d['published']]
            if published:
                return [self._format_draw(data, published[-1], yesterday=True)]
        except (httpx.HTTPError, ValueError, KeyError):
            logger.warning('bicho_yesterday_fetch_failed', date=date_str)
        return [Reply.to(data).text('Nenhum sorteio publicado ainda hoje. 🎲')]

    @staticmethod
    def _format_draw(data: CommandData, draw: dict, *, yesterday: bool = False) -> BotMessage:
        now = datetime.now(tz=UTC)
        if yesterday:
            display_date = now - timedelta(days=1)
            suffix = ' (ontem)'
        else:
            display_date = now
            suffix = ''
        date_str = display_date.strftime('%d/%m/%Y')
        lines = [
            f'🎲 *Jogo do Bicho — {draw["label"]}*{suffix}',
            f'📅 {date_str}',
            '',
        ]
        for i, prize in enumerate(draw['prizes']):
            emoji = PRIZE_EMOJIS[i] if i < len(PRIZE_EMOJIS) else f'{i + 1}:'
            lines.append(
                f'{emoji}  {prize["milhar"]} · {prize["emoji"]} *{prize["animal"]}* '
                f'(grupo {prize["group"]})'
            )
        return Reply.to(data).text('\n'.join(lines))

    @staticmethod
    def _parse_prize_row(row) -> dict | None:  # type: ignore[no-untyped-def]
        cols = row.find_all('td')
        milhar_td = row.find('td', class_='dnp-milhar')
        milhar = milhar_td.get_text(strip=True) if milhar_td else ''
        group_a = cols[2].find('a') if len(cols) >= LotteryCommand.MIN_COLUMNS else None
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
            prize = LotteryCommand._parse_prize_row(row)
            if prize:
                prizes.append(prize)
        return prizes

    @classmethod
    async def _fetch_draws(cls, url: str) -> list[dict]:
        response = await HttpClient.get(url, headers=BROWSER_HEADERS)
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
