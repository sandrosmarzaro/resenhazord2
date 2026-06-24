"""SQLAlchemy ORM tables for per-group command config (ADR 0012)."""

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.infrastructure.database import Base


class ChatRow(Base):
    __tablename__ = 'chat'
    __table_args__ = (UniqueConstraint('platform', 'native_id', name='uq_chat_platform_native'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(16))
    native_id: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(8))
    default_policy: Mapped[str] = mapped_column(String(8), default='open')

    overrides: Mapped[list['CommandOverrideRow']] = relationship(
        back_populates='chat',
        cascade='all, delete-orphan',
        lazy='selectin',
    )


class CommandOverrideRow(Base):
    __tablename__ = 'command_override'
    __table_args__ = (UniqueConstraint('chat_id', 'command_name', name='uq_override_chat_command'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chat.id', ondelete='CASCADE'))
    command_name: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean)

    chat: Mapped['ChatRow'] = relationship(back_populates='overrides')
