# CHANGELOG

<!-- version list -->

## v1.5.0 (2026-05-04)

### Bug Fixes

- Add comma prefix to agent examples for command mapping
  ([`04f4b45`](https://github.com/sandrosmarzaro/resenhazord2/commit/04f4b4539cb8de586cf9d7399a0b13df703f6532))

- Add MessageHandler for Telegram agent mentions
  ([`b0a1eac`](https://github.com/sandrosmarzaro/resenhazord2/commit/b0a1eaceeea9106a0534589f0b33da2734166b07))

- Add RESENHAZORD2_LID env var and improve bot ID detection for test environments
  ([`0d070d5`](https://github.com/sandrosmarzaro/resenhazord2/commit/0d070d5b8cc472f6e0ee3baf332c56ce046078c1))

- Add rule 34 aliases and video content handling
  ([`47c3259`](https://github.com/sandrosmarzaro/resenhazord2/commit/47c32594f68b2a9c5ef1d0a28d11e47fe0f24c37))

- Add text preview to ws command ack
  ([`dcb6051`](https://github.com/sandrosmarzaro/resenhazord2/commit/dcb605146648e163cf3f284b164070c32191e449))

- Address lint warnings in application layer
  ([`4ebf85e`](https://github.com/sandrosmarzaro/resenhazord2/commit/4ebf85e54df2faf5918e591d1c496b3854701204))

- Agent mode media, args, and menu chunking
  ([`72c266c`](https://github.com/sandrosmarzaro/resenhazord2/commit/72c266c827975c753ee8fb39ac286e8f0bdd0141))

- Apply lint fixes to discord adapter and tests
  ([`ab83822`](https://github.com/sandrosmarzaro/resenhazord2/commit/ab838222d44a5681773ff0f6c9ae9016af61b52e))

- Apply lint rules to LLM infrastructure
  ([`5374115`](https://github.com/sandrosmarzaro/resenhazord2/commit/5374115edd3ebac52ebb935c7b602415758d87e6))

- Compare bot IDs by numeric part only, not full JID
  ([`b5889c3`](https://github.com/sandrosmarzaro/resenhazord2/commit/b5889c365555c93dd997dd95af469115988aa1d0))

- Correct zh-cn and zh-tw language codes
  ([`b30d297`](https://github.com/sandrosmarzaro/resenhazord2/commit/b30d2970e1ccb64d29e13243f8c291af0b1bda7a))

- Forward WhatsApp DM messages to Python for agent mode
  ([`e03c4bc`](https://github.com/sandrosmarzaro/resenhazord2/commit/e03c4bc5368d7ed7edc70dcf46d4dbde8334e1f9))

- Guard undefined JIDs in hasResenhazordMention
  ([`44143bd`](https://github.com/sandrosmarzaro/resenhazord2/commit/44143bdec29327add1aae3d2198f8a69370e64fb))

- Improve command parsing and strategy resolution
  ([`725eeac`](https://github.com/sandrosmarzaro/resenhazord2/commit/725eeaca786f26fd45d418a6ce04acb659eb885a))

- Improve WhatsApp @mention detection for agent
  ([`405688f`](https://github.com/sandrosmarzaro/resenhazord2/commit/405688fe61462d0bdeed4f6df2dc921e54a69420))

- Improve WhatsApp mention detection in gateway
  ([`95bc425`](https://github.com/sandrosmarzaro/resenhazord2/commit/95bc425c7da965d5711268a97872b23becad6f1e))

- Improve WhatsApp mention detection with JID + text fallback
  ([`d5b0417`](https://github.com/sandrosmarzaro/resenhazord2/commit/d5b04171a38c2d3fe19458888dcb4b1964678307))

- Make quality flag optional without dash for sticker command
  ([`0c01277`](https://github.com/sandrosmarzaro/resenhazord2/commit/0c01277d2bde273cbbfbe6d2154ceeed6f56993d))

- Preserve media fields in agent executor for sticker commands
  ([`a2b4d0e`](https://github.com/sandrosmarzaro/resenhazord2/commit/a2b4d0eedcb58c3953ba59ed37be31db42d77c2c))

- Prevent duplicate command registration in Discord
  ([`59055dd`](https://github.com/sandrosmarzaro/resenhazord2/commit/59055dd6cddb64cef4fbc4d6da768b3d3a7e3630))

- Reformat async with statement in discord renderer
  ([`98e0c74`](https://github.com/sandrosmarzaro/resenhazord2/commit/98e0c74b76c9d54481c18e29ed40f5836fce7abf))

- Remove dashes from agent-generated flags
  ([`1c0ba53`](https://github.com/sandrosmarzaro/resenhazord2/commit/1c0ba530c4de5cc71687cda05fb789e5969ab09f))

- Remove dashes from system prompt examples
  ([`606e6d6`](https://github.com/sandrosmarzaro/resenhazord2/commit/606e6d607dfd2d77995add6ba62b7ab12c9fe876))

- Remove menu fallback when agent can't map command
  ([`67f7af0`](https://github.com/sandrosmarzaro/resenhazord2/commit/67f7af0cb5b7608a8e4b23ebfb94abf8b65fcaba))

- Run ruff autofix on test infrastructure files
  ([`bf51f54`](https://github.com/sandrosmarzaro/resenhazord2/commit/bf51f543cbe4242cb1c5f0012e885193a1aceccd))

- Strip backticks from agent text response
  ([`75a1e9b`](https://github.com/sandrosmarzaro/resenhazord2/commit/75a1e9b0cf8231773153ae397596e1f234d27596))

- Strip leading dashes from agent text response
  ([`6557b32`](https://github.com/sandrosmarzaro/resenhazord2/commit/6557b324057cc06cd3ba10477e1e76663f226f3c))

- Strip quotes from agent text response
  ([`09e0b89`](https://github.com/sandrosmarzaro/resenhazord2/commit/09e0b89259d8d35e79788533d76f343bfc2587b2))

- Strip quotes from mapped command
  ([`5e4df0c`](https://github.com/sandrosmarzaro/resenhazord2/commit/5e4df0cf7fa34b5e33b1e38f2e4068a828a402f2))

- Update system prompt with args field
  ([`7532bf1`](https://github.com/sandrosmarzaro/resenhazord2/commit/7532bf12061fab6995e4d0253f7adf00ce7a6c0e))

- Update tests to expect flags without dashes
  ([`98d2dce`](https://github.com/sandrosmarzaro/resenhazord2/commit/98d2dceb035c01551f18b4547d4d610634e91b4e))

- Use full Discord 2000 char limit for chunking
  ([`3ac9197`](https://github.com/sandrosmarzaro/resenhazord2/commit/3ac91979d013b082e9b73e8180b88def0a797605))

- Use io.BytesIO instead of discord.BytesIO
  ([`4a803fc`](https://github.com/sandrosmarzaro/resenhazord2/commit/4a803fcd0a1ecd66bac62ae2382f6c504342ae50))

- **agent**: Address review findings from multi-agent audit
  ([`7a883aa`](https://github.com/sandrosmarzaro/resenhazord2/commit/7a883aac57753f3ef9a9b4af833174fde1c6020b))

- **agent**: Apply review-audit blocker fixes
  ([`50749a9`](https://github.com/sandrosmarzaro/resenhazord2/commit/50749a9a9978c76a5e3f183e534623a53b080e96))

- **ci**: Add persist-credentials to release checkout and revert to v5
  ([`76afb29`](https://github.com/sandrosmarzaro/resenhazord2/commit/76afb29c68ea4193bf45b5690fe6a98b442682a5))

- **ci**: Fix pipeline.yml job indentation
  ([`cf48a1f`](https://github.com/sandrosmarzaro/resenhazord2/commit/cf48a1f9b747c4248974ccf3f7da740f8da89dbd))

- **ci**: Make SonarCloud self-contained in check.yml, remove from pipeline.yml
  ([`4ae3167`](https://github.com/sandrosmarzaro/resenhazord2/commit/4ae3167e91c084cd833a55975632ff52815ce8f6))

- **ci**: Pin checkout@v4 for semantic-release and update git-flow docs
  ([`72f80c7`](https://github.com/sandrosmarzaro/resenhazord2/commit/72f80c74626392b41ed299c8bffb584af88fcd4a))

- **ci**: Remove redundant SonarCloud job and config
  ([`3c16463`](https://github.com/sandrosmarzaro/resenhazord2/commit/3c16463def90e8b23b9f03589bdc094f2fed737c))

- **ci**: Resolve remaining SonarCloud quality gate issues
  ([`0d5eb76`](https://github.com/sandrosmarzaro/resenhazord2/commit/0d5eb76c1336614d826effa5385419e87ccc3334))

- **ci**: Resolve SonarCloud quality gate — remove size from load_default
  ([`74b9e2c`](https://github.com/sandrosmarzaro/resenhazord2/commit/74b9e2c037f4fd8dd1c232cf18049f3f5f6267ff))

- **deploy**: Add default case to case statement
  ([`6eaa53f`](https://github.com/sandrosmarzaro/resenhazord2/commit/6eaa53fe452b0e905e42516df02246f93de469d7))

- **deps**: Resolve all security vulnerabilities
  ([`4823f1b`](https://github.com/sandrosmarzaro/resenhazord2/commit/4823f1be84a0f213a128f5556f107396900e27cb))

- **discord**: Narrow message.guild and use Coroutine return
  ([`d8a7b63`](https://github.com/sandrosmarzaro/resenhazord2/commit/d8a7b63fa4a68f2ee8f79cebc28efab3720e56b7))

- **gateway**: Drop hasAnyMention from forward heuristic
  ([`4fed8f4`](https://github.com/sandrosmarzaro/resenhazord2/commit/4fed8f4e4e01b3862cb8909e8304d8233fff64ae))

- **gateway**: Extract nested ternary in WAMessageFactory
  ([`96c292f`](https://github.com/sandrosmarzaro/resenhazord2/commit/96c292f67ca8becedb5832e3652e61c9b0707354))

- **gateway**: Remove unnecessary type assertions and await
  ([`72f68f4`](https://github.com/sandrosmarzaro/resenhazord2/commit/72f68f434a92fdbadc216387083480c67359df17))

- **http_client**: Coerce explicit headers=None to empty dict
  ([`bab9552`](https://github.com/sandrosmarzaro/resenhazord2/commit/bab9552790a2c701485025f6bccf49fba8c1ea04))

- **python**: Remove regex character class duplicates and simplify patterns
  ([`b4cbed4`](https://github.com/sandrosmarzaro/resenhazord2/commit/b4cbed427f156e30898894cc53294b301261f52b))

- **python**: Resolve SonarQube blockers and bugs
  ([`dd085ce`](https://github.com/sandrosmarzaro/resenhazord2/commit/dd085cea94dc27b0c3dd704e4d2b177ced353ae3))

- **security**: Address remaining Aikido vulnerabilities
  ([`11901aa`](https://github.com/sandrosmarzaro/resenhazord2/commit/11901aa6c89d2e41d98e7df45f4b7a3273692e80))

- **sticker**: Accept quality without % suffix
  ([`9325fb4`](https://github.com/sandrosmarzaro/resenhazord2/commit/9325fb4340a5fd900137b0df84e70c992a2e7772))

- **telegram**: Extend upload timeouts for large media
  ([`febf9bd`](https://github.com/sandrosmarzaro/resenhazord2/commit/febf9bda0d88a63ac251f53db79c122c911d107c))

- **telegram**: Pre-download video and raw media URLs
  ([`a2138d1`](https://github.com/sandrosmarzaro/resenhazord2/commit/a2138d17b7471c7a0479bf0d3b929b8da2751679))

- **telegram**: Swallow transient setMyCommands failures
  ([`d8caee9`](https://github.com/sandrosmarzaro/resenhazord2/commit/d8caee94d8942aa51328581d5e0bb7a3f312386d))

- **test**: Correct test_dm_flag test text to not include option
  ([`1eee8ed`](https://github.com/sandrosmarzaro/resenhazord2/commit/1eee8edaabade863fc24db7eac9dd5ed15836a3f))

- **tests**: Correct MagicMock name attribute in discord bot mention test
  ([`b191670`](https://github.com/sandrosmarzaro/resenhazord2/commit/b191670b699fa2ebab7b7583d855ff88bd22a67e))

- **tests**: Improve HTML fixture accessibility
  ([`ddb1aaa`](https://github.com/sandrosmarzaro/resenhazord2/commit/ddb1aaa8e21899d2f12ed71de26b0082400d6495))

- **tests**: Use approximate float comparison and remove unnecessary async
  ([`779514d`](https://github.com/sandrosmarzaro/resenhazord2/commit/779514dfbaa87142061b6a550084972d540d3b9b))

### Chores

- Add .coverage.* to gitignore
  ([`5149e14`](https://github.com/sandrosmarzaro/resenhazord2/commit/5149e1467ea87dc68edc0a53a751f850369ac0d2))

- Add LLM provider env vars and update claude settings
  ([`22c2fd3`](https://github.com/sandrosmarzaro/resenhazord2/commit/22c2fd32550b3721b1b0e35ef8b8eb5854307ff8))

- Ignore *.log instead of exact docker.log, add log task
  ([`2026d3b`](https://github.com/sandrosmarzaro/resenhazord2/commit/2026d3b7f4afa4d5dc8cedc21b025d83a9ac9e0f))

- Ignore docker.log in git
  ([`0d8e2bb`](https://github.com/sandrosmarzaro/resenhazord2/commit/0d8e2bb79884e9b68a4ad06badb1313833e27a62))

- Remove dead google_secrect.json.example and gitignore entry
  ([`ccd298f`](https://github.com/sandrosmarzaro/resenhazord2/commit/ccd298fbda9fdee60cfc6b3841109cc740df057d))

- **claude**: Disable unused MCPs and plugins project-scope
  ([`0df2093`](https://github.com/sandrosmarzaro/resenhazord2/commit/0df20934c3f2265f1aa83c21e16ece428586cc2f))

- **docs**: Remove temporary llm-agent-plan
  ([`6265d22`](https://github.com/sandrosmarzaro/resenhazord2/commit/6265d22b4e32c8c0af976c013b4883df08c84aec))

- **env**: Add Mistral and Groq API key placeholders
  ([`2373781`](https://github.com/sandrosmarzaro/resenhazord2/commit/2373781630125708671e631d129f4e4c7ade0a4c))

- **github**: Add default and release PR templates
  ([`8720b8e`](https://github.com/sandrosmarzaro/resenhazord2/commit/8720b8e8d40233f62e0efa530c55762ebc889789))

- **ruff**: Exempt register_commands lazy import from PLC0415
  ([`c753e29`](https://github.com/sandrosmarzaro/resenhazord2/commit/c753e295c897163edf8620ca528e3696f42ec214))

### Code Style

- **docker**: Merge consecutive RUN instructions
  ([`06c476a`](https://github.com/sandrosmarzaro/resenhazord2/commit/06c476a50e1ead110e9d0a2429f719aef6c45936))

- **gateway**: Add readonly modifiers to class properties
  ([`5b76292`](https://github.com/sandrosmarzaro/resenhazord2/commit/5b76292d1d04f2d77d91b5b22bc1017171cfef1b))

- **gateway**: Justify any cast on Baileys union fallback
  ([`ae0a3bf`](https://github.com/sandrosmarzaro/resenhazord2/commit/ae0a3bf4d959b967f4bb848e01a9f81cd6aefa70))

- **gateway**: Use nullish coalescing assignment and re-export syntax
  ([`ab60df6`](https://github.com/sandrosmarzaro/resenhazord2/commit/ab60df6e3db9cc83ed516afb8d877d5342eb3802))

- **handler**: Justify noqa C901 on handle dispatch
  ([`3e612b2`](https://github.com/sandrosmarzaro/resenhazord2/commit/3e612b26d1eb4774cdc0a85b5d4600076a977584))

- **shell**: Use double brackets in conditional tests
  ([`6e9e36c`](https://github.com/sandrosmarzaro/resenhazord2/commit/6e9e36c6600b8214d0eb6d9d47456c7d25d2c374))

- **tests**: Apply ruff format to llm test files
  ([`20f004f`](https://github.com/sandrosmarzaro/resenhazord2/commit/20f004f369fb464756fdaec09fcf33634cf1c68b))

### Continuous Integration

- Run check workflow on PRs targeting develop
  ([`cc939f7`](https://github.com/sandrosmarzaro/resenhazord2/commit/cc939f73f10db78c37edd52c3e84f7838d9db1c7))

- **sonar**: Add SonarCloud analysis to PR and push pipelines
  ([`f6c69f3`](https://github.com/sandrosmarzaro/resenhazord2/commit/f6c69f36a5891e2da739a4e797950ec69a9f054c))

### Documentation

- Add note about avoiding leading dashes in agent commands
  ([`9ca8d7a`](https://github.com/sandrosmarzaro/resenhazord2/commit/9ca8d7a1a9777fe3e83a5ebb0915280e6e1582a2))

- Update plan with CI fix and no leading dash rule
  ([`bc116cb`](https://github.com/sandrosmarzaro/resenhazord2/commit/bc116cb62af36da2ec3d908fe09c1666b7014a49))

- Update plan with completed items
  ([`cc33f9e`](https://github.com/sandrosmarzaro/resenhazord2/commit/cc33f9e169c7985f953931c3c2da55b168a3d9ad))

- **agent**: Clarify sticker type mappings
  ([`9fec49f`](https://github.com/sandrosmarzaro/resenhazord2/commit/9fec49f2b3b269a6e91a66319ac0550c174504d2))

- **architecture**: Describe telegram adapter
  ([`4a9fef5`](https://github.com/sandrosmarzaro/resenhazord2/commit/4a9fef55a89ebc2ded5a56f857fe599382c731c3))

- **architecture**: Rewrite python-first with project tree + discord
  ([`4da70b1`](https://github.com/sandrosmarzaro/resenhazord2/commit/4da70b19fc054fbe526014b6977595ccbe3536aa))

- **claude**: Add /check-py, /check-ts, /rules slash commands
  ([`eef49e7`](https://github.com/sandrosmarzaro/resenhazord2/commit/eef49e726be8f3354e060fab4dc70fae1df64308))

- **claude**: Add file-scoped rule files under .claude/rules/
  ([`e785b53`](https://github.com/sandrosmarzaro/resenhazord2/commit/e785b532f080b1e393ba73454cebadd8e9b49035))

- **claude**: Rewrite CLAUDE.md as index-first with code philosophy
  ([`7f78ab7`](https://github.com/sandrosmarzaro/resenhazord2/commit/7f78ab7f2df84edd5d45c1a40809b882a424c1d5))

- **git-flow**: Adopt two-branch flow with develop integration
  ([`79b7358`](https://github.com/sandrosmarzaro/resenhazord2/commit/79b73589920c725fdef4cc181a40b77d9fd432f1))

- **logging**: Rename sentry.md to logging.md and lead with Python
  ([`c1d2e2b`](https://github.com/sandrosmarzaro/resenhazord2/commit/c1d2e2b8a6945a0be11aa404d62131316012df0c))

### Features

- Add Discord agent mention and async audio rendering
  ([`c9339d8`](https://github.com/sandrosmarzaro/resenhazord2/commit/c9339d816127ce63f9863265c64731c64ce03e88))

- Add quoted message context to agent mode
  ([`5945af7`](https://github.com/sandrosmarzaro/resenhazord2/commit/5945af7e5f4dd9d062c4293f3212025b18a5789c))

- Add SUGGEST prefix for conversational fallback with command suggestion
  ([`5a15f2d`](https://github.com/sandrosmarzaro/resenhazord2/commit/5a15f2d2c0ec68cd851ddc7c3c82e09fd210c926))

- Add WhatsApp @mention support for agent
  ([`e676a17`](https://github.com/sandrosmarzaro/resenhazord2/commit/e676a17a3e73debb226ece19b4b8e151109d9a89))

- Enable agent mode in Telegram and Discord DMs
  ([`4aa5a5a`](https://github.com/sandrosmarzaro/resenhazord2/commit/4aa5a5a46aa769db6c37ade959205a63b6a2cf5c))

- **agent**: Add LLM agent for natural language command mapping
  ([`628e82a`](https://github.com/sandrosmarzaro/resenhazord2/commit/628e82a5a44f97f9d3d06c7785681c96a5c6b678))

- **discord**: Add agent mention handler with command execution
  ([`1fbbd7c`](https://github.com/sandrosmarzaro/resenhazord2/commit/1fbbd7cbe220213d5cc8dda13959b4ee02fecb9e))

- **domain**: Add Platform.ALL to avoid repeating the platform list
  ([`18a0771`](https://github.com/sandrosmarzaro/resenhazord2/commit/18a0771b55c5021c6e06a273fd891838d6b0a3fa))

- **telegram**: Acknowledge commands with thumbs-up reaction
  ([`462dc56`](https://github.com/sandrosmarzaro/resenhazord2/commit/462dc56b39369afa6e87b8d00fce1e2dda796906))

- **telegram**: Add agent mention handler for @bot_username mentions
  ([`50a8701`](https://github.com/sandrosmarzaro/resenhazord2/commit/50a87016061731910c876c0610c6c280b3010440))

- **telegram**: Add platform enum, settings, dependency
  ([`fd42635`](https://github.com/sandrosmarzaro/resenhazord2/commit/fd42635046232c0b61d28d4134d9e6e75b91e6af))

- **telegram**: Add TelegramBot lifecycle
  ([`b9c1667`](https://github.com/sandrosmarzaro/resenhazord2/commit/b9c1667469f679a5a1596e4d588605c1c766f429))

- **telegram**: Add TelegramBotAdapter
  ([`820ec21`](https://github.com/sandrosmarzaro/resenhazord2/commit/820ec21f2cc037028716457ee3c890d02a8426db))

- **telegram**: Add TelegramPort protocol and TelegramOutbound
  ([`6b37cf1`](https://github.com/sandrosmarzaro/resenhazord2/commit/6b37cf11fe5cd157768abee9f30c7789018681c3))

- **telegram**: Add update handler and skeleton renderer
  ([`fc0f787`](https://github.com/sandrosmarzaro/resenhazord2/commit/fc0f787e0191f563b64d50dd97adb1a5350d0ca9))

- **telegram**: Alias /start to the menu command
  ([`230a31b`](https://github.com/sandrosmarzaro/resenhazord2/commit/230a31b5b2b1d8a0dc1836f3c8d380ac14752508))

- **telegram**: Enable platform on remaining discord commands
  ([`52e8788`](https://github.com/sandrosmarzaro/resenhazord2/commit/52e8788a6a5bf605bc4d6cda1cad532a54baaee8))

- **telegram**: Keep typing indicator alive during long commands
  ([`affccd4`](https://github.com/sandrosmarzaro/resenhazord2/commit/affccd4372f2691b88a9b59340fb1c9ee3eabbcf))

- **telegram**: Opt /oi, /d20, /menu into Platform.TELEGRAM
  ([`97a6288`](https://github.com/sandrosmarzaro/resenhazord2/commit/97a62883ec73f67332cafa9a92763be82bf96ec8))

- **telegram**: Opt media pilot commands into platform
  ([`62b8bb6`](https://github.com/sandrosmarzaro/resenhazord2/commit/62b8bb68515d23a78969799d672c206882c07fd2))

- **telegram**: Publish command aliases in setMyCommands
  ([`14da217`](https://github.com/sandrosmarzaro/resenhazord2/commit/14da217a6d550d4017367490010aa255287fa2c4))

- **telegram**: Publish NSFW commands per configured chat scope
  ([`14163c0`](https://github.com/sandrosmarzaro/resenhazord2/commit/14163c01a8ee825efa296e8be43ce63dbfe39e47))

- **telegram**: Render dash list items as bullet dots
  ([`87ba3b4`](https://github.com/sandrosmarzaro/resenhazord2/commit/87ba3b46c5b57ebd9c82bd90884112f8557d269c))

- **telegram**: Render media content types and wire preprocess
  ([`d429659`](https://github.com/sandrosmarzaro/resenhazord2/commit/d429659f3486d55757605439861cc4d770bee4c7))

- **telegram**: Start and stop TelegramBot in the FastAPI lifespan
  ([`d3d125e`](https://github.com/sandrosmarzaro/resenhazord2/commit/d3d125e8f283e5b21522914052de3e8634d59c6a))

- **telegram**: Translate whatsapp markdown to html parse_mode
  ([`b68f373`](https://github.com/sandrosmarzaro/resenhazord2/commit/b68f373d3419271d4209da12563413cb872b22b7))

- **whatsapp**: Add agent mention handler for natural language commands
  ([`828e63f`](https://github.com/sandrosmarzaro/resenhazord2/commit/828e63fc8fa7f9c97ff6d38251acd9350ddc75b9))

### Performance Improvements

- **handler**: Cache bot numeric ids on init
  ([`e42c4ad`](https://github.com/sandrosmarzaro/resenhazord2/commit/e42c4ad2f496018e1994686d27bb3423102f27d9))

- **registry**: Index commands by name and aliases
  ([`188ede1`](https://github.com/sandrosmarzaro/resenhazord2/commit/188ede1d34e0c1a10bc4b80f67f54e293cb09d69))

- **telegram**: Parallelize message preprocess downloads
  ([`b83ff89`](https://github.com/sandrosmarzaro/resenhazord2/commit/b83ff89e1519eea6c554a1fb0c365388ff48608c))

### Refactoring

- Extract magic number to named constant
  ([`c58a514`](https://github.com/sandrosmarzaro/resenhazord2/commit/c58a514ff86712fa079f47d44a8702143c4721e2))

- Improve command handler cohesion
  ([`55e955d`](https://github.com/sandrosmarzaro/resenhazord2/commit/55e955d1aa2796bdf631d223075ae8928631b764))

- **agent**: Extract response translator from executor
  ([`1e4fa9d`](https://github.com/sandrosmarzaro/resenhazord2/commit/1e4fa9d28bb1e7f28d228f4104ce5b01e95ab8a4))

- **application**: Extract shared message preprocess module
  ([`1e3c6b6`](https://github.com/sandrosmarzaro/resenhazord2/commit/1e3c6b63a74fe34144462bfaf436f3b63e9f6cfe))

- **caption**: Extract nested ternary into if/elif/else
  ([`5933710`](https://github.com/sandrosmarzaro/resenhazord2/commit/5933710ca90dc11ce468381c729522e8685e8228))

- **commands**: Reduce cognitive complexity in football_player and movie_series
  ([`9ded065`](https://github.com/sandrosmarzaro/resenhazord2/commit/9ded0652cc1ca5448b8527fc4fab01e9bcfab1aa))

- **data**: Extract duplicated string literals into constants
  ([`46c708c`](https://github.com/sandrosmarzaro/resenhazord2/commit/46c708c8b9f2462fb4f3f921a5cf97253c05e586))

- **discord**: Split bot, slash registrar, and agent router
  ([`864d792`](https://github.com/sandrosmarzaro/resenhazord2/commit/864d792cc46b03ee72bed799e60449aaa22f1937))

- **gateway**: Move handler constants into the class
  ([`ad2c109`](https://github.com/sandrosmarzaro/resenhazord2/commit/ad2c109bea80104e4aab94247dee3ef1c0be26b1))

- **gateway**: Reduce cognitive complexity in CommandParser
  ([`27a6746`](https://github.com/sandrosmarzaro/resenhazord2/commit/27a6746617f56f0b86ba132b29953f40e53f7e1d))

- **gateway**: Reduce cognitive complexity in MediaHandler
  ([`7302bae`](https://github.com/sandrosmarzaro/resenhazord2/commit/7302bae254af3bb1c1c771562020735bee5c8b5a))

- **gateway**: Replace any cast with narrow shape interface
  ([`6cb89b6`](https://github.com/sandrosmarzaro/resenhazord2/commit/6cb89b6e30604141e1763ca9867aad43bbb76574))

- **gateway**: Split CommandHandler into mention + forwarder
  ([`ce34b03`](https://github.com/sandrosmarzaro/resenhazord2/commit/ce34b03dda7a4f0b68872173b919822092831c02))

- **handler**: Split handle and drop noqa C901
  ([`2e910cd`](https://github.com/sandrosmarzaro/resenhazord2/commit/2e910cd6e8893004b8fc3dd01812558c9f03d385))

- **llm**: Extract complete() into LLMProvider base
  ([`a966140`](https://github.com/sandrosmarzaro/resenhazord2/commit/a966140c197ef54c12a751a20cdbd06597557fba))

- **llm**: Rename cfg to config in build_tools_for_prompt
  ([`47ba961`](https://github.com/sandrosmarzaro/resenhazord2/commit/47ba961d9492f6b8e4e62192b68d8630dd31c650))

- **llm**: Split providers module into per-class files
  ([`940ec03`](https://github.com/sandrosmarzaro/resenhazord2/commit/940ec037fd369f90404f10c7efc8d518a87fa96f))

- **llm**: Use unicodedata + regex for ascii name normalisation
  ([`f5655af`](https://github.com/sandrosmarzaro/resenhazord2/commit/f5655afd4ecab044ff504bfff3e85540d1ee16e5))

- **parser**: Extract regex builder from CommandParser
  ([`61e08df`](https://github.com/sandrosmarzaro/resenhazord2/commit/61e08df44ded30805dd4698acf7aee78e3f8d88e))

- **parser**: Flatten nested loops via small helper methods
  ([`3e34681`](https://github.com/sandrosmarzaro/resenhazord2/commit/3e3468164c0b2c03454b4256fd6071b23da82122))

- **provider-chain**: Convert module singleton to class singleton
  ([`9887985`](https://github.com/sandrosmarzaro/resenhazord2/commit/988798599cd00fcae2a8006935d08f9e598bf568))

- **provider-chain**: Use time.monotonic for cooldown clock
  ([`c55022a`](https://github.com/sandrosmarzaro/resenhazord2/commit/c55022a5c8bce1fe6f38c7aed95c058d093f6986))

- **python**: Extract nested conditional and replace single-task TaskGroup
  ([`adaf58e`](https://github.com/sandrosmarzaro/resenhazord2/commit/adaf58e1b1d166730b3da792ae8ea18f35e60cdd))

- **register**: Hoist provider chain import to module top
  ([`b848e39`](https://github.com/sandrosmarzaro/resenhazord2/commit/b848e396901e4a5baeeb4cebfb9c8a0aeca93b85))

- **telegram**: Dedupe registry-patching boilerplate in test_bot
  ([`6299038`](https://github.com/sandrosmarzaro/resenhazord2/commit/629903895643cbfb00526c5c5e972f8427cd7c0c))

- **telegram**: Drop redundant formatter tests in test_renderer
  ([`fd53177`](https://github.com/sandrosmarzaro/resenhazord2/commit/fd531779e89fc019bc711155511199f3d499a567))

- **telegram**: Hoist bare module constants into classes
  ([`d8857c5`](https://github.com/sandrosmarzaro/resenhazord2/commit/d8857c5117786976decc50024be98a9955fbf75f))

- **telegram**: Split handler and agent router
  ([`3fe8f7d`](https://github.com/sandrosmarzaro/resenhazord2/commit/3fe8f7dcfedc9388369243517d10474d505a971d))

- **telegram**: Split handler and agent router
  ([`c0da896`](https://github.com/sandrosmarzaro/resenhazord2/commit/c0da896903209f995f3a3adf2e4f35c0a525c861))

- **telegram**: Wrap formatter in a class
  ([`38a82b9`](https://github.com/sandrosmarzaro/resenhazord2/commit/38a82b9721fd6b56233439feba0a5dbb875c5a55))

- **tests**: Split agent executor and translator suites
  ([`bf300fb`](https://github.com/sandrosmarzaro/resenhazord2/commit/bf300fbe03cc07f427bba71b1d921aaaa323519a))

- **tests**: Split discord slash-register suite by concern
  ([`f3a39b9`](https://github.com/sandrosmarzaro/resenhazord2/commit/f3a39b9dae9466a74b1beaff015bf30a12ae66ee))

- **tests**: Split discord test_bot into focused suites
  ([`28af581`](https://github.com/sandrosmarzaro/resenhazord2/commit/28af58131589ce0ad4e5c74e4705df7c6b73a2b1))

- **tests**: Split telegram renderer and dedupe FakeCommand
  ([`34c8b10`](https://github.com/sandrosmarzaro/resenhazord2/commit/34c8b10a5d186086b890a039ea796f6ab5e0cb0a))

- **transfermarkt**: Reduce cognitive complexity across parsers
  ([`dfccac8`](https://github.com/sandrosmarzaro/resenhazord2/commit/dfccac873a2e9d86b1495e7581fdd05f57043fca))

### Testing

- Add agent detection tests for DM and 'mande um' pattern
  ([`5052d15`](https://github.com/sandrosmarzaro/resenhazord2/commit/5052d15110bb728783080d01ce5857e5ca2740e5))

- Add regression tests for agent and Discord fixes
  ([`699dfc9`](https://github.com/sandrosmarzaro/resenhazord2/commit/699dfc9bfee6ffbb6b65823855e9e2e3be7e6636))

- Add regression tests for duplicate command registration
  ([`31730bb`](https://github.com/sandrosmarzaro/resenhazord2/commit/31730bb61c5bee257e9c1321d648c7ac086f0d57))

- Add regression tests for SUGGEST and CLARIFY agent prefixes
  ([`5d10dba`](https://github.com/sandrosmarzaro/resenhazord2/commit/5d10dbad0b9bf1e767e283180874334978cb6048))

- **agent**: Add unit tests for LLM agent components
  ([`b4ed524`](https://github.com/sandrosmarzaro/resenhazord2/commit/b4ed52402c17eb9668c3a40ee39eb2ab33243b85))

- **agent-response**: Cover json decode error, non-string values, quote stripping, command name
  resolution
  ([`b073eee`](https://github.com/sandrosmarzaro/resenhazord2/commit/b073eee80969c5e4a784ceb1bd5dd191bea5d8d9))

- **command-handler**: Cover agent mention by JID/tag, run_agent fallbacks, command exceptions
  ([`a0b7f84`](https://github.com/sandrosmarzaro/resenhazord2/commit/a0b7f84ff5d9465ea6daed34646c1a0cc9241212))

- **commands**: Parametrize duplicated platform-support assertions
  ([`490ad29`](https://github.com/sandrosmarzaro/resenhazord2/commit/490ad295facd34fa0a063c532715c8421b326e9c))

- **discord**: Cover agent router mention, dispatch exception, send reply, group data
  ([`b473362`](https://github.com/sandrosmarzaro/resenhazord2/commit/b4733628c064dfacdbc77569faf29e28b2ed2aa5))

- **discord**: Cover async audio download, render_many_async, raw empty caption
  ([`8d65746`](https://github.com/sandrosmarzaro/resenhazord2/commit/8d65746b20c4be710f30aeb9dafc1035d51923b0))

- **discord**: Cover slash register callback, duplicate command, configure options
  ([`db1e06e`](https://github.com/sandrosmarzaro/resenhazord2/commit/db1e06ec20819e633fa9b4bf2438a43fc686b531))

- **discord**: Narrow guild type in dm test factory
  ([`2e633fc`](https://github.com/sandrosmarzaro/resenhazord2/commit/2e633fcf4884dd7c5e0eaa20b6d5ac1aca277a5e))

- **gateway**: Add ts-expect-error for readonly override in test
  ([`85a4b67`](https://github.com/sandrosmarzaro/resenhazord2/commit/85a4b67cbfecde4c6c9c4a219a7a352268ea4422))

- **llm**: Assert post payload and post-cooldown skip
  ([`5c5d5e0`](https://github.com/sandrosmarzaro/resenhazord2/commit/5c5d5e071d399f7a05039b9e7f740f5bd89168fa))

- **llm**: Cover provider chain configure, missing keys, first-provider success, non-429 HTTP
  ([`b90f86b`](https://github.com/sandrosmarzaro/resenhazord2/commit/b90f86bcee6a4708a0fb873c6f196278f22dbaba))

- **llm**: Cover scope filter in build_tools_for_prompt
  ([`55f493f`](https://github.com/sandrosmarzaro/resenhazord2/commit/55f493f00f2cdf2d61a4fa2eb09b8006c11e52f8))

- **parser**: Cover duplicate option and flag skip in command parser
  ([`945508b`](https://github.com/sandrosmarzaro/resenhazord2/commit/945508bc306045b114d335322332a04cea6340ff))

- **preprocess**: Consolidate anyio_backend asyncio pins
  ([`caf5fe4`](https://github.com/sandrosmarzaro/resenhazord2/commit/caf5fe4ea15173fa0caa36640f7c41229fa00796))

- **sticker**: Add coverage for quality without percent
  ([`23a3c08`](https://github.com/sandrosmarzaro/resenhazord2/commit/23a3c0840904beabe66fc7c51bc2ad7bfd69110f))

- **telegram**: Cast mocked set_my_commands for pyright
  ([`6685d15`](https://github.com/sandrosmarzaro/resenhazord2/commit/6685d153f7bf5ab49992b829506676b33090417e))

- **telegram**: Cover adapter, bot, handler, and renderer
  ([`6cad693`](https://github.com/sandrosmarzaro/resenhazord2/commit/6cad69389f37ffe32055b5f2b8abcff986ed050d))

- **telegram**: Cover agent router mention detection, safe react, run and reply, send messages
  ([`68b3148`](https://github.com/sandrosmarzaro/resenhazord2/commit/68b31485100bc2e9607e32cb8e28ff34a8731252))

- **telegram**: Cover bot lifecycle, handler registration, and callback
  ([`2137a16`](https://github.com/sandrosmarzaro/resenhazord2/commit/2137a16f0cf9a5e4aced9227320a44242f726966))

- **telegram**: Satisfy basedpyright and ruff format
  ([`4840ddf`](https://github.com/sandrosmarzaro/resenhazord2/commit/4840ddf8dbdfe186547eb7cfb153224f5842aa7c))

- **telegram**: Tighten bare assert_called_once arg checks
  ([`319bef7`](https://github.com/sandrosmarzaro/resenhazord2/commit/319bef7753b157371b0fa3b7a4c65c85b757681a))


## v1.4.1 (2026-04-18)

### Bug Fixes

- **sticker**: Keep all frames unless size exceeds sticker limit
  ([`08eeafe`](https://github.com/sandrosmarzaro/resenhazord2/commit/08eeafea4e61074e350b69de695652c8a8a282ad))

- **sticker**: Parse per-frame durations from ANMF chunks
  ([`51c1515`](https://github.com/sandrosmarzaro/resenhazord2/commit/51c1515f30b82c98ed6bad09f4b79b31ffc81b7d))

- **sticker**: Preserve animation when input is animated webp
  ([`92b30f5`](https://github.com/sandrosmarzaro/resenhazord2/commit/92b30f5f144f860d7e4432314fde0ea9ec7513f4))


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
