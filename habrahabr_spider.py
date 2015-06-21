# -*- coding: utf-8 -*

import datetime
import urlparse
import dateutil.parser

import scrapy
import scrapy.crawler
import scrapy.settings



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


class TMSpider(scrapy.Spider):
    name = 'tm'
    allowed_domains = ['habrahabr.ru', 'megamozg.ru', 'geektimes.ru', 'tmtmfeed.ru']

    tm_sites = ['http://habrahabr.ru', 'http://megamozg.ru', 'http://geektimes.ru']
    feed_pages = ['/interesting/', '/all/', '/top/']

    def __init__(self, post_ids=None, *args, **kwargs):
        super(TMSpider, self).__init__(*args, **kwargs)

        if post_ids is not None:
            if isinstance(post_ids, str):
                post_ids = eval(post_ids)
        self.post_ids = post_ids

    def start_requests(self):
        yield scrapy.Request('http://tmfeed.ru/', self.parse_tmfeed)

        for site in self.tm_sites:
            for page in self.feed_pages:
                url = urlparse.urljoin(site, page)
                yield scrapy.Request(url, self.parse_feed)

        if self.post_ids:
            for post_id in self.post_ids:
                yield scrapy.Request('http://habrahabr.ru/post/%d/' % post_id, self.parse_post)

    def parse_post(self, response):
        last_update = datetime.datetime.now()
        page_title = response.xpath('//html/head/title/text()').extract_first()

        post_sel = response.css('.post')

        post_id = post_sel.css('::attr(id)').extract_first()
        if post_id.startswith('post_'):
            post_id = post_id[len('post_'):]
        else:
            raise RuntimeError('Bad post_id: "%s"' % post_id)

        post_title = post_sel.css('h1.title span.post_title ::text').extract_first()
        post_published = parse_habrahabr_datetime(post_sel.css('div.published ::text').extract_first())

        # flags (tutorial, sandbox, etc.)
        flags = []
        flag_classes = ' '.join(post_sel.css('h1.title .flag ::attr(class)').extract()).split(' ')
        for flag_class in flag_classes:
            if flag_class.startswith('flag_'):
                flags.append(flag_class[len('flag_'):])

        # hubs
        hubs_sel = post_sel.css('.hubs a.hub')
        hubs = []
        for hub_sel in hubs_sel:
            hub_name = hub_sel.xpath('text()').extract_first()
            hub_url = hub_sel.xpath('@href').extract_first()
            hubs.append((hub_name, hub_url))
            yield scrapy.Request(hub_url, self.parse_feed)

        content_html = post_sel.css('div.content').extract_first()
        tags = post_sel.css('ul.tags li a ::text').extract()

        infopanel_sel = post_sel.css('div.infopanel')[0]
        pageviews = int(infopanel_sel.css('div.pageviews ::text').extract_first())
        favs_count = infopanel_sel.css('div.favs_count ::text').extract_first()
        favs_count = int(favs_count) if favs_count is not None else 0

        author_sel = infopanel_sel.css('div.author')
        author_name = author_sel.css('a ::text').extract_first()
        author_url = author_sel.css('a ::attr(href)').extract_first()
        author_rating = float(author_sel.css('span.rating ::text').extract_first().replace(u'\u2013', '-').replace(',', '.'))

        comments_sel = response.css('#comments')
        comments_count = comments_sel.css('h2.title span#comments_count ::text').extract_first()

        def extract_comments(sel):
            childs_sel = sel.xpath('./div[@class="comment_item"]')

            extracted_comments = []
            commenter_urls = set()

            for child_sel in childs_sel:
                body_sel = child_sel.xpath('./div[@class="comment_body "]')[0]
                reply_sel = child_sel.xpath('./div[@class="reply_comments"]')[0]
                replies, child_commenter_urls = extract_comments(reply_sel)
                commenter_urls.update(child_commenter_urls)

                if len(body_sel.css('div.author_banned')) > 0:
                    comment = {
                        'banned': True,
                        'replies': replies,
                    }
                else:
                    time = body_sel.css('time ::text').extract_first()
                    time = parse_habrahabr_datetime(time)
                    username = body_sel.css('a.username ::text').extract_first()
                    user_url = body_sel.css('a.username ::attr(href)').extract_first()
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
                    commenter_urls.add(user_url)

                extracted_comments.append(comment)

            return extracted_comments, commenter_urls

        comments, commenter_urls = extract_comments(comments_sel)

        yield scrapy.Request(author_url, self.parse_user)
        for user_url in commenter_urls:
            yield scrapy.Request(user_url, self.parse_user)

        yield {
            '_type': 'post',
            '_id': post_id,
            'title': post_title,
            'published': post_published,
            'flags': flags,
            'hubs': hubs,
            'content_html': content_html,
            'tags': tags,
            'pageviews': pageviews,
            'favs_count': favs_count,
            'author': author_name,
            'author_rating': author_rating,
            'comments_count': comments_count,
            'comments': comments,
            'last_update': last_update,
        }

        for entry in self.parse_page_links(response):
            yield entry


    def parse_user(self, response):
        return
        if 0:
            yield {
                '_type': 'user',

            }

    def parse_user_feed(self, response):
        return

    def parse_feed(self, response):
        feed_post_urls = response.css('div.posts div.post h1.title a.post_title ::attr(href)').extract()
        for post_url in feed_post_urls:
            post_url = urlparse.urljoin(response.url, post_url)
            yield scrapy.Request(post_url, self.parse_post)

        nav_urls = response.css('div.page-nav ul#nav-pages li a ::attr(href)').extract()
        for page_url in nav_urls:
            page_url = urlparse.urljoin(response.url, page_url)
            yield scrapy.Request(page_url, self.parse_feed)

        for entry in self.parse_page_links(response):
            yield entry

    def parse_user_rating(self, response):
        return
        sel_users = response.css('div#peoples div.user div.info div.userlogin div.username')
        for sel_user in sel_users:
            user_name = sel_user.css('::text').extract_first()
            user_url = sel_user.css('::attr(href)').extract_first()
            user_url = urlparse.urljoin(response.url, user_url)
            yield scrapy.Request(user_url, self.parse_user)

        nav_urls = response.css('div.page-nav ul#nav-pages li a ::attr(href)').extract()
        for page_url in nav_urls:
            page_url = urlparse.urljoin(response.url, page_url)
            yield scrapy.Request(page_url, self.parse_user_rating)

    def parse_page_links(self, response):
        block_post_urls = response.css('div.post_item a.post_name ::attr(href)').extract()
        for post_url in block_post_urls:
            post_url = urlparse.urljoin(response.url, post_url)
            yield scrapy.Request(post_url, self.parse_post)

        block_hub_urls = response.css('ul.categories li a ::attr(href)').extract()
        for hub_url in block_hub_urls:
            hub_url = urlparse.urljoin(response.url, hub_url)
            yield scrapy.Request(hub_url, self.parse_feed)

    def parse_tmfeed(self, response):
        return



if __name__ == '__main__':
    print 'Usage: scrapy runspider %s' % __file__

    # settings = scrapy.settings.Settings({
    #     'AUTOTHROTTLE_ENABLED': True,
    # })
    # runner = scrapy.crawler.CrawlerProcess(settings)
    # runner.crawl(HabrahabrSpider, posts_range=xrange(50))
