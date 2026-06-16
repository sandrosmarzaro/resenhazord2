"""Few-shot examples for LLM agent command mapping.

These examples are used in the system prompt to help the LLM
map natural language requests to the correct bot commands.

Language: pt-br (matches user voice and menu_description)
"""

_SCORE_NOW = ',score --now'
_MENU = ',menu'
_CARRO = ',carro'
_STIC = ',stic'
_MUSICA_ROCK = ',música rock'
_AUDIO_LANG_ZH = ',áudio lang zh'

AGENT_EXAMPLES = [
    # Score command
    ('mostrar placar dos jogos', _SCORE_NOW),
    ('placar football agora', _SCORE_NOW),
    ('jogos encerrados', ',score --past'),
    ('próximos jogos', ',score --next'),
    ('ver placar ao vivo', _SCORE_NOW),
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
    ('lista de comandos', _MENU),
    ('o que você pode fazer', _MENU),
    ('comandos disponíveis', _MENU),
    # Random - dados
    ('jogar dado', ',d20'),
    ('rolar dados', ',d20 2d6'),
    ('sortear número', ',d20'),
    # Random - cars
    ('me mande um carro', _CARRO),
    ('foto de carro', _CARRO),
    ('carro aleatório', _CARRO),
    ('mostra um carro', _CARRO),
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
    ('transformar em sticker', _STIC),
    ('fazer figurinha', _STIC),
    ('tornar figurinha', _STIC),
    ('figurinha centralizada', ',stic type crop'),
    ('sticker centralizado', ',stic type crop'),
    ('figurinha com bordas arredondadas', ',stic type rounded'),
    ('sticker sem bordas', ',stic type rounded'),
    ('figurinha redonda', ',stic type circle'),
    ('sticker circular', ',stic type circle'),
    # Greetings
    ('oi', ',oi'),
    ('me mande um oi', ',oi'),
    # Music genres
    ('tocar música rock', _MUSICA_ROCK),
    ('música funk', ',música funk'),
    ('rock', _MUSICA_ROCK),
    ('pagode', ',música pagode'),
    ('sertanejo', ',música sertanejo'),
    ('mpb', ',música mpb'),
    ('reggaeton', ',música reggaeton'),
    ('kpop', ',música kpop'),
    ('rock pauleira', ',música rock'),
    ('toque um metal pauleira', ',música metal'),
    # Audio / TTS - only for voice, text-to-speech, language learning
    ('mande um áudio em mandarim', _AUDIO_LANG_ZH),
    ('áudio em japonês', ',áudio lang ja'),
    ('fala em inglês', ',áudio lang en'),
    ('áudio chino', _AUDIO_LANG_ZH),
    ('leia让我说中文', _AUDIO_LANG_ZH),
    # Info
    ('jogo do bicho', ',bicho'),
    ('fase da lua', ',lua'),
    # Unknown - use menu
    ('não sei', _MENU),
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
 7. SE NÃO SOUBER qual comando: chame a ferramenta `clarify` com uma pergunta
    em pt-br. Ex: clarify(question="Você quer ver a tabela do brasileiro?").
    Não responda apenas "não entendi".
 8. PEDIDO FORA DAS FUNÇÕES com comando SIMILAR: chame a ferramenta `suggest`,
    respondendo CONVERSACIONALMENTE, SEM executar o comando.
    Ex: "qual a fundação do flamengo?" →
    suggest(message="Não sei a data exata, mas posso te mandar um time! Use ,time", command=",time")
    Ex: "por que o céu é azul?" →
    suggest(message="Não sei responder, mas posso te contar um fato! Use ,fato", command=",fato")
  9. STICKER type:
     - crop: "centralizada", "centralizado", "cortada", "meio"
     - rounded: "bordas arredondadas", "sem bordas", "cantos arredondados"
     - circle: "redonda", "circular", "completamente circular"
     - full: padrão, sem especificação
 10. CONTEXTO DE RESPOSTA: Se o usuário está RESPONDENDO a uma mensagem do bot
    (reply/quotation), use o contexto para inferir o comando correto.
    Ex: se o bot disse "Use ,fato" e o usuário responde "sim" → ",fato"
    Ex: se o bot sugeriu "Use ,tabela bl" e o usuário diz "sim" → ",tabela bl"{context}

{user_context}
Comando:"""
