import discord


class DiscordInteractionAdapter:
    def __init__(self, interaction: discord.Interaction) -> None:
        self._interaction = interaction
        self._deferred = False

    @property
    def is_deferred(self) -> bool:
        return self._deferred

    async def send_message(
        self,
        text: str | None = None,
        *,
        embed: discord.Embed | None = None,
        file: discord.File | None = None,
    ) -> None:
        if self._deferred:
            await self.send_followup(text, embed=embed, file=file)
            return
        kwargs: dict = {}
        if text is not None:
            kwargs['content'] = text
        if embed is not None:
            kwargs['embed'] = embed
        if file is not None:
            kwargs['file'] = file
        await self._interaction.response.send_message(**kwargs)

    async def defer(self) -> None:
        await self._interaction.response.defer()
        self._deferred = True

    async def send_followup(
        self,
        text: str | None = None,
        *,
        embed: discord.Embed | None = None,
        file: discord.File | None = None,
    ) -> None:
        kwargs: dict = {}
        if text is not None:
            kwargs['content'] = text
        if embed is not None:
            kwargs['embed'] = embed
        if file is not None:
            kwargs['file'] = file
        await self._interaction.followup.send(**kwargs)
