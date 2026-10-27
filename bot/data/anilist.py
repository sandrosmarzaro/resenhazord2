ANILIST_MEDIA_QUERY = """
query ($page: Int, $perPage: Int, $type: MediaType, $sort: [MediaSort]) {
  Page(page: $page, perPage: $perPage) {
    media(type: $type, sort: $sort, isAdult: false) {
      title { romaji }
      coverImage { extraLarge }
      episodes
      chapters
      startDate { year }
      averageScore
      rankings { rank type allTime }
      genres
      tags { name category }
      studios(isMain: true) { nodes { name } }
      staff(perPage: 6) { edges { role node { name { full } } } }
    }
  }
}
"""

ANILIST_AUTHOR_ROLE_PREFIXES: tuple[str, ...] = ('Story', 'Art')
