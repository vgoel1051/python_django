"""
    url module
"""

from django.urls import path
from .views import (
    FilteredEbayItemListView,
    item_badewanne,
    EbayItemsListView,
    EbayItemsUpdateView
)


urlpatterns = [
    path('', FilteredEbayItemListView.as_view(), name='ebay_index'),
    path('items/', EbayItemsListView.as_view(), name='items-list'),
    path('items/<int:pk>/', EbayItemsUpdateView.as_view(), name='items-partial-update'),
    path('badewanne/', item_badewanne, name='badewanne'),
]
