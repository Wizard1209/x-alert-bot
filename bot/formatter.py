"""Format Tweet objects into Telegram messages using aiogram formatting."""

from dataclasses import dataclass, field

from aiogram.utils.formatting import (
    Bold,
    Text,
    TextLink,
    as_list,
    as_line,
)

from bot.twitter import Tweet, TweetType


@dataclass
class TelegramAlert:
    """Ready-to-send Telegram message with optional photo preview."""

    text: Text
    photo_url: str | None = None
    extra_photos: list[str] = field(default_factory=list)
    silent: bool = False


_TYPE_LABELS = {
    TweetType.RETWEET: '🔁 Retweet',
    TweetType.REPLY: '💬 Reply',
    TweetType.QUOTE: '💬 Quote',
}


def format_tweet(tweet: Tweet) -> TelegramAlert:
    """Format a single Tweet into a Telegram-ready alert."""
    # Type badge for non-original tweets
    type_label = _TYPE_LABELS.get(tweet.tweet_type)

    # Author line: **@username** (Name)
    author = as_line(
        Bold(f'@{tweet.author_username}'),
        f' ({tweet.author_name})',
    )

    parts: list = []
    if type_label:
        parts.append(Bold(type_label))
    parts.append(author)
    parts.append(Text(tweet.text))
    parts.append('')
    parts.append(TextLink('Open on X', url=tweet.url))
    if tweet.tweet_type == TweetType.ORIGINAL:
        parts.append('❤️ like · 🔁 share · 💬 comment')

    text = as_list(*parts, sep='\n')

    # First media URL becomes the photo preview, rest are extras
    photo_url = tweet.media_urls[0] if tweet.media_urls else None
    extra_photos = (
        tweet.media_urls[1:] if len(tweet.media_urls) > 1 else []
    )

    # Retweets and replies are sent silently
    silent = tweet.tweet_type in (
        TweetType.RETWEET,
        TweetType.REPLY,
        TweetType.QUOTE,
    )

    return TelegramAlert(
        text=text,
        photo_url=photo_url,
        extra_photos=extra_photos,
        silent=silent,
    )


def format_tweet_batch(tweets: list[Tweet]) -> list[TelegramAlert]:
    """Format multiple tweets into individual alerts."""
    return [format_tweet(t) for t in tweets]


