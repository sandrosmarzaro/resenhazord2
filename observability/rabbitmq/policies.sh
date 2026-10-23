#!/bin/sh
# Queue limits, applied by the edge deploy inside the broker container. They are
# policies, not queue arguments: both nodes declare these durable queues, and
# redeclaring one with new arguments fails with PRECONDITION_FAILED. A definitions
# file is out too: importing one at boot skips seeding the default vhost and user.
# set_policy is idempotent and the broker keeps policies on its volume.
set -e

rabbitmqctl -q await_startup

# Past 100 commands or 64 MiB the oldest is dropped: in a backlog an old command has
# lost its moment, and the cap stays under the 256 MiB memory watermark.
rabbitmqctl -q set_policy --apply-to queues commands-bounded '^commands$' \
  '{"max-length":100,"max-length-bytes":67108864,"overflow":"drop-head"}'

# Dead letters keep a week, 500 messages or 32 MiB, oldest dropped first.
rabbitmqctl -q set_policy --apply-to queues dlq-retention '^commands\.dlq$' \
  '{"message-ttl":604800000,"max-length":500,"max-length-bytes":33554432,"overflow":"drop-head"}'
