"""Meta-tools the agent calls to clarify or suggest instead of mapping a command.

These replace the legacy CLARIFY:/SUGGEST: text markers with structured tool
calls, so the agent's three outcomes (execute / clarify / suggest) are all
expressed as tool calls and routed by tool name, not by parsing a text prefix.
"""

CLARIFY_TOOL_NAME = 'clarify'
SUGGEST_TOOL_NAME = 'suggest'

CLARIFY_TOOL = {
    'type': 'function',
    'function': {
        'name': CLARIFY_TOOL_NAME,
        'description': 'Pergunte ao usuário quando não souber qual comando ele quer.',
        'parameters': {
            'type': 'object',
            'properties': {
                'question': {
                    'type': 'string',
                    'description': 'A pergunta de esclarecimento, em pt-br.',
                },
            },
            'required': ['question'],
        },
    },
}

SUGGEST_TOOL = {
    'type': 'function',
    'function': {
        'name': SUGGEST_TOOL_NAME,
        'description': (
            'Responda conversacionalmente sugerindo um comando similar quando o pedido '
            'foge das funções do bot, sem executar o comando.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'message': {
                    'type': 'string',
                    'description': 'Resposta conversacional em pt-br, citando o comando.',
                },
                'command': {
                    'type': 'string',
                    'description': 'O comando sugerido, ex: ,time flamengo.',
                },
            },
            'required': ['message'],
        },
    },
}

AGENT_META_TOOLS = [CLARIFY_TOOL, SUGGEST_TOOL]
