"""Tests for bot.formatter — format_tweet() and format_tweet_batch()."""

from datetime import datetime, timezone

from bot.formatter import format_tweet, format_tweet_batch
from bot.twitter import Tweet, TweetType


def _make_tweet(**overrides) -> Tweet:
    defaults = {
        'id': '100',
        'text': 'Hello world',
        'created_at': datetime(2026, 3, 3, tzinfo=timezone.utc),
        'url': 'https://x.com/alice/status/100',
        'tweet_type': TweetType.ORIGINAL,
        'author_username': 'alice',
        'author_name': 'Alice Dev',
    }
    defaults.update(overrides)
    return Tweet(**defaults)


def test_format_original():
    alert = format_tweet(_make_tweet())

    assert alert.silent is False
    # Text should render without raising
    rendered = alert.text.as_kwargs()
    assert 'text' in rendered


def test_format_retweet():
    alert = format_tweet(
        _make_tweet(tweet_type=TweetType.RETWEET)
    )

    assert alert.silent is True


def test_format_reply():
    alert = format_tweet(
        _make_tweet(tweet_type=TweetType.REPLY)
    )

    assert alert.silent is True


def test_format_with_photo():
    alert = format_tweet(
        _make_tweet(
            media_urls=['https://pbs.twimg.com/media/photo1.jpg']
        )
    )

    assert alert.photo_url == (
        'https://pbs.twimg.com/media/photo1.jpg'
    )
    assert alert.extra_photos == []


def test_format_multiple_photos():
    urls = [
        'https://pbs.twimg.com/media/a.jpg',
        'https://pbs.twimg.com/media/b.jpg',
        'https://pbs.twimg.com/media/c.jpg',
    ]
    alert = format_tweet(_make_tweet(media_urls=urls))

    assert alert.photo_url == urls[0]
    assert alert.extra_photos == urls[1:]


def test_format_batch():
    tweets = [_make_tweet(id=str(i)) for i in range(3)]
    alerts = format_tweet_batch(tweets)

    assert len(alerts) == 3
    assert all(a.text is not None for a in alerts)
