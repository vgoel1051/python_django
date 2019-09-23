"""
    This module defines how the ebayitem is visualized in table
"""

import django_tables2 as tables

from .models import EbayItem


class TableControlMixin(tables.Table):
    """
        Define a checkbox for every row in the table
    """
    selection = tables.CheckBoxColumn(
        accessor="pk",
        attrs={
            "th__input": {
                "onclick": "toggle(this)"
            }
        },
        orderable=False,
        exclude_from_export=True
    )


class EbayItemTable(TableControlMixin, tables.Table):
    """
        Define how to visualize the table, and render
        the percentage value with percentage sign
    """

    class Meta: # pylint: disable=too-few-public-methods
        """
            Tell which model is to be visualized and
            which template to be used
        """
        model = EbayItem
        template_name = 'django_tables2/bootstrap4.html'

    def render_percent(self, value):
        """
            Render decimal value to string with percentage sign
        :param value: decimal
        :return: string with percentage sign
        """
        return "{}%".format(value)

    def render_sales_goal_reached_in_last7days(self, value):
        """
            render sales_goal_reached_in_last7days with percentage sign
        :param value: decimal value
        :return: string with percentage sign
        """
        return self.render_percent(value)

    def render_sales_goal_reached_in_last14days(self, value):
        """
            render sales_goal_reached_in_last14days with percentage sign
        :param value: decimal value
        :return: string with percentage sign
        """
        return self.render_percent(value)

    def render_sales_goal_reached_mtd(self, value):
        """
            render sales_goal_reached_mtd with percentage sign
        :param value: decimal value
        :return: string with percentage sign
        """
        return self.render_percent(value)

    def render_cogs_24h_vs_7d(self, value):
        """
            render cogs_24h_vs_7d with percentage sign
        :param value: decimal value
        :return: string with percentage sign
        """
        return self.render_percent(value)
