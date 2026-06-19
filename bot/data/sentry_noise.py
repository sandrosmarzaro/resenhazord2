"""Expected, self-healing exceptions filtered out of Sentry as noise."""

# 429s from the LLM provider are absorbed by the LangChain fallback chain
# (github -> mistral -> groq); the request still succeeds on the next provider.
ABSORBED_EXCEPTION_NAMES: frozenset[str] = frozenset({'RateLimitError'})

# The broker refuses connections only while the edge node is briefly unreachable;
# aio_pika's RobustConnection reconnects on its own. Both the exception and the
# aiormq log-record form embed the class name and the errno-111 phrase.
BROKER_REFUSAL_EXCEPTION_NAME = 'AMQPConnectionError'
BROKER_REFUSAL_MARKER = 'Connection refused'
