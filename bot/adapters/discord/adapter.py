import discord


class DiscordInteractionAdapter:
    def __init__(self, interaction: discord.Interaction) -> None:
        self._interaction = interaction

    async def send_response(self, text: str) -> None:
        await self._interaction.response.send_message(text)

    async def defer(self) -> None:
        await self._interaction.response.defer()

    async def send_followup(self, text: str) -> None:
        await self._interaction.followup.send(text)
