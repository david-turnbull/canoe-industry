# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 14:12:38 2025

@author: david
"""
from __future__ import annotations
import pandas as pd
from typing import Dict
from common import setup_logging, data_year

logger = setup_logging()

SECTOR_TABLE_MAP = {
    'CON': 3, 'PULP': 4, 'SMELT': 5, 'REFINING': 6, 'CEMENT': 7,
    'CHEM': 8, 'STEEL': 9, 'OTH_MAN': 10, 'FOR': 11, 'MINING': 12
}

COM_TO_COL = {
    'elc': 13, 'ng': 14, 'dsl': 15, 'hfo': 16, 'pcoke': 17,
    'ngl': 18, 'coal': 19, 'coke': 20, 'wood': 21, 'oth': 22
}

ATL_MAP = { 'PEI': 'Prince Edward Island', 'NS': 'Nova Scotia', 'NB': 'New Brunswick', 'NLLAB': 'Newfoundland and Labrador' }


def build_limit_tech_input_split_industry(
    comb_dict: Dict[str, pd.DataFrame],
    loaded_df: dict[str, dict[int, pd.DataFrame]],
    atl_shares: dict[str, dict[str, float]],
) -> Dict[str, pd.DataFrame]:
    dom = comb_dict['__domain__']
    ids = comb_dict['__ids__']
    dem_map = comb_dict['__canoe_dem_to_sec__']

    province_list = dom['province_list']
    sector_list = dom['sector_list']
    sector_abv = dom['sector_abv']
    periods = dom['periods']
    atl_pro = set(dom['atl_pro'])

    rows = []
    for region in province_list:
        for per in periods:
            for sec in sector_list:
                rn = SECTOR_TABLE_MAP.get(sec)
                if rn is None:
                    continue

                # If ATL province, skip sectors not present in shares (presence gating)
                if region in atl_pro:
                    sec_name = dem_map.get(f"D_{sec}")
                    if not sec_name:
                        continue
                    if ATL_MAP[region] not in (atl_shares.get(sec_name) or {}):
                        continue

                tis_vals: list[float | str] = []
                coms: list[str] = []
                for com, idx in COM_TO_COL.items():
                    try:
                        value = (
                            loaded_df['ATL'][rn]['2022'][idx] if region in atl_pro
                            else loaded_df[region][rn]['2022'][idx]
                        )
                    except Exception:
                        value = None

                    if value in (None, '0.0'):
                        continue
                    elif value in ('n.a.', 'X'):
                        tis = 'na'
                    else:
                        tis = round(float(value) / 100, 3)
                    tis_vals.append(tis)
                    coms.append(com)

                na_count = tis_vals.count('na')
                float_vals = [v for v in tis_vals if isinstance(v, float)]
                total_known = sum(float_vals)

                if total_known > 1.0 and float_vals:
                    excess = round(total_known - 1.0, 3)
                    min_val = min(float_vals)
                    min_idx = tis_vals.index(min_val)
                    corrected = max(0.0, round(min_val - excess, 3))
                    tis_vals[min_idx] = corrected
                    float_vals = [v for v in tis_vals if isinstance(v, float)]
                    total_known = sum(float_vals)

                for i, tis in enumerate(tis_vals):
                    com = coms[i]
                    if tis != 'na':
                        final_val = float(tis)
                    else:
                        if na_count == 0:
                            continue
                        missing_total = max(0.0, 1.0 - total_known)
                        final_val = round(missing_total / na_count, 3)

                    rows.append([
                        region,
                        per,
                        f"I_{com}",
                        f"{sector_abv}{sec}",
                        'ge',
                        final_val,
                        (
                            f'Calculated from NRCan 2022 comprehensive database (data year '
                            f'{data_year(per, periods)}). If values were n.a., '
                            'the remainder to 100% is evenly distributed.'
                        ),
                        'I1',
                        2, 1, 2, 3, 3,
                        ids[region],
                    ])

    df = pd.DataFrame(rows, columns=comb_dict['LimitTechInputSplitAnnual'].columns)
    comb_dict['LimitTechInputSplitAnnual'] = pd.concat([comb_dict['LimitTechInputSplitAnnual'], df], ignore_index=True)
    logger.info("LimitTechInputSplitAnnual rows: %d", len(rows))
    return comb_dict