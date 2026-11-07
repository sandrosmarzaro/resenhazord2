import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ('module', 'dependency'),
    [
        ('bot.domain.commands.lottery', 'bs4'),
        ('bot.domain.commands.porno', 'bs4'),
        ('bot.domain.services.rule34_images', 'bs4'),
        ('bot.domain.services.full_lineup_builder', 'statistics'),
        ('bot.domain.services.team_name_matcher', 'difflib'),
        ('bot.infrastructure.http_client', 'httpx_retries'),
    ],
)
def test_importing_a_module_defers_its_heavy_dependency(module, dependency):
    probe = f'import sys, {module}; sys.exit({dependency!r} in sys.modules)'

    result = subprocess.run([sys.executable, '-c', probe], check=False)

    assert result.returncode == 0
