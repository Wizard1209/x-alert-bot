"""X/Twitter API client using search/recent endpoint."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

from bot.config import CONFIG

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.x.com/2'


class TweetType:
    ORIGINAL = 'original'
    RETWEET = 'retweet'
    REPLY = 'reply'
    QUOTE = 'quote'


@dataclass
class Tweet:
    id: str
    text: str
    created_at: datetime
    url: str
    tweet_type: str = TweetType.ORIGINAL
    # Author info (from expansions)
    author_username: str = ''
    author_name: str = ''
    author_followers: int = 0
    author_verified: bool = False
    # Media (photos/video thumbnails)
    media_urls: list[str] = field(default_factory=list)


def build_query(
    usernames: list[str],
    *,
    tweets_only: bool = False,
) -> str:
    """Build search query: (from:user1 OR from:user2).

    When tweets_only=True, appends -is:retweet -is:reply to exclude
    replies and retweets at the API level (quotes still pass through).
    """
    parts = [f'from:{u}' for u in usernames]
    q = f'({" OR ".join(parts)})'
    if tweets_only:
        q += ' -is:retweet -is:reply'
    return q


@dataclass
class TwitterClient:
    bearer_token: str
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={'Authorization': f'Bearer {self.bearer_token}'},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def poll(
        self,
        since_id: str | None = None,
        last_polled: datetime | None = None,
    ) -> tuple[list[Tweet], str | None]:
        """Poll search/recent for all watched users.

        Returns (tweets, new_cursor) where new_cursor is the
        highest tweet ID in the batch (or None if no tweets).
        """
        query = build_query(
            CONFIG.watch_users, tweets_only=CONFIG.tweets_only
        )

        params: dict[str, str | int] = {
            'query': query,
            'max_results': 100,
            'sort_order': 'recency',
            'tweet.fields': 'created_at,text,entities,referenced_tweets',
            'expansions': 'author_id,attachments.media_keys',
            'user.fields': (
                'username,name,public_metrics,'
                'verified,verified_type'
            ),
            'media.fields': 'preview_image_url,url,type',
        }

        start_dt: datetime | None = None  # for client-side filtering

        if since_id:
            params['since_id'] = since_id
        else:
            # Use last poll time, or fall back to poll_interval ago
            start_dt = last_polled or (
                datetime.now(timezone.utc)
                - timedelta(minutes=CONFIG.poll_interval)
            )
            params['start_time'] = start_dt.strftime(
                '%Y-%m-%dT%H:%M:%SZ'
            )

        resp = await self._client.get(
            '/tweets/search/recent', params=params
        )
        resp.raise_for_status()
        data = resp.json()

        # Log X API soft errors (e.g. partial failures)
        if api_errors := data.get('errors'):
            logger.warning('X API soft errors: %s', api_errors)

        tweets_raw = data.get('data', [])
        if not tweets_raw:
            logger.info('Poll: 0 tweets returned')
            return [], since_id

        # Filter out the since_id tweet itself (X API edge case)
        if since_id:
            tweets_raw = [t for t in tweets_raw if t['id'] != since_id]
            if not tweets_raw:
                logger.info('Poll: 0 tweets after dedup')
                return [], since_id

        # Client-side time filter: X API occasionally ignores
        # start_time and returns older tweets (observed in prod).
        if start_dt and tweets_raw:
            before = len(tweets_raw)
            tweets_raw = [
                t for t in tweets_raw
                if datetime.fromisoformat(
                    t['created_at'].replace('Z', '+00:00')
                ) >= start_dt
            ]
            if len(tweets_raw) < before:
                logger.warning(
                    'Dropped %d tweets older than start_time %s',
                    before - len(tweets_raw),
                    start_dt.isoformat(),
                )
            if not tweets_raw:
                return [], None

        # Build author lookup from includes
        includes = data.get('includes', {})
        authors: dict[str, dict] = {}
        for user in includes.get('users', []):
            authors[user['id']] = user

        # Build media lookup: media_key -> image URL
        media_map: dict[str, str] = {}
        for media in includes.get('media', []):
            key = media.get('media_key')
            if not key:
                continue
            # Photos have 'url', videos/GIFs have 'preview_image_url'
            url = (
                media.get('url')
                if media.get('type') == 'photo'
                else media.get('preview_image_url')
            )
            if url:
                media_map[key] = url

        tweets: list[Tweet] = []
        for t in tweets_raw:
            tid = t['id']
            author = authors.get(t.get('author_id', ''), {})
            username = author.get('username', '')

            # Determine tweet type from referenced_tweets
            tweet_type = TweetType.ORIGINAL
            refs = t.get('referenced_tweets', [])
            for ref in refs:
                rt = ref.get('type', '')
                if rt == 'retweeted':
                    tweet_type = TweetType.RETWEET
                    break
                elif rt == 'replied_to':
                    tweet_type = TweetType.REPLY
                elif rt == 'quoted':
                    tweet_type = TweetType.QUOTE

            # Resolve media URLs for this tweet
            tweet_media: list[str] = []
            media_keys = t.get('attachments', {}).get(
                'media_keys', []
            )
            for mk in media_keys:
                if img_url := media_map.get(mk):
                    tweet_media.append(img_url)

            # Strip trailing t.co media links from text
            tweet_text = t['text']
            if media_keys:
                for u in reversed(
                    t.get('entities', {}).get('urls', [])
                ):
                    expanded = u.get('expanded_url', '')
                    if 'photo' in expanded or 'video' in expanded:
                        tweet_text = (
                            tweet_text[: u['start']]
                            + tweet_text[u['end'] :]
                        ).rstrip()

            tweets.append(
                Tweet(
                    id=tid,
                    text=tweet_text,
                    tweet_type=tweet_type,
                    created_at=datetime.fromisoformat(
                        t['created_at'].replace('Z', '+00:00')
                    ),
                    url=f'https://x.com/{username}/status/{tid}',
                    author_username=username,
                    author_name=author.get('name', ''),
                    author_followers=author.get(
                        'public_metrics', {}
                    ).get('followers_count', 0),
                    author_verified=(
                        author.get('verified', False)
                        or author.get('verified_type', '') != ''
                    ),
                    media_urls=tweet_media,
                )
            )

        # New cursor = highest tweet ID (tweets sorted by recency,
        # so first item has the highest ID)
        new_cursor = max(t.id for t in tweets)
        logger.info('Poll: %d tweets, cursor → %s', len(tweets), new_cursor)
        return tweets, new_cursor
