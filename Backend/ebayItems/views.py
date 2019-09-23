"""
ebayItems's views, which defines how to response the user request.
"""

import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.timezone import get_current_timezone
from django_filters.views import FilterView
from django_filters.rest_framework import DjangoFilterBackend
from django_tables2.views import SingleTableMixin
from django_tables2.export.views import ExportMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework import generics

from .serializers import EbayItemsSerializer
from .models import EbayItem, EbayItemsFilter, BWStageEnum
from .tables import EbayItemTable
from .tasks import badewanne_process_tracking


LOGGER = logging.getLogger(__name__)


class FilteredEbayItemListView(LoginRequiredMixin, SingleTableMixin, ExportMixin, FilterView):
    """
    Display filter form and item detail table
    """
    login_url = '/accounts/login/'
    table_class = EbayItemTable
    model = EbayItem
    template_name = 'ebayItems/ebayItems.html'

    filterset_class = EbayItemsFilter

@login_required()
def item_badewanne(request):
    """
        Function when user clicked start or end badewanne
    :param request:
    :return:
    """
    if request.method == "POST":
        pks = request.POST.getlist("selection")
        if "start-badewanne" in request.POST:
            items = EbayItem.objects.filter(
                pk__in=pks,
                item_status=BWStageEnum.BW_READY.value,
            )
            LOGGER.info("Items to start Badewanne: %s", items)
            items.update(item_status=BWStageEnum.BW_STAGE0.value,
                         last_bw_start_date=datetime.now(tz=get_current_timezone()))
            badewanne_process_tracking(list(items.values_list('id', flat=True)), schedule=5)
        elif "stop-badewanne" in request.POST:
            items = EbayItem.objects.filter(
                pk__in=pks,
                item_status__startswith='BW_STAGE',
            )
            LOGGER.info("Items to stop Badewanne: %s", items)
            items.update(item_status=BWStageEnum.BW_TOBLOCK.value)
            badewanne_process_tracking(list(items.values_list('id', flat=True)), schedule=5)
    return redirect(request.META.get('HTTP_REFERER'))


class EbayItemsListView(generics.ListAPIView):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = EbayItem.objects.all()
    serializer_class = EbayItemsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EbayItemsFilter


class EbayItemsUpdateView(generics.GenericAPIView, UpdateModelMixin):
    """
        REST API Update View
    """
    queryset = EbayItem.objects.all()
    serializer_class = EbayItemsSerializer

    def put(self, request, *args, **kwargs):
        """
            REST API put
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return self.partial_update(request, *args, **kwargs)
