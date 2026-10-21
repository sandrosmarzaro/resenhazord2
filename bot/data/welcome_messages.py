WELCOME_TEMPLATE = """👋 {bold}E aí, galera! Sou o Resenhazord2.{bold}

Bot de resenha: memes, downloads, figurinhas, jogos e muito mais. \
Manda {menu_command} pra ver tudo que eu sei fazer."""

WHATSAPP_WELCOME = WELCOME_TEMPLATE.format(bold='*', menu_command='*,menu*')
# Bare, so Telegram keeps it a tappable command.
TELEGRAM_WELCOME = WELCOME_TEMPLATE.format(bold='*', menu_command='/menu')
# Discord renders markdown as-is: a single * is italics there.
DISCORD_WELCOME = WELCOME_TEMPLATE.format(bold='**', menu_command='`/menu`')
