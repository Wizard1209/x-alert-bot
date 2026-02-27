"""Format Tweet objects into Telegram messages using aiogram formatting."""

from dataclasses import dataclass, field

from aiogram.utils.formatting import (
    Bold,
    Text,
    TextLink,
    as_list,
    as_line,
)

from bot.twitter import Tweet


@dataclass
class TelegramAlert:
    """Ready-to-send Telegram message with optional photo preview."""

    text: Text
    photo_url: str | None = None
    extra_photos: list[str] = field(default_factory=list)


def format_tweet(tweet: Tweet) -> TelegramAlert:
    """Format a single Tweet into a Telegram-ready alert."""
    # Author line: **@username** (Name)
    author = as_line(
        Bold(f'@{tweet.author_username}'),
        f' ({tweet.author_name})',
    )

    text = as_list(
        author,
        Text(tweet.text),
        '',
        TextLink('Open on X', url=tweet.url),
        'Распространите это среди жильцов нашего ЖЭКа.',
        sep='\n',
    )

    # First media URL becomes the photo preview, rest are extras
    photo_url = tweet.media_urls[0] if tweet.media_urls else None
    extra_photos = tweet.media_urls[1:] if len(tweet.media_urls) > 1 else []

    return TelegramAlert(
        text=text,
        photo_url=photo_url,
        extra_photos=extra_photos,
    )


def format_tweet_batch(tweets: list[Tweet]) -> list[TelegramAlert]:
    """Format multiple tweets into individual alerts."""
    return [format_tweet(t) for t in tweets]


