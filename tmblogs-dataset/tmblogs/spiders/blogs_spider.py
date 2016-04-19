import datetime
import urlparse

import scrapy
import scrapy.crawler
import scrapy.settings

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from tmblogs import parsers


TM_SITES = ['http://habrahabr.ru', 'http://megamozg.ru', 'http://geektimes.ru']
FEED_PAGES = ['/interesting/', '/all/', '/top/']

deny_list = ['m.habrahabr.ru', 'm.megamozg.ru', 'm.geektimes.ru', 'm.tmfeed.ru']

class BlogsSpider(CrawlSpider):
    name = 'tmblogs'
    allowed_domains = ['habrahabr.ru', 'megamozg.ru', 'geektimes.ru', 'tmfeed.ru']


    rules = (
        Rule(LinkExtractor(allow=[r'/post/(\d+)/$'], deny_domains=deny_list), callback='parse_post'),

        Rule(LinkExtractor(allow=[r'/users/(\w+)/topics/'], deny_domains=deny_list), callback='parse_user_topics'),
        Rule(LinkExtractor(allow=[r'/users/(\w+)/comments/'], deny_domains=deny_list), callback='parse_user_comments'),
        Rule(LinkExtractor(allow=[r'/users/(\w+)/favorites/'], deny_domains=deny_list), callback='parse_user_favorites'),
        Rule(LinkExtractor(allow=[r'/users/(\w+)/$'], deny_domains=deny_list), callback='parse_user_profile'),

        Rule(LinkExtractor(allow=[r'/company/(\w+)/blog/(\d+)/$'], deny_domains=deny_list), callback='parse_post'),
        Rule(LinkExtractor(allow=[r'/company/(\w+)/profile/$'], deny_domains=deny_list), callback='parse_company_profile'),
        Rule(LinkExtractor(allow=[r'/company/(\w+)/fans/all/rating/'], deny_domains=deny_list), callback='parse_company_fans'),
        Rule(LinkExtractor(), follow=True),
    )

    start_urls = ['http://tmfeed.ru'] + [
        urlparse.urljoin(site, feed_page)
        for site in TM_SITES
        for feed_page in FEED_PAGES
    ]

    def __init__(self, post_ids=None, *args, **kwargs):
        super(BlogsSpider, self).__init__(*args, **kwargs)

        if post_ids is not None:
            if isinstance(post_ids, str):
                post_ids = eval(post_ids)
        self.habr_post_ids = post_ids

    def parse_post(self, response):
        """
        Parse post page, examples:
        http://habrahabr.ru/post/251189/
        http://geektimes.ru/post/252302/
        """

        update_time = datetime.datetime.now()

        post = parsers.parse_post(response)
        if post is not None:
            post.update({
                '_type': 'post',
                '_id': post['blog_id'] + '/' + post['post_id'],
                '_udpate': update_time,
            })
            yield post

    def parse_user_topics(self, response):
        pass

    def parse_user_comments(self, response):
        pass

    def parse_user_favorites(self, response):
        pass

    def parse_user_profile(self, response):
        update_time = datetime.datetime.now()
        profile = parsers.parse_user_profile(response)
        if profile is not None:
            profile.update({
                '_type': 'user',
                '_id': profile['blog_id'] + '/' + profile['user_id'],
                '_update': update_time,
            })
            yield profile

    def parse_company_profile(self, response):
        update_time = datetime.datetime.now()
        profile = parsers.parse_company_profile(response)
        if profile is not None:
            profile.update({
                '_type': 'company',
                '_id': profile['blog_id'] + '/' + profile['company_id'],
                '_update': update_time,
            })
            yield profile

    def parse_company_fans(self, response):
        pass

