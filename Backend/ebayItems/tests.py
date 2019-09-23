"""
    This module is implementing test cases for ebayItems app
"""

import datetime
import requests

import pandas as pd

from django.db.models import Q
from django.db import connection
from django.forms.models import model_to_dict
from django.test import TestCase
from django.utils.timezone import get_current_timezone

from .models import EbayItem, BWStageEnum
from .tables import EbayItemTable
from . import tasks


class TasksDBRelatedTestCase(TestCase):
    """
        Test for database related function in tasks
    """
    def setUp(self) -> None:
        """
        Setup
        :return: None
        """
        ebay_items = pd.DataFrame(data={
            'ItemNo': [10027587, 10027587, 10026400],
            'eBayItemID': ['32908', '34572', '32410'],
            'AuctionID': ['121497332358', '361127495438', '121853803976'],
            'SKU': ['10027587;0', '10027587;0', '10026400;0'],
            'ItemDescription': ['Klarstein Biggie Einkochtopf 27 l',
                                'Klarstein Biggie Einkochtopf 27 l',
                                'Klarfit Cycloony MiniBike Motor 120kg schwarz/oran'],
            'SalesGoalReachedInLast14Days': [78.89, 78.89, 132.81],
            'SalesGoalReachedInLast7Days': [100.21, 100.21, 74.04],
            'FC_Erf_MTD': [20.05, 30.05, 40.05],
            'Channel': ['ebay', 'ebay', 'ebay'],
            'Country': ['DE', 'DE', 'DE'],
            'OurPurchasePrice': [46.53, 46.53, 40.22],
            'CurrentSalePrice': [99.99, 99.99, 109.99],
            'SuggestedSalePrice': [69.99, 69.99, 76.99],
            'DIO1': [24, 24, 6],
            'DIO2': [67, 67, 26],
            'Bestand_Gesamt': [113, 113, 24],
            'LRW': [195, 195, 147],
            'FC': [115, 115, 50],
            'PositionCurrentDay': [501, 501, 501],
            'ItemStatus': ['BW_STAGE0', 'BW_STAGE2', 'NORMAL'],
            'COGS24HVS7D': [20, 20, 20]
        })
        for _, row in ebay_items.iterrows():
            EbayItem.objects.create(
                item_no=row['ItemNo'],
                item_id=row['eBayItemID'],
                auction_id=row['AuctionID'],
                sku=row['SKU'],
                item_description=row['ItemDescription'],
                sales_goal_reached_in_last14days=row['SalesGoalReachedInLast14Days'],
                sales_goal_reached_in_last7days=row['SalesGoalReachedInLast7Days'],
                sales_goal_reached_mtd=row['FC_Erf_MTD'],
                channel=row['Channel'],
                country=row['Country'],
                our_purchase_price=row['OurPurchasePrice'],
                current_sale_price=row['CurrentSalePrice'],
                suggested_sale_price=row['SuggestedSalePrice'],
                last_humansetprice_before_badewanne=row['CurrentSalePrice'],
                new_price=row['CurrentSalePrice'],
                dio1=row['DIO1'],
                dio2=row['DIO2'],
                stock=row['Bestand_Gesamt'],
                lrw=row['LRW'],
                fc=row['FC'],
                cogs_24h_vs_7d=row['COGS24HVS7D'],
                item_ranking_today=row['PositionCurrentDay'],
                item_status=row['ItemStatus']
            )
        # data from BIServer
        self.ebay_item_daily = pd.DataFrame(data={
            'ItemNo': [10027587, 10027587, 10026400, 10026500],
            'eBayItemID': ['32908', '34572', '32410', '32410'],
            'AuctionID': ['121497332358', '361127495438', '121853803976', '121853803977'],
            'SKU': ['10027587;0', '10027587;0', '10026400;0', '10026400;0'],
            'ItemDescription': ['Klarstein Biggie Einkochtopf 27 l',
                                'Klarstein Biggie Einkochtopf 27 l',
                                'Klarfit Cycloony MiniBike Motor 120kg schwarz/oran',
                                'Klarfit Cycloony MiniBike Motor 120kg schwarz/oran'],
            'SalesGoalReachedInLast14Days': [178.89, 78.89, 132.81, 132.81],
            'SalesGoalReachedInLast7Days': [1100.21, 100.21, 74.04, 74.04],
            'FC_Erf_MTD': [120.05, 130.05, 140.05, 140.05],
            'Channel': ['ebay', 'ebay', 'ebay', 'ebay'],
            'Country': ['FR', 'DE', 'DE', 'DE'],
            'OurPurchasePrice': [146.53, 246.53, 40.22, 40.22],
            'CurrentSalePrice': [199.99, 299.99, 109.99, 109.99],
            'SuggestedSalePrice': [169.99, 269.99, 76.99, 76.99],
            'DIO1': [124, 224, 6, 6],
            'DIO2': [167, 267, 26, 26],
            'Bestand_Gesamt': [1113, 1113, 24, 24],
            'LRW': [1195, 3195, 147, 147],
            'FC': [1115, 2115, 50, 50],
            'PositionCurrentDay': [1, 10, 501, 501],
            'ItemStatus': ['BW_STAGE0', 'BW_STAGE2', 'NORMAL', 'NORMAL'],
            'COGS24HVS7D': [20, 20, 20, 20]
        })

    def test_update_or_create_ebay_items(self) -> None:
        """
        Test tasks function update_or_create_ebay_items
        :return: None
        """
        query = str(EbayItem.objects.all().values(
            'id', 'item_no', 'auction_id', 'item_status'
        ).query)
        ebay_price_old = pd.read_sql_query(query, connection)
        tasks.update_or_create_ebay_items(self.ebay_item_daily, ebay_price_old)
        query = str(EbayItem.objects.all().values(
            'item_no',
            'item_id',
            'auction_id',
            'sku',
            'item_description',
            'sales_goal_reached_in_last14days',
            'sales_goal_reached_in_last7days',
            'sales_goal_reached_mtd',
            'channel',
            'country',
            'our_purchase_price',
            'current_sale_price',
            'suggested_sale_price',
            'dio1',
            'dio2',
            'stock',
            'lrw',
            'fc',
            'item_ranking_today',
            'item_status',
            'cogs_24h_vs_7d',
        ).query)
        ebay_price_old_updated = pd.read_sql_query(query, connection)
        self.assertEqual(
            ebay_price_old_updated.values.tolist(),
            self.ebay_item_daily.values.tolist(),
            "The updated ebayitem table equals to BIServer"
        )

    def test_get_all_django_exist_items(self) -> None:
        """
            test function get_all_django_exist_items
        :return: None
        """
        ebay_django = tasks.get_all_django_exist_items()
        self.assertIsInstance(
            ebay_django,
            pd.DataFrame
        )
        self.assertEqual(
            ebay_django.columns.to_list(),
            ['id', 'ItemNo', 'AuctionID', 'ItemStatus']
        )
        self.assertEqual(
            ebay_django[['ItemNo', 'AuctionID', 'ItemStatus']].loc[0].to_list(),
            [10027587, '121497332358', 'BW_STAGE0']
        )


