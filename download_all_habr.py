# -*- coding: utf-8 -*-

import os
import json
import datetime
import traceback

import dateutil.parser
import scrapy
import requests

def parse_page_datetime(date_str):
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


def datetime_to_iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def parse_habrahabr_page(text):
    page_sel = scrapy.Selector(text=text)
    page_title = page_sel.xpath('//html/head/title/text()').extract_first()
 
    if page_title is not None and page_title.endswith(u'Доступ к странице ограничен'):
        return

    post_sel = page_sel.css('.post')

    post_id_tag = post_sel.xpath('@id').extract_first()
    post_id = int(post_id_tag.split('_', 1)[1])

    title = post_sel.css('h1.title span.post_title ::text').extract_first()
    published = post_sel.css('div.published ::text').extract_first()

    published = datetime_to_iso(parse_page_datetime(published))
    
    hubs_sel = post_sel.css('.hubs a.hub')
    hubs = []
    for hub_sel in hubs_sel:
        hub_name = hub_sel.xpath('text()').extract_first()
        hub_url = hub_sel.xpath('@href').extract_first()
        hubs.append((hub_name, hub_url))
        
    content_html = post_sel.css('div.content').extract_first()
    
    tags = post_sel.css('ul.tags li a ::text').extract()
    
    infopanel_sel = post_sel.css('div.infopanel')[0]
    pageviews = int(infopanel_sel.css('div.pageviews ::text').extract_first())
    favs_count = infopanel_sel.css('div.favs_count ::text').extract_first()
    favs_count = int(favs_count) if favs_count is not None else None

    author_sel = infopanel_sel.css('div.author')
    author = author_sel.css('a ::text').extract_first()
    author_url = author_sel.css('a ::attr(href)').extract_first()
    author_rating = author_sel.css('span.rating ::text').extract_first()
    author_rating = float(author_rating.replace(u'\u2013', '-').replace(',', '.')) if author_rating is not None else None

    
    comments_sel = page_sel.css('#comments')
    comments_count = comments_sel.css('h2.title span#comments_count ::text').extract_first()
    if comments_count is not None:
        comments_count = int(comments_count)
    
    def extract_comments(sel):
        childs_sel = sel.xpath('./div[@class="comment_item"]')

        extracted_comments = []

        for child_sel in childs_sel:
            body_sel = child_sel.xpath('./div[@class="comment_body "]')[0]

            reply_sel = child_sel.xpath('./div[@class="reply_comments"]')
            replies = []
            if len(reply_sel) > 0:
                replies = extract_comments(reply_sel[0])
            
            if len(body_sel.css('div.author_banned')) > 0:               
                comment = {
                    'banned': True,
                    'replies': replies,
                }
            else:
                time = body_sel.css('time ::text').extract_first()
                time = datetime_to_iso(parse_page_datetime(time)) if time is not None else None
                username = body_sel.css('a.username ::text').extract_first()
                link_to_comment = body_sel.css('a.link_to_comment ::attr(href)').extract_first()
                votes = body_sel.css('div.voting span.score ::text').extract_first()
                if votes is not None:
                    votes = int(votes.replace(u'\u2013', '-'))
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
    
    comments = extract_comments(comments_sel)
    
    post = {
        '_id': post_id,
        '_last_update': datetime_to_iso(datetime.datetime.now()),
        'title': title, 
        'published': published,
        'hubs': hubs,
        'content_html': content_html,
        'tags': tags,
        'pageviews': pageviews,
        'favs_count': favs_count,
        'author': author,
        'author_url': author_url,
        'author_rating': author_rating,
        'comments_count': comments_count,
        'comments': comments,
    }
    
    return post


def download_habr_page(page_index):
    name = str(page_index)
    if (os.path.exists('habr_posts/%s' % name)
        or os.path.exists('habr_posts/._404_%s' % name)
        or os.path.exists('habr_posts/._forbid_%s' % name)):
        #or os.path.exists('habr_posts/._exception_%s' % name)):
        return

    url = 'http://habrahabr.ru/post/%s/' % name

    print 'Reading', page_index
    print '   url:', url

    resp = requests.get(url)
    print '   status:', resp.status_code
    if resp.status_code == 404:
        # not found
        with open('habr_posts/._404_%s' % name, 'w') as f:
            pass
    elif resp.status_code == 200:
        try:
            page_record = parse_habrahabr_page(resp.text)
            if page_record is None:
                with open('habr_posts/._forbid_%s' % name, 'w') as f:
                    pass
            else:
                print '   title:', page_record['title']
                with open('habr_posts/%s' % name, 'w') as f:
                    json.dump(page_record, f)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            exception_filename = 'habr_posts/._exception_%s' % name
            with open(exception_filename, 'w') as f:
                f.write(traceback.format_exc())
            print '   can\'t parse, exception %s, see %s' % (e.__class__.__name__, exception_filename)

    else:
        print 'Page %s: status %d' % (name, resp.status_code)


if __name__ == '__main__':
    import argparse
    import multiprocessing

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--start-index', type=int, required=True)
    parser.add_argument('-f', '--finish-index', type=int, required=True)
    parser.add_argument('-p', '--processes', type=int, default=1)
    args = parser.parse_args()

    indices = range(args.start_index, args.finish_index)

    if not os.path.exists('habr_posts'):
        os.mkdir('habr_posts')

    if args.processes == 1:    
        for page_index in indices:
            download_habr_page(page_index)
    else:
        import signal
        
        def init_worker():
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        pool = multiprocessing.Pool(args.processes, init_worker)
        pool.map(download_habr_page, indices)
