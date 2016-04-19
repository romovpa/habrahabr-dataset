# -*- coding: utf-8 -*

import datetime
import urlparse
import dateutil.parser
import re

NETLOC_TO_BLOG_ID = {
    'habrahabr.ru': 'habrahabr',
    'megamozg.ru': 'megamozg',
    'geektimes.ru': 'geektimes',
}

def element_html_content(selector):
    return ''.join(selector.xpath('node()').extract()).strip()


def extract_company_id(url):
    m = re.search(r'/company/([^/]+)/', url)
    if m is None:
        return
    company_id = m.group(1)
    return company_id

def extract_post_id(url):
    m = re.search(r'/([^/]+/)*(?P<post_id>\d+)/', url)
    if m is None:
        return
    post_id = int(m.group('post_id'))
    return post_id

def extract_user_id(url):
    m = re.search(r'/users/([^/]+)/', url)
    if m is None:
        return
    user_id = m.group(1)
    return user_id

def extract_hub_id(url):
    m = re.search(r'/hub/([^/]+)/', url)
    if m is None:
        return
    hub_id = m.group(1)
    return hub_id

def extract_blog_id(url):
    url_parts = urlparse.urlsplit(url)
    blog_id = NETLOC_TO_BLOG_ID.get(url_parts.netloc)
    if blog_id is None:
        raise RuntimeError('Invalid blog type: %s' % url)
    return blog_id


def extract_canonical_url(response):
    url = response.url
    meta_link = response.css('head > link[rel="canonical"] ::attr(href)').extract_first()
    if meta_link is not None:
        url = meta_link
    return url


