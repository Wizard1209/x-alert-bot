"""Realistic X API v2 response dicts for GET /2/tweets/search/recent."""

SEARCH_ORIGINAL = {
    'data': [
        {
            'id': '1900000000000000001',
            'text': 'Hello from the X API! Check out this photo',
            'author_id': '100001',
            'created_at': '2026-03-03T12:00:00.000Z',
            'referenced_tweets': [],
            'attachments': {'media_keys': ['media_001']},
            'entities': {
                'urls': [
                    {
                        'start': 35,
                        'end': 58,
                        'expanded_url': (
                            'https://twitter.com/user/status/'
                            '1900000000000000001/photo/1'
                        ),
                    }
                ]
            },
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
        'media': [
            {
                'media_key': 'media_001',
                'type': 'photo',
                'url': 'https://pbs.twimg.com/media/photo1.jpg',
            }
        ],
    },
    'meta': {
        'newest_id': '1900000000000000001',
        'oldest_id': '1900000000000000001',
        'result_count': 1,
    },
}

SEARCH_RETWEET = {
    'data': [
        {
            'id': '1900000000000000002',
            'text': 'RT @bob: Original tweet content here',
            'author_id': '100001',
            'created_at': '2026-03-03T12:05:00.000Z',
            'referenced_tweets': [
                {'type': 'retweeted', 'id': '1800000000000000099'}
            ],
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
    },
    'meta': {
        'newest_id': '1900000000000000002',
        'oldest_id': '1900000000000000002',
        'result_count': 1,
    },
}

SEARCH_REPLY = {
    'data': [
        {
            'id': '1900000000000000003',
            'text': '@bob I agree with you on this point!',
            'author_id': '100001',
            'created_at': '2026-03-03T12:10:00.000Z',
            'referenced_tweets': [
                {'type': 'replied_to', 'id': '1800000000000000050'}
            ],
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
    },
    'meta': {
        'newest_id': '1900000000000000003',
        'oldest_id': '1900000000000000003',
        'result_count': 1,
    },
}

SEARCH_MULTI = {
    'data': [
        {
            'id': '1900000000000000010',
            'text': 'Latest original tweet from alice',
            'author_id': '100001',
            'created_at': '2026-03-03T13:00:00.000Z',
            'referenced_tweets': [],
        },
        {
            'id': '1900000000000000009',
            'text': 'RT @charlie: Something interesting',
            'author_id': '100002',
            'created_at': '2026-03-03T12:55:00.000Z',
            'referenced_tweets': [
                {'type': 'retweeted', 'id': '1800000000000000077'}
            ],
        },
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            },
            {
                'id': '100002',
                'username': 'bob',
                'name': 'Bob Builder',
                'verified': True,
                'verified_type': 'business',
                'public_metrics': {'followers_count': 12000},
            },
        ],
    },
    'meta': {
        'newest_id': '1900000000000000010',
        'oldest_id': '1900000000000000009',
        'result_count': 2,
    },
}

SEARCH_EMPTY = {'meta': {'result_count': 0}}

SEARCH_WITH_ERRORS = {
    'data': [
        {
            'id': '1900000000000000020',
            'text': 'Tweet with soft error alongside',
            'author_id': '100001',
            'created_at': '2026-03-03T14:00:00.000Z',
            'referenced_tweets': [],
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
    },
    'errors': [
        {
            'resource_type': 'tweet',
            'field': 'non_public_metrics',
            'title': 'Field Authorization Error',
            'detail': 'Sorry, you are not authorized.',
        }
    ],
    'meta': {
        'newest_id': '1900000000000000020',
        'oldest_id': '1900000000000000020',
        'result_count': 1,
    },
}

# API returns the since_id tweet itself (edge case bug)
SEARCH_SINCE_ID_DUPE = {
    'data': [
        {
            'id': '1900000000000000050',
            'text': 'This is the since_id tweet returned again',
            'author_id': '100001',
            'created_at': '2026-03-03T16:00:00.000Z',
            'referenced_tweets': [],
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
    },
    'meta': {
        'newest_id': '1900000000000000050',
        'oldest_id': '1900000000000000050',
        'result_count': 1,
    },
}

# Mix of since_id dupe + a genuine new tweet
SEARCH_SINCE_ID_DUPE_WITH_NEW = {
    'data': [
        {
            'id': '1900000000000000051',
            'text': 'Brand new tweet',
            'author_id': '100001',
            'created_at': '2026-03-03T16:05:00.000Z',
            'referenced_tweets': [],
        },
        {
            'id': '1900000000000000050',
            'text': 'This is the since_id tweet returned again',
            'author_id': '100001',
            'created_at': '2026-03-03T16:00:00.000Z',
            'referenced_tweets': [],
        },
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
    },
    'meta': {
        'newest_id': '1900000000000000051',
        'oldest_id': '1900000000000000050',
        'result_count': 2,
    },
}

# API ignores start_time and leaks old tweets (observed in prod)
SEARCH_OLD_TWEETS_LEAK = {
    'data': [
        {
            'id': '1900000000000000100',
            'text': 'New tweet',
            'author_id': '100001',
            'created_at': '2026-03-04T15:27:00.000Z',
            'referenced_tweets': [],
        },
        {
            'id': '1900000000000000090',
            'text': 'Old tweet that should be filtered',
            'author_id': '100002',
            'created_at': '2026-03-04T04:52:38.000Z',
            'referenced_tweets': [],
        },
        {
            'id': '1900000000000000080',
            'text': 'Even older tweet',
            'author_id': '100003',
            'created_at': '2026-03-03T12:00:00.000Z',
            'referenced_tweets': [],
        },
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            },
            {
                'id': '100002',
                'username': 'bob',
                'name': 'Bob Builder',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 12000},
            },
            {
                'id': '100003',
                'username': 'charlie',
                'name': 'Charlie Test',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 300},
            },
        ],
    },
    'meta': {
        'newest_id': '1900000000000000100',
        'oldest_id': '1900000000000000080',
        'result_count': 3,
    },
}

SEARCH_MULTI_MEDIA = {
    'data': [
        {
            'id': '1900000000000000030',
            'text': 'Check out these photos!',
            'author_id': '100001',
            'created_at': '2026-03-03T15:00:00.000Z',
            'referenced_tweets': [],
            'attachments': {
                'media_keys': [
                    'media_010',
                    'media_011',
                    'media_012',
                ]
            },
            'entities': {
                'urls': [
                    {
                        'start': 20,
                        'end': 43,
                        'expanded_url': (
                            'https://twitter.com/alice/status/'
                            '1900000000000000030/photo/1'
                        ),
                    }
                ]
            },
        }
    ],
    'includes': {
        'users': [
            {
                'id': '100001',
                'username': 'alice',
                'name': 'Alice Dev',
                'verified': False,
                'verified_type': '',
                'public_metrics': {'followers_count': 5000},
            }
        ],
        'media': [
            {
                'media_key': 'media_010',
                'type': 'photo',
                'url': 'https://pbs.twimg.com/media/photo_a.jpg',
            },
            {
                'media_key': 'media_011',
                'type': 'photo',
                'url': 'https://pbs.twimg.com/media/photo_b.jpg',
            },
            {
                'media_key': 'media_012',
                'type': 'photo',
                'url': 'https://pbs.twimg.com/media/photo_c.jpg',
            },
        ],
    },
    'meta': {
        'newest_id': '1900000000000000030',
        'oldest_id': '1900000000000000030',
        'result_count': 1,
    },
}
