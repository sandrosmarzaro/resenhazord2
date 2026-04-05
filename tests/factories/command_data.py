from factory.base import Factory
from factory.declarations import LazyAttribute, LazyFunction, Sequence

from bot.domain.models.command_data import CommandData


class GroupCommandDataFactory(Factory):
    class Meta:
        model = CommandData

    text = ''
    jid = LazyAttribute(lambda o: f'1203630000000000{o.meta_seq}@g.us')
    sender_jid = LazyAttribute(lambda o: f'5511900000{o.meta_seq:03d}@s.whatsapp.net')
    participant = LazyAttribute(lambda o: o.sender_jid)
    is_group = True
    expiration = None
    mentioned_jids = LazyFunction(list)
    quoted_message_id = None
    quoted_text = None
    media_type = None
    media_source = None
    media_is_animated = False
    media_caption = None
    message_id = LazyAttribute(lambda o: f'MSG_{o.meta_seq}')
    push_name = LazyAttribute(lambda o: f'User {o.meta_seq}')

    class Params:
        meta_seq = Sequence(lambda n: n + 1)


class PrivateCommandDataFactory(Factory):
    class Meta:
        model = CommandData

    text = ''
    jid = LazyAttribute(lambda o: f'5511900000{o.meta_seq:03d}@s.whatsapp.net')
    sender_jid = LazyAttribute(lambda o: o.jid)
    participant = None
    is_group = False
    expiration = None
    mentioned_jids = LazyFunction(list)
    quoted_message_id = None
    quoted_text = None
    media_type = None
    media_source = None
    media_is_animated = False
    media_caption = None
    message_id = LazyAttribute(lambda o: f'MSG_{o.meta_seq}')
    push_name = LazyAttribute(lambda o: f'User {o.meta_seq}')

    class Params:
        meta_seq = Sequence(lambda n: n + 1)