def create_ebayitem(item_no=10029331, item_id='3190685',
                    auction_id='282846089528', sku='10029331;0',
                    item_description='Klarstein Monroe Black Kühl- & Gefrierkombination',
                    sales_goal_reached_in_last14days=75.65,
                    sales_goal_reached_in_last7days=64.55,
                    sales_goal_reached_mtd=81.56, cogs_24h_vs_7d=18.44,
                    channel='ebay', country='DE', stock=184, lrw=286,
                    fc=45, item_ranking_today=377, our_purchase_price=106.21,
                    current_sale_price=239.99, suggested_sale_price=167.99,
                    last_humansetprice_before_badewanne=249.99, new_price=224.99, dio1=158,
                    dio2=146, item_status=BWStageEnum.NORMAL.value,
                    last_bw_end_date=datetime.datetime.now(tz=get_current_timezone()),
                    last_bw_start_date=datetime.datetime.now(tz=get_current_timezone())):
    """
        Create an EbayItem object
    :param item_no:
    :param item_id:
    :param auction_id:
    :param sku:
    :param item_description:
    :param sales_goal_reached_in_last14days:
    :param sales_goal_reached_in_last7days:
    :param sales_goal_reached_mtd:
    :param cogs_24h_vs_7d:
    :param channel:
    :param country:
    :param stock:
    :param lrw:
    :param fc:
    :param item_ranking_today:
    :param our_purchase_price:
    :param current_sale_price:
    :param suggested_sale_price:
    :param last_humansetprice_before_badewanne:
    :param new_price:
    :param dio1:
    :param dio2:
    :param item_status:
    :param last_bw_end_date:
    :param last_bw_start_date:
    :return: EbayItem object
    """
    return EbayItem.objects.create(
        item_no=item_no, item_id=item_id, auction_id=auction_id, sku=sku,
        item_description=item_description,
        sales_goal_reached_in_last7days=sales_goal_reached_in_last7days,
        sales_goal_reached_in_last14days=sales_goal_reached_in_last14days,
        sales_goal_reached_mtd=sales_goal_reached_mtd,
        cogs_24h_vs_7d=cogs_24h_vs_7d, channel=channel, country=country,
        stock=stock, lrw=lrw, fc=fc, item_ranking_today=item_ranking_today,
        our_purchase_price=our_purchase_price, current_sale_price=current_sale_price,
        suggested_sale_price=suggested_sale_price,
        last_humansetprice_before_badewanne=last_humansetprice_before_badewanne,
        new_price=new_price, dio1=dio1, dio2=dio2,
        item_status=item_status, last_bw_end_date=last_bw_end_date,
        last_bw_start_date=last_bw_start_date
    )

