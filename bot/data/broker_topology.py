# The broker topology both nodes declare at startup (ADR 0017). The gateway declares the
# same in gateway/src/data/BrokerTopology.json, and a test keeps the two equal.

COMMANDS_EXCHANGE = 'resenhazord.commands'
EVENTS_EXCHANGE = 'resenhazord.events'
TOPIC_EXCHANGES = (COMMANDS_EXCHANGE, EVENTS_EXCHANGE)

# The queues keep the names and arguments they had before the exchanges: the live
# policies match them by name, and a redeclare with other arguments fails with
# PRECONDITION_FAILED. The retry queue still dead-letters through the default exchange.
RETRY_QUEUE_ARGUMENTS: frozendict[str, int | str] = frozendict(
    {
        'x-message-ttl': 30_000,
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': 'commands',
    }
)
DURABLE_QUEUES: frozendict[str, frozendict[str, int | str]] = frozendict(
    {
        'commands': frozendict(),
        'replies': frozendict(),
        'wa_actions': frozendict(),
        'wa_rpc': frozendict(),
        'group_events': frozendict(),
        'commands.dlq': frozendict(),
        'commands.retry': RETRY_QUEUE_ARGUMENTS,
    }
)

# (exchange, binding pattern, queue)
BINDINGS = (
    (COMMANDS_EXCHANGE, 'command.#', 'commands'),
    (COMMANDS_EXCHANGE, 'wa.action.#', 'wa_actions'),
    (COMMANDS_EXCHANGE, 'wa.rpc.#', 'wa_rpc'),
    (EVENTS_EXCHANGE, 'reply.whatsapp', 'replies'),
    (EVENTS_EXCHANGE, 'group.#', 'group_events'),
)
