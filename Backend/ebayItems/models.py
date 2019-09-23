"""
This Module defines the table to store ebay item data.
"""

import datetime
from enum import Enum

from django.db import models
from django.utils.timezone import get_current_timezone
import django_filters
from django_filters import rest_framework as filters
from django_filters.filters import forms


class BWStageEnum(Enum):
    """
    Enum class to define various item status
    """
    BW_STAGE0 = 'BW_STAGE0'
    BW_STAGE1_30D = 'BW_STAGE1_30D'
    BW_STAGE2_20D = 'BW_STAGE2_20D'
    BW_STAGE3_10D = 'BW_STAGE3_10D'
    BW_STAGE4_0D = 'BW_STAGE4_0D'
    BW_STAGE5_5I = 'BW_STAGE5_5I'
    BW_STAGE6_10I = 'BW_STAGE6_10I'
    BW_BLOCKED = 'BW_BLOCKED'
    BW_TOBLOCK = 'BW_TOBLOCK'
    BW_READY = 'BW_READY'
    NORMAL = 'NORMAL'
    LRW_LIST = 'LRW_LIST'


class EbayItem(models.Model):
    """
    Create table EbayItem to store the item infos
    """
    item_no = models.BigIntegerField(
        null=False, verbose_name='ItemNo', db_column='ItemNo'
    )
    item_id = models.CharField(
        max_length=50, null=False, verbose_name='EbayItemID', db_column='ItemID'
    )
    auction_id = models.CharField(
        max_length=50, null=False, verbose_name='AuctionID', db_column='AuctionID'
    )
    sku = models.CharField(max_length=250, null=False, verbose_name='SKU', db_column='SKU')
    item_description = models.CharField(
        max_length=1000, null=False, verbose_name='Description', db_column='ItemDescription'
    )
    sales_goal_reached_in_last14days = models.FloatField(
        null=False, max_length=10, verbose_name='SalesL14',
        db_column='SalesGoalReachedInLast14Days'
    )
    sales_goal_reached_in_last7days = models.FloatField(
        null=False, max_length=10, verbose_name='SalesL7',
        db_column='SalesGoalReachedInLast7Days'
    )
    sales_goal_reached_mtd = models.FloatField(
        null=False, max_length=10, verbose_name='SalesMTD',
        db_column='SalesGoalReachedMTD'
    )
    cogs_24h_vs_7d = models.FloatField(
        null=False, max_length=10, verbose_name='COGS24HVS7D',
        db_column='COGS24HVS7D'
    )
    channel = models.CharField(
        null=False, max_length=200, verbose_name='Channel', db_column='Channel'
    )
    country = models.CharField(
        null=False, max_length=200, verbose_name='Country', db_column='Country'
    )
    stock = models.IntegerField(null=False, verbose_name='Stock', db_column='Stock')
    lrw = models.IntegerField(null=False, verbose_name='LRW', db_column='LRW')
    fc = models.IntegerField(null=False, verbose_name='FC', db_column='FC')
    item_ranking_today = models.IntegerField(
        null=False, verbose_name='Rank', db_column='ItemRankingToday'
    )
    item_status = models.CharField(
        max_length=15,
        choices=[(tag, tag.value) for tag in BWStageEnum],
        default=BWStageEnum.NORMAL.value,
        verbose_name='Status',
        db_column='ItemStatus'
    )
    our_purchase_price = models.FloatField(
        null=False, max_length=10, verbose_name='PPrice',
        db_column='OurPurchasePrice'
    )
    current_sale_price = models.FloatField(
        null=False, max_length=10, verbose_name='CPrice',
        db_column='CurrentSalePrice'
    )
    suggested_sale_price = models.FloatField(
        null=False, max_length=10, verbose_name='SPrice',
        db_column='SuggestedSalePrice')
    last_humansetprice_before_badewanne = models.FloatField(
        null=False, max_length=10, verbose_name='LHSPrice',
        db_column='LastHumanSetPriceBeforeBadewanne'
    )
    new_price = models.FloatField(
        null=False, max_length=10, verbose_name='NewPrice',
        db_column='NewPrice'
    )
    dio1 = models.IntegerField(null=False, verbose_name='DIO1', db_column='DIO1')
    dio2 = models.IntegerField(null=False, verbose_name='DIO2', db_column='DIO2')
    last_bw_start_date = models.DateTimeField(
        default=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=get_current_timezone()),
        verbose_name='LBWSDate',
        db_column='LastBWStartDate'
    )
    last_bw_end_date = models.DateTimeField(
        default=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=get_current_timezone()),
        verbose_name='LBWEDate',
        db_column='LastBWEndDate'
    )
    objects = models.Manager()


class EbayItemsFilter(filters.FilterSet):
    """
    Model filter which defines the filter fields and lookup rules.
    """

    class Meta: # pylint: disable=too-few-public-methods
        """
        Meta
        """
        model = EbayItem
        fields = {
            'item_no': ['exact'],
            'item_id': ['exact'],
            'auction_id': ['exact'],
            'country': ['exact']
        }

    item_status = django_filters.LookupChoiceFilter(
        field_class=forms.CharField,
        field_name='item_status',
        lookup_choices=[
            ('exact', 'Equals'),
            ('startswith', 'Startswith')
        ]
    )
    rank = django_filters.LookupChoiceFilter(
        field_class=forms.IntegerField,
        field_name='item_ranking_today',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )
    sales_l7 = django_filters.LookupChoiceFilter(
        field_class=forms.FloatField,
        field_name='sales_goal_reached_in_last7days',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )
    sales_l14 = django_filters.LookupChoiceFilter(
        field_class=forms.FloatField,
        field_name='sales_goal_reached_in_last14days',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )

    sales_mtd = django_filters.LookupChoiceFilter(
        field_class=forms.FloatField,
        field_name='sales_goal_reached_mtd',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )

    fc = django_filters.LookupChoiceFilter(
        field_class=forms.IntegerField,
        field_name='fc',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )

    stock = django_filters.LookupChoiceFilter(
        field_class=forms.IntegerField,
        field_name='stock',
        lookup_choices=[
            ('exact', 'Equals'),
            ('gt', 'Greater than'),
            ('lt', 'Less than'),
        ]
    )
