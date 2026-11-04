<h1 align="center"><b>🗿 Resenhazord 2️⃣</b></h1>

<p align="center">
  <a href="https://github.com/sandrosmarzaro/resenhazord2/actions/workflows/pipeline.yml?query=branch%3Amain"><img src="https://github.com/sandrosmarzaro/resenhazord2/actions/workflows/pipeline.yml/badge.svg?branch=main" alt="Pipeline"></a>
  <a href="https://codecov.io/gh/sandrosmarzaro/resenhazord2"><img src="https://codecov.io/gh/sandrosmarzaro/resenhazord2/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="https://sonarcloud.io/summary/new_code?id=resenhazord2"><img src="https://sonarcloud.io/api/project_badges/measure?project=resenhazord2&metric=alert_status&token=fa18bbc55c1c86e0611890ddbe5c44b095d30f82" alt="Quality Gate"></a>
  <a href="https://sonarcloud.io/summary/new_code?id=resenhazord2"><img src="https://sonarcloud.io/api/project_badges/measure?project=resenhazord2&metric=security_rating&token=fa18bbc55c1c86e0611890ddbe5c44b095d30f82" alt="Security Rating"></a>
  <a href="https://sonarcloud.io/summary/new_code?id=resenhazord2"><img src="https://sonarcloud.io/api/project_badges/measure?project=resenhazord2&metric=sqale_rating&token=fa18bbc55c1c86e0611890ddbe5c44b095d30f82" alt="Maintainability Rating"></a>
  <a href="https://sonarcloud.io/summary/new_code?id=resenhazord2"><img src="https://sonarcloud.io/api/project_badges/measure?project=resenhazord2&metric=reliability_rating&token=fa18bbc55c1c86e0611890ddbe5c44b095d30f82" alt="Reliability Rating"></a>
</p>

<p align="center">
  <a href="https://github.com/sandrosmarzaro/resenhazord2/releases/latest"><img src="https://img.shields.io/github/v/release/sandrosmarzaro/resenhazord2?logo=github" alt="Release"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsandrosmarzaro%2Fresenhazord2%2Fdevelop%2Fpyproject.toml&logo=python&logoColor=white" alt="Python"></a>
  <a href="gateway/"><img src="https://img.shields.io/badge/Bun-gateway-000000?logo=bun&logoColor=white" alt="Bun"></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fuv%2Fmain%2Fassets%2Fbadge%2Fv0.json" alt="uv"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fruff%2Fmain%2Fassets%2Fbadge%2Fv2.json" alt="Ruff"></a>
  <a href="https://www.conventionalcommits.org/"><img src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white" alt="Conventional Commits"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/WhatsApp-25D366?logo=whatsapp&logoColor=white" alt="WhatsApp">
  <img src="https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white" alt="Discord">
  <img src="https://img.shields.io/badge/Telegram-26A5E4?logo=telegram&logoColor=white" alt="Telegram">
</p>

Resenhazord 2 is the chatbot of A Resenha, a group of friends who wanted memes, media downloads,
stickers, games and a bit of chaos in their chats. It answers on WhatsApp, Discord and Telegram
with the same set of about fifty commands, and it understands plain-language requests through an
LLM agent when nobody remembers the exact command.

## 💬 Platforms

| Platform | How to call it | Adapter |
|---|---|---|
| WhatsApp | `,menu` | Bun + [Baileys](https://github.com/WhiskeySockets/Baileys) gateway in `gateway/` |
| Discord | `/menu` slash command | [discord.py](https://github.com/Rapptz/discord.py) in `bot/adapters/discord/` |
| Telegram | `/menu` | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) in `bot/adapters/telegram/` |

Each platform starts only when its credentials are configured, so the bot runs with any
combination of them.

## 🧭 How it works

<p align="center">
  <img src="docs/architecture.svg" width="100%" alt="Production architecture: the WhatsApp gateway and RabbitMQ run on an edge VPS, the Python core with the Discord, Telegram and LLM adapters runs on a core VPS, they talk over AMQP on a private network, and each node uses its own managed data stores and telemetry sinks.">
</p>

All business logic lives in a Python core (FastAPI) under `bot/`, where every command is parsed
and executed through a single `CommandRegistry`. The WhatsApp gateway receives messages, downloads
their media and forwards them to the core over RabbitMQ, then delivers the replies the core sends
back. The Discord and Telegram adapters run inside the core and translate their native events into
the same command calls. In production the gateway and the broker run on an edge node and the core
on a separate node, and they deploy independently. The full flow, the project tree and the design
decisions are in [docs/architecture.md](docs/architecture.md) and [docs/adr/](docs/adr/).

## 🚀 Quick start

You need Docker with Compose. Copy the environment template, fill in the platforms you want and
start the stack.

```bash
git clone git@github.com:sandrosmarzaro/resenhazord2.git
cd resenhazord2
cp .env.example .env
docker compose up -d --build
```

The first WhatsApp start prints a pairing QR code in the gateway logs. The wiki covers every step
in detail.

- [Install](https://github.com/sandrosmarzaro/resenhazord2/wiki/Install) sets up the tools for
  running and developing the bot.
- [Run](https://github.com/sandrosmarzaro/resenhazord2/wiki/Run) configures `.env`, pairs WhatsApp
  and starts the stack.

[CONTRIBUTING.md](CONTRIBUTING.md) explains branches, commits, tests, pull requests and the rules
for AI-assisted contributions. Everyone follows the [Code of Conduct](CODE_OF_CONDUCT.md), and
vulnerabilities are reported privately as described in [SECURITY.md](SECURITY.md).

## 📚 Documentation

| Topic | Where |
|---|---|
| Architecture and message flow | [docs/architecture.md](docs/architecture.md) |
| Nodes, memory budget and dependencies | [docs/infrastructure.md](docs/infrastructure.md) |
| Branching and releases | [docs/git-flow.md](docs/git-flow.md) |
| Logging, Sentry and OpenTelemetry | [docs/logging.md](docs/logging.md) |
| Dashboards and alerts | [docs/observability-dashboards.md](docs/observability-dashboards.md) |
| Bot reply formatting | [docs/response-conventions.md](docs/response-conventions.md) |
| External API integration | [docs/api-integration.md](docs/api-integration.md) |
| Command parser regex safety | [docs/security.md](docs/security.md) |
| Architecture decision records | [docs/adr/](docs/adr/) |

## 📜 History

The first [Resenhazord](https://github.com/sandrosmarzaro/resenhazord-chatbot) was a side project
from the start of an undergraduate program, built on [Venom](https://github.com/orkestral/venom).
Resenhazord 2 began as a cleaner rewrite, moved from WWeb.js to Baileys for stability, and later
moved its business logic from TypeScript to Python so that one core could serve several platforms.

## ⚖️ License

[MIT](LICENSE)
