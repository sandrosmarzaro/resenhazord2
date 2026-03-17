# TS-to-Python Migration Plan

## Overview

Migration of all Resenhazord2 business logic from TypeScript/Bun (gateway) to Python/FastAPI (engine). The gateway remains as a thin WhatsApp adapter; the engine handles all command processing via WebSocket bridge.

**Why:** Python is the preferred language; decoupling logic from WhatsApp transport enables future Discord/Telegram reuse.

**IPC:** WebSocket at `ws://python-core:8000/ws`. Single persistent connection. Commands forwarded via `PythonBridge` fallthrough in `CommandHandler.ts`. WhatsApp operations available to Python commands via `wa_call` messages.

**Stack:** FastAPI + uvicorn, httpx + httpx-retries, structlog + sentry-sdk, Pillow, pytest + anyio.

---

## Wave Summary

| Wave | Description | Commands | Status |
|------|-------------|----------|--------|
| 0 | Foundation | 0 | COMPLETED (2026-03-16) |
| 1 | Simple pure commands | 4 | COMPLETED (2026-03-16) |
| 2a | Simple API commands | 4 | COMPLETED (2026-03-16) |
| 2b | Data-heavy API commands | 3 | COMPLETED (2026-03-16) |
| 2c | Alias and multi-step commands | 3 | COMPLETED (2026-03-16) |
| 2d | Complex API + scraping | 3 | COMPLETED (2026-03-17) |
| 2e | NSFW + scraping | 3 | COMPLETED (2026-03-17) |
| 3a | TTS + audio | 1 | COMPLETED (2026-03-17) |
| 3b | Card game commands | 4 | PLANNED |
| 4a | Simple API + media | 2 | PLANNED |
| 4b | Multi-source API | 2 | PLANNED |
| 4c | Complex scraping + media | 2 | PLANNED |
| 5a | MongoDB commands | 2 | PLANNED |
| 5b | Menu command | 1 | PLANNED |
| 6 | WhatsApp-dependent (gateway-only) | 7 | PLANNED |
| 7 | Cleanup + TS removal | 0 | PLANNED |

**Total:** 41 commands (21 migrated, 13 to migrate, 7 gateway-only)

---

## Completed Waves

### Wave 0: Foundation (2026-03-16)

Set up the Python project, core domain, FastAPI app, WebSocket bridge, Docker, and CI.

**What was built:**
- Python project with UV (Python 3.13), ruff, basedpyright, pytest-anyio
- Core domain: Command ABC, CommandParser, Reply builder, BotMessage + content types, CommandRegistry
- FastAPI app: `/health` + `/ws` WebSocket endpoint
- TS bridge: `gateway/src/bridge/PythonBridge.ts` — auto-reconnect, command dispatch, `wa_call` routing
- Docker: `engine/Dockerfile` + docker-compose with `python-core` service
- CI: `deploy.yml` with Python lint/typecheck/test jobs

### Wave 1: Simple Pure Commands (2026-03-16)

Migrated 4 zero-dependency text-only commands.

| Command | Config Name | Description |
|---------|------------|-------------|
| OiCommand | `oi` | Greeting with mention |
| D20Command | `d20` | Random dice roll |
| MateusCommand | `mateus` | Random probability |
| FatoCommand | `fato` | Random fact from uselessfacts API |

**Infrastructure added:**
- `CommandHandler.ts` fallthrough to PythonBridge
- `register_commands.py` module wired into FastAPI startup
- Bridge lifecycle in `Resenhazord2.ts` (connect/disconnect)

### Wave 2a: Simple API Commands (2026-03-16)

Migrated 4 single-API commands.

| Command | Config Name | API | Notes |
|---------|------------|-----|-------|
| AlcoraoCommand | `alcorão` | alquran.cloud | Random Quran verse |
| BaralhoCommand | `baralho` | deckofcardsapi | Random playing card, image |
| MealRecipesCommand | `receita` | themealdb | Random recipe, image + ingredients |
| PuppyCommand | `puppy` | dog.ceo + cataas | Random dog/cat, option, image buffer |

### Wave 2b: Data-Heavy API Commands (2026-03-16)

Migrated 3 commands with static data maps.

