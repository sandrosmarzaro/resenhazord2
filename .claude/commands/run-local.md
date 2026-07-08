Stop both prod VPS and run the full stack locally to observe/debug the bot live.

## Stop prod (frees the single WhatsApp session + broker)

```
ssh resenhazord-core 'cd ~/resenhazord2 && docker compose -f compose.core.yml down'
ssh resenhazord-edge 'cd ~/resenhazord2 && docker compose -f compose.edge.yml down'
```

## Run local (gateway + bot + rabbitmq + postgres)

```
docker compose up -d --build
```

- Alembic `upgrade head` runs on bot startup (compose `command`) — no manual migration.
- Gateway resumes the same WhatsApp session from Mongo `auth_state` (no QR) **only while edge is down**; the session is single-holder.
- `groups_mentions` + `auth_state` = prod Mongo (via `.env`). Local postgres is a throwaway (per-group config only).

## Verify

```
docker compose logs whatsapp | grep -E 'connection_opened|qr_received|bad_session'
docker inspect -f '{{.State.Health.Status}}' bot
docker compose logs -f whatsapp bot   # watch live
```

`connection_opened` + bot `healthy` = ready. Send the command in the WhatsApp group; read logs.

## Restore prod (when done)

```
docker compose down
ssh resenhazord-core 'cd ~/resenhazord2 && docker compose -f compose.core.yml up -d'
ssh resenhazord-edge 'cd ~/resenhazord2 && docker compose -f compose.edge.yml up -d'
```

Bring local down first so edge can reclaim the WhatsApp session.

## Debug tips

- Add a temporary `logger.info({ event: 'diag', key: data.key })` in `gateway/src/bridge/CommandPublisher.ts` to inspect incoming message keys (lid/pn, `participantAlt`), then `docker compose up -d --build whatsapp`.
- Stale local pg schema (`column ... does not exist` / orphan alembic rev): `docker compose stop bot postgres && docker volume rm resenhazord2_postgres-data && docker compose up -d` (migrations re-run fresh).
