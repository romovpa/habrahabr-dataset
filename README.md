habrahabr-dataset
=================

Dataset collected from popular Russian collective blogs [Habrahabr](http://habrahabr.ru/),
[Geektimes](http://geektimes.ru/) and [Megamozg](http://megamozg.ru/) owned by [TM](http://tmtm.ru/).


## Data format

#### `habr_pages/<page_id>.json`

Parsed contents of the post.

```json
{
    "pageviews": 5046,
    "author": "geraxe",
    "author_rating": 6.8,
    "title": "...",
    ...
}
```

#### `posts.csv`

Summary table about all the posts from the dataset in CSV format. Encoding is UTF-8. Here are the first lines:

```
| PostId | Count | Title |
```

## Exploration of the dataset

Some experiments and visualizations.

To be done...

## How to create dataset

Use script `download_all_habr.py` to fetch and parse all the pages available now. Habrahabr posts are
indexed with continuous integer numbers from 1 to about 300000. You should specify the range of indices to download.
If you want to distribute your download across several machines, just specify them different pieces of the whole range.

```bash
$ python download_all_habr.py --start-index 1 --finish-index 300000
```

Script will create the directory `habr_pages` and download post contents there.

## Distributed downloading of the content with AWS

To be done...
