# -*- coding: utf-8 -*-

import pymongo

from scrapy.conf import settings


class MongoExportPipeline(object):
    def __init__(self):
        connection = pymongo.MongoClient(
            settings['MONGODB_ADDR'],
        )
        self.db = connection[settings['MONGODB_DB']]

    def process_item(self, item, spider):
        item_type = item.pop('_type')
        item_id = item.pop('_id')

        self.db[item_type].replace_one({'_id': item_id}, item, upsert=True)
        return item
