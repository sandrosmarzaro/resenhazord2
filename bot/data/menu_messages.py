"""Static preset menu messages for specific command sections."""

MENU_GRUPO = """\t\t\t📝 *COMANDOS DE GRUPO* 📝

🎉 _Criar_
- *,grupo create* valorant
> Cria o grupo valorant com você
- *,grupo create* valorant @fulano @ciclano
> Cria o grupo valorant com você e mais pessoas

⚰️ _Deletar_
- *,grupo delete* valorant
> Deleta o grupo valorant (admin)

✏️ _Editar_
- *,grupo rename* valorant val
> Renomeia o grupo valorant para val (admin)

🫂 _Adicionar_
- *,grupo add* val
> Se adiciona no grupo val
- *,grupo add* val @fulano @ciclano
> Adiciona pessoas no grupo val (admin)

🚷 _Sair_
- *,grupo exit*
> Saia do grupo val
- *,grupo exit* @fulano @ciclano
> Tire pessoas do grupo val (admin)

📚 Listagem
- *,grupo list*
> Liste os grupos
- *,grupo list* val
> Liste os números no grupo val

💬 _Mensagem_
- *,grupo* val texto
> Mande um texto marcando todos do grupo val"""

MENU_BIBLIA = """\t\t\t📝 *COMANDOS DE BÍBLIA* 📝

🎲 _Aleatório_
- *,biblia*
> Receba um versículo aleatório da bíblia.

📒 _Por Referência_
- *,biblia* _Mateus 1:2_
> Receba o versículo especificado da bíbla.

📚 _Múltiplas Referências_
- *,biblia* _Mateus 1:2-3_
> Receba junto os vários versículos especificados.

📜 _Versão da Bíblia_
- *,biblia* _nvi_
> Especifique a versão da bíblia que tu desejas.

_Versões_:
-  nvi: Nova Versão Internacional
-   ra: Revista e Atualizada
-  acf: Almeida Corrigida Fiel
-  kjv: King James Version
-  bbe: Bible in Basic English
- apee: La Bible de L'Épée
-  rvr: Reina Valera Revisada"""

CATEGORY_HEADERS: dict[str, str] = {
    'grupo': '🫂 FUNÇÕES DE GRUPO 🫂',
    'aleatórias': '🎲 FUNÇÕES ALEATÓRIAS 🎲',
    'download': '💾 FUNÇÕES DE DOWNLOAD 💾',
    'outras': '🙂 OUTRAS FUNÇÕES 🙂',
}

CATEGORY_ORDER: list[str] = ['grupo', 'aleatórias', 'download', 'outras']

ALEATORIA_SUBHEADER = (
    '\n\n_(use as opções *show* e/ou *dm* para enviar imagens'
    ' no chat privado e sem visualização única respectivamente)_'
)
