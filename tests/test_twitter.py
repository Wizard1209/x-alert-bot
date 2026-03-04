"""Tests for bot.twitter — TwitterClient.poll() and build_query()."""

import logging

import pytest

from bot.twitter import TweetType, build_query

from tests.fixtures.x_api_responses import (
    SEARCH_EMPTY,
    SEARCH_MULTI,
    SEARCH_MULTI_MEDIA,
    SEARCH_ORIGINAL,
    SEARCH_REPLY,
    SEARCH_RETWEET,
    SEARCH_SINCE_ID_DUPE,
    SEARCH_SINCE_ID_DUPE_WITH_NEW,
    SEARCH_WITH_ERRORS,
)


def test_build_query_single():
    assert build_query(['alice']) == '(from:alice)'


def test_build_query_multi():
    result = build_query(['alice', 'bob', 'charlie'])
    assert result == '(from:alice OR from:bob OR from:charlie)'


@pytest.mark.asyncio
async def test_poll_original_tweet(make_twitter_client):
    client = make_twitter_client(SEARCH_ORIGINAL)
    tweets, cursor = await client.poll(since_id='1')

    assert len(tweets) == 1
    t = tweets[0]
    assert t.id == '1900000000000000001'
    assert t.author_username == 'alice'
    assert t.tweet_type == TweetType.ORIGINAL
    assert t.media_urls == ['https://pbs.twimg.com/media/photo1.jpg']
    assert 'alice' in t.url
    assert cursor == '1900000000000000001'
    await client.close()


@pytest.mark.asyncio
async def test_poll_retweet(make_twitter_client):
    client = make_twitter_client(SEARCH_RETWEET)
    tweets, _ = await client.poll(since_id='1')

    assert len(tweets) == 1
    assert tweets[0].tweet_type == TweetType.RETWEET
    await client.close()


@pytest.mark.asyncio
async def test_poll_reply(make_twitter_client):
    client = make_twitter_client(SEARCH_REPLY)
    tweets, _ = await client.poll(since_id='1')

    assert len(tweets) == 1
    assert tweets[0].tweet_type == TweetType.REPLY
    await client.close()


@pytest.mark.asyncio
async def test_poll_media_resolution(make_twitter_client):
    client = make_twitter_client(SEARCH_MULTI_MEDIA)
    tweets, _ = await client.poll(since_id='1')

    assert len(tweets) == 1
    assert len(tweets[0].media_urls) == 3
    assert tweets[0].media_urls[0] == (
        'https://pbs.twimg.com/media/photo_a.jpg'
    )
    await client.close()


@pytest.mark.asyncio
async def test_poll_empty(make_twitter_client):
    client = make_twitter_client(SEARCH_EMPTY)
    tweets, cursor = await client.poll(since_id='1')

    assert tweets == []
    assert cursor is None
    await client.close()


@pytest.mark.asyncio
async def test_poll_no_fallback(make_twitter_client):
    """When since_id returns 0 tweets, exactly 1 HTTP call is made."""
    client = make_twitter_client(SEARCH_EMPTY)

    # Track calls via transport
    call_count = 0
    original_handler = client._client._transport.handle_async_request

    async def counting_handler(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return await original_handler(*args, **kwargs)

    client._client._transport.handle_async_request = counting_handler

    tweets, cursor = await client.poll(since_id='12345')
    assert tweets == []
    assert call_count == 1
    await client.close()


@pytest.mark.asyncio
async def test_poll_first_run_uses_start_time(make_twitter_client):
    """Without since_id, start_time param is sent instead."""
    captured_request = {}

    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request['url'] = str(request.url)
        return httpx.Response(
            200,
            json=SEARCH_EMPTY,
            request=request,
        )

    from bot.twitter import TwitterClient

    transport = httpx.MockTransport(handler)
    client = TwitterClient(bearer_token='test')
    client._client = httpx.AsyncClient(
        base_url='https://api.x.com/2',
        headers={'Authorization': 'Bearer test'},
        transport=transport,
    )

    await client.poll(since_id=None)
    assert 'start_time' in captured_request['url']
    assert 'since_id' not in captured_request['url']
    await client.close()


@pytest.mark.asyncio
async def test_poll_soft_errors_logged(
    make_twitter_client, caplog
):
    client = make_twitter_client(SEARCH_WITH_ERRORS)

    with caplog.at_level(logging.WARNING, logger='bot.twitter'):
        tweets, _ = await client.poll(since_id='1')

    assert len(tweets) == 1
    assert 'soft errors' in caplog.text.lower()
    await client.close()


@pytest.mark.asyncio
async def test_poll_multi_cursor(make_twitter_client):
    """Cursor should be the highest tweet ID from a multi-tweet batch."""
    client = make_twitter_client(SEARCH_MULTI)
    tweets, cursor = await client.poll(since_id='1')

    assert len(tweets) == 2
    assert cursor == '1900000000000000010'
    await client.close()


@pytest.mark.asyncio
async def test_poll_filters_since_id_dupe(make_twitter_client):
    """API returning the since_id tweet itself is filtered out."""
    client = make_twitter_client(SEARCH_SINCE_ID_DUPE)
    tweets, cursor = await client.poll(
        since_id='1900000000000000050'
    )

    assert tweets == []
    assert cursor is None
    await client.close()


@pytest.mark.asyncio
async def test_poll_filters_since_id_dupe_keeps_new(
    make_twitter_client,
):
    """Dupe filtered but genuine new tweets kept."""
    client = make_twitter_client(SEARCH_SINCE_ID_DUPE_WITH_NEW)
    tweets, cursor = await client.poll(
        since_id='1900000000000000050'
    )

    assert len(tweets) == 1
    assert tweets[0].id == '1900000000000000051'
    assert cursor == '1900000000000000051'
    await client.close()


@pytest.mark.asyncio
async def test_poll_last_polled_as_start_time(make_twitter_client):
    """last_polled is used as start_time when no since_id."""
    from datetime import datetime, timezone

    import httpx

    from bot.twitter import TwitterClient

    captured_url = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_url['url'] = str(request.url)
        return httpx.Response(200, json=SEARCH_EMPTY, request=request)

    transport = httpx.MockTransport(handler)
    client = TwitterClient(bearer_token='test')
    client._client = httpx.AsyncClient(
        base_url='https://api.x.com/2',
        headers={'Authorization': 'Bearer test'},
        transport=transport,
    )

    last = datetime(2026, 3, 3, 10, 30, 0, tzinfo=timezone.utc)
    await client.poll(since_id=None, last_polled=last)

    assert 'start_time=2026-03-03T10%3A30%3A00Z' in captured_url['url']
    assert 'since_id' not in captured_url['url']
    await client.close()