class TestTablesCase(TestCase):
    """
        Test the class methods in tables.py
    """

    def test_render_values(self) -> None:
        """
            Test function render_values
        :return: None
        """
        table = EbayItemTable(create_ebayitem().__dict__)
        self.assertEqual(table.render_percent(value=64.55), '64.55%')
        self.assertEqual(table.render_sales_goal_reached_in_last7days(value=60.89), '60.89%')
        self.assertEqual(table.render_sales_goal_reached_in_last14days(value=60.89), '60.89%')
        self.assertEqual(table.render_cogs_24h_vs_7d(value=0.35), '0.35%')
        self.assertEqual(table.render_sales_goal_reached_mtd(value=0.55), '0.55%')

class TestTasksMaintainListCase(TestCase):
    """
        Test functions in tasks which maintain various item lists
    """
    def test_maintain_bwready_list(self) -> None:
        """
            Test function maintain_bwready_list
        :return: None
        """
        create_ebayitem(sales_goal_reached_in_last7days=90,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100)
        create_ebayitem(sales_goal_reached_in_last7days=110,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100)
        create_ebayitem(sales_goal_reached_in_last7days=90,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100,
                        item_status=BWStageEnum.BW_STAGE1_30D.value)
        tasks.maintain_bwready_list()
        self.assertEqual(
            list(EbayItem.objects.all().values('item_status')),
            [
                {'item_status': 'BW_READY'},
                {'item_status': 'NORMAL'},
                {'item_status': 'BW_STAGE1_30D'}
            ]
        )

    def test_maintain_normal_list(self) -> None:
        """
            Test function maintain_normal_list
        :return: None
        """
        create_ebayitem(last_bw_end_date=datetime.datetime.now(tz=get_current_timezone()) -
                        datetime.timedelta(days=31),
                        item_status=BWStageEnum.BW_BLOCKED.value)
        create_ebayitem(lrw=51, item_status=BWStageEnum.LRW_LIST.value)
        create_ebayitem(sales_goal_reached_in_last7days=90,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100,
                        item_status=BWStageEnum.BW_READY.value)
        create_ebayitem(sales_goal_reached_in_last7days=100,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100,
                        item_status=BWStageEnum.BW_READY.value)
        tasks.maintain_normal_list()
        self.assertEqual(
            list(EbayItem.objects.all().values('item_status')),
            [
                {'item_status': 'NORMAL'},
                {'item_status': 'NORMAL'},
                {'item_status': 'BW_READY'},
                {'item_status': 'NORMAL'}
            ]
        )

    def test_maintain_blocked_list(self) -> None:
        """
            Test function maintain_blocked_list
        :return: None
        """
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                        last_bw_start_date=datetime.datetime.now(tz=get_current_timezone()) -
                        datetime.timedelta(days=31))
        create_ebayitem(item_status=BWStageEnum.BW_READY.value,
                        last_bw_start_date=datetime.datetime.now(tz=get_current_timezone()) -
                        datetime.timedelta(days=31))
        create_ebayitem(item_status=BWStageEnum.BW_TOBLOCK.value)
        create_ebayitem(item_status=BWStageEnum.NORMAL.value)
        tasks.maintain_blocked_list()
        self.assertEqual(
            list(EbayItem.objects.all().values('item_status')),
            [
                {'item_status': 'BW_BLOCKED'},
                {'item_status': 'BW_READY'},
                {'item_status': 'BW_BLOCKED'},
                {'item_status': 'NORMAL'},
            ]
        )

    def test_maintain_lrw_list(self) -> None:
        """
            Test function maintain_lrw_list
        :return: None
        """
        create_ebayitem(item_status=BWStageEnum.NORMAL.value, lrw=49)
        create_ebayitem(item_status=BWStageEnum.NORMAL.value, lrw=51)
        create_ebayitem(item_status=BWStageEnum.BW_READY.value, lrw=49)
        tasks.maintain_lrw_list()
        self.assertEqual(
            list(EbayItem.objects.all().values('item_status')),
            [
                {'item_status': 'LRW_LIST'},
                {'item_status': 'NORMAL'},
                {'item_status': 'BW_READY'},
            ]
        )

    def test_sync_items_status(self) -> None:
        """
            Test function sync_items_status
        :return: None
        """
        create_ebayitem(item_status=BWStageEnum.NORMAL.value, lrw=49)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                        last_bw_start_date=datetime.datetime.now(tz=get_current_timezone()) -
                        datetime.timedelta(days=31))
        create_ebayitem(last_bw_end_date=datetime.datetime.now(tz=get_current_timezone()) -
                        datetime.timedelta(days=31),
                        item_status=BWStageEnum.BW_BLOCKED.value, fc=14)
        create_ebayitem(sales_goal_reached_in_last7days=90,
                        sales_goal_reached_in_last14days=90,
                        sales_goal_reached_mtd=90, lrw=60,
                        stock=200, fc=20, item_ranking_today=100)
        tasks.sync_items_status()
        self.assertEqual(
            list(EbayItem.objects.all().values('item_status')),
            [
                {'item_status': 'LRW_LIST'},
                {'item_status': 'BW_BLOCKED'},
                {'item_status': 'NORMAL'},
                {'item_status': 'BW_READY'},
            ]
        )


