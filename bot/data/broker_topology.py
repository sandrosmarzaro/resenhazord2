# The broker topology both nodes declare at startup (ADR 0017). The gateway declares the
# same in gateway/src/data/BrokerTopology.json, and a test keeps the two equal.

COMMANDS_EXCHANGE = 'resenhazord.commands'
EVENTS_EXCHANGE = 'resenhazord.events'
TOPIC_EXCHANGES = (COMMANDS_EXCHANGE, EVENTS_EXCHANGE)
# A headers exchange: it routes a dead letter by the reason it died (ADR 0004).
DEAD_LETTER_EXCHANGE = 'resenhazord.dlx'

COMMANDS_QUEUE = 'commands.quorum'
DEAD_LETTER_QUEUE = 'commands.dlq'
# The classic queues the nodes declared before the quorum queue. Their names and
# arguments stay as they were: the live policies match them by name, and a redeclare
# with other arguments fails with PRECONDITION_FAILED. The core drains the old commands
# queue into the quorum one until no node publishes to it.
LEGACY_COMMANDS_QUEUE = 'commands'
LEGACY_RETRY_QUEUE = 'commands.retry'
RETRY_QUEUE_ARGUMENTS: frozendict[str, int | str] = frozendict(
    {
        'x-message-ttl': 30_000,
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': LEGACY_COMMANDS_QUEUE,
    }
)
# A command that kills the core before its ack comes back on every restart; past the
# limit the broker dead-letters it instead of delivering it again.
COMMANDS_QUEUE_ARGUMENTS: frozendict[str, int | str] = frozendict(
    {
        'x-queue-type': 'quorum',
        'x-delivery-limit': 3,
        'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE,
    }
)
DURABLE_QUEUES: frozendict[str, frozendict[str, int | str]] = frozendict(
    {
        LEGACY_COMMANDS_QUEUE: frozendict(),
        COMMANDS_QUEUE: COMMANDS_QUEUE_ARGUMENTS,
        'replies': frozendict(),
        'wa_actions': frozendict(),
        'wa_rpc': frozendict(),
        'group_events': frozendict(),
        DEAD_LETTER_QUEUE: frozendict(),
        LEGACY_RETRY_QUEUE: RETRY_QUEUE_ARGUMENTS,
    }
)

# (exchange, binding pattern, queue)
BINDINGS = (
    (COMMANDS_EXCHANGE, 'command.#', LEGACY_COMMANDS_QUEUE),
    (COMMANDS_EXCHANGE, 'wa.action.#', 'wa_actions'),
    (COMMANDS_EXCHANGE, 'wa.rpc.#', 'wa_rpc'),
    (EVENTS_EXCHANGE, 'reply.whatsapp', 'replies'),
    (EVENTS_EXCHANGE, 'group.#', 'group_events'),
)

# Death reason (x-last-death-reason) → where the dead-letter exchange sends it. A reason
# without a route is dropped, as a full queue's oldest command (maxlen) should be.
DEAD_LETTER_ROUTES: frozendict[str, str] = frozendict({'delivery_limit': DEAD_LETTER_QUEUE})
