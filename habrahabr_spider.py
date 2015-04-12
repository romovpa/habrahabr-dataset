# -*- coding: utf-8 -*

import datetime

import scrapy
import scrapy.crawler
import scrapy.settings
import dateutil.parser


class PostItem(scrapy.Item):
    title = scrapy.Field()
    published = scrapy.Field()
    hubs = scrapy.Field()
    content = scrapy.Field()
    tags = scrapy.Field()
    pageviews = scrapy.Field()
    favs_count = scrapy.Field()
    author = scrapy.Field()
    author_url = scrapy.Field()
    author_rating = scrapy.Field()
    comments_count = scrapy.Field()
    comments = scrapy.Field()

    last_update = scrapy.Field()


def parse_habrahabr_datetime(date_str):
    month_name_map = {
        u'января': 'Jan',
        u'февраля': 'Feb',
        u'марта': 'Mar',
        u'апреля': 'Apr',
        u'мая': 'May',
        u'июня': 'Jun',
        u'июля': 'Jul',
        u'августа': 'Aug',
        u'сентября': 'Sep',
        u'октября': 'Oct',
        u'ноября': 'Nov',
        u'декабря': 'Dec',
    }
    s = date_str
    for month1, month2 in month_name_map.iteritems():
        s = s.replace(month1, month2)
    s = s.replace(u' в ', ' ')
    s = s.replace(u'сегодня', datetime.datetime.now().strftime('%Y-%m-%d'))
    s = s.replace(u'вчера', (datetime.datetime.now()-datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
    return dateutil.parser.parse(s)


class HabrahabrSpider(scrapy.Spider):
    name = 'habrahabr'

    def __init__(self, posts_range=None, *args, **kwargs):
        super(HabrahabrSpider, self).__init__(*args, **kwargs)
        self.posts_range = eval(posts_range)

    def start_requests(self):
        for post_id in self.posts_range:
            yield scrapy.Request('http://habrahabr.ru/post/%d/' % post_id, callback=self.parse_post)

    def parse_post(self, response):
        page_title = response.xpath('//html/head/title/text()').extract_first()

        FORBID_TITLES = [
            u'Geektimes \u2014 \u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d',
            u'\u0425\u0430\u0431\u0440\u0430\u0445\u0430\u0431\u0440 \u2014 \u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d',
        ]

        if page_title in FORBID_TITLES:
            return

        post = PostItem()

        post_sel = response.css('.post')
        post['title'] = post_sel.css('h1.title span.post_title ::text').extract_first()
        post['published'] = parse_habrahabr_datetime(post_sel.css('div.published ::text').extract_first())

        hubs_sel = post_sel.css('.hubs a.hub')
        hubs = []
        for hub_sel in hubs_sel:
            hub_name = hub_sel.xpath('text()').extract_first()
            hub_url = hub_sel.xpath('@href').extract_first()
            hubs.append((hub_name, hub_url))
        post['hubs'] = hubs

        post['content'] = post_sel.css('div.content').extract_first()
        post['tags'] = post_sel.css('ul.tags li a ::text').extract()

        infopanel_sel = post_sel.css('div.infopanel')[0]
        post['pageviews'] = int(infopanel_sel.css('div.pageviews ::text').extract_first())
        favs_count = infopanel_sel.css('div.favs_count ::text').extract_first()
        post['favs_count'] = int(favs_count) if favs_count is not None else 0

        author_sel = infopanel_sel.css('div.author')
        post['author'] = author_sel.css('a ::text').extract_first()
        post['author_url'] = author_sel.css('a ::attr(href)').extract_first()
        post['author_rating'] = float(author_sel.css('span.rating ::text').extract_first().replace(u'\u2013', '-').replace(',', '.'))

        comments_sel = response.css('#comments')
        post['comments_count'] = comments_sel.css('h2.title span#comments_count ::text').extract_first()

        def extract_comments(sel):
            childs_sel = sel.xpath('./div[@class="comment_item"]')

            extracted_comments = []

            for child_sel in childs_sel:
                body_sel = child_sel.xpath('./div[@class="comment_body "]')[0]
                reply_sel = child_sel.xpath('./div[@class="reply_comments"]')[0]
                replies = extract_comments(reply_sel)

                if len(body_sel.css('div.author_banned')) > 0:
                    comment = {
                        'banned': True,
                        'replies': replies,
                    }
                else:
                    time = body_sel.css('time ::text').extract_first()
                    time = parse_habrahabr_datetime(time)
                    username = body_sel.css('a.username ::text').extract_first()
                    link_to_comment = body_sel.css('a.link_to_comment ::attr(href)').extract_first()
                    votes = int(body_sel.css('div.voting span.score ::text').extract_first().replace(u'\u2013', '-'))
                    message_html = body_sel.css('div.message').extract_first()

                    comment = {
                        'banned': False,
                        'time': time,
                        'username': username,
                        'link': link_to_comment,
                        'votes': votes,
                        'message_html': message_html,
                        'replies': replies,
                    }

                extracted_comments.append(comment)

            return extracted_comments

        post['comments'] = extract_comments(comments_sel)
        post['last_update'] = datetime.datetime.now()

        yield post


    def parse_user(self, response):
        raise NotImplementedError()



if __name__ == '__main__':
    print 'Usage: scrapy runspider %s' % __file__

    # settings = scrapy.settings.Settings({
    #     'AUTOTHROTTLE_ENABLED': True,
    # })
    # runner = scrapy.crawler.CrawlerProcess(settings)
    # runner.crawl(HabrahabrSpider, posts_range=xrange(50))