class TestTasksItemFilteringCase(TestCase):
    """
        Test functions in tasks which filters items based on various rules
    """

    def test_items_price_decrease_20percent(self) -> None:
        """
            Test function items_price_decrease_20percent
        :return: None
        """
        # Fulfills rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                        cogs_24h_vs_7d=29, item_ranking_today=49,
                        sales_goal_reached_in_last7days=89)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        cogs_24h_vs_7d=29, item_ranking_today=49,
                        sales_goal_reached_in_last7days=88)
        # Not fulfills rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        cogs_24h_vs_7d=29, item_ranking_today=51,
                        sales_goal_reached_in_last7days=87)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE2_20D.value,
                        cogs_24h_vs_7d=29, item_ranking_today=49,
                        sales_goal_reached_in_last7days=86)
        ids = list(EbayItem.objects.filter(
            item_status=BWStageEnum.BW_STAGE0.value
        ).values_list('id', flat=True))
        items = tasks.items_price_decrease_20percent(90, ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days=88))
        )
        items = tasks.items_price_decrease_20percent(90)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days__in=[89, 88]))
        )

    def test_items_price_decrease_10percent(self) -> None:
        """
            Test function items_price_decrease_10percent
        :return: None
        """
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE2_20D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last7days=101)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last7days=102)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last7days=103)
        # Not Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last7days=99)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE3_10D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last7days=104)
        ids = list(EbayItem.objects.filter(
            item_status=BWStageEnum.BW_STAGE0.value
        ).values_list('id', flat=True))
        items = tasks.items_price_decrease_10percent(100, ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days=103))
        )
        items = tasks.items_price_decrease_10percent(100)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days__in=[101, 102, 103]))
        )

    def test_items_price_decrease_0percent(self) -> None:
        """
            Test function items_price_decrease_0percen
        :return: None
        """
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE3_10D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=100)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE2_20D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=101)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=102)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=103)
        # Not Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=89)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE5_5I.value, cogs_24h_vs_7d=39,
                        item_ranking_today=21, sales_goal_reached_in_last14days=104)
        ids = list(EbayItem.objects.filter(
            item_status=BWStageEnum.BW_STAGE0.value
        ).values_list('id', flat=True))
        items = tasks.items_price_decrease_0percent(90, ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last14days=103))
        )
        items = tasks.items_price_decrease_0percent(90)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last14days__in=[100, 101, 102, 103]))
        )

    def test_items_price_increase_5percent(self) -> None:
        """
            Test function items_price_increase_5percent
        :return: None
        """
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE4_0D.value,
                        sales_goal_reached_in_last7days=111)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE3_10D.value,
                        sales_goal_reached_in_last7days=112)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE2_20D.value,
                        sales_goal_reached_in_last7days=113)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                        sales_goal_reached_in_last7days=114)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        sales_goal_reached_in_last7days=115)
        # Not Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        sales_goal_reached_in_last7days=109)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE5_5I.value,
                        sales_goal_reached_in_last7days=116)
        ids = list(EbayItem.objects.filter(
            item_status=BWStageEnum.BW_STAGE0.value
        ).values_list('id', flat=True))
        items = tasks.items_price_increase_5percent(ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days=115))
        )
        items = tasks.items_price_increase_5percent()
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(
                Q(sales_goal_reached_in_last7days__gt=110) &
                Q(sales_goal_reached_in_last7days__lt=116)
            ))
        )

    def test_items_price_increase_10percent(self) -> None:
        """
            Test function items_price_increase_10percent
        :return: None
        """
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE5_5I.value,
                        sales_goal_reached_in_last7days=121)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE4_0D.value,
                        sales_goal_reached_in_last7days=122)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE3_10D.value,
                        sales_goal_reached_in_last7days=123)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE2_20D.value,
                        sales_goal_reached_in_last7days=124)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                        sales_goal_reached_in_last7days=125)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        sales_goal_reached_in_last7days=126)
        # Not Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                        sales_goal_reached_in_last7days=119)
        create_ebayitem(item_status=BWStageEnum.BW_STAGE6_10I.value,
                        sales_goal_reached_in_last7days=127)
        ids = list(EbayItem.objects.filter(
            item_status=BWStageEnum.BW_STAGE0.value
        ).values_list('id', flat=True))
        items = tasks.items_price_increase_10percent(ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(sales_goal_reached_in_last7days=126))
        )
        items = tasks.items_price_increase_10percent()
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(
                Q(sales_goal_reached_in_last7days__gt=120) &
                Q(sales_goal_reached_in_last7days__lt=127)
            ))
        )

    def test_items_to_blocked(self) -> None:
        """
            Test function items_to_blocked
        :return: None
        """
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_TOBLOCK.value,
                        stock=121, fc=15)
        create_ebayitem(item_status=BWStageEnum.BW_TOBLOCK.value,
                        stock=122, fc=16)
        # Fulfill filter rules
        create_ebayitem(item_status=BWStageEnum.BW_STAGE6_10I.value,
                        stock=122, fc=17)
        ids = list(EbayItem.objects.filter(stock=122).values_list('id', flat=True))
        items = tasks.items_to_blocked(ids)
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(fc=16))
        )
        items = tasks.items_to_blocked()
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(fc__in=[15, 16]))
        )


