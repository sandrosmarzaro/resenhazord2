"""OP.GG MCP client for fetching League of Legends builds via JSON-RPC."""

import ast
import json
import re
from typing import Self

import httpx
import structlog

from bot.settings import Settings

logger = structlog.get_logger()

_ERROR_EMPTY_RESPONSE = 'Empty response from OP.GG'
_ERROR_NO_CONTENT = 'No parseable content in response'


class OpggMcpError(Exception):
    """Error communicating with OP.GG MCP server."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _error(message: str) -> OpggMcpError:
    return OpggMcpError(message)


class OpggClient:
    _instance: Self | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._session_id: str | None = None
        settings = Settings()
        self._mcp_url = settings.opgg_mcp_url

    async def get_champion_analysis(self, champion_name: str) -> dict:
        """Fetch champion analysis including builds, runes, and spells."""
        try:
            if not self._session_id:
                await self._initialize()

            champion_upper = champion_name.upper().replace(' ', '_').replace("'", '')

            result = await self._call_tool(
                'lol_get_champion_analysis',
                arguments={
                    'champion': champion_upper,
                    'game_mode': 'ranked',
                    'position': 'mid',
                    'lang': 'pt_BR',
                    'desired_output_fields': [
                        'data.summary.{id,is_rip,is_rotation,roles}',
                        'data.core_items.{ids,ids_names,pick_rate,play,win}',
                        'data.starter_items.{ids,ids_names,pick_rate,play,win}',
                        'data.runes.{id,pick_rate,play,primary_page_name,primary_rune_names,'
                        'secondary_page_name,secondary_rune_names,stat_mod_ids,stat_mod_names,win}',
                        'data.summoner_spells.{ids,ids_names,pick_rate,play,win}',
                        'data.boots.{ids,ids_names,pick_rate,play,win}',
                    ],
                },
            )
            return self._parse_result(result)
        except OpggMcpError:
            raise
        except Exception as exc:
            logger.exception('opgg_fetch_error', champion=champion_name)
            msg = f'Failed to fetch analysis for {champion_name}'
            raise OpggMcpError(msg) from exc

    async def _initialize(self) -> None:
        """Initialize MCP session."""
        init_req = {
            'jsonrpc': '2.0',
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'resenhazord2', 'version': '1.0.0'},
            },
            'id': 1,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._mcp_url, json=init_req)
            resp.raise_for_status()
            data = resp.json()
            if 'error' in data:
                err_msg = str(data['error'])
                msg = f'Initialize failed: {err_msg}'
                raise OpggMcpError(msg)
            result = data.get('result', {})
            self._session_id = result.get('protocolVersion', '1.0.0')

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a MCP tool."""
        req = {
            'jsonrpc': '2.0',
            'method': 'tools/call',
            'params': {'name': tool_name, 'arguments': arguments},
            'id': 2,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._mcp_url, json=req)
            resp.raise_for_status()
            data = resp.json()
            if 'error' in data:
                err_msg = str(data['error'])
                msg = f'Tool call failed: {err_msg}'
                raise OpggMcpError(msg)
            return data.get('result', {})

    def _parse_result(self, result: dict) -> dict:
        """Parse the tool call result."""
        if not result:
            msg = _ERROR_EMPTY_RESPONSE
            raise OpggMcpError(msg)

        content = result.get('content', [])
        if not content:
            msg = _ERROR_NO_CONTENT
            raise OpggMcpError(msg)

        for item in content:
            if item.get('type') == 'text':
                try:
                    return json.loads(item['text'])
                except json.JSONDecodeError:
                    pass
                return self._parse_custom_format(item['text'])

        msg = _ERROR_NO_CONTENT
        raise OpggMcpError(msg)

    def _parse_custom_format(self, text: str) -> dict:
        """Parse OP.GG's custom class format into a dict."""
        result = {}
        lines = text.strip().split('\n')
        field_mapping: dict[str, list[str]] = {}
        for line in lines:
            if line.startswith('class '):
                match = re.match(r'class (\w+): (.+)', line)
                if match:
                    class_name = match.group(1)
                    fields = [f.strip() for f in match.group(2).split(',')]
                    field_mapping[class_name.lower()] = fields

        final_match = re.search(r'(\w+)\(([\s\S]*)\)$', text.strip())
        if final_match:
            root_class = final_match.group(1).lower()
            data_str = final_match.group(2)
            result[root_class] = self._parse_nested(data_str, field_mapping, root_class)

        return result

    def _parse_nested(
        self, data_str: str, field_mapping: dict[str, list[str]], context: str
    ) -> dict:
        """Recursively parse nested class data."""
        fields = field_mapping.get(context, [])
        args = self._split_args(data_str)
        result = {}

        for idx, raw_arg in enumerate(args):
            field_name = fields[idx] if idx < len(fields) else f'field_{idx}'
            result[field_name] = self._parse_arg(raw_arg, field_mapping)

        return result

    def _split_args(self, data_str: str) -> list[str]:
        """Split arguments handling nested parentheses and lists."""
        args = []
        depth = 0
        start = 0
        in_list = False
        list_depth = 0

        for i, char in enumerate(data_str):
            if char == '[':
                list_depth += 1
                in_list = True
            elif char == ']':
                list_depth -= 1
                if list_depth == 0:
                    in_list = False
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0 and not in_list:
                args.append(data_str[start:i].strip())
                start = i + 1
        args.append(data_str[start:].strip())
        return args

    def _parse_arg(
        self, arg: str, field_mapping: dict[str, list[str]]
    ) -> dict | list | str | int | float:
        """Parse a single argument."""
        arg = arg.strip()

        if arg.startswith('[') and arg.endswith(']'):
            return self._parse_list(arg)
        if '(' in arg and arg.endswith(')'):
            nested_match = re.match(r'(\w+)\((.*)\)$', arg)
            if nested_match:
                nested_class = nested_match.group(1).lower()
                nested_data = nested_match.group(2)
                return self._parse_nested(nested_data, field_mapping, nested_class)
        return self._parse_value(arg)

    def _parse_list(self, text: str) -> list:
        """Parse a list like [1, 2, 3] or ['a', 'b']."""
        try:
            return ast.literal_eval(text)
        except Exception:  # noqa: BLE001
            return [text]

    def _parse_value(self, text: str) -> str | int | float:
        """Parse a value that could be string, int, or float."""
        text = text.strip()
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        is_quoted = (text.startswith('"') and text.endswith('"')) or (
            text.startswith("'") and text.endswith("'")
        )
        if is_quoted:
            return text[1:-1]
        return text


opgg_client = OpggClient()
