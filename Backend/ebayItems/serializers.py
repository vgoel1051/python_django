"""
    This module defines how the EbayItem model is going to be serialized,
    which is necessary for creating REST API Json response
"""

from rest_framework import serializers
from .models import EbayItem, BWStageEnum


class EbayItemsSerializer(serializers.ModelSerializer):
    """
        Serializers of model EbayItem
    """
    sales_l14 = serializers.FloatField(source='sales_goal_reached_in_last14days')
    sales_l7 = serializers.FloatField(source='sales_goal_reached_in_last7days')
    item_status = serializers.ChoiceField(choices=[(tag.value, tag.value) for tag in BWStageEnum])

    class Meta: # pylint: disable=too-few-public-methods
        """
            Defines model and which fields to be serialized
        """
        model = EbayItem
        fields = [
            'id',
            'item_no',
            'auction_id',
            'sales_l14',
            'sales_l7',
            'fc',
            'item_status'
        ]