| Command | Config Name | API | Data Maps |
|---------|------------|-----|-----------|
| ClashRoyaleCommand | `clashroyale` | royaleapi | RARITY_EMOJIS, TYPE_EMOJIS |
| LeagueOfLegendsCommand | `lol` | ddragon (2 calls) | LOL_ROLE_EMOJIS |
| CountryFlagCommand | `bandeira` | restcountries | REGION_MAP, SUBREGION_PT |

### Wave 2c: Alias and Multi-Step Commands (2026-03-16)

Migrated 3 commands with aliases and complex API flows.

| Command | Config Name | API | Notes |
|---------|------------|-----|-------|
| BeerCommand | `cerveja` | OpenFoodFacts | Scraper with retry logic |
| FilmeSerieCommand | `filme` | TMDB | aliases=['série'], options=['top','pop'] |
| MyAnimeListCommand | `anime` | Jikan (MyAnimeList) | aliases=['manga'] |

### Wave 2d: Complex API + Scraping (2026-03-17)

Migrated 3 commands with options, args, and complex interactions.

| Command | Config Name | API | Notes |
|---------|------------|-----|-------|
| BibliaCommand | `bíblia` | abibliadigital | options=[lang, version], verse ranges |
| TorahCommand | `torá` | Sefaria | options=[lang], TORAH_BOOKS data file |
| BichoCommand | `bicho` | eojogodobicho | HTML scraper, beautifulsoup4 |

**Dependencies added:** beautifulsoup4
**Data files added:** `engine/bot/data/torah_books.py`, `engine/bot/data/bicho.py`

### Bug Fixes (2026-03-17)

1. **WebSocket binary detection:** Bun delivers binary as `Buffer`, not `ArrayBuffer`/`Blob`. Changed to `typeof !== 'string'` check in PythonBridge.
2. **WebSocket frame ordering:** Send binary frames BEFORE JSON response to avoid race condition.
3. **HTTP redirects:** httpx doesn't follow redirects by default. Enabled `follow_redirects=True` globally.

### Wave 2e: NSFW + Scraping (2026-03-17)

Migrated 3 NSFW commands using direct HTTP APIs and HTML scraping.

| Command | Config Name | API | Notes |
|---------|------------|-----|-------|
| FuckCommand | `fuck` | nsfwhub API | groupOnly, args=Required(@mention), raw video with mentions |
| PornoCommand | `porno` | nsfwhub API + XVideos scraper | flags=[ia, show, dm], dual mode (AI vs real) |
| Rule34Command | `rule 34` | rule34.xxx scraper | beautifulsoup4 HTML scraping, banner URL skip |

**Key implementation notes:**
- `nsfwhub` Node.js lib replaced with direct httpx calls to `https://nsfwhub.onrender.com/nsfw?type={tag}`
- XVideosScraper rewritten in Python as a static method using httpx + beautifulsoup4
- FuckCommand uses `Reply.to(data).raw()` for video with mentions — `mentioned_jids` already available in `CommandData`
- PornoCommand real mode: scrape listing → pick random video → extract URL from JS vars
- Data file added: `engine/bot/data/nsfw_tags.py`

### Wave 3a: TTS + Audio (2026-03-17)

Migrated 1 command by replicating Google TTS URL construction in Python (no gTTS needed).

| Command | Config Name | Python Approach | Notes |
|---------|------------|-----------------|-------|
| AudioCommand | `áudio` | Direct Google TTS URL construction | options=[lang pattern], args=Optional, multi-chunk splitting |

**Key implementation notes:**
- Replicated `google-tts-api` URL construction in pure Python using `urllib.parse.urlencode`
- Text splitting algorithm (splitLongText) ported from JS — splits on space/punctuation at 200-char boundaries
- Language validation against 140-entry LANGUAGES set in `engine/bot/data/languages.py`
- Short text (<=200 chars) returns single audio message; long text returns multiple
- No external library needed — just URL construction, no audio download

---

## Planned Waves

**Migration pattern:** Replace Node.js-specific libraries with Python HTTP + scraping equivalents.

### Wave 3b: Card Game Commands (4 commands)

API-heavy commands with optional booster pack image rendering via sharp.

