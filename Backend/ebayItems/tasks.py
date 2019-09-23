"""
The task module define tasks which need to be run repeatedly in background.
This module will responsible for sync ebay item data from BIServer in the
Background and periodically. The item price changing is also done in background
and can be scheduled, which improve the front user experience and organize the
task in more manageable way.
"""
import datetime
import json
import logging
import math
from typing import List, Tuple
import requests
import numpy as np
import pymssql
import pandas as pd

from background_task import background
from django.db.models import Q, query
from django.db import connection
from django.utils.timezone import get_current_timezone

from .models import EbayItem, BWStageEnum

LOGGER = logging.getLogger(__name__)


@background()
def ebay_badewanne_update() -> None:
    """
    Background task which scheduled in every certain point of time.
    First to sync the data from BIServer, then update all the items
    in Badewanne.
    :return:  None
    """
    sync_eaby_item()
    sync_items_status()
    badewanne_process_tracking.now()


def sync_eaby_item() -> None:
    """
    Sync ebayitem table to vFactEbayPrices from BIServer.
    :return: None
    """
    ebay_price_daily = get_data_from_biserver()
    ebay_price_old = get_all_django_exist_items()
    update_or_create_ebay_items(ebay_price_daily, ebay_price_old)


def get_all_django_exist_items() -> pd.DataFrame:
    """
    Get items exist in django web system database
    :return: item data in pandas dataframe
    """
    sql_query = str(EbayItem.objects.all().values(
        'id', 'item_no', 'auction_id', 'item_status'
    ).query)
    ebay_price_old = pd.read_sql_query(sql_query, connection)
    return ebay_price_old


def get_data_from_biserver() -> pd.DataFrame:
    """
    Get the latest data from vFactEbayPrices in BIServer
    :return: item data in pandas dataframe
    """
    LOGGER.info("Connecting to BIServer")
    conn = pymssql.connect(
        server='BIServer.chal-tec.local',
        user=r'chal-tec\PricingMaster',
        password='2Xy5Lq,P9Sz;QE=lV%X!T0tD~3H67-8.',
        database='CT dwh 04 Analysis'
    )

    ebay_price_daily = pd.read_sql(
        sql="SELECT * from vFactEbayPrices;",
        con=conn,
        index_col='id'
    )
    ebay_price_daily.dropna(inplace=True)
    LOGGER.info("Num of rows from BIServer: %s", ebay_price_daily.shape)
    return ebay_price_daily


