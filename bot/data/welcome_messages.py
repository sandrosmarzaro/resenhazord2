WELCOME_TEMPLATE = """👋 *E aí, galera! Sou o Resenhazord2.*

Bot de resenha: memes, downloads, figurinhas, jogos e muito mais. \
Manda {menu_command} pra ver tudo que eu sei fazer."""

WHATSAPP_WELCOME = WELCOME_TEMPLATE.format(menu_command='*,menu*')
# Bare, so Telegram keeps it a tappable command.
TELEGRAM_WELCOME = WELCOME_TEMPLATE.format(menu_command='/menu')
