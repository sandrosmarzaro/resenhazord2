from typing import Final

# Held-out natural-language requests, worded differently from AGENT_EXAMPLES, each
# paired with the command prefix a correct mapping must start with. Kept out of the
# example bank on purpose: the prompt has to generalize to these, not memorize them.
# The eval asserts aggregate accuracy, so a few misses are tolerated (the LLM is
# stochastic); a real prompt regression drops many at once.
PROMPT_REGRESSION_CASES: Final[list[tuple[str, str]]] = [
    ('qual a pontuação da partida agora', ',score'),
    ('quero a tabela do campeonato brasileiro', ',tabela br'),
    ('me mostra a escalação do são paulo', ',time'),
    ('joga um dado pra mim', ',d20'),
    ('manda a foto de um automóvel', ',carro'),
    ('quero ver um cachorrinho', ',puppy'),
    ('me mostra uma carta de yugioh', ',ygo'),
    ('abre um pacote de pokémon', ',pokemon booster'),
    ('sugere uma cerveja pra mim', ',cerveja'),
    ('quero uma receita de comida', ',comida'),
    ('recomenda um anime', ',anime'),
    ('sugere um filme pra assistir', ',filme'),
    ('me conta uma curiosidade', ',fato'),
    ('lê esse texto em japonês', ',áudio lang ja'),
    ('coloca uma música de pagode', ',música pagode'),
    ('transforma essa imagem em figurinha', ',stic'),
    ('qual é o meu horóscopo hoje', ',horóscopo'),
    ('me mostra a lista de comandos', ',menu'),
]
