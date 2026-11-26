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

# Field names that name a chat or a person: their whole value is hashed whatever it
# looks like, since a Telegram or Discord id is too short to be told from a number.
IDENTITY_FIELDS: frozenset[str] = frozenset(
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

# Field names a bug report may show, for log fields, span attributes and frame
# arguments alike: names, codes, counts and durations. Any other name is dropped (or,
# for a frame argument, shown as its type), free text above all, since its content
# is the chat's.
SAFE_FIELDS: frozenset[str] = frozenset(
    {
        'attempt',
        'attempts',
        'batch',
        'bytes',
        'chat_type',
        'command',
        'command.name',
        'command.outcome',
        'content_type',
        'count',
        'duration_ms',
        'elapsed_ms',
        'error.type',
        'error_type',
        'fps',
        'height',
        'http.method',
        'http.request.method',
        'http.response.status_code',
        'http.status_code',
        'index',
        'kind',
        'limit',
        'model',
        'outcome',
        'page',
        'platform',
        'provider',
        'quality',
        'repeat',
        'retry_after',
        'server.address',
        'size',
        'status',
        'status_code',
        'timeout',
        'upstream',
        'version',
        'width',
        'work.kind',
    }
)

# URL-valued span attributes: shown as scheme, host and path only.
URL_FIELDS: frozenset[str] = frozenset({'http.url', 'url.full'})
