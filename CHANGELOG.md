# CHANGELOG

<!-- version list -->

## v1.4.0 (2026-04-17)

### Features

- **sticker**: Add -X% option to reduce quality and resolution
  ([`0750194`](https://github.com/sandrosmarzaro/resenhazord2/commit/075019467b33b595e344d0ff4331be3075cb8540))


## v1.3.2 (2026-04-16)

### Bug Fixes

- **transfermarkt**: Cap concurrency and tolerate partial failures
  ([`7a52b31`](https://github.com/sandrosmarzaro/resenhazord2/commit/7a52b31904e3d3cae39f5fa9ac88c12b28345494))


## v1.3.1 (2026-04-16)

### Bug Fixes

- **deploy**: Align bot image ref with pipeline push tag
  ([`a3542a3`](https://github.com/sandrosmarzaro/resenhazord2/commit/a3542a330b6e615604e352f5ac518319d7f064cd))


## v1.3.0 (2026-04-16)

### Features

- **menu**: Add INFORMATION category for info commands
  ([`c8b7fd4`](https://github.com/sandrosmarzaro/resenhazord2/commit/c8b7fd423c6f0acbc98e63b9d6d4295fbafbc0c9))

- **menu**: Move currency to INFORMATION category
  ([`fe469af`](https://github.com/sandrosmarzaro/resenhazord2/commit/fe469af56a4c9531bf4e720896bf6e314db40834))

### Testing

- **menu**: Add regression tests for Category enum integration
  ([`395edbd`](https://github.com/sandrosmarzaro/resenhazord2/commit/395edbde2540191a829186a2d2749e728ce50242))


## v1.2.1 (2026-04-15)

### Bug Fixes

- **football**: Format_date_label uses date comparison
  ([`272f11f`](https://github.com/sandrosmarzaro/resenhazord2/commit/272f11f8d1a21bf20590befb00880110a08b71e7))

- **football**: Resolve type and lint errors in score module
  ([`230bf76`](https://github.com/sandrosmarzaro/resenhazord2/commit/230bf7648e558a2d480e260b5c97bb15ffff3358))

- **football**: Return league code string from GlobalTopTeam.find_league
  ([`ac7a0af`](https://github.com/sandrosmarzaro/resenhazord2/commit/ac7a0aff950164f9a45cdd1d152358bc4284d0be))

- **football**: Score emoji returns dash for none
  ([`57eff1c`](https://github.com/sandrosmarzaro/resenhazord2/commit/57eff1c96d23626a83ae69ba9780df2b7bffd3b2))

### Documentation

- **conventions**: Require English for Python file/class/function names
  ([`7f4a5b8`](https://github.com/sandrosmarzaro/resenhazord2/commit/7f4a5b81224507e6a979a9a6c2161cefc546fee7))

### Refactoring

- **football**: Extract caption building to TeamCaptionBuilder
  ([`c4a8601`](https://github.com/sandrosmarzaro/resenhazord2/commit/c4a8601ece27fb04be457ce8ea6861651af53586))

- **football**: Extract FullLineupBuilder from football_team
  ([`c0c5259`](https://github.com/sandrosmarzaro/resenhazord2/commit/c0c52598446e26f53d618880a751c51514e1698b))

- **football**: Extract services for cleaner code
  ([`aa32b5a`](https://github.com/sandrosmarzaro/resenhazord2/commit/aa32b5af30502cb05e456917e06670655c8a3c14))

- **football**: Fix Scout audit violations
  ([`43268d3`](https://github.com/sandrosmarzaro/resenhazord2/commit/43268d3c9e778214c59421a263f5da4533c79b23))

- **score**: Fix TYPE_CHECKING imports and remove TC001 suppress
  ([`0d817ff`](https://github.com/sandrosmarzaro/resenhazord2/commit/0d817ffac8b92aff1ace6a7d1d9114415e390e43))

- **score**: Rename placar module to score for English naming
  ([`bb5c03a`](https://github.com/sandrosmarzaro/resenhazord2/commit/bb5c03a399eaba066a4f760b03764a1a6931c8ba))

- **transfermarkt**: Extract live-match parsing to live_parser.py
  ([`d3c57e7`](https://github.com/sandrosmarzaro/resenhazord2/commit/d3c57e726777efcfc2d9d455efb970a4c0b8350e))

- **transfermarkt**: Move module-level constants to class attributes
  ([`8e56946`](https://github.com/sandrosmarzaro/resenhazord2/commit/8e56946115989411f9e1a5226acfbf556161cc71))

- **transfermarkt**: Split LiveMatchParser into focused parser classes
  ([`6260bc0`](https://github.com/sandrosmarzaro/resenhazord2/commit/6260bc07daad57c302a2e141d1ffdb0a10a6e080))

- **transfermarkt**: Split TransfermarktParser into focused parser classes
  ([`15f6b20`](https://github.com/sandrosmarzaro/resenhazord2/commit/15f6b208e7ff5317dada92da16637651f7f6fcbe))


## v1.2.0 (2026-04-14)

### Bug Fixes

- **placar**: Use timedelta for tomorrow calculation
  ([`5c5e068`](https://github.com/sandrosmarzaro/resenhazord2/commit/5c5e06865c9cf8bc9a0dc856b014e228db8d7753))

- **transfermarkt**: Accept mixed-case competition codes
  ([`f383d5a`](https://github.com/sandrosmarzaro/resenhazord2/commit/f383d5a1ed2b4036e343ace3e0e474b78bed4e2b))

- **transfermarkt**: Correct _is_live_score to detect '2 - 1' format
  ([`c0625e4`](https://github.com/sandrosmarzaro/resenhazord2/commit/c0625e4009e56565ef5efa94e92cd15a6d15e99b))

- **transfermarkt**: Parallelize HTTP fetch with error handling
  ([`39fac58`](https://github.com/sandrosmarzaro/resenhazord2/commit/39fac58491035472ad7b5a766b028c59d788bbeb))

- **transfermarkt**: Resolve type check errors
  ([`88c5e50`](https://github.com/sandrosmarzaro/resenhazord2/commit/88c5e5012251333da38915aa7e6ca5ed5cb8dfed))

### Chores

- Add TC001 ignore for placar.py TYPE_CHECKING imports
  ([`aa904d1`](https://github.com/sandrosmarzaro/resenhazord2/commit/aa904d1d052be33ebc412a7c4fd2d696b25e315e))

### Features

- Add fetch_live_matches method and parse_live_matches parser
  ([`9b8c813`](https://github.com/sandrosmarzaro/resenhazord2/commit/9b8c813002443c185cbbb04e391266fab49f2646))

- Add placar command with score alias for live football matches
  ([`289706d`](https://github.com/sandrosmarzaro/resenhazord2/commit/289706dba0747d2c46fd46b3d815520cec336808))

- Add TmLiveMatch model and MatchStatus enum for live matches
  ([`a66cea0`](https://github.com/sandrosmarzaro/resenhazord2/commit/a66cea060f7b05385b12caadae4d73f0857990ed))

- **placar**: Add past/now/next flags to filter sections
  ([`5393e7a`](https://github.com/sandrosmarzaro/resenhazord2/commit/5393e7a7ed91a68a1b95e9d529b51d1eb1092d33))

- **placar**: Add upcoming matches section with date labels
  ([`3394ed1`](https://github.com/sandrosmarzaro/resenhazord2/commit/3394ed1b65a9cdeff6da4897911811490e49703f))

- **placar**: Italicize teams, add finished-results with league priority cap
  ([`e7b1887`](https://github.com/sandrosmarzaro/resenhazord2/commit/e7b1887ef76c1cd631dc5a2a253d723a7d0fa245))

- **transfermarkt**: Add continental and missing-country flag overrides
  ([`eb60645`](https://github.com/sandrosmarzaro/resenhazord2/commit/eb606451f53d3c4e6260fbbd7374486f528c2c2a))

- **transfermarkt**: Parse live and finished matches with flag overrides
  ([`f4f1463`](https://github.com/sandrosmarzaro/resenhazord2/commit/f4f1463b77ca830250c28597d0e45393e4af225b))

- **transfermarkt**: Tag live matches with source_date
  ([`1894855`](https://github.com/sandrosmarzaro/resenhazord2/commit/1894855c943882d903643854e81c51286b6c25fd))

### Refactoring

- Move NUMBER_EMOJI to bot/data/
  ([`7cae5e9`](https://github.com/sandrosmarzaro/resenhazord2/commit/7cae5e9a6c658c041cab888ab501584a3a8e3e03))

- **placar**: Cap all sections and break line before match time
  ([`06c8f63`](https://github.com/sandrosmarzaro/resenhazord2/commit/06c8f63a5280460e1542e106ab2529281c00adc5))

- **placar**: Rebalance league priorities
  ([`e5c040c`](https://github.com/sandrosmarzaro/resenhazord2/commit/e5c040c74b36677321643578ebd095fcacc744dc))

- **transfermarkt**: Pre-compile regex and reduce params
  ([`6909718`](https://github.com/sandrosmarzaro/resenhazord2/commit/690971891ad460daa4f5af7b7680717b21533c7e))

- **transfermarkt**: Resolve flag overrides via nationality_flag
  ([`fb2864f`](https://github.com/sandrosmarzaro/resenhazord2/commit/fb2864f454ac858bd6b3dabf9a2d85988e8a0626))

### Testing

- Add unit tests for placar command and parse_live_matches
  ([`1a2a879`](https://github.com/sandrosmarzaro/resenhazord2/commit/1a2a8799ba419b1344546eb85762eb8c60270e77))

- **placar**: Add tests for upcoming matches and date formatting
  ([`1cac3af`](https://github.com/sandrosmarzaro/resenhazord2/commit/1cac3afac7f08154d29140a313f3e4f8d9d79f6d))

- **transfermarkt**: Add box-section fixture and fix trio tests
  ([`f8be3fb`](https://github.com/sandrosmarzaro/resenhazord2/commit/f8be3fb5fe22efd923e470ccf4d32fc00480a0bb))


## v1.1.0 (2026-04-13)

### Documentation

- Update CLAUDE.md with code conventions and add git-flow.md
  ([`694adbd`](https://github.com/sandrosmarzaro/resenhazord2/commit/694adbd8e17d287321684f5af7fbab1462250c89))

### Features

- **command**: Add tabela command for football standings
  ([`436d96a`](https://github.com/sandrosmarzaro/resenhazord2/commit/436d96a1d3c40e909956f4e0fc6fb803258ea56e))


## v1.0.0 (2026-04-13)

- Initial Release