| Command | Config Name | API | Image Rendering | Notes |
|---------|------------|-----|-----------------|-------|
| HeartstoneCommand | `hs` | Blizzard OAuth + HS API | sharp (booster) | OAuth token, card images |
| MagicTheGatheringCommand | `mtg` | Scryfall/MTG API | sharp (booster) | Redirect handling |
| PokemonTCGCommand | `pokémontcg` | TCGdex | sharp (booster) | aliases=['ptcg'], retry logic |
| YugiohCommand | `ygo` | YGOProDeck | sharp (booster) | Card images |

**Key considerations:**
- All 4 use `sharp` for compositing booster pack images — replace with Pillow in Python
- Booster mode: fetch multiple cards → composite into a single image → return as buffer
- HeartstoneCommand requires OAuth2 flow (Blizzard API) — implement with httpx
- MTG needs to follow image URL redirects
- Pillow dependency already in engine's stack

### Wave 4a: Simple API + Media (2 commands)

| Command | Config Name | API | Notes |
|---------|------------|-----|-------|
| AnimalCommand | `animal` | Wikipedia API | Random animal article + image |
| PokemonCommand | `pokémon` | PokeAPI | flags=[team, show, dm], team mode uses sharp |

**Key considerations:**
- AnimalCommand fetches random Wikipedia article + first image
- PokemonCommand has a `team` flag that generates 6 random Pokemon + composites into team image (sharp → Pillow)
- Both return image buffers

### Wave 4b: Multi-Source API (2 commands)

| Command | Config Name | APIs | Notes |
|---------|------------|------|-------|
| GameCommand | `game` | IGDB + RAWG | Fallback chain: try IGDB, catch → try RAWG |
| MusicCommand | `música` | Deezer + Jamendo | flags=[free], free flag uses Jamendo, default uses Deezer |

**Key considerations:**
- GameCommand: IGDB requires Twitch OAuth2 → implement token management
- GameCommand: RAWG is the fallback — both return game info with cover image
- MusicCommand: Deezer API for mainstream, Jamendo for free/CC music
- MusicCommand: Returns audio URL message

### Wave 4c: Complex Scraping + Media (2 commands)

| Command | Config Name | Dependencies | Notes |
|---------|------------|--------------|-------|
| CarroCommand | `carro` | FIPE + Wikipedia + Commons APIs | Very complex: random car model → FIPE price → Wikipedia image |
| HentaiCommand | `hentai` | Hitomi.la + Nhentai scraping | flags=[hitomi, nhentai], requires Referer headers for CDN |

**Key considerations:**
- CarroCommand is the most complex non-WhatsApp command: 3 API sources, filtering, fallback
- HentaiCommand requires `Referer: https://hitomi.la/` header for CDN images
- HentaiCommand has hitomi/nhentai provider flags
- Both need careful error handling and fallback logic

### Wave 5a: MongoDB Commands (2 commands)

| Command | Config Name | MongoDB Usage | Notes |
|---------|------------|---------------|-------|
| BorgesCommand | `borges` | MongoDBConnection (read) | Simple: fetch random Borges quote |
| GroupMentionsCommand | `grupo` | GroupMentionsService (CRUD) | Complex state machine: create/join/leave/list mentions |

**Key considerations:**
- Need MongoDB client in Python engine (Motor + Beanie already in stack)
- BorgesCommand: simple random document fetch from a collection
- GroupMentionsCommand: complex CRUD with participant tracking, expiry, groupOnly
- GroupMentionsCommand uses args with subcommands pattern — most complex non-WhatsApp command

### Wave 5b: Menu Command (1 command)

| Command | Config Name | Dependencies | Notes |
|---------|------------|--------------|-------|
| MenuCommand | `menu` | CommandFactory introspection | Lists all available commands grouped by category |

**Key considerations:**
- MenuCommand introspects `CommandFactory.getAllStrategies()` to list commands
- In hybrid mode, needs to know about BOTH TS and Python commands
- Options: migrate last (after all other commands are in Python) OR implement `wa_call` to get Python command list and merge
- **Recommended:** migrate as the LAST command before Wave 6, when all non-WhatsApp commands are in Python

### Wave 6: WhatsApp-Dependent Commands (7 commands — gateway-only)

These commands require direct WhatsApp socket operations that cannot be trivially proxied via `wa_call`.

