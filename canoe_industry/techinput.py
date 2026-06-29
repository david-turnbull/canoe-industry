# -*- coding: utf-8 -*-
"""
Industry: LimitTechInputSplitAnnual + Efficiency builder

efficiency.py has been merged into this module: for each LimitTechInputSplitAnnual
row produced, a corresponding Efficiency row is emitted in the same loop, avoiding
a second pass over the data.
"""
from __future__ import annotations
import sqlite3
from canoe_industry.common import setup_logging, data_year, ATL_MAP
from canoe_industry.setup import CANOEIndustryRuntime
from canoe_schema.v4_0.models import Efficiency, LimitTechInputSplitAnnual

logger = setup_logging()


def _to_output_comm(sector_abv: str, sec: str) -> str:
    return f"{sector_abv}d_{sec.lower()}"


def build_limit_tech_and_efficiency_industry(
    runtime: CANOEIndustryRuntime,
    cursor: sqlite3.Cursor,
    loaded_df: dict[str, dict[int, object]],
    atl_shares: dict[str, dict[str, float]],
) -> None:
    province_list = runtime.province_list
    sector_list = runtime.sector_list
    sector_abv = runtime.sector_abv
    periods = runtime.periods
    atl_pro = runtime.atl_pro
    ids = runtime.ids
    dem_map = runtime.canoe_dem_to_sec
    sector_table_map = runtime.sector_table_map
    com_to_col = runtime.com_to_col
    dq = runtime.dq_limit_tech_input

    ltisa_rows: list[LimitTechInputSplitAnnual] = []
    eff_rows: list[Efficiency] = []

    for region in province_list:
        for per in periods:
            for sec in sector_list:
                rn = SECTOR_TABLE_MAP.get(sec)
                if rn is None:
                    continue

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
                    tis_vals[min_idx] = max(0.0, round(min_val - excess, 3))
                    float_vals = [v for v in tis_vals if isinstance(v, float)]
                    total_known = sum(float_vals)

                tech = f"{sector_abv}{sec}"
                output_comm = _to_output_comm(sector_abv, sec)

                for i, tis in enumerate(tis_vals):
                    com = coms[i]
                    input_comm = f"I_{com}"
                    if tis != 'na':
                        final_val = float(tis)
                    else:
                        if na_count == 0:
                            continue
                        final_val = round(max(0.0, 1.0 - total_known) / na_count, 3)

                    ltisa_rows.append(
                        LimitTechInputSplitAnnual(
                            region=region,
                            period=per,
                            input_comm=input_comm,
                            tech=tech,
                            operator='ge',
                            proportion=final_val,
                            notes=(
                                f'Calculated from NRCan 2022 comprehensive database (data year '
                                f'{data_year(per, periods)}). If values were n.a., '
                                'the remainder to 100% is evenly distributed.'
                            ),
                            data_source='I1',
                            dq_cred=dq.dq_cred,
                            dq_geog=dq.dq_geog,
                            dq_struc=dq.dq_struc,
                            dq_tech=dq.dq_tech,
                            dq_time=dq.dq_time,
                            data_id=ids[region],
                        )
                    )

                    eff_rows.append(
                        Efficiency(
                            region=region,
                            input_comm=input_comm,
                            tech=tech,
                            vintage=per,
                            output_comm=output_comm,
                            efficiency=1.0,
                            notes=(
                                'All technologies are assumed to have arbitrary efficiency; '
                                f'included commodities from NRCan Comp DB '
                                f'(data year {data_year(per, periods)})'
                            ),
                            data_source='I1',
                            data_id=ids[region],
                        )
                    )

    if ltisa_rows:
        cursor.executemany(*LimitTechInputSplitAnnual.bulk_insert_or_ignore_sql(ltisa_rows))
        logger.info("LimitTechInputSplitAnnual rows written: %d", len(ltisa_rows))
    else:
        logger.warning("No LimitTechInputSplitAnnual rows were generated.")

    if eff_rows:
        cursor.executemany(*Efficiency.bulk_insert_or_ignore_sql(eff_rows))
        logger.info("Efficiency rows written: %d", len(eff_rows))
    else:
        logger.warning("No Efficiency rows were generated.")
