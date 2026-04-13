Run GitHub Actions CI checks locally using `act`.

Run the Check workflow (lint + tests) simulating a pull_request event:

```
act pull_request -W .github/workflows/check.yml
```

If it fails, show the relevant error output and suggest fixes.

Optional: pass `$ARGUMENTS` to run specific jobs (e.g. `lint-py`, `lint-ts`, `test-py`, `test-ts`):

```
act pull_request -W .github/workflows/check.yml -j <job_name>
```