def parse_habr_datetime(date_str):
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
    s = s.replace(u'вчера', (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
    return dateutil.parser.parse(s)



def parse_post(response):
    """
    Parse post page, examples:
    http://habrahabr.ru/post/251189/
    http://geektimes.ru/post/252302/
    """
    url = extract_canonical_url(response)

    blog_id = extract_blog_id(url)

    post_sel = response.css('.post')
    if len(post_sel) == 0:
        return

    post_id = post_sel.css('::attr(id)').extract_first()
    if post_id.startswith('post_'):
        post_id = post_id[len('post_'):]
    else:
        raise RuntimeError('Bad post_id: "%s"' % post_id)

    post_title = post_sel.css('h1.title span.post_title ::text').extract_first()
    post_published = parse_habr_datetime(post_sel.css('div.published ::text').extract_first())

    # flags (tutorial, sandbox, etc.)
    flags = []
    flag_classes = ' '.join(post_sel.css('h1.title .flag ::attr(class)').extract()).split(' ')
    for flag_class in flag_classes:
        if flag_class.startswith('flag_'):
            flags.append(flag_class[len('flag_'):])

    # hubs
    hubs_sel = post_sel.css('.hubs a.hub')
    hubs = []
    company_blog = None
    for hub_sel in hubs_sel:
        hub_url = hub_sel.css('::attr(href)').extract_first()
        hub_id = extract_hub_id(hub_url)
        company_id = extract_company_id(hub_url)
        if company_id is not None:
            company_blog = company_id
        if hub_id is not None:
            hubs.append(hub_id)


    content_html = element_html_content(post_sel.css('div.content'))
    tags = post_sel.css('ul.tags li a ::text').extract()

    pageviews = int(post_sel.css('div.views-count_post ::text').extract_first())
    favs_count = post_sel.css('span.js-favs_count ::text').extract_first()
    favs_count = int(favs_count) if favs_count is not None else None
    voting_score = post_sel.css('span.js-score ::text').extract_first()
    try:
        voting_score = voting_score.replace(u'\u2013', '-') if voting_score is not None else None
        voting_score = int(voting_score)
    except:
        print 'Voting score:', repr(voting_score)
        voting_score = None

    author_company = None
    author_user = None

    author_anchors = set(response.css('div.post-type a ::attr(href) , div.author-info a ::attr(href)').extract())
    for href in author_anchors:
        if href.startswith('/company/'):
            author_company = href[len('/company/'):]
        if href.startswith('/users/'):
            author_user = href[len('/users/'):]

    comments_sel = response.css('#comments')
    comments_count = comments_sel.css('h2.title span#comments_count ::text').extract_first()

    users_participated = set()
    if author_user is not None:
        users_participated.add(author_user)

    def extract_comments(sel):
        childs_sel = sel.xpath('./div[@class="comment_item"]')

        extracted_comments = []
        commenter_urls = set()

        for child_sel in childs_sel:
            body_sels = child_sel.xpath('./div[@class="comment_body "]')
            if not body_sels:
                continue
            body_sel = body_sels[0]

            replies = []
            reply_selectors = child_sel.xpath('./div[@class="reply_comments"]')
            for reply_sel in reply_selectors:
                child_replies, child_commenter_urls = extract_comments(reply_sel)
                replies += child_replies
                commenter_urls.update(child_commenter_urls)

            if len(body_sel.css('div.author_banned')) > 0:
                comment = {
                    'banned': True,
                    'replies': replies,
                }
            else:
                time = body_sel.css('time ::text').extract_first()
                time = parse_habr_datetime(time)
                username = body_sel.css('a.username ::text').extract_first()
                user_url = body_sel.css('a.username ::attr(href)').extract_first()
                link_to_comment = body_sel.css('a.link_to_comment ::attr(href)').extract_first()
                votes = int(body_sel.css('div.voting span.score ::text').extract_first().replace(u'\u2013', '-'))
                message_html = element_html_content(body_sel.css('div.message'))

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

                if username is not None:
                    users_participated.add(username)

            extracted_comments.append(comment)

        return extracted_comments, commenter_urls

    comments, commenter_urls = extract_comments(comments_sel)

    return {
        'blog_id': blog_id,
        'post_id': int(post_id),

        'url': url,
        'title': post_title,
        'published': post_published,
        'flags': flags,
        'hubs': hubs,
        'company_blog': company_blog,
        'content_html': content_html,
        'tags': tags,
        'pageviews': pageviews,
        'favs_count': favs_count,
        'voting_score': voting_score,

        'author_company': author_company,
        'author_user': author_user,

        'users_participated': list(users_participated),

        'comments_count': comments_count,
        'comments': comments,
    }


def parse_company_profile(response):
    url = extract_canonical_url(response)
    blog_id = extract_blog_id(url)
    company_id = extract_company_id(url)

    company_header = response.css('div.company_header')
    if len(company_header) == 0:
        return

    icon_url = company_header.css('div.company_icon > img ::attr(src)').extract_first()
    icon_url = urlparse.urljoin(response.url, icon_url)

    name = company_header.css('div.name > a ::text').extract_first()

    company_profile = response.css('div.company_profile')

    company_about_html = None
    company_website = None
    company_registration_date = None
    company_staff = []
    company_info = {}

    for dl_element in company_profile.css('dl'):
        key = dl_element.css('dt ::text').extract_first()
        if key is None:
            continue
        key = key.strip().rstrip(':')
        value = dl_element.css('dd ::text').extract_first().strip()
        value_html = element_html_content(dl_element.css('dd'))

        if key == u'О компании':
            company_about_html = value_html
        elif key == u'Сайт':
            company_website = dl_element.css('dd > a ::attr(href)').extract_first()
        elif key.startswith(u'Сотрудники на'):
            company_staff = dl_element.css('dd ul.users > li > a ::text').extract()
        elif key.startswith(u'Дата') and key.endswith(u'регистрации'):
            company_registration_date = parse_habr_datetime(value)
        else:
            company_info[key] = value_html

    return {
        'blog_id': blog_id,
        'company_id': company_id,

        'name': name,
        'icon_url': icon_url,
        'about_html': company_about_html,
        'website_url': company_website,
        'registration_date': company_registration_date,
        'staff_users': company_staff,

        'info': [
            {'key': key, 'value': value}
            for key, value in company_info.iteritems()
        ],
    }


def parse_user_profile(response):
    url = extract_canonical_url(response)
    blog_id = extract_blog_id(url)
    user_id = extract_user_id(url)

    user_header = response.css('div.user_header')
    if len(user_header) == 0:
        return

    avatar_url = user_header.css('a.avatar > img ::attr(src)').extract_first()
    avatar_url = urlparse.urljoin(url, avatar_url)

    username = user_header.css('h2.username > a ::text').extract_first().strip()

    karma = user_header.css('div.karma div.num ::text').extract_first()
    try:
        karma = float(karma.replace(',', '.'))
    except:
        karma = None

    rating = user_header.css('div.rating div.num ::text').extract_first()
    try:
        rating = float(rating.replace(',', '.'))
    except:
        rating = None

    user_profile = response.css('div.user_profile')

    fullname = user_profile.css('div.fullname ::text').extract_first().strip()

    user_about_html = None
    user_website = None
    user_registration_date = None
    user_last_activity = None

    user_info = {}
    user_working_companies = []
    user_favorite_companies = []
    user_hubs = []
    user_invites = []
    user_tags = []

    def parse_list_of_ids(dl_element, id_extractor):
        result = []
        for item_el in dl_element.css('dd > ul > li'):
            try:
                id = id_extractor(item_el.css('a ::attr(href)').extract_first())
                if id is not None:
                    result.append(id)
            except:
                pass
        return result

    for dl_element in user_profile.css('dl'):
        key = dl_element.css('dt ::text').extract_first()
        if key is None:
            continue
        el_id = dl_element.css('::attr(id)').extract_first()
        key = key.strip().rstrip(':')
        value = dl_element.css('dd ::text').extract_first().strip()
        value_html = element_html_content(dl_element.css('dd'))

        if key == u'О себе':
            user_about_html = value_html
        elif key == u'Сайт':
            user_website = dl_element.css('dd > a ::attr(href)').extract_first()
        elif key == u'Зарегистрирован':
            invite_str_start = value.find(u'по приглашению')
            if invite_str_start > 0:
                value = value[:invite_str_start]
            user_registration_date = parse_habr_datetime(value)
        elif key == u'Активность':
            user_last_activity = parse_habr_datetime(
                re.sub(u'Последний[^\d]*на сайте', '', value).strip()
            )
        elif el_id == 'working_in':
            user_working_companies = parse_list_of_ids(dl_element, extract_company_id)
        elif el_id == 'favorite_companies_list':
            user_favorite_companies = parse_list_of_ids(dl_element, extract_company_id)
        elif key == u'Состоит в':
            user_hubs = parse_list_of_ids(dl_element, extract_hub_id)
        elif key.startswith(u'Пригласил на'):
            user_invites = parse_list_of_ids(dl_element, extract_user_id)
        elif key == u'Интересы':
            user_tags = dl_element.css('dd > a ::text').extract()
        else:
            user_info[key] = value_html

    return {
        'blog_id': blog_id,
        'user_id': user_id,

        'username': username,
        'fullname': fullname,
        'avatar_url': avatar_url,

        'registration_date': user_registration_date,
        'last_activity': user_last_activity,

        'karma': karma,
        'rating': rating,

        'about_html': user_about_html,
        'website_url': user_website,

        'working_companies': user_working_companies,
        'favorite_companies': user_favorite_companies,
        'hubs': user_hubs,
        'tags': user_tags,
        'invites': user_invites,

        'info': [
            {'key': key, 'value': value}
            for key, value in user_info.iteritems()
        ],
    }

