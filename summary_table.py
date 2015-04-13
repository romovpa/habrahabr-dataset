import json
import os
import pandas
import datetime
import collections
import argparse


def parse_iso_datetime(s):
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')


if __name__ == '__main__':
    post_ids = sorted(int(name) for name in os.listdir('habr_posts/') if not name.startswith('.'))

    columns = [
        'post_id',
        'last_update',
        'published',
        'title',
        'author',
        'favs_count',
        'pageviews',
        'comments_count',
        'comments_parsed',
        'comments_banned',
        'first_comment_time',
        'last_comment_time',
        'author_comments',
        'tags',
        'content_length',
        'hubs_count',
        'hubs',
    ]

    df = collections.OrderedDict([
        (column, []) for column in columns
    ])


    for n, post_id in enumerate(post_ids):
        with open('habr_posts/%d' % post_id) as f:
            post = json.load(f)

        comments_parsed = 0
        comments_banned = 0
        first_comment_time = None
        last_comment_time = None
        author_comments = 0

        def pass_comments(comments):
            global first_comment_time, last_comment_time, author_comments, comments_parsed, comments_banned
            for comment in comments:
                if comment['banned']:
                    comments_banned += 1
                if not comment['banned'] and comment['time'] is not None:
                    comments_parsed += 1
                    time = parse_iso_datetime(comment['time'])
                    if first_comment_time is None or first_comment_time > time:
                        first_comment_time = time
                    if last_comment_time is None or last_comment_time < time:
                        last_comment_time = time
                    if comment.get('author') == post['author']:
                        author_comments += 1
                pass_comments(comment['replies'])

        pass_comments(post['comments'])

        df['post_id'].append(post['_id'])
        df['last_update'].append(parse_iso_datetime(post['_last_update']))
        df['published'].append(parse_iso_datetime(post['published']))
        df['title'].append(post['title'])
        df['author'].append(post['author'])
        df['favs_count'].append(post['favs_count'])
        df['pageviews'].append(post['pageviews'])
        df['comments_count'].append(post['comments_count'])
        df['comments_parsed'].append(comments_parsed)
        df['comments_banned'].append(comments_banned)
        df['first_comment_time'].append(first_comment_time)
        df['last_comment_time'].append(last_comment_time)
        df['author_comments'].append(author_comments)
        df['hubs_count'].append(len(post['hubs']))
        df['hubs'].append(','.join(map(lambda pair: pair[0], post['hubs'])))
        df['tags'].append(len(post['tags']))
        df['content_length'].append(len(post['content_html']))

        if n % 10000 == 0:
            print 'Processed', n, 'posts'

    df = pandas.DataFrame(df).ix[:, columns]
    df.to_csv('posts.csv', encoding='utf8', header=True, index=False)