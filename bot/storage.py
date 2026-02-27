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

    def get_users(self) -> dict[int, dict[str, Any]]:
        return self._users.copy()


def load_cursor() -> str | None:
    """Load the since_id cursor from disk."""
    if CURSOR_FILE.exists():
        data = json.loads(CURSOR_FILE.read_text())
        cursor = data.get('since_id')
        if cursor:
            logger.info('Loaded cursor: %s', cursor)
            return str(cursor)
    return None


def save_cursor(since_id: str) -> None:
    """Persist the since_id cursor to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    CURSOR_FILE.write_text(
        json.dumps({'since_id': since_id}, indent=2)
    )
    logger.debug('Saved cursor: %s', since_id)
