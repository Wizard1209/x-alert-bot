"""Tests for bot.storage — UserStorage and cursor persistence."""

import json
from datetime import datetime, timedelta, timezone


from bot.storage import load_cursor, save_cursor


def test_get_users_is_copy(tmp_storage):
    tmp_storage.add_user(123, 'alice', 'Alice')
    users = tmp_storage.get_users()
    users[999] = {'username': 'hacker'}
    assert 999 not in tmp_storage.get_users()


# ── Cursor with staleness ────────────────────────────────────────


def test_save_cursor_writes_timestamp(tmp_storage):
    """save_cursor persists since_id + saved_at timestamp."""
    save_cursor('123456')
    from bot.storage import CURSOR_FILE

    data = json.loads(CURSOR_FILE.read_text())
    assert data['since_id'] == '123456'
    assert 'saved_at' in data
    # saved_at should be a valid ISO timestamp
    datetime.fromisoformat(data['saved_at'])


def test_load_cursor_fresh(tmp_storage):
    """Fresh cursor (just saved) is loaded successfully."""
    save_cursor('100')
    result = load_cursor(max_age_minutes=30)
    assert result == '100'


def test_load_cursor_stale(tmp_storage):
    """Cursor older than max_age_minutes returns None."""
    save_cursor('100')

    # Fake the saved_at to 2 hours ago
    from bot.storage import CURSOR_FILE

    data = json.loads(CURSOR_FILE.read_text())
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    data['saved_at'] = old_time.isoformat()
    CURSOR_FILE.write_text(json.dumps(data))

    result = load_cursor(max_age_minutes=30)
    assert result is None


def test_load_cursor_exactly_at_boundary(tmp_storage):
    """Cursor exactly at max_age boundary is considered stale."""
    save_cursor('100')

    from bot.storage import CURSOR_FILE

    data = json.loads(CURSOR_FILE.read_text())
    boundary = datetime.now(timezone.utc) - timedelta(minutes=30, seconds=1)
    data['saved_at'] = boundary.isoformat()
    CURSOR_FILE.write_text(json.dumps(data))

    result = load_cursor(max_age_minutes=30)
    assert result is None


def test_load_cursor_just_under_boundary(tmp_storage):
    """Cursor slightly younger than max_age is loaded."""
    save_cursor('100')

    from bot.storage import CURSOR_FILE

    data = json.loads(CURSOR_FILE.read_text())
    recent = datetime.now(timezone.utc) - timedelta(minutes=29)
    data['saved_at'] = recent.isoformat()
    CURSOR_FILE.write_text(json.dumps(data))

    result = load_cursor(max_age_minutes=30)
    assert result == '100'


def test_load_cursor_no_file(tmp_storage):
    """No cursor file on disk returns None."""
    result = load_cursor(max_age_minutes=30)
    assert result is None


def test_load_cursor_missing_saved_at(tmp_storage):
    """Legacy cursor without saved_at returns None."""
    from bot.storage import CURSOR_FILE, DATA_DIR

    DATA_DIR.mkdir(exist_ok=True)
    CURSOR_FILE.write_text(json.dumps({'since_id': '100'}))

    result = load_cursor(max_age_minutes=30)
    assert result is None


def test_load_cursor_missing_since_id(tmp_storage):
    """Cursor file without since_id returns None."""
    from bot.storage import CURSOR_FILE, DATA_DIR

    DATA_DIR.mkdir(exist_ok=True)
    CURSOR_FILE.write_text(
        json.dumps({
            'saved_at': datetime.now(timezone.utc).isoformat(),
        })
    )

    result = load_cursor(max_age_minutes=30)
    assert result is None
