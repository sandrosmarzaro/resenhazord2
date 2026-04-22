"""Few-shot examples for LLM agent command mapping.

These examples are used in the system prompt to help the LLM
map natural language requests to the correct bot commands.

Language: pt-br (matches user voice and menu_description)
"""

AGENT_EXAMPLES = [
    # Score command
    ('mostrar placar dos jogos', 'score --now'),
    ('placar football agora', 'score --now'),
    ('jogos encerrados', 'score --past'),
    ('próximos jogos', 'score --next'),
    ('ver placar ao vivo', 'score --now'),
    ('Resultados dos jogos', 'score --past --now'),
    # Football team
    ('time completo do flamengo', 'time flamengo'),
    ('escalação do palmeiras', 'time palmeiras'),
    ('time do corinthians', 'time corinthians'),
    ('que time é o flamengo', 'time flamengo'),
    ('ranking times brasileiros', 'time --liga br'),
    # Score / Tabela
    ('tabela do brasileiro', 'tabela br'),
    ('classificação champions', 'tabela bl'),
    # Menu
    ('lista de comandos', 'menu'),
    ('o que você pode fazer', 'menu'),
    ('comandos disponíveis', 'menu'),
    # Random - dados
    ('jogar dado', 'd20'),
    ('rolar dados', 'd20 2d6'),
    ('sortear número', 'd20'),
    # Random - cars
    ('me mande um carro', 'carro'),
    ('foto de carro', 'carro'),
    ('carro aleatório', 'carro'),
    ('mostra um carro', 'carro'),
    # Random - animals
    ('animal aleatório', 'animal'),
    ('foto de cachorro', 'puppy'),
    ('foto de gato', 'puppy cat'),
    # Random - poker/battle
    ('carta de poker', 'carta'),
    ('carta aleatória baralho', 'carta'),
    ('carta yu-gi-oh', 'ygo'),
    ('carta magic', 'mtg'),
    ('carta pokemon', 'pokemon'),
    ('carta hearthstone', 'hs'),
    ('carta clash royale', 'cr'),
    # Random - food/drink
    ('cerveja aleatória', 'cerveja'),
    ('receita de comida', 'comida'),
    ('comida aleatória', 'comida'),
    # Random - anime/game/movie
    ('anime aleatório', 'anime'),
    ('manga aleatório', 'manga'),
    ('jogo aleatório', 'game'),
    ('filme aleatório', 'filme'),
    ('série aleatória', 'série'),
    # Random - other
    ('fato aleatório', 'fato'),
    ('horóscopo', 'horóscopo'),
    ('jogador aleatório', 'jogador'),
    ('moeda conversão', 'moeda'),
    # Greetings
    ('oi', 'oi'),
    ('me mande um oi', 'oi'),
    # Music
    ('tocar música', 'música'),
    ('achar música', 'música'),
    ('baixar música', 'música'),
    ('música funk', 'música funk'),
    ('funk', 'música funk'),
    ('rock', 'música rock'),
    ('pop', 'música pop'),
    ('tocar uma música', 'música'),
    # Download
    ('baixar vídeo', 'dl'),
    ('áudio do youtube', 'dl'),
    # Info
    ('jogo do bicho', 'bicho'),
    ('fase da lua', 'lua'),
    # Unknown - use menu
    ('não sei', 'menu'),
]

SYSTEM_PROMPT_TEMPLATE = """Você é um assistente que mapeia pedidos
naturais em comandos do bot Resenhazord.

Lista de comandos disponíveis com descrições:
{command_list}

Exemplos de mapeamento (USE ESSES PARA INFERIR PADRÕES):
{examples}

IMPORTANTE:
- infira o comando baseado na descrição e semântica (ex: funk->música, video->dl)
- Responda APENAS com o comando: ",nome_do_comando flag"

Regras OBRIGATÓRIAS:
1. Infira o comando mais próximo da descrição given
2. funk->música, music->música, spotify->música,.video->dl, download->dl, youtube->dl
3. Se não souber o comando exato, use ",menu"
4. Nunca responda com texto livre - apenas ",comando"

Pedido do usuário: {user_input}
Comando:"""
