# Infrastructure

Production runs on two Oracle Cloud Always Free VMs and a set of managed free tiers. This page
records what the hardware is, how its memory is split, and where every external dependency
lives, with numbers measured from the nodes themselves on 2026-10-21. The topology rationale
is in [ADR 0002](adr/0002-two-node-topology.md) and the deploy flow in
[ADR 0006](adr/0006-two-node-cicd-deploy.md).

## Nodes

Both nodes are identical.

| | |
|---|---|
| Account | OCI Free Tier (not Pay As You Go) |
| Region | `sa-saopaulo-1` |
| Shape | `VM.Standard.E2.1.Micro` |
| CPU | 1 OCPU, which the guest sees as 2 vCPUs (`nproc` = 2) |
| Memory | 1 GB, 954 MiB usable |
| Swap | 2 GiB swap file |
| Network | 0.48 Gbps |
| Disk | 45 GB boot volume |
| OS | Ubuntu 24.04 Minimal (24.04.4, kernel 6.17 oracle) |

The edge node (`resenhazord-edge`, private IP `10.0.0.211`) runs the WhatsApp gateway,
RabbitMQ and node-exporter. The core node (`resenhazord-core`) runs the bot and Grafana Alloy.
They talk over the VCN private subnet, where a TCP connect from core to the broker takes
under 1 ms.

Ampere A1 (ARM, up to 4 OCPU and 24 GB on Always Free) is not an option. Its capacity in
`sa-saopaulo-1` has never been available to this Free Tier account, so the design has to fit
two micros.

A Free Tier account is subject to Oracle's idle reclaim, which can stop an Always Free
instance whose 95th-percentile CPU and network stay under 20% for seven days. A chatbot for one
group of friends is idle most of the time, so the risk applies to both nodes. Pay As You Go
accounts are exempt.

## Memory budget

Every container has a `mem_limit`. Docker leaves `memswap_limit` unset, which lets each
container use as much swap again as its RAM cap, so the caps bound RAM only.

| Node | Container | Cap | Measured 2026-10-21 |
|---|---|---|---|
| edge | `whatsapp` | 384m | 153 MiB |
| edge | `rabbitmq` | 400m | 96 MiB now, 165 MiB peak over 7 days |
| edge | `node-exporter` | 32m | 9 MiB |
| core | `bot` | 640m | 63 MiB now, 378 MiB peak plus 212 MiB swap since the last restart |
| core | `alloy` | 150m | 149 MiB, pinned at its cap with 51 MiB in swap |

At the host level the lowest free memory over 30 days was 146 MiB on the edge and 176 MiB on
the core, and swap use peaked at 623 MiB on the edge and 334 MiB on the core.

RabbitMQ computes a relative memory watermark from the host RAM instead of its container cap,
so the default 0.4 came out as 381 MiB against a 400m limit and the OOM killer always won.
`observability/rabbitmq/20-memory.conf` sets an absolute 256 MiB watermark. In a local flood
test on one CPU the alarm fired at about 285 MiB used and blocked publishers for 9 seconds
without an OOM kill. Classic queues page persistent messages to disk, so 25 messages of 21 MB
each kept the broker near 200 MiB.

## Disk

Deploys pull a new image on every release. Before the deploy jobs pruned old images, the core
held 76 images (2 in use) and 4.8 GB of build cache and reached 80% of its 45 GB disk. After a
prune it sits at 17%. The edge was at 22%.

## External dependencies

Region comes from the hostname or the reverse DNS of the resolved address. TCP is the median
connect time from the core node, and the round trip is the median of five read-only calls
through the bot's own clients (`PING`, `select 1`, index `info`).

| Service | Used for | Region | TCP | Round trip | Usage |
|---|---|---|---|---|---|
| MongoDB Atlas | WhatsApp session, mentions, counters | São Paulo | 1 ms | 4 ms, 674 ms to connect | 0.6 MiB data, 1.9 MiB index, 3-member replica set |
| Neon Postgres | per-group config | AWS `us-east-1` | 114 ms | 114 ms, 1353 ms to connect | 7.5 MiB, Postgres 18.6 |
| Upstash Redis | group metadata cache | AWS `sa-east-1` | 1 ms | 2 ms | 0 keys, 64 MB maxmemory |
| Redis Cloud | agent checkpoints | AWS `sa-east-1` | 1 ms | 1 ms, 90 ms to connect | 2.4 MB, Redis 8.6 with `search` and `ReJSON` |
| Upstash Vector | few-shot examples | AWS `us-east-1` | 113 ms | 116 ms | 277 vectors, 1536 dimensions, 1.7 MB |
| Grafana Cloud | metrics, logs, traces | AWS `sa-east-1` | 1 ms | | |
| Sentry | errors | `ingest.us`, GCP anycast | 2 ms | | |
| LangSmith | prompt registry | GCP anycast | 2 ms | | |
| Mistral, Groq | LLM providers | Cloudflare edge | 1 ms | | |
| Gemini | LLM provider | Google edge | 1 ms | | |
| WhatsApp | Baileys socket and media | Meta `gru1`/`gru2` (Guarulhos) | 1 ms | | |
| Discord | gateway and API | Cloudflare edge | 1 ms | | |
| Telegram | bot API | outside South America | 199 ms | | |
| GHCR | images | Azure | 3 ms | | |

A 1 ms TCP connect to an anycast or CDN address only shows that the nearest edge is in São
Paulo. Inference for the LLM providers and storage for Sentry and LangSmith may be elsewhere.

TLS handshakes took between 20 and 250 ms even where the TCP connect took 1 ms, because the
handshake is CPU-bound on the micro. Long-lived pooled connections avoid paying it per request.

Neon and Upstash Vector are the two dependencies outside São Paulo. Every per-group config
read pays about 114 ms, and the first query after Neon autosuspends pays more than a second.
Every agent turn pays about 116 ms for retrieval.
