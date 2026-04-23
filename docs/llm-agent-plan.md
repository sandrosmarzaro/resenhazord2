# LLM Integration Plan

## Completed

- Telegram agent mention detection (added `MessageHandler` for regular messages with @bot mentions)
- WhatsApp @mention support (extract from extendedTextMessage contextInfo)
- Discord agent mention + async audio rendering
- Remove menu fallback when agent fails
- Strip bot mentions from response text before sending to LLM
- Strip leading dashes from agent text response
- Add debug logging for command matching
- Strip backticks from agent text response
- Strip quotes from mapped command

## In Progress


## Notes

- Telegram mentions require `mentioned_jids` from gateway - if missing, fallback to text pattern matching
- WhatsApp gateway strips @mention from text, must parse from message context separately
- Agent must strip @mention from text before sending to gateway to avoid duplicate mentions