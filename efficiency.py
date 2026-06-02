# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 16:02:06 2025

@author: david
"""
from __future__ import annotations
import pandas as pd
from typing import Dict
from common import setup_logging, data_year
import numpy as np

logger = setup_logging()


def _to_output_comm(tech: str) -> str | None:
    parts = tech.split('_', 1)
    if len(parts) == 2:
        prefix, name = parts
        return f"{prefix}_d_{name.lower()}"
    return None


def build_efficiency_industry(comb_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    inp = comb_dict['LimitTechInputSplitAnnual'][['region', 'input_comm', 'tech', 'period', 'data_id']].copy()
    model_periods: list[int] = comb_dict['__domain__']['periods']

    eff_df = comb_dict['Efficiency'].copy()
    if eff_df.empty:
        eff_df = pd.DataFrame(columns=comb_dict['Efficiency'].columns)

    eff_df = pd.concat([
        eff_df,
        pd.DataFrame({
            'region': inp['region'],
            'input_comm': inp['input_comm'],
            'tech': inp['tech'],
            'vintage': inp['period'],
            'output_comm': inp['tech'].apply(_to_output_comm),
            'efficiency': 1.0,
            'notes': inp['period'].apply(
                lambda p: (
                    f'All technologies are assumed to have arbitrary efficiency; '
                    f'included commodities from NRCan Comp DB (data year {data_year(p, model_periods)})'
                )
            ),
            'data_source': 'I1',
            'data_id': inp['data_id'],
            'dq_cred': np.nan, 'dq_geog': np.nan, 'dq_struc': np.nan, 'dq_tech': np.nan, 'dq_time': np.nan,
        })
    ], ignore_index=True)

    comb_dict['Efficiency'] = eff_df
    logger.info("Efficiency rows: %d", len(eff_df))
    return comb_dict