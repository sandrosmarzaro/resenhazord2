# Contributing to Resenhazord 2

Thanks for helping with the bot of A Resenha. Everyone who takes part follows the
[Code of Conduct](CODE_OF_CONDUCT.md), and security problems go through the private channel in
[SECURITY.md](SECURITY.md) instead of a public issue.

The coding standards live in [CLAUDE.md](CLAUDE.md) and [.claude/rules/](.claude/rules), and the
branching and release flow in [docs/git-flow.md](docs/git-flow.md). This guide covers the
day-to-day part. The [wiki](https://github.com/sandrosmarzaro/resenhazord2/wiki) explains how to
install and run the stack.

## Before you start

Open an issue before a large change or a new command, so the idea gets agreed on before anyone
writes code. Small fixes can go straight to a pull request. Questions and ideas that aren't a
concrete task fit better in [Discussions](https://github.com/sandrosmarzaro/resenhazord2/discussions).

Code, file names and comments are in English. The text the bot sends, command names and menu
descriptions stay in Brazilian Portuguese, since that is the product's voice.

## Create a branch

Branch from `develop`, which is the default branch, with a prefix that matches the type of change.

```bash
git switch develop && git pull
git switch -c feat/short-description
```

Urgent production fixes are the exception and branch from `main` as `hotfix/short-description`.

## Commit

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) with a required scope,
an imperative lowercase subject and no trailing period, for example
`fix(gateway): drop null send options before calling baileys`. Commitizen reads these subjects to
pick the next version, so the type matters.

| Type | Use it for |
|:----:|:-----------|
| feat | A new feature |
| fix | A bug fix |
| docs | Documentation only |
| style | Formatting with no change in meaning |
| refactor | A change that neither fixes a bug nor adds a feature |
| perf | A performance improvement |
| test | Adding or correcting tests |
| chore | Build, CI, dependencies and tooling |
| revert | Reverting an earlier commit |

Keep each commit to one logical change and stage files explicitly with `git add <file>`.

## Test

New behavior comes with tests written before or alongside the code. The core uses pytest with
anyio and the factories in `tests/factories/`, and the gateway uses Vitest with the fixtures in
`gateway/tests/fixtures/`. Every changed line needs a test, because CI requires 100% patch coverage
including both sides of each branch. The pre-push hook checks the same thing locally.

```bash
uv run pre-commit run --hook-stage pre-push --from-ref origin/develop --to-ref HEAD
```

## Open a pull request

Push the branch and open the pull request against `develop`, filling in the template. CI runs the
Python and gateway jobs only for the side your change touches. When a change depends on another
open pull request, branch from that branch and open yours with it as the base. GitHub moves it to
`develop` once the parent merges, as described under Stacked PRs in the git flow document.

A maintainer reviews the pull request and merges it once CI is green.

## AI-assisted contributions

AI tools are welcome here. Much of this project is written with Claude Code, and
[CLAUDE.md](CLAUDE.md) with [.claude/rules/](.claude/rules) is what coding agents read before they
touch the code. The rules below keep a person responsible for every contribution, whatever tool
helped make it.

You are the author of what you submit and you answer for all of it. Read and review every line a
tool generated before you ask for a review, run the tests, and be ready to explain the change and
answer questions about it in the pull request. If you can't explain a part, leave it out until you
can. Feeding review comments back into a model without understanding them wastes the reviewer's
time.

Say so when a tool wrote a substantial part of a contribution. In commits, add a trailer such as
`Assisted-by: <tool and model>`, or keep the `Co-Authored-By:` trailer your tool adds, as Claude
Code does. Mention it in the pull request description too. Disclosure exists to help the review,
so there is no need to label every generated line.

Some uses are not accepted:

- Agents that open issues, pull requests or comments in this repository without a person
  approving each action.
- Automated review comments that nobody read before they were posted.
- Unreviewed model output, whose review would cost more than it gives the project. A maintainer may
  close it with a pointer to this section.

You also need the right to contribute what you submit under the [MIT License](LICENSE). A tool
reproducing someone else's copyrighted code doesn't remove that copyright, so check that such code
doesn't end up in your contribution.

This section is adapted from the
[LLVM AI Tool Use Policy](https://llvm.org/docs/AIToolPolicy.html) and the
[Fedora AI-Assisted Contributions Policy](https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/).
