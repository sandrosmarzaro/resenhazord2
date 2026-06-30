"""Fail if uv.lock pins a non-allowlisted package published less than the cooldown
window ago.

Supply-chain mitigation: a freshly published (and possibly compromised) release
should sit public for a review window before we depend on it. The gateway enforces
this natively through bun's `minimumReleaseAge` (gateway/bunfig.toml). uv has no
baked-in setting compatible with this project's intentionally-fresh LLM stack, so
this auditor gates the committed lockfile instead — it checks release ages without
re-resolving, sidestepping the LangChain version cascade. See docs/security.md.
"""

import concurrent.futures
import datetime
import json
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

COOLDOWN_DAYS = 7
PYPI_TIMEOUT_SECONDS = 15
MAX_WORKERS = 16

# Intentionally tracked at the latest release: the agentic LangChain/LangGraph
# stack ships weekly and the project floors it deliberately, so it bypasses the
# cooldown. Keep this list tight — every entry is an accepted supply-chain risk.
ALLOWLISTED_PREFIXES = ('langchain', 'langgraph', 'langsmith')


def _is_allowlisted(name: str) -> bool:
    return name.startswith(ALLOWLISTED_PREFIXES)


def _locked_packages(lock_path: str) -> list[tuple[str, str]]:
    with Path(lock_path).open('rb') as lock_file:
        lock = tomllib.load(lock_file)
    return [
        (package['name'], package['version'])
        for package in lock.get('package', [])
        if 'version' in package and package.get('source', {}).get('registry')
    ]


def _age_in_days(package: tuple[str, str]) -> tuple[str, str, int] | None:
    name, version = package
    url = f'https://pypi.org/pypi/{name}/{version}/json'
    try:
        with urllib.request.urlopen(url, timeout=PYPI_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.URLError, TimeoutError, json.JSONDecodeError:
        return None
    files: list[dict[str, str]] = payload.get('urls') or []
    if not files:
        return None
    uploaded = min(file['upload_time_iso_8601'] for file in files)
    uploaded_date = datetime.datetime.fromisoformat(uploaded).date()
    today = datetime.datetime.now(tz=datetime.UTC).date()
    return name, version, (today - uploaded_date).days


def main() -> int:
    candidates = [pkg for pkg in _locked_packages('uv.lock') if not _is_allowlisted(pkg[0])]

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        ages = list(pool.map(_age_in_days, candidates))
    violations = [age for age in ages if age and age[2] < COOLDOWN_DAYS]

    if not violations:
        print(f'cooldown ok: no non-allowlisted package younger than {COOLDOWN_DAYS} days')
        return 0

    print(f'cooldown violated: packages published less than {COOLDOWN_DAYS} days ago')
    for name, version, age in sorted(violations):
        print(f'  {name}=={version} (published {age} day(s) ago)')
    print('Wait out the cooldown, or add the package to ALLOWLISTED_PREFIXES if it is')
    print('an intentionally tracked dependency. See docs/security.md.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
