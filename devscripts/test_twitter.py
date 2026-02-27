"""Quick manual test for TwitterClient (search/recent).

Run: uv run python -m devscripts.test_twitter
"""

import asyncio
import logging

from bot.config import CONFIG
from bot.twitter import TwitterClient, build_query

logging.basicConfig(level=CONFIG.log_level)


async def main() -> None:
    client = TwitterClient(bearer_token=CONFIG.x_api_key)
    try:
        query = build_query(CONFIG.watch_users)
        print(f'Query: {query}')
        print('Polling (no cursor — first run)...\n')

        tweets, cursor = await client.poll(since_id=None)
        print(f'--- {len(tweets)} tweet(s), cursor={cursor} ---\n')
        for t in tweets:
            print(f'@{t.author_username} ({t.author_name})')
            print(f'  {t.text[:120]}')
            if t.media_urls:
                print(f'  media: {t.media_urls}')
            print(f'  {t.url}')
            print()

        if cursor:
            print(f'--- Polling again with cursor={cursor} ---')
            tweets2, cursor2 = await client.poll(since_id=cursor)
            print(f'{len(tweets2)} new tweet(s), cursor={cursor2}')
    finally:
        await client.close()


if __name__ == '__main__':
    asyncio.run(main())
