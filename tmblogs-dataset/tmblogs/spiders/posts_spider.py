import datetime
import urlparse

from scrapy.spiders import Spider, Request

from tmblogs import parsers

DEFAULT_BLOG_URLS = [
    'http://habrahabr.ru/',
    'http://geektimes.ru/',
    'http://megamozg.ru/',
]

class BlogsSpider(Spider):
    name = 'tmposts'

    def __init__(self, blog_urls=None, min_post_id=0, max_post_id=500000, **kwargs):
        super(BlogsSpider, self).__init__(**kwargs)

        self.min_post_id = int(min_post_id)
        self.max_post_id = int(max_post_id)
        self.blog_urls = blog_urls if blog_urls is not None else DEFAULT_BLOG_URLS

    def start_requests(self):
        for post_id in xrange(self.min_post_id, self.max_post_id+1):
            for blog_url in self.blog_urls:
                url = urlparse.urljoin(blog_url, '/post/{post_id}'.format(**locals()))
                yield Request(url)

    def parse(self, response):
        """
        Parse post page, examples:
        http://habrahabr.ru/post/251189/
        http://geektimes.ru/post/252302/
        """

        update_time = datetime.datetime.now()

        post = parsers.parse_post(response)
        if post is not None:
            post.update({
                '_type': 'posts',
                '_id': '{blog_id}/{post_id}'.format(**post),
                '_updated': update_time,
            })
            yield post
