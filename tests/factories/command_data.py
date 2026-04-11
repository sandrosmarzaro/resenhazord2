from factory import Factory, LazyAttribute, LazyFunction, Sequence
from faker import Faker

from bot.domain.models.command_data import CommandData

fake = Faker(['pt_BR', 'en_US'])


class BaseCommandDataFactory(Factory):
    class Meta:
        model = CommandData

    message_id = Sequence(lambda n: f'MSG_{n:04d}')
    push_name = LazyAttribute(lambda o: fake.name())

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class(**kwargs)


class GroupCommandDataFactory(BaseCommandDataFactory):
    class Meta:
        model = CommandData

    text = ''
    jid = LazyAttribute(lambda o: f'1203630000000000{o.meta_seq:04d}@g.us')
    sender_jid = LazyAttribute(lambda o: f'55119{fake.msisdn()[:4]}@s.whatsapp.net')
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

    class Params:
        meta_seq = Sequence(lambda n: n + 1)


class PrivateCommandDataFactory(BaseCommandDataFactory):
    class Meta:
        model = CommandData

    text = ''
    jid = LazyAttribute(lambda o: f'55119{fake.msisdn()[:4]}@s.whatsapp.net')
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

    class Params:
        meta_seq = Sequence(lambda n: n + 1)


class MentionedGroupCommandDataFactory(GroupCommandDataFactory):
    @classmethod
    def build(cls, **kwargs) -> CommandData:
        mentions = kwargs.pop('mentioned_jids', None)
        if mentions is None:
            num_mentions = kwargs.pop('_num_mentions', 2)
            mentions = [f'55119{fake.msisdn()[:4]}@s.whatsapp.net' for _ in range(num_mentions)]
        return super().build(mentioned_jids=mentions, **kwargs)


class QuotedCommandDataFactory(GroupCommandDataFactory):
    @classmethod
    def build(cls, **kwargs) -> CommandData:
        return super().build(
            quoted_message_id=f'QUOTE_MSG_{fake.random_number(digits=5)}',
            quoted_text=fake.sentence(),
            **kwargs,
        )


class MediaCommandDataFactory(GroupCommandDataFactory):
    @classmethod
    def build(cls, **kwargs) -> CommandData:
        media_type = kwargs.pop('media_type', 'image')
        return super().build(
            media_type=media_type,
            media_source=f'https://example.com/media/{fake.uuid4()}.jpg',
            media_is_animated=kwargs.pop('media_is_animated', False),
            media_caption=kwargs.pop('media_caption', fake.catch_phrase()),
            **kwargs,
        )
