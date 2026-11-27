from typing import ClassVar


class Markdown:
    """Escaping for text that lands in a GitHub issue.

    A pipe would split a table cell and a backtick close a code span. An @name would
    notify that GitHub user, so a zero-width space follows every @.
    """

    _NO_MENTION: ClassVar[str] = '@\u200b'

    @classmethod
    def code(cls, value: object) -> str:
        return f'`{cls._cell(str(value).replace("`", "'"))}`'

    @classmethod
    def text(cls, value: object) -> str:
        return cls._cell(str(value).replace('@', cls._NO_MENTION))

    @classmethod
    def quote(cls, value: str) -> str:
        quiet = value.replace('@', cls._NO_MENTION)
        return '\n'.join(f'> {line}' for line in quiet.splitlines())

    @staticmethod
    def _cell(value: str) -> str:
        return value.replace('|', '\\|').replace('\n', ' ')
