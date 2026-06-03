# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 16:02:06 2025

@author: david
"""
from __future__ import annotations
import pandas as pd
from typing import Dict
from canoe_industry.common import setup_logging, data_year
from canoe_schema.v3_2.models import Efficiency

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

    rows: list[Efficiency] = []
    for _, rec in inp.iterrows():
        rows.append(
            Efficiency(
                region=rec['region'],
                input_comm=rec['input_comm'],
                tech=rec['tech'],
                vintage=int(rec['period']),
                output_comm=_to_output_comm(rec['tech']),
                efficiency=1.0,
                notes=(
                    'All technologies are assumed to have arbitrary efficiency; '
                    f"included commodities from NRCan Comp DB (data year {data_year(int(rec['period']), model_periods)})"
                ),
                data_source='I1',
                data_id=rec['data_id'],
            )
        )

    eff_df = pd.DataFrame(
        [row.model_dump(mode='python') for row in rows],
        columns=comb_dict['Efficiency'].columns,
    )
    comb_dict['Efficiency'] = pd.concat([comb_dict['Efficiency'], eff_df], ignore_index=True)
    logger.info("Efficiency rows: %d", len(rows))
    return comb_dict