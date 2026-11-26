"""What a bug report may carry out of the process into a public GitHub issue."""

# Name fragments that mark the value next to them (`x_api_key=`, `"token": `,
# `client_secret: `) as a credential. Matched case-insensitively, anywhere in the name.
SECRET_NAME_PARTS: tuple[str, ...] = (
    'authorization',
    'key',
    'passwd',
    'password',
    'secret',
    'session',
    'signature',
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

# Log fields the record already carries elsewhere, or that only add noise to an issue.
OMITTED_LOG_FIELDS: frozenset[str] = frozenset(
    {
        'correlation_id',
        'event',
        'exc_info',
        'level',
        'logger',
        'stack_info',
        'timestamp',
    }
)

# Span attributes worth reading in an issue. Everything else stays in Tempo.
KEPT_SPAN_ATTRIBUTES: frozenset[str] = frozenset(
    {
        'command.name',
        'command.outcome',
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