class TestTaskPriceChaningAPIRelatedCase(TestCase):
    """
        Test functions in tasks which are related to ebay pricing
        changing api
    """

    def test_prepare_pricing_api_data(self) -> None:
        """
        Test function prepare_pricing_api_data
        :return: None
        """
        item_stage0 = create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                                      current_sale_price=100.00,
                                      last_humansetprice_before_badewanne=90.00,
                                      our_purchase_price=30.00,
                                      new_price=0.00)
        item_stage1 = create_ebayitem(item_status=BWStageEnum.BW_STAGE1_30D.value,
                                      current_sale_price=63.00,
                                      last_humansetprice_before_badewanne=90.00,
                                      our_purchase_price=30.00,
                                      new_price=63.00)
        batch_price_data, items = tasks.prepare_pricing_api_data(
            [item_stage0],
            0.3,
            'EBay_Badewanne_Auto_Start_BW_STAGE1'
        )
        self.assertEqual(
            batch_price_data,
            [{
                "Price": 69.99,
                "ListingId": item_stage0.auction_id,
                "SKU": item_stage0.sku,
                "Reason": 'EBay_Badewanne_Auto_Start_BW_STAGE1'
            }]
        )
        self.assertEqual(
            model_to_dict(items[0], fields=[
                'current_sale_price',
                'last_humansetprice_before_badewanne',
                'new_price'
            ]),
            {
                'current_sale_price': 69.99,
                'last_humansetprice_before_badewanne': 100.00,
                'new_price': 69.99
            }
        )

        batch_price_data, items = tasks.prepare_pricing_api_data(
            [item_stage1],
            0.2,
            'EBay_Badewanne_Auto_Start_BW_STAGE2'
        )

        self.assertEqual(
            batch_price_data,
            [{
                "Price": 72.99,
                "ListingId": item_stage1.auction_id,
                "SKU": item_stage1.sku,
                "Reason": 'EBay_Badewanne_Auto_Start_BW_STAGE2'
            }]
        )

        self.assertEqual(
            model_to_dict(items[0], fields=[
                'current_sale_price',
                'last_humansetprice_before_badewanne',
                'new_price'
            ]),
            {
                'current_sale_price': 72.99,
                'last_humansetprice_before_badewanne': 90.00,
                'new_price': 72.99
            }
        )

    def test_get_price_changing_success_items(self) -> None:
        """
        Test function get_price_changing_success_items
        :return: None
        """
        stage0_item1 = create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                                       current_sale_price=100.00,
                                       last_humansetprice_before_badewanne=90.00,
                                       new_price=0.00, auction_id='100101102')
        stage0_item2 = create_ebayitem(item_status=BWStageEnum.BW_STAGE0.value,
                                       current_sale_price=200.00,
                                       last_humansetprice_before_badewanne=90.00,
                                       new_price=0.00, auction_id='100101101')
        response = requests.models.Response()
        response._content = b'{"HasErrors": true, "Results":' \
                            b'[{"IsSuccessful": true, "Message": "sample string 2"}, ' \
                            b'{"IsSuccessful": false, "Message": "sample string 2"}]}'
        items = tasks.get_price_changing_success_items(response, [stage0_item1, stage0_item2])
        self.assertEqual(
            list(items),
            list(EbayItem.objects.filter(auction_id='100101102'))
        )

        response = requests.models.Response()
        response._content = b'{"HasErrors": false, "Results":' \
                            b'[{"IsSuccessful": true, "Message": "sample string 2"}, ' \
                            b'{"IsSuccessful": true, "Message": "sample string 2"}]}'
        items = tasks.get_price_changing_success_items(response, [stage0_item1, stage0_item2])
        self.assertEqual(
            list(items),
            list(EbayItem.objects.all())
        )

class TestTasksUtilCase(TestCase):
    """
        Test utility functions in tasks.
    """

    def test_get_smart_price_number(self) -> None:
        """
        Test function get_smart_price_number
        :return: None
        """
        self.assertEqual(
            tasks.get_smart_price_number(119, 59.99, 0.3),
            83.99
        )
        self.assertEqual(
            tasks.get_smart_price_number(83.99, 59.59, 0.3),
            68.99
        )
        self.assertEqual(
            tasks.get_smart_price_number(100, 29.59, 0.3),
            69.99
        )
        self.assertEqual(
            tasks.get_smart_price_number(12.99, 3.59, 0.3),
            9.49
        )
        self.assertEqual(
            tasks.get_smart_price_number(9.99, 3.59, 0.3),
            6.99
        )
