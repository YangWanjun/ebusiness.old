# coding: UTF-8
"""
Created on 2016/01/12

@author: Yang Wanjun
"""
import logging

from .base_batch import BaseBatch
from eb import biz_batch
from utils import constants

logger = logging.getLogger(__name__)


class Command(BaseBatch):
    BATCH_NAME = constants.BATCH_SYNC_MEMBERS
    BATCH_TITLE = u"社員導入バッチ"
    MAIL_TITLE = u"【営業支援システム】社員導入"

    def handle(self, *args, **options):
        username = options.get('username')

        logger.info(u"バッチ実行開始。username: %s" % username)
        # count = biz_batch.sync_members(self.batch)
        biz_batch.sync_members_for_change(self.batch)
        logger.info(u"バッチ実行終了。username: %s" % username)
