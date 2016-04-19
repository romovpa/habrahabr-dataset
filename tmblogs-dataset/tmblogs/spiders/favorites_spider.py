import urlparse
import logging

from scrapy.spiders import Spider, Request
from scrapy.conf import settings
import pymongo

from tmblogs import parsers


logger = logging.getLogger(__name__)

BLOG_URLS = {
    'habrahabr': 'http://habrahabr.ru/',
    'geektimes': 'http://geektimes.ru/',
    'megamozg': 'http://megamozg.ru/',
}


class UsersSpider(Spider):
    name = 'tmusers'

    def __init__(self, **kwargs):
        super(UsersSpider, self).__init__(**kwargs)

    def start_requests(self):
        connection = pymongo.MongoClient(
            settings['MONGODB_ADDR'],
        )
        db = connection[settings['MONGODB_DB']]
        posts = db['posts']

        logger.info('Querying mongo to get participants')
        participants = posts.aggregate(pipeline=[
            {'$project': {'users_participated': 1, 'blog_id': 1}},
            {'$unwind': '$users_participated'},
            {'$group': {
                '_id': {'username': '$users_participated', 'blog_id': '$blog_id'},
                'count': {'$sum': 1}
            },
            },
            {'$sort': {'count': -1}},
        ])
        participants = list(participants)
        logger.info('Total {} participants'.format(len(participants)))

        for entry in participants:
            _id = entry['_id']
            blog_url = BLOG_URLS[_id['blog_id']]
            yield Request(
                urlparse.urljoin(blog_url, '/users/{}/favorites/'.format(_id['username'])),
                self.parse_favorites,
                priority=1,
            )
            yield Request(
                urlparse.urljoin(blog_url, '/users/{}/'.format(_id['username'])),
                self.parse_user,
            )

    def parse_favorites(self, response):
        username = response.css('h2.username > a ::text').extract_first()
        favorites_sel = response.css('div.user_favorites')
        for post in favorites_sel.css('div.post'):
            post_url = post.css('a.post_title ::attr(href)').extract_first()
            if post_url is not None:
                post_id = parsers.extract_post_id(post_url)
                blog_id = parsers.extract_blog_id(post_url)
                if blog_id is not None and post_id is not None:
                    yield {
                        '_type': 'favorites',
                        '_id': {'user': username, 'post': '{}/{}'.format(blog_id, post_id)},
                    }

        for next_url in response.css('ul#nav-pages a ::attr(href)').extract():
            yield Request(
                urlparse.urljoin(response.url, next_url),
                callback=self.parse_favorites,
                priority=2,
            )

    def parse_user(self, response):
        pass
