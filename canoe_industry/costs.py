# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 12:33:38 2025

@author: david
"""
# TODO: complete CostInvest migration before uncommenting.
# Placeholder values (0.1 M$/PJ) need to be replaced with real data.

from __future__ import annotations
import sqlite3
from canoe_industry.common import setup_logging
from canoe_schema.v4_0.models import CostInvest

logger = setup_logging()


def build_cost_invest_industry(meta: dict, cursor: sqlite3.Cursor) -> None:
    province_list: list[str] = meta['province_list']
    sector_list: list[str] = meta['sector_list']
    sector_abv: str = meta['sector_abv']
    periods: list[int] = meta['periods']
    ids: dict[str, str] = meta['ids']

    first_vintage = min(periods)
    rows: list[CostInvest] = []
    for province in province_list:
        for sec in sector_list:
            rows.append(
                CostInvest(
                    region=province,
                    tech=f"{sector_abv}{sec}",
                    vintage=first_vintage,
                    cost=0.1,
                    units="M$/PJ",
                    notes="Arbitrary amount for first time period",
                    data_id=ids[province],
                )
            )

    if rows:
        cursor.executemany(*CostInvest.bulk_insert_or_ignore_sql(rows))
        logger.info("CostInvest rows written: %d", len(rows))
