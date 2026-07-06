# -*- coding: utf-8 -*-
"""
Industry: Demand & ExistingCapacity builder
"""
from __future__ import annotations
import sqlite3
from canoe_industry.common import setup_logging, data_year, ATL_MAP
from canoe_industry.setup import CANOEIndustryRuntime
from canoe_schema.v4_0.models import Demand, ExistingCapacity

logger = setup_logging()


def _get_atl_share(
    province: str,
    dem_code: str,
    atl_shares: dict[str, dict[str, float]],
    dem_to_sec: dict[str, str],
) -> float | None:
    """Return the province's fractional share of the ATL aggregate, or None if unavailable."""
    sector_name = dem_to_sec.get(dem_code)
    if sector_name is None:
        return None
    province_name = ATL_MAP.get(province)
    if province_name is None:
        return None
    try:
        return float(atl_shares[sector_name][province_name])
    except Exception:
        return None


def _safe_loaded_value(
    loaded_df: dict, prov: str, nrcan_table_idx: int, year: str, x_index: int
) -> float | None:
    try:
        val = loaded_df[prov][nrcan_table_idx][year][x_index]
        if val in (None, '', '0'):
            return 0.0 if val == '0' else None
        return float(val)
    except Exception:
        return None


def build_demand_and_capacity_industry(
    runtime: CANOEIndustryRuntime,
    cursor: sqlite3.Cursor,
    loaded_df: dict[str, dict[int, object]],
    macro_df: object,
    atl_shares: dict[str, dict[str, float]],
) -> None:
    sector_abv = runtime.sector_abv
    province_list = runtime.province_list
    sector_list = runtime.sector_list
    atl_pro = runtime.atl_pro
    periods = runtime.periods
    ids = runtime.ids
    dem_to_sec = runtime.canoe_dem_to_sec
    demand_com_list = runtime.demand_com_list
    nrcan_year = runtime.nrcan_year
    gdp_scenario = runtime.gdp_scenario
    gdp_variable = runtime.gdp_variable
    dq = runtime.dq_demand

    import pandas as pd
    gdp_df = macro_df.copy()
    end_years = [data_year(p, periods) for p in periods]
    all_gdp_years = sorted(set([nrcan_year]) | set(end_years))
    gdp_df = gdp_df[gdp_df['Year'].isin(all_gdp_years)]
    gdp_df = gdp_df[gdp_df['Variable'] == gdp_variable]
    gdp_df = gdp_df[gdp_df['Scenario'] == gdp_scenario]
    gdp_df = gdp_df.sort_values('Year').reset_index(drop=True)

    gdp_base_rows = gdp_df[gdp_df['Year'] == nrcan_year]
    gdp_base_val = float(gdp_base_rows.iloc[0]['Value']) if not gdp_base_rows.empty else None
    if gdp_base_val is None:
        logger.warning("GDP data missing for NRCan base year %d; scale factors default to 1.0", nrcan_year)

    gdp_dict: dict[int, float] = {
        int(row['Year']): (float(row['Value']) / gdp_base_val if gdp_base_val else 1.0)
        for _, row in gdp_df.iterrows()
    }

    def _baseline_dict_for_year(year_str: str) -> dict[str, dict[str, float | None]]:
        d: dict[str, dict[str, float | None]] = {
            'AB': {}, 'ON': {}, 'MB': {}, 'QC': {}, 'BC': {}, 'SK': {}, 'ATL': {}
        }
        for t, dem in enumerate(demand_com_list):
            x = t + 2
            for prov in d:
                d[prov][dem] = _safe_loaded_value(loaded_df, prov, 2, year_str, x)
        return d

    base_2022 = _baseline_dict_for_year('2022')
    # base_2021 = _baseline_dict_for_year('2021')  # needed when ExistingCapacity is enabled

    # ---- Demand rows ----
    dem_rows: list[Demand] = []
    for pro in province_list:
        for year in periods:
            dy = data_year(year, periods)
            scale = float(gdp_dict.get(dy, 1.0))

            for dem in demand_com_list:
                val: float | None = None
                notes = ''
                ref = ''

                if pro in ('AB', 'ON', 'BC', 'QC', 'MB', 'SK'):
                    base = base_2022[pro].get(dem)
                    if base is None:
                        continue
                    val = float(base) * scale
                    notes = (
                        f'GDP-scaled from NRCan 2022 baseline to data year {dy} '
                        'using CER CEF Global Net-zero GDP growth'
                    )
                    ref = 'I2'
                elif pro in atl_pro:
                    temp_val = base_2022['ATL'].get(dem)
                    if temp_val in (None, 0.0):
                        continue
                    share = _get_atl_share(pro, dem, atl_shares, dem_to_sec)
                    if share is None or share == 0.0:
                        continue
                    val = float(temp_val) * share * scale
                    notes = (
                        f'GDP-scaled from NRCan 2022 ATL baseline to data year {dy} '
                        'using CER CEF Global Net-zero GDP growth and StatCan regional shares'
                    )
                    ref = 'I4'

                if val in (None, ''):
                    continue
                if val == '0':
                    val = 0.0

                dem_rows.append(
                    Demand(
                        region=pro,
                        period=int(year),
                        commodity=sector_abv + dem.lower(),
                        demand=float(val),
                        units='PJ',
                        notes=notes,
                        data_source=ref,
                        dq_cred=dq.dq_cred,
                        dq_geog=dq.dq_geog,
                        dq_struc=dq.dq_struc,
                        dq_tech=dq.dq_tech,
                        dq_time=dq.dq_time,
                        data_id=ids[pro],
                    )
                )

    if dem_rows:
        cursor.executemany(*Demand.bulk_insert_or_ignore_sql(dem_rows))
        logger.info("Demand rows written: %d", len(dem_rows))
    else:
        logger.warning("No Demand rows were generated.")

    # ---- ExistingCapacity from previous year (2021) values ----
    # cap_year = 2021  # year before the 2022 NRCan baseline
    # cap_rows: list[ExistingCapacity] = []

    # for pro in province_list:
    #     for sec in sector_list:
    #         dem_key = f"D_{sec}"

    #         if pro in ('AB', 'ON', 'BC', 'QC', 'MB', 'SK'):
    #             val = base_2021[pro].get(dem_key)
    #         elif pro in atl_pro:
    #             temp_val = base_2021['ATL'].get(dem_key)
    #             if temp_val in (None, 0.0):
    #                 continue
    #             share = _get_atl_share(pro, dem_key, atl_shares, dem_to_sec)
    #             if share is None or share == 0.0:
    #                 continue
    #             val = float(temp_val) * share
    #         else:
    #             val = None

    #         if val in (None, ''):
    #             continue
    #         if val == '0':
    #             val = 0.0

    #         # ATL values use StatCan shares (I3); non-ATL are direct NRCan reads (I1)
    #         ref = 'I1' if pro not in atl_pro else 'I3'

    #         cap_rows.append(
    #             ExistingCapacity(
    #                 region=pro,
    #                 tech=sector_abv + sec,
    #                 vintage=cap_year,
    #                 capacity=float(val),
    #                 units='PJ',
    #                 notes='Existing capacity from NRCan comprehensive energy database, year prior to demand baseline',
    #                 data_source=ref,
    #                 dq_cred=1,
    #                 dq_geog=1,
    #                 dq_struc=2,
    #                 dq_tech=3,
    #                 dq_time=2,
    #                 data_id=ids[pro],
    #             )
    #         )

    # if cap_rows:
    #     cursor.executemany(*ExistingCapacity.bulk_insert_or_ignore_sql(cap_rows))
    #     logger.info("ExistingCapacity rows written: %d", len(cap_rows))
    # else:
    #     logger.warning("No ExistingCapacity rows were generated.")
