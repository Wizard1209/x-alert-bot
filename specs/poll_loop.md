# Poll Loop Spec

## Overview

The poll loop is a long-running background task that periodically fetches new tweets from the X API and delivers them as Telegram alerts to all registered users. It runs alongside the aiogram dispatcher on the same event loop.

## Components

The loop should be decomposed into three layers:

### 1. Orchestrator (`run_poll_loop`)

The top-level infinite loop. Responsibilities:

- Load initial cursor from storage on startup
- Sleep for `poll_interval` minutes between iterations
- Catch and log all exceptions per iteration (never crash)
- Notify admin on any unhandled iteration error
- Delegate all work to the two layers below

### 2. Poll Step (`poll_step`)

A single poll-then-deliver iteration. Receives current cursor, returns new cursor. Responsibilities:

- Call `TwitterClient.poll(cursor)` to fetch new tweets
- If no tweets, return current cursor unchanged
- If tweets found, pass them to the delivery layer
- Advance cursor only after **all** deliveries complete (success or handled failure)
- Persist new cursor to storage
- Return the new cursor to the orchestrator

### 3. Delivery (`deliver_alerts`)

Sends formatted alerts to all users. Responsibilities:

- Accept a list of tweets (already in chronological order, oldest first)
- Format each tweet into a `TelegramAlert`
- For each alert, iterate over all registered users and send
- Handle per-user send failures individually (never skip remaining users)
- Return a list of user IDs that should be removed (blocked the bot)

## Error Handling

### Per-user send errors

| Error | Action |
|---|---|
| `TelegramForbiddenError` (user blocked bot) | Collect user ID for removal. Do NOT remove mid-iteration — return removals to caller |
| Any other send error | Log, notify admin, continue to next user |

### Poll errors (X API)

| Error | Action |
|---|---|
| HTTP error / timeout | Log, notify admin, skip iteration, retain current cursor |
| X API soft errors (`errors` key in response) | Log warning, process whatever `data` was returned |

### Orchestrator errors

Any unhandled exception from `poll_step` is caught, logged, and reported to admin. The loop continues with the same cursor.

## Cursor Contract

- Cursor is a tweet ID string (`since_id`). The X API returns only tweets with ID strictly greater than `since_id`.
- On first run (no cursor): use `start_time = now - poll_interval` as seed. This is handled inside `TwitterClient.poll()`, not the loop.
- Cursor advances to the highest tweet ID in the batch.
- Cursor is persisted to disk only after delivery completes — if the process crashes mid-delivery, tweets will be re-fetched and re-sent on restart (at-least-once semantics).

## Delivery Order

- X API returns newest first. Deliver oldest first (reverse the batch before sending).
- Between each alert delivery, sleep briefly (150ms) to respect Telegram rate limits.

## Alert Sending

A single alert send consists of:

1. If alert has a `photo_url`: send as photo message with caption
2. If no photo: send as text message
3. If alert has `extra_photos`: send each as a separate photo message
4. Retweets, replies, and quotes are sent with `disable_notification=True`

## User List

- Snapshot user list once at the start of each `poll_step`, not per-tweet. A user registering mid-delivery won't receive partial alerts from that batch.
- Process blocked-user removals after the full delivery pass completes.

## Testability Requirements

- `poll_step` must be independently callable with injected dependencies (bot, client, storage, cursor) and return the new cursor. No infinite loop, no sleep.
- `deliver_alerts` must accept a bot, user dict, and list of alerts. Return blocked user IDs. No storage side effects.
- `send_alert` remains a standalone function for sending one alert to one chat.
- The orchestrator (`run_poll_loop`) is the only piece that loops/sleeps and is tested via integration or manual verification.