def update_or_create_ebay_items(items_new: pd.DataFrame, items_old: pd.DataFrame) -> None:
    """
    Insert the new ebay item info into db, update ebay
    item info if already exist in db
    :param items_new: pandas dataframe of ebay item info from BIServer
    :param items_old: pandas dataframe of ebay item existed in django model table
    :return: None
    """
    batch_insert = []
    batch_update = []
    is_baygraph_rank_down = np.array_equal(
        items_new['PositionCurrentDay'].unique(),
        np.array([501])
    )
    LOGGER.info("Checking rows to be inserted or updated")
    for _, row in items_new.iterrows():
        item = EbayItem(
            item_no=row['ItemNo'],
            item_id=row['eBayItemID'],
            item_description=row['ItemDescription'],
            sales_goal_reached_in_last14days=row['SalesGoalReachedInLast14Days'],
            sales_goal_reached_in_last7days=row['SalesGoalReachedInLast7Days'],
            sales_goal_reached_mtd=row['FC_Erf_MTD'],
            cogs_24h_vs_7d=row['COGS24HVS7D'],
            channel=row['Channel'],
            country=row['Country'],
            our_purchase_price=row['OurPurchasePrice'],
            current_sale_price=row['CurrentSalePrice'],
            suggested_sale_price=row['SuggestedSalePrice'],
            last_humansetprice_before_badewanne=row['CurrentSalePrice'],
            new_price=row['CurrentSalePrice'],
            auction_id=row['AuctionID'],
            sku=row['SKU'],
            dio1=row['DIO1'],
            dio2=row['DIO2'],
            stock=row['Bestand_Gesamt'],
            lrw=row['LRW'],
            fc=row['FC'],
            item_ranking_today=row['PositionCurrentDay']
        )
        # Check if the row from BIServer already exists in ebayitem table
        search_item = items_old.loc[(items_old.ItemNo == item.item_no) &
                                    (items_old.AuctionID == item.auction_id)]
        if search_item.empty:
            item.last_humansetprice_before_badewanne = row['CurrentSalePrice']
            item.new_price = row['CurrentSalePrice']
            batch_insert.append(item)
        else:
            item.id = search_item.iloc[0].id
            batch_update.append(item)
    LOGGER.info('Insert %s new rows to db and update %s rows', len(batch_insert), len(batch_update))
    EbayItem.objects.bulk_create(batch_insert)
    update_cols = [
        'item_description', 'sales_goal_reached_in_last14days',
        'sales_goal_reached_in_last7days', 'sales_goal_reached_mtd', 'channel',
        'country', 'our_purchase_price', 'current_sale_price',
        'suggested_sale_price', 'dio1', 'dio2',
        'lrw', 'fc', 'stock', 'item_id', 'cogs_24h_vs_7d'
    ]
    if not is_baygraph_rank_down:
        update_cols.append('item_ranking_today')
    EbayItem.objects.bulk_update(batch_update, update_cols)
    LOGGER.info("Finish ebayitem db update")


def sync_items_status() -> None:
    """
    Maintain the items status based on their performance
    :return: None
    """
    maintain_lrw_list()
    maintain_blocked_list()
    maintain_normal_list()
    maintain_bwready_list()


