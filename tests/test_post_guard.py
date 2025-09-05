import tempfile
import shutil
import time
import json
from pathlib import Path

import os

from skoolhud.ai import tools


def test_post_guard_mark_and_allowed(tmp_path, monkeypatch):
    # point STATUS_DIR to a temp dir
    td = tmp_path / "status"
    monkeypatch.setattr(tools, 'STATUS_DIR', td)

    from skoolhud.config import get_tenant_slug
    slug = get_tenant_slug(None)
    name = 'testguard'
    # initially allowed
    assert tools.post_guard_allowed(slug, name, cooldown_env_var=None, default=1)

    # mark now
    tools.post_guard_mark(slug, name)
    guard = td / f"{name}_last_post_{slug}.json"
    assert guard.exists()
    data = json.loads(guard.read_text(encoding='utf-8'))
    assert 'last_post' in data

    # immediately after marking, not allowed if cooldown is large
    assert not tools.post_guard_allowed(slug, name, cooldown_env_var=None, default=3600)

    # after sleep beyond small cooldown it becomes allowed
    time.sleep(1)
    assert tools.post_guard_allowed(slug, name, cooldown_env_var=None, default=0)
