"""What a bug report may carry out of the process into a public GitHub issue."""

# Name fragments that mark the value next to them (`x_api_key=`, `"token": `,
# `client_secret: `) as a credential. Matched case-insensitively, anywhere in the name.
SECRET_NAME_PARTS: tuple[str, ...] = (
    'auth',
    'credential',
    'key',
    'pass',
    'pwd',
    'secret',
    'session',
    'sig',
    'token',
)

# Prefixes of provider credentials that show up bare in exception messages: Groq,
# LangSmith, OpenAI-style, Slack, GitHub.
PROVIDER_KEY_PREFIXES: tuple[str, ...] = (
    'github_pat_',
    'gho_',
    'ghp_',
    'ghr_',
    'ghs_',
    'ghu_',
    'gsk_',
    'lsv2_',
    'sk-',
    'xoxa-',
    'xoxb-',
    'xoxp-',
    'xoxr-',
    'xoxs-',
)

# Log fields that name a chat or a person: their whole value is hashed whatever it
# looks like, since a Telegram or Discord id is too short to be told from a number.
IDENTITY_LOG_FIELDS: frozenset[str] = frozenset(
    {
        'author_id',
        'channel',
        'channel_id',
        'chat',
        'chat_id',
        'dev',
        'from_user',
        'guild_id',
        'jid',
        'mentioned_jids',
        'participant',
        'sender',
        'sender_jid',
        'user',
        'user_id',
    }
)

# Log fields a bug report may show: names, codes, counts and durations. Any other
# field is dropped, free text above all (the message, the prompt, an error string),
# since its content is the chat's. Identity fields are kept, hashed.
SAFE_LOG_FIELDS: frozenset[str] = frozenset(
    {
        'attempt',
        'attempts',
        'batch',
        'bytes',
        'chat_type',
        'command',
        'content_type',
        'count',
        'duration_ms',
        'elapsed_ms',
        'error_type',
        'kind',
        'model',
        'outcome',
        'platform',
        'provider',
        'repeat',
        'retry_after',
        'size',
        'status',
        'status_code',
        'upstream',
        'version',
    }
)

# Span attributes worth reading in an issue. Everything else stays in Tempo.
KEPT_SPAN_ATTRIBUTES: frozenset[str] = frozenset(
    {
        'command.name',
        'command.outcome',
        'error.type',
        'http.method',
        'http.request.method',
        'http.response.status_code',
        'http.status_code',
        'http.url',
        'server.address',
        'url.full',
        'work.kind',
    }
)
