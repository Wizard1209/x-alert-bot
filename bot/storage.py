import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
USERS_FILE = DATA_DIR / 'users.json'
CURSOR_FILE = DATA_DIR / 'cursor.json'


class UserStorage:
    def __init__(self) -> None:
        self._users: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if USERS_FILE.exists():
            data = json.loads(USERS_FILE.read_text())
            self._users = {int(k): v for k, v in data.items()}
            logger.info('Loaded %d users from storage', len(self._users))

    def _save(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        USERS_FILE.write_text(json.dumps(self._users, indent=2))

    def add_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str,
    ) -> bool:
        """Save user. Returns True if new user, False if already existed."""
        is_new = user_id not in self._users
        self._users[user_id] = {
            'username': username,
            'first_name': first_name,
            'last_seen': datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        if is_new:
            logger.info('New user: %s (%d)', username or first_name, user_id)
        return is_new

    def remove_user(self, user_id: int) -> bool:
        """Remove user from storage. Returns True if user existed."""
        if user_id in self._users:
            del self._users[user_id]
            self._save()
            logger.info('Removed user %d from storage', user_id)
            return True
        return False

    def get_users(self) -> dict[int, dict[str, Any]]:
        return self._users.copy()


def load_cursor(max_age_minutes: int) -> str | None:
    """Load cursor from disk if it's fresher than max_age_minutes."""
    if not CURSOR_FILE.exists():
        return None
    data = json.loads(CURSOR_FILE.read_text())
    cursor = data.get('since_id')
    saved_at = data.get('saved_at')
    if not cursor or not saved_at:
        return None
    age = datetime.now(timezone.utc) - datetime.fromisoformat(saved_at)
    if age.total_seconds() > max_age_minutes * 60:
        logger.info(
            'Cursor %s is stale (%.0fm old), ignoring',
            cursor,
            age.total_seconds() / 60,
        )
        return None
    logger.info('Loaded cursor: %s (%.0fm old)', cursor, age.total_seconds() / 60)
    return str(cursor)


def save_cursor(since_id: str) -> None:
    """Persist cursor with timestamp."""
    DATA_DIR.mkdir(exist_ok=True)
    CURSOR_FILE.write_text(
        json.dumps(
            {
                'since_id': since_id,
                'saved_at': datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    logger.debug('Saved cursor: %s', since_id)
