import factory

from bot.domain.models.command_data import CommandData


class GroupCommandDataFactory(factory.Factory):
    class Meta:
        model = CommandData

    text = ''
    jid = factory.LazyAttribute(lambda o: f'1203630000000000{o.meta_seq}@g.us')
    sender_jid = factory.LazyAttribute(lambda o: f'5511900000{o.meta_seq:03d}@s.whatsapp.net')
    participant = factory.LazyAttribute(lambda o: o.sender_jid)
    is_group = True
    expiration = None
    mentioned_jids = factory.LazyFunction(list)
    quoted_message_id = None
    media_type = None
    media_source = None
    media_is_animated = False
    media_caption = None
    message_id = factory.LazyAttribute(lambda o: f'MSG_{o.meta_seq}')
    push_name = factory.LazyAttribute(lambda o: f'User {o.meta_seq}')

    class Params:
        meta_seq = factory.Sequence(lambda n: n + 1)


class PrivateCommandDataFactory(factory.Factory):
    class Meta:
        model = CommandData

    text = ''
    jid = factory.LazyAttribute(lambda o: f'5511900000{o.meta_seq:03d}@s.whatsapp.net')
    sender_jid = factory.LazyAttribute(lambda o: o.jid)
    participant = None
    is_group = False
    expiration = None
    mentioned_jids = factory.LazyFunction(list)
    quoted_message_id = None
    media_type = None
    media_source = None
    media_is_animated = False
    media_caption = None
    message_id = factory.LazyAttribute(lambda o: f'MSG_{o.meta_seq}')
    push_name = factory.LazyAttribute(lambda o: f'User {o.meta_seq}')

    class Params:
        meta_seq = factory.Sequence(lambda n: n + 1)