@background()
def badewanne_process_tracking(ids: List = None) -> None:
    """
    Update item status and change price according to rules
    :param ids: List of item id, which are going to be
    forwarded various stage
    :return: None
    """
    LOGGER.info("Start badewanne process tracking.")

    # Threshold definition
    first_threshold = 90.0
    second_threshold = 100.0
    last_threshold = 90.0

    # Put manually selected items to blocked list
    items = items_to_blocked(ids)
    if items:
        LOGGER.info("%s BW_TOBLOCK items to be forwarded BW_BLOCKED.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_BLOCKED, 0.0)

    # increase 10 percent price for items with too great performance
    items = items_price_increase_10percent(ids)
    if items:
        LOGGER.info("%s items to be forwarded stage 6, "
                    "increase price 10%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE6_10I, -0.1)

    # increase 5 percent price for items with too good performance
    items = items_price_increase_5percent(ids)
    if items:
        LOGGER.info("%s items to be forwarded stage 5, "
                    "increase price 5%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE5_5I, -0.05)

    # decrease 0 percent price for items with stage4 performance
    items = items_price_decrease_0percent(last_threshold, ids)
    if items:
        LOGGER.info("%s items to be forwarded stage 4, "
                    "decrease price 0%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE4_0D, 0.0)

    # decrease 10 percent price for items with stage3 performance
    items = items_price_decrease_10percent(second_threshold, ids)
    if items:
        LOGGER.info("%s items to be forwarded stage 3, "
                    "decrease price 10%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE3_10D, 0.1)

    # decrease 20 percent price for items with stage2 performance
    items = items_price_decrease_20percent(first_threshold, ids)
    if items:
        LOGGER.info("%s items to be forwarded stage 2, "
                    "decrease price 20%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE2_20D, 0.2)

    # decrease 30 percent price for items with stage1 performance
    items = EbayItem.objects.filter(item_status=BWStageEnum.BW_STAGE0.value)
    if items:
        LOGGER.info("%s items to be forwarded stage 1, "
                    "decrease price 30%% wrt LastHumanSetPrice.",
                    items.values_list('id', flat=True))
        forward_badewanne_stage(list(items), BWStageEnum.BW_STAGE1_30D, 0.3)


def forward_badewanne_stage(items: List[EbayItem], target_stage: BWStageEnum,
                            discount: float) -> None:
    """
    Forward the badewanne stage for items, change price wrt discount
    of the last human set price for those items.
    :param items: Queryset of items which to be forwarded into target_stage
    :param target_stage: stage which the items should be forwarded
    :return: None
    """
    # get batch price data and updated item list for ebay batch pricing api
    batch_price_data, updated_items = prepare_pricing_api_data(
        items, discount,
        'EBay_Badewanne_Auto_Start_{}'.format(target_stage.value)
    )
    # get response of ebay pricing api call
    response = execute_ebay_batch_pricing_api(batch_price_data)
    # get items whose price changed successfully
    success_items = get_price_changing_success_items(response, updated_items)
    # update success items' item status
    success_items.update(item_status=target_stage.value)
    if target_stage == BWStageEnum.BW_BLOCKED:
        success_items.update(last_bw_end_date=datetime.datetime.now(tz=get_current_timezone()))


def prepare_pricing_api_data(items: List[EbayItem], discount: float,
                             price_change_reason: str) -> Tuple[List[dict], List[EbayItem]]:
    """
    Prepare the post data for ebay batch item pricing api
    :param items: list of EbayItem object
    :param discount: discount rate
    :param price_change_reason: reason for price changing
    :return: batch price data for pricing api
    """
    batch_price_data = []
    for item in items:
        if BWStageEnum(item.item_status) is BWStageEnum.BW_STAGE0:
            item.last_humansetprice_before_badewanne = item.current_sale_price
        item.new_price = get_smart_price_number(
            item.last_humansetprice_before_badewanne,
            item.our_purchase_price,
            discount
        )
        item.current_sale_price = item.new_price
        batch_price_data.append({
            "Price": item.new_price,
            "ListingId": item.auction_id,
            "SKU": item.sku,
            "Reason": price_change_reason
        })
    return batch_price_data, items


def get_smart_price_number(base_price: float, purchase_price: float,
                           discount: float) -> float:
    """
    Set price limit which make sure we are not losing money and round
    the price to be more customer friendly, like 9.99, 5.49, 25.99.
    :param base_price: base price for badewanne process
    :param purchase_price: price we pay for manufacture
    :param discount: discount value
    :return: smarter price
    """
    discount_price = base_price * (1 - discount)
    if discount_price < purchase_price * 1.15:
        discount_price = purchase_price * 1.15
    discount_price_integer = math.floor(discount_price)
    discount_price_decimal = discount_price - discount_price_integer
    if discount_price_integer > 20 or (discount_price_integer < 20
                                       and discount_price_decimal > 0.5):
        discount_price_decimal = 0.99
    else:
        discount_price_decimal = 0.49

    if discount_price_integer % 10 == 0:
        return discount_price_integer - 0.01
    else:
        return discount_price_integer + discount_price_decimal


def execute_ebay_batch_pricing_api(batch_price_data: List[dict]) -> requests.Response:
    """
    execute ebay pricing api with the batch price post data and get response
    :param batch_price_data: batch of items's price data
    :return: request response
    """
    response = requests.post(
        url="http://pricingapi.chal-tec.local/Ebay/EbayPrices",
        data=json.dumps({
            "BatchRequests": batch_price_data,
            "HaltOnError": False
        }),
        headers={
            'content-type': "application/json",
            'cache-control': "no-cache",
        }
    )
    return response


def get_price_changing_success_items(response: requests.Response,
                                     items: List[EbayItem]) -> query.QuerySet:
    """
    get the items whose prices has been changed successfully
    :param response: api response
    :param items: list of EbayItem items in the api call
    :return: return the queryset of the successful items
    """
    success_items = []
    failed_items = []
    if response.json()['HasErrors']:
        for indx, data in enumerate(response.json()['Results']):
            if data['IsSuccessful']:
                success_items.append(items[indx])
            else:
                failed_items.append(items[indx])
                LOGGER.info("Item %s changing price fails with the reason: %s",
                            items[indx],
                            data['Message'])
        LOGGER.info("Items whose price failed to be changed: %s",
                    [item.id for item in failed_items])
    else:
        success_items = items

    LOGGER.info("[%s/%s] items' prices have been changed successfully!",
                len(success_items), len(items))
    EbayItem.objects.bulk_update(success_items, [
        'last_humansetprice_before_badewanne',
        'new_price'
    ])
    return EbayItem.objects.filter(id__in=[item.id for item in success_items])


def items_to_blocked(ids: List = None) -> query.QuerySet:
    """
    Get items to be blocked. When ids is None search all objects available;
    otherwise, search items in id list.
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status=BWStageEnum.BW_TOBLOCK.value)
    if ids:
        rules &= Q(id__in=ids)

    return EbayItem.objects.filter(
        rules
    )


def items_price_increase_10percent(ids: List = None):
    """
    Get items to stage 6 and set their price to 10 percent increase.
    When ids is None search all objects available; otherwise,
    search items in id list.
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status__startswith="BW_STAGE") & \
            (~Q(item_status=BWStageEnum.BW_STAGE6_10I.value)) & \
            Q(sales_goal_reached_in_last7days__gt=120)
    if ids:
        rules &= Q(id__in=ids)

    return EbayItem.objects.filter(
        rules
    )


def items_price_increase_5percent(ids: List = None):
    """
    Get items to stage 5 and set their price to 5 percent increase.
    When ids is None search all objects available; otherwise,
    search items in id list.
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status__startswith="BW_STAGE") & \
            (~Q(item_status__in=[BWStageEnum.BW_STAGE6_10I.value,
                                 BWStageEnum.BW_STAGE5_5I.value])) & \
            Q(sales_goal_reached_in_last7days__gt=110)
    if ids:
        rules &= Q(id__in=ids)

    return EbayItem.objects.filter(
        rules
    )


def items_price_decrease_0percent(last_threshold: float, ids: List = None):
    """
    Get items to stage 4 and set their price to 0 percent increase.
    When ids is None search all objects available; otherwise,
    search items in id list.
    :param lastThreshold: Last 14 days sale fulfillment threshold
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status__in=[
        BWStageEnum.BW_STAGE3_10D.value,
        BWStageEnum.BW_STAGE2_20D.value,
        BWStageEnum.BW_STAGE1_30D.value,
        BWStageEnum.BW_STAGE0.value
    ]) & (
        Q(item_ranking_today__lt=10) |
        Q(sales_goal_reached_in_last14days__gt=last_threshold) |
        Q(cogs_24h_vs_7d__gt=50.0)
    )
    if ids:
        rules &= Q(id__in=ids)

    return EbayItem.objects.filter(
        rules
    )


def items_price_decrease_10percent(second_threshold: float, ids: List = None):
    """
    Get items to stage 3 and set their price to 10 percent decrease.
    When ids is None search all objects available; otherwise,
    search items in id list.
    :param secondThreshold: last 7 days sales fulfillment threshold
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status__in=[
        BWStageEnum.BW_STAGE2_20D.value,
        BWStageEnum.BW_STAGE1_30D.value,
        BWStageEnum.BW_STAGE0.value
    ]) & (
        Q(cogs_24h_vs_7d__gt=40.0) |
        Q(item_ranking_today__lt=20) |
        Q(sales_goal_reached_in_last7days__gt=second_threshold)
    )
    if ids:
        rules &= Q(id__in=ids)
    return EbayItem.objects.filter(
        rules
    )


def items_price_decrease_20percent(first_threshold: float, ids: List = None):
    """
    Get items to stage 2 and set their price to 20 percent decrease.
    When ids is None search all objects available; otherwise,
    search items in id list.
    :param firstThreshold: last 7 days sale fulfillment threshold
    :param ids: list of item id
    :return: items
    """
    rules = Q(item_status__in=[
        BWStageEnum.BW_STAGE1_30D.value,
        BWStageEnum.BW_STAGE0.value
    ]) & (
        Q(cogs_24h_vs_7d__gt=30.0) |
        Q(item_ranking_today__lt=50) |
        Q(sales_goal_reached_in_last7days__gt=first_threshold)
    )
    if ids:
        rules &= Q(id__in=ids)
    return EbayItem.objects.filter(
        rules
    )


def maintain_lrw_list() -> None:
    """
    Add normal item to lrw_list when it meets the rule
    :return: None
    """
    # Move fufilled items into lrw_List
    items = EbayItem.objects.filter(
        Q(item_status=BWStageEnum.NORMAL.value) &
        Q(lrw__lt=50)
    )
    if items:
        LOGGER.info("%s items to be forwarded LRW_LIST.",
                    items.values_list('id', flat=True))
        items.update(item_status=BWStageEnum.LRW_LIST.value)


def maintain_blocked_list() -> None:
    """
    Add items to blocked list when it meets the rule
    :return: None
    """
    # Move items to blocked list if badewanne lasts for more than 30 days or
    # item status is toblock
    items = EbayItem.objects.filter(
        (
            Q(item_status__startswith="BW_STAGE") &
            Q(last_bw_start_date__lt=datetime.datetime.now(tz=get_current_timezone()) -
              datetime.timedelta(days=30))
        ) | (
            Q(item_status=BWStageEnum.BW_TOBLOCK.value)
        )
    )
    if items:
        LOGGER.info("%s items to be forwarded to BLOCKED_LIST.",
                    items.values_list('id', flat=True))
        items.update(item_status=BWStageEnum.BW_BLOCKED.value)


def maintain_normal_list() -> None:
    """
    Add items to normal list when it meets the rule
    :return: None
    """
    # Move items to normal list when it fulfills
    items = EbayItem.objects.filter(
        # items not fulfill bw_ready any more
        (Q(item_status=BWStageEnum.BW_READY.value) & ~(
            Q(sales_goal_reached_in_last7days__lt=100) &
            Q(sales_goal_reached_in_last14days__lt=100) &
            Q(sales_goal_reached_mtd__lt=100) &
            Q(lrw__gt=50) &
            Q(stock__gt=150) &
            Q(fc__gt=15) &
            Q(item_ranking_today__gt=50)
        )) | (
            # items in blocked list more than 30 days
            Q(item_status=BWStageEnum.BW_BLOCKED.value) &
            Q(last_bw_end_date__lt=datetime.datetime.now(tz=get_current_timezone()) -
              datetime.timedelta(days=30))
        ) | (
            # items in lrw_list more than 50 lrw
            Q(item_status=BWStageEnum.LRW_LIST.value) &
            Q(lrw__gt=50)
        )
    )
    if items:
        LOGGER.info("%s items to be forwarded to NORMAL.",
                    items.values_list('id', flat=True))
        items.update(item_status=BWStageEnum.NORMAL.value)


def maintain_bwready_list() -> None:
    """
    Add normal items to bwready when it meets the rule
    :return: None
    """
    # Forward items to bw_ready if it fulfills the requirements
    items = EbayItem.objects.filter(
        Q(item_status=BWStageEnum.NORMAL.value) &
        Q(sales_goal_reached_in_last7days__lt=100) &
        Q(sales_goal_reached_in_last14days__lt=100) &
        Q(sales_goal_reached_mtd__lt=100) &
        Q(lrw__gt=50) &
        Q(stock__gt=150) &
        Q(fc__gt=15) &
        Q(item_ranking_today__gt=50)
    )
    if items:
        LOGGER.info("%s items to be forwarded BW_READY.",
                    items.values_list('id', flat=True))
        items.update(item_status=BWStageEnum.BW_READY.value)
