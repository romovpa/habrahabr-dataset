habrahabr-dataset
=================

Dataset collected from popular Russian collective blogs [Habrahabr](http://habrahabr.ru/),
[Geektimes](http://geektimes.ru/) and [Megamozg](http://megamozg.ru/) owned by [TM](http://tmtm.ru/).

[Data Archives](https://yadi.sk/d/b13MG_XGfxVBp)

## Data format

#### `habr_posts/<post_id>`

```json
{
    "_id": 115710,
    "_last_update": "2015-04-08T00:00:00",
    "title": "Собираем данные с помощью Scrapy",
    "published": "2011-03-18T23:13:00",
    "author": "bekbulatov",
    "author_url": "http://habrahabr.ru/users/bekbulatov/",
    "author_rating": 3.8,
    "hubs": [["Python", "http://habrahabr.ru/hub/python/"]],
    "favs_count": 315,
    "pageviews": 21281,
    "tags": ["scrapy", "парсинг", "python", "crawler"],
    "comments_count": 49,
    "content_html": "..."
}
```

#### `posts.csv`

Summary table about all posts from the dataset in CSV format. Encoding is UTF-8.

Columns:
 - post_id
 - last_update
 - published
 - title
 - author
 - favs_count
 - pageviews
 - comments_count
 - comments_parsed
 - comments_banned
 - first_comment_time
 - last_comment_time
 - author_comments
 - tags
 - content_length
 - hubs_count
 - hubs

## How to create dataset

Use script `download_all_habr.py` to fetch and parse all the pages available now. Habrahabr posts are
indexed with continuous integer numbers from 1 to about 300000. You should specify the range of indices to download.
If you want to distribute your download across several machines, just specify them different pieces of the whole range.

```bash
$ python download_all_habr.py --start-index 1 --finish-index 300000
```

Script will create the directory `habr_pages` and download post contents there.

