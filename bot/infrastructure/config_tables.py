from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.infrastructure.models import Base


class ChatRow(Base):
    __tablename__ = 'chat'
    __table_args__ = (UniqueConstraint('platform', 'native_id', name='uq_chat_platform_native'),)

    platform: Mapped[str] = mapped_column(String(16))
    native_id: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(8))
    default_policy: Mapped[str] = mapped_column(String(8), default='open')
    dev_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    overrides: Mapped[list['CommandOverrideRow']] = relationship(
        back_populates='chat',
        cascade='all, delete-orphan',
    )
    blocked: Mapped[list['BlockedUserRow']] = relationship(
        back_populates='chat',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:
        return f'ChatRow(platform={self.platform!r}, native_id={self.native_id!r})'


class CommandOverrideRow(Base):
    __tablename__ = 'command_override'
    __table_args__ = (UniqueConstraint('chat_id', 'command_name', name='uq_override_chat_command'),)

    chat_id: Mapped[UUID] = mapped_column(ForeignKey('chat.id', ondelete='CASCADE'))
    command_name: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean)

    chat: Mapped['ChatRow'] = relationship(back_populates='overrides')

    def __repr__(self) -> str:
        return f'CommandOverrideRow(command_name={self.command_name!r}, enabled={self.enabled!r})'


class BlockedUserRow(Base):
    __tablename__ = 'chat_blocked_user'
    __table_args__ = (UniqueConstraint('chat_id', 'user_key', name='uq_blocked_chat_user'),)

    chat_id: Mapped[UUID] = mapped_column(ForeignKey('chat.id', ondelete='CASCADE'))
    user_key: Mapped[str] = mapped_column(String(64))
    alt_key: Mapped[str | None] = mapped_column(String(64))

    chat: Mapped['ChatRow'] = relationship(back_populates='blocked')

    def __repr__(self) -> str:
        return f'BlockedUserRow(user_key={self.user_key!r}, alt_key={self.alt_key!r})'
