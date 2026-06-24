# Resenhazord2

Platform-agnostic chatbot: a Python core owns all command logic; thin platform
adapters (WhatsApp, Discord, Telegram) translate native messages into one command
surface. This glossary fixes the domain terms; it is not a spec.

## Language

**Command**:
A single bot capability triggered by a comma-prefix (`,menu`) or a native slash
command. Declares a static `CommandScope` in code.
_Avoid_: action, handler (those are implementation roles).

**Scope**:
A command's code-declared visibility class: `PUBLIC`, `NSFW`, `INTERNAL`, `ADMIN`,
`DEV`, `DISABLED`. Set in code, not per chat.
_Avoid_: permission, role.

**Platform**:
One of WhatsApp, Discord, Telegram. Adapters map native messages onto Commands.

**Chat**:
A single conversation the bot serves, identified by `(platform, native_id)`. Its
`type` is `group` or `private`.
_Avoid_: room, channel, conversation.

**Default policy**:
A chat's baseline command posture. `OPEN` = public commands on, NSFW off. `CURATED`
= everything off; overrides act as an allow-list. The `,only resenhaz` setting means
a chat is `CURATED`.
_Avoid_: mode, profile.

**Command override**:
A stored per-chat deviation from a command's code default — `enabled` true or false.
No override row means "use the default." Only `PUBLIC` and `NSFW` commands are
overridable.
_Avoid_: setting, flag, rule.

**Togglable command**:
A command an admin may override: scope `PUBLIC` or `NSFW` only. Infra scopes
(`DISABLED`, `DEV`, `ADMIN`, `INTERNAL`) are never togglable.
_Avoid_: configurable.

**Effective enablement**:
The resolved on/off for a `(chat, command)` pair after applying default policy and
overrides over the code default. The value `_dispatch` acts on.
