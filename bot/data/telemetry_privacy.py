"""What a bug report may carry out of the process into a public GitHub issue."""

# Query parameters whose value is a credential. Matched case-insensitively in any URL a
# span, log or exception message holds.
SECRET_QUERY_KEYS: tuple[str, ...] = (
    'access_token',
    'api_key',
    'apikey',
    'auth',
    'client_secret',
    'key',
    'password',
    'secret',
    'session',
    'sig',
    'signature',
    'token',
)

# Log fields that name a chat or a person: their whole value is hashed.
IDENTITY_LOG_FIELDS: frozenset[str] = frozenset(
    {
        'chat',
        'chat_id',
        'dev',
        'jid',
        'participant',
        'sender',
        'sender_jid',
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
