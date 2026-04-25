"""Few-shot examples for LLM agent command mapping.

These examples are used in the system prompt to help the LLM
map natural language requests to the correct bot commands.

Language: pt-br (matches user voice and menu_description)
"""

AGENT_EXAMPLES = [
    # Score command
    ('mostrar placar dos jogos', ',score --now'),
    ('placar football agora', ',score --now'),
    ('jogos encerrados', ',score --past'),
    ('próximos jogos', ',score --next'),
    ('ver placar ao vivo', ',score --now'),
    ('Resultados dos jogos', ',score --past --now'),
    # Football team
    ('time completo do flamengo', ',time flamengo'),
    ('escalação do palmeiras', ',time palmeiras'),
    ('time do corinthians', ',time corinthians'),
    ('que time é o flamengo', ',time flamengo'),
    ('ranking times brasileiros', ',time --liga br'),
    # Score / Tabela
    ('tabela do brasileiro', ',tabela br'),
    ('classificação champions', ',tabela bl'),
    # Menu
    ('lista de comandos', ',menu'),
    ('o que você pode fazer', ',menu'),
    ('comandos disponíveis', ',menu'),
    # Random - dados
    ('jogar dado', ',d20'),
    ('rolar dados', ',d20 2d6'),
    ('sortear número', ',d20'),
    # Random - cars
    ('me mande um carro', ',carro'),
    ('foto de carro', ',carro'),
    ('carro aleatório', ',carro'),
    ('mostra um carro', ',carro'),
    # Random - animals
    ('animal aleatório', ',animal'),
    ('foto de cachorro', ',puppy'),
    ('foto de gato', ',puppy cat'),
    # Random - poker/battle
    ('carta de poker', ',carta'),
    ('carta aleatória baralho', ',carta'),
    ('carta yu-gi-oh', ',ygo'),
    ('carta magic', ',mtg'),
    ('carta pokemon', ',pokemon'),
    ('carta hearthstone', ',hs'),
    ('carta clash royale', ',cr'),
    # Booster packs
    ('me mande um pacotinho de yugioh', ',ygo booster'),
    ('pacote de pokemon', ',pokemon booster'),
    ('booster de magic', ',mtg booster'),
    ('me envia um pacotinho de yu-gi-oh', ',ygo booster'),
    # Random - food/drink
    ('cerveja aleatória', ',cerveja'),
    ('receita de comida', ',comida'),
    ('comida aleatória', ',comida'),
    # Random - anime/game/movie
    ('anime aleatório', ',anime'),
    ('manga aleatório', ',manga'),
    ('jogo aleatório', ',game'),
    ('filme aleatório', ',filme'),
    ('série aleatória', ',série'),
    # Random - other
    ('fato aleatório', ',fato'),
    ('horóscopo', ',horóscopo'),
    ('jogador aleatório', ',jogador'),
    ('moeda conversão', ',moeda'),
    # Sticker
    ('transformar em sticker', ',stic'),
    ('fazer figurinha', ',stic'),
    ('tornar figurinha', ',stic'),
    # Greetings
    ('oi', ',oi'),
    ('me mande um oi', ',oi'),
    # Music genres
    ('tocar música rock', ',música rock'),
    ('música funk', ',música funk'),
    ('rock', ',música rock'),
    ('pagode', ',música pagode'),
    ('sertanejo', ',música sertanejo'),
    ('mpb', ',música mpb'),
    ('reggaeton', ',música reggaeton'),
    ('kpop', ',música kpop'),
    ('rock pauleira', ',música rock'),
    ('toque um metal pauleira', ',música metal'),
    # Audio / TTS - only for voice, text-to-speech, language learning
    ('mande um áudio em mandarim', ',áudio lang zh'),
    ('áudio em japonês', ',áudio lang ja'),
    ('fala em inglês', ',áudio lang en'),
    ('áudio chino', ',áudio lang zh'),
    ('leia让我说中文', ',áudio lang zh'),
    # Info
    ('jogo do bicho', ',bicho'),
    ('fase da lua', ',lua'),
    # Unknown - use menu
    ('não sei', ',menu'),
]

SYSTEM_PROMPT_TEMPLATE = """Você é um assistente que mapeia pedidos
naturais em comandos do bot Resenhazord.

Lista de comandos disponíveis com descrições:
{command_list}

Exemplos de mapeamento (USE ESSES PARA INFERIR PADRÕES):
{examples}

REGRAS DE INFERÊNCIA:
 1. Sempre use VÍRGULA (,) como prefixo do comando.
    Ex: "carro" → ",carro", "menu" → ",menu", "score now" → ",score --now"
 2. GÊNEROS DE MÚSICA: quando o usuário menciona um gênero musical
    (rock, funk, pagode, sertanejo, pop, mpb, etc.), use "música <gênero>".
    Ex: "rock pauleira" → ",música rock", "funk" → ",música funk"
 3. NSFW: "porno", "pornô", "xvideos" → ",porno". Se mencionar "ia", use "--ia".
    Ex: "porno ia" → ",porno --ia"
 4. Nunca adicione "todos" ou múltiplos gêneros se usuário especificou apenas um
 5. ÁUDIO: apenas para synthesis de voz, TTS, ou aprender idiomas.
    "áudio" → synthesis de voz/leitura; "música" → gêneros/bandas.
    Ex: "fala em japonês" → ",áudio lang ja", "toque rock" → ",música rock"
 6. SHOW FLAG: NÃO use --show a menos que o usuário solicite explicitamente
    "view once", "temporal", " visualize" ou similar.
    Por padrão, envie mídias em modo view-once (com --show MUDA o comportamento).
 7. SE NÃO SOUBER mapear: Responda com "CLARIFY: <pergunta>".
    Ex: "CLARIFY: Você quer ver a tabela do brasileiro?"
    Não responda apenas "não entendi".
 8. Responda APENAS com o comando (com vírgula) ou "CLARIFY: <pergunta>".

Pedido do usuário: {user_input}
Comando:"""
