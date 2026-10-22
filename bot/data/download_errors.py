FILE_TOO_LARGE_MESSAGE = 'Vídeo muito grande pra baixar 📦'

NO_VIDEO_IN_POST = 'There is no video in this post'
NO_VIDEO_IN_TWEET = 'No video could be found in this tweet'

YTDLP_ERROR_MESSAGES: dict[str, str] = {
    NO_VIDEO_IN_TWEET: 'Esse tweet não tem vídeo 📸',
    'Unsupported URL': 'Esse link não é suportado 🔗',
    'login required': 'Esse conteúdo precisa de login 🔐',
    'Video unavailable': 'Esse vídeo não está disponível 😔',
    'Private video': 'Esse vídeo é privado 🔒',
    'Sign in to confirm your age': 'Esse vídeo tem restrição de idade 🔞',
    'HTTP Error 403': 'Acesso ao vídeo foi bloqueado 🚫',
    'Forbidden': 'Acesso ao vídeo foi bloqueado 🚫',
    'exceeds': FILE_TOO_LARGE_MESSAGE,
    'File is larger': FILE_TOO_LARGE_MESSAGE,
}

FALLBACK_MESSAGE = 'Não consegui baixar esse vídeo 😅'
