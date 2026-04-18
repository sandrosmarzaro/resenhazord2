# Release PR: `develop` → `main`

> **Merge strategy: "Create a merge commit". Do NOT squash.**
>
> Squashing collapses every Conventional Commit into a single subject and breaks semantic-release version inference.
> See [docs/git-flow.md](../../docs/git-flow.md#release-workflow-develop--main).

## Highlights

<!-- Group the accumulated changes by type -->

### ✨ Features (`feat`)

-

### 🐛 Fixes (`fix`)

-

### 💥 Breaking changes

-

### Other

- <!-- chore / docs / refactor / perf / test / ci -->

## Deploy impact

- [ ] New env vars / secrets required (list below, and add to `.env.example`)
- [ ] Schema / data migrations included
- [ ] Rollback plan if deploy fails

<!-- Details: -->

## Pre-merge checklist

- [ ] CI green on this PR
- [ ] `develop` has no conflicts with `main`
- [ ] Highlights list matches the commit range (`git log main..develop --oneline`)
- [ ] Merge button set to **"Create a merge commit"**