| Command | Config Name | WhatsApp Operations | Notes |
|---------|------------|---------------------|-------|
| AddCommand | `add` | `groupParticipantsUpdate('add')` | Add member by phone number |
| AdmCommand | `adm` | `groupParticipantsUpdate('promote'/'demote')` | Toggle admin status |
| BanCommand | `ban` | `groupParticipantsUpdate('remove')` | Remove member |
| DriveCommand | `drive` | Media download + DiscordService | Download media → upload to Discord |
| ExtrairCommand | `extrair` | `updateMediaMessage` + sharp | Extract/convert media |
| ScarraCommand | `scarra` | ViewOnce message unwrapping | Reveal viewOnce messages |
| StickerCommand | `stic` | wa-sticker-formatter + ffmpeg | Create stickers from media |

**Migration approach options:**
1. **Keep in gateway** — these 7 commands remain in TS permanently (simplest)
2. **wa_call bridge** — migrate logic to Python, use `wa_call` for WhatsApp operations (more complex but consistent)
3. **Hybrid** — migrate simple ones (Add/Adm/Ban) via `wa_call`, keep media-heavy ones in TS

**Recommended:** Option 3 — migrate Add/Adm/Ban (simple group participant ops) via `wa_call`, keep Drive/Extrair/Scarra/Sticker in TS (heavy binary/media processing better in Bun's runtime).

### Wave 7: Cleanup + TS Command Removal

Final cleanup after all migratable commands are in Python.

**Tasks:**
1. Remove all migrated TS command source files from `gateway/src/commands/`
2. Remove all migrated TS command tests from `gateway/tests/unit/commands/`
3. Remove unused TS data files from `gateway/src/data/`
4. Remove unused TS services/scrapers/clients
5. Remove unused npm dependencies from `gateway/package.json`
6. Update MenuCommand to only list Python commands (if in engine) or remaining TS commands (if in gateway)
7. Final CI verification: all tests pass, Docker builds succeed
8. Update CLAUDE.md for post-migration structure

---

## Command Inventory (All 41 Commands)

### Migrated to Python (20 commands)

| # | Command | Config Name | Wave | Category |
|---|---------|------------|------|----------|
| 1 | OiCommand | `oi` | 1 | aleatórias |
| 2 | D20Command | `d20` | 1 | aleatórias |
| 3 | MateusCommand | `mateus` | 1 | aleatórias |
| 4 | FatoCommand | `fato` | 1 | aleatórias |
| 5 | AlcoraoCommand | `alcorão` | 2a | aleatórias |
| 6 | BaralhoCommand | `baralho` | 2a | aleatórias |
| 7 | MealRecipesCommand | `receita` | 2a | aleatórias |
| 8 | PuppyCommand | `puppy` | 2a | aleatórias |
| 9 | ClashRoyaleCommand | `clashroyale` | 2b | aleatórias |
| 10 | LeagueOfLegendsCommand | `lol` | 2b | aleatórias |
| 11 | CountryFlagCommand | `bandeira` | 2b | aleatórias |
| 12 | BeerCommand | `cerveja` | 2c | aleatórias |
| 13 | FilmeSerieCommand | `filme` | 2c | aleatórias |
| 14 | MyAnimeListCommand | `anime` | 2c | aleatórias |
| 15 | BibliaCommand | `bíblia` | 2d | aleatórias |
| 16 | TorahCommand | `torá` | 2d | aleatórias |
| 17 | BichoCommand | `bicho` | 2d | outras |
| 18 | FuckCommand | `fuck` | 2e | grupo |
| 19 | PornoCommand | `porno` | 2e | aleatórias |
| 20 | Rule34Command | `rule 34` | 2e | aleatórias |
| 21 | AudioCommand | `áudio` | 3a | download |

### Remaining — To Migrate (13 commands)

| # | Command | Config Name | Planned Wave | Category | Key Dependencies |
|---|---------|------------|--------------|----------|------------------|
| 1 | HeartstoneCommand | `hs` | 3b | aleatórias | Blizzard OAuth + sharp → Pillow |
| 2 | MagicTheGatheringCommand | `mtg` | 3b | aleatórias | MTG API + sharp → Pillow |
| 3 | PokemonTCGCommand | `pokémontcg` | 3b | aleatórias | TCGdex + sharp → Pillow |
| 4 | YugiohCommand | `ygo` | 3b | aleatórias | YGOProDeck + sharp → Pillow |
| 5 | AnimalCommand | `animal` | 4a | aleatórias | Wikipedia API |
| 6 | PokemonCommand | `pokémon` | 4a | aleatórias | PokeAPI + sharp → Pillow |
| 7 | GameCommand | `game` | 4b | aleatórias | IGDB OAuth + RAWG fallback |
| 8 | MusicCommand | `música` | 4b | download | Deezer + Jamendo |
| 9 | CarroCommand | `carro` | 4c | aleatórias | FIPE + Wikipedia + Commons |
| 10 | HentaiCommand | `hentai` | 4c | aleatórias | Hitomi + Nhentai scraping |
| 11 | BorgesCommand | `borges` | 5a | outras | MongoDB |
| 12 | GroupMentionsCommand | `grupo` | 5a | grupo | MongoDB state machine |
| 13 | MenuCommand | `menu` | 5b | outras | CommandFactory introspection |

### Gateway-Only (7 commands — Wave 6)

| # | Command | Config Name | Category | WhatsApp Operations |
|---|---------|------------|----------|---------------------|
| 1 | AddCommand | `add` | grupo | groupParticipantsUpdate('add') |
| 2 | AdmCommand | `adm` | grupo | groupParticipantsUpdate('promote/demote') |
| 3 | BanCommand | `ban` | grupo | groupParticipantsUpdate('remove') |
| 4 | DriveCommand | `drive` | grupo | Media download + Discord upload |
| 5 | ExtrairCommand | `extrair` | download | updateMediaMessage + sharp |
| 6 | ScarraCommand | `scarra` | download | ViewOnce unwrapping |
| 7 | StickerCommand | `stic` | download | wa-sticker-formatter + ffmpeg |

---

## Library Mapping (TS → Python)

| TS Library | Python Equivalent | Used In |
|-----------|-------------------|---------|
| axios / AxiosClient | httpx / HttpClient | All API commands |
| cheerio | beautifulsoup4 | Rule34, BichoCommand |
| sharp | Pillow | Card games, Pokemon team, Extrair |
| google-tts-api | gTTS | AudioCommand |
| nsfwhub | Direct HTTP to API | Fuck, Porno |
| wa-sticker-formatter | N/A (stays in gateway) | Sticker |
| fluent-ffmpeg | N/A (stays in gateway) | Sticker |
| mongodb (MongoClient) | Motor + Beanie | Borges, GroupMentions |
| pino | structlog | Logging |
| @sentry/bun | sentry-sdk | Error tracking |

---

## Technical Notes

### Migration Pattern Per Command

1. Read TS source → understand config, execute logic, API calls
2. Create `engine/bot/domain/commands/<name>.py` extending `Command`
3. Define `config` property with `CommandConfig`
4. Implement `execute(data, parsed)` using `Reply.to(data)` builder
5. Create `engine/tests/unit/commands/test_<name>.py` with mocked API calls
6. Register in `engine/bot/application/register_commands.py`
7. Remove from `gateway/src/factories/CommandFactory.ts`
8. Update `gateway/tests/unit/factories/CommandFactory.test.ts`
9. Run both test suites: `bun test:run` (991+) + `uv run pytest` (467+)

### WebSocket Binary Protocol

Commands returning media (images, audio, video) send binary frames through WebSocket:
- Python sends binary frames BEFORE JSON response (ordering fix from 2026-03-17)
- Gateway PythonBridge detects binary via `typeof !== 'string'` (Bun sends Buffer, not ArrayBuffer)
- Binary data stored in `pendingBinary` map, attached to response messages by `deserializeMessages()`

### wa_call Bridge

For commands needing WhatsApp operations:
```
Python → ws.send_json({type: 'wa_call', method: 'groupParticipantsUpdate', data: {...}})
Gateway → executes via BaileysAdapter → ws.send_json({type: 'wa_result', id: msg_id, data: result})
Python → asyncio.Future resolved with result
```

### Data Files

Static data (emoji maps, book lists, draw configs) stored in `engine/bot/data/`:
- `torah_books.py` — Torah book names and chapter verse counts
- `bicho.py` — Jogo do Bicho animal emojis, draw IDs, prize emojis
- Future: card game data, language lists, NSFW tags, etc.
