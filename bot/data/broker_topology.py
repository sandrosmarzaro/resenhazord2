# The broker topology both nodes declare at startup (ADR 0017). The gateway declares the
# same in gateway/src/data/BrokerTopology.json, and a test keeps the two equal.

COMMANDS_EXCHANGE = 'resenhazord.commands'
EVENTS_EXCHANGE = 'resenhazord.events'
# Picks the retry ladder step for a rejected command by its routing key (ADR 0004).
RETRY_EXCHANGE = 'resenhazord.retry'
TOPIC_EXCHANGES = (COMMANDS_EXCHANGE, EVENTS_EXCHANGE, RETRY_EXCHANGE)
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
# The retry ladder (ADR 0004). A rejected command dead-letters with the routing key it
# arrived with, and each step dead-letters it back with the key of the next step, so the
# key counts the attempts: the first rejection waits 5 s, the second 30 s, the third 2 m,
# and the fourth goes to the DLQ. RetryRouter parks a command in the DLQ itself once its
# MAX_ATTEMPTS run out; the ladder's end caps anything rejected past that.
RETRY_LADDER = ('commands.retry.5s', 'commands.retry.30s', 'commands.retry.2m')
LADDER_TO_30S = 'retry.30s'
LADDER_TO_2M = 'retry.2m'
LADDER_TO_DLQ = 'retry.dead'


def _retry_step(ttl_ms: int, next_key: str) -> frozendict[str, int | str]:
    return frozendict(
        {
            'x-message-ttl': ttl_ms,
            'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE,
            'x-dead-letter-routing-key': next_key,
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
        RETRY_LADDER[0]: _retry_step(5_000, LADDER_TO_30S),
        RETRY_LADDER[1]: _retry_step(30_000, LADDER_TO_2M),
        RETRY_LADDER[2]: _retry_step(120_000, LADDER_TO_DLQ),
    }
)

# (exchange, binding pattern, queue)
BINDINGS = (
    (COMMANDS_EXCHANGE, 'command.#', LEGACY_COMMANDS_QUEUE),
    (COMMANDS_EXCHANGE, 'wa.action.#', 'wa_actions'),
    (COMMANDS_EXCHANGE, 'wa.rpc.#', 'wa_rpc'),
    (EVENTS_EXCHANGE, 'reply.whatsapp', 'replies'),
    (EVENTS_EXCHANGE, 'group.#', 'group_events'),
    # A command enters the quorum queue by its name through the default exchange.
    (RETRY_EXCHANGE, COMMANDS_QUEUE, RETRY_LADDER[0]),
    (RETRY_EXCHANGE, LADDER_TO_30S, RETRY_LADDER[1]),
    (RETRY_EXCHANGE, LADDER_TO_2M, RETRY_LADDER[2]),
    (RETRY_EXCHANGE, LADDER_TO_DLQ, DEAD_LETTER_QUEUE),
)

# Death reason (x-last-death-reason) → where the dead-letter exchange sends it. A reason
# without a route is dropped, as a full queue's oldest command (maxlen) should be. A
# poison command skips the ladder: back in the quorum queue with no rejection on the way,
# RabbitMQ would drop it as a dead-letter cycle.
DEAD_LETTER_ROUTES: frozendict[str, str] = frozendict(
    {
        'rejected': RETRY_EXCHANGE,
        'expired': COMMANDS_QUEUE,
        'delivery_limit': DEAD_LETTER_QUEUE,
    }
)
