# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 12:33:38 2025

@author: david
"""

from __future__ import annotations
import pandas as pd
from typing import Dict
from canoe_industry.common import setup_logging
from canoe_schema.v3_2.models import CostInvest

logger = setup_logging()


def build_cost_invest_industry(comb_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    dom = comb_dict["__domain__"]
    ids = comb_dict["__ids__"]

    province_list = dom['province_list']
    sector_list = dom['sector_list']
    sector_abv = dom['sector_abv']
    periods = dom['periods']
    atl_pro = set(dom['atl_pro'])
    dem_map = comb_dict['__canoe_dem_to_sec__']

    # Optional: restrict to sectors present in ATL via shares (presence gating happens in demands/techinput too)
    rows: list[CostInvest] = []
    first_vintage = min(periods)
    for province in province_list:
        for sec in sector_list:
            # gate ATL regions by the StatCan shares presence if available
            if province in atl_pro:
                # We don't know presence here; rely on up/downstream gating. Keep a simple rule: allow all, or integrate a share check in caller.
                pass
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

    df = pd.DataFrame(
        [row.model_dump(mode='python') for row in rows],
        columns=comb_dict['CostInvest'].columns,
    )
    comb_dict['CostInvest'] = pd.concat([comb_dict['CostInvest'], df], ignore_index=True)
    logger.info("CostInvest rows: %d", len(rows))
    return comb_dict