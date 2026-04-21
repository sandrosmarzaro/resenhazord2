"""Few-shot examples for LLM agent command mapping.

These examples are used in the system prompt to help the LLM
map natural language requests to the correct bot commands.

Language: pt-br (matches user voice and menu_description)
"""

AGENT_EXAMPLES = [
    # Score command
    ("mostrar placar dos jogos", "score --now"),
    ("placar football agora", "score --now"),
    ("jogos encerrados", "score --past"),
    ("próximos jogos", "score --next"),
    ("ver placar ao vivo", "score --now"),
    ("Resultados dos jogos", "score --past --now"),
    # Football team
    ("time completo do flamengo", "time flamengo"),
    ("escalação do palmeiras", "time palmeiras"),
    ("time do corinthians", "time corinthians"),
    ("que time é o flamengo", "time flamengo"),
    ("ranking times brasileiros", "time --liga br"),
    # Score / Tabela
    ("tabela do brasileiro", "tabela br"),
    ("classificação champions", "tabela bl"),
    # Menu
    ("lista de comandos", "menu"),
    ("o que você pode fazer", "menu"),
    ("comandos disponíveis", "menu"),
    # Random - dados
    ("jogar dado", "d20"),
    ("rolar dados", "d20 2d6"),
    ("sortear número", "d20"),
    # Random - cars
    ("me mande um carro", "carro"),
    ("foto de carro", "carro"),
    ("carro aleatório", "carro"),
    ("mostra um carro", "carro"),
    # Random - animals
    ("animal aleatório", "animal"),
    ("foto de cachorro", "puppy"),
    ("foto de gato", "puppy cat"),
    # Random - poker/battle
    ("carta de poker", "carta"),
    ("carta aleatória baralho", "carta"),
    ("carta yu-gi-oh", "ygo"),
    ("carta magic", "mtg"),
    ("carta pokemon", "pokemon"),
    ("carta hearthstone", "hs"),
    ("carta clash royale", "cr"),
    # Random - food/drink
    ("cerveja aleatória", "cerveja"),
    ("receita de comida", "comida"),
    ("comida aleatória", "comida"),
    # Random - anime/game/movie
    ("anime aleatório", "anime"),
    ("manga aleatório", "manga"),
    ("jogo aleatório", "game"),
    ("filme aleatório", "filme"),
    ("série aleatória", "série"),
    # Random - other
    ("fato aleatório", "fato"),
    ("horóscopo", "horóscopo"),
    ("jogador aleatório", "jogador"),
    ("moeda conversão", "moeda"),
    # Greetings
    ("oi", "oi"),
    ("me mande um oi", "oi"),
    # Music
    ("tocar música", "música"),
    ("achar música", "música"),
    ("baixar música", "música"),
    # Download
    ("baixar vídeo", "dl"),
    ("áudio do youtube", "dl"),
    # Info
    ("jogo do bicho", "bicho"),
    ("fase da lua", "lua"),
    # Unknown - use menu
    ("não sei", "menu"),
]

SYSTEM_PROMPT_TEMPLATE = """Você é um assistente que mapeia pedidos naturais em comandos do bot Resenhazord.

Lista de comandos disponíveis:
{command_list}

Exemplos de mapeamento:
{examples}

IMPORTANTE - Formato de saída:
- Responda APENAS com o comando no formato: ",nome_do_comando --flag"
- Ex: ",menu" ou ",score --now flamengo" ou ",d20"
- NUNCA responda com texto livre

Regras OBRIGATÓRIAS:
1. SEMPRE responda no formato ",comando --flags"
2. Se não souber o comando exato, use ",menu"
3. Ignore '@resenhazord' se estiver no pedido

Pedido do usuário: {user_input}
Comando:"""
