# -*- coding: utf-8 -*-
"""
Industry: Demand & ExistingCapacity builder

Functionalized from the user's working 'demands_work.py' so it can be called by
the ETL aggregator:
    from demands import build_demand_and_capacity_industry

Key behavior (kept as in the working script):
- Demand baseline uses NRCan CEUD 2022 by province; ATL is split using StatCan shares.
- Demand for model years ≠ baseline is GDP-scaled using CER CEF GNZ.
- ExistingCapacity uses the previous year (2021) values.
- Notes/refs and column orders match the existing schema tables in comb_dict.
"""

from __future__ import annotations
from typing import Dict
import pandas as pd
from common import setup_logging, data_year

logger = setup_logging()


# -----------------------------
# Internal helpers
# -----------------------------
def _get_atl_share_key(dem_code: str, dem_to_sec: Dict[str, str]) -> str | None:
    """Map 'D_MINING' -> ATL share category label via comb_dict['__canoe_dem_to_sec__']."""
    try:
        return dem_to_sec[dem_code]
    except Exception:
        return None


def _apply_atl_split(temp_val: float, dem_code: str, province: str,
                     atl_shares: dict[str, dict[str, float]],
                     dem_to_sec: Dict[str, str]) -> float | None:
    """Split an ATL aggregate value into a specific Atlantic province using atl_shares."""
    share_key = _get_atl_share_key(dem_code, dem_to_sec)
    if share_key is None:
        return None

    prov_map = {
        'PEI': 'Prince Edward Island',
        'NB': 'New Brunswick',
        'NS': 'Nova Scotia',
        'NLLAB': 'Newfoundland and Labrador',
    }
    atl_name = prov_map.get(province)
    if atl_name is None:
        return None

    try:
        share = atl_shares[share_key][atl_name]
        return float(temp_val) * float(share)
    except Exception:
        return None


def _safe_loaded_value(loaded_df: dict, prov: str, nrcan_table_idx: int, year: str, x_index: int) -> float | None:
    """
    Access loaded_df[prov][nrcan_table_idx][year][x_index] defensively.
    Returns float or None if unavailable.
    """
    try:
        val = loaded_df[prov][nrcan_table_idx][year][x_index]
        if val in (None, '', '0'):
            # Normalize strings that represent zero
            return 0.0 if val == '0' else None
        return float(val)
    except Exception:
        return None


# -----------------------------
# Public entry point
# -----------------------------
def build_demand_and_capacity_industry(
    comb_dict: Dict[str, pd.DataFrame],
    loaded_df: dict[str, dict[int, pd.DataFrame]],
    pop_df: pd.DataFrame,
    atl_shares: dict[str, dict[str, float]],
) -> Dict[str, pd.DataFrame]:
    """
    Build Demand and ExistingCapacity tables and append to comb_dict.

    Parameters
    ----------
    comb_dict : dict[str, pd.DataFrame]
        Working table frames + meta from the setup/techcom stages.
    loaded_df : dict[str, dict[int, pd.DataFrame]]
        NRCan CEUD aggregated tables as returned by data_scraper.load_cached_or_fetch_industry(..).
    pop_df : pd.DataFrame
        CER CEF macro indicators (contains Year, Scenario, Variable, Value).
    atl_shares : dict[str, dict[str, float]]
        StatCan ATL presence shares (sector -> {region_name -> share}).

    Returns
    -------
    comb_dict : dict[str, pd.DataFrame]
        With Demand and ExistingCapacity appended.
    """
    # ---- Domain/meta pulled from comb_dict ----
    dom = comb_dict['__domain__']
    ids = comb_dict['__ids__']
    dem_to_sec = comb_dict['__canoe_dem_to_sec__']

    sector_abv: str = dom['sector_abv']
    province_list: list[str] = dom['province_list']
    sector_list: list[str] = dom['sector_list']
    atl_pro: set[str] = set(dom['atl_pro'])
    periods: list[int] = dom['periods']

    # Demand commodities (comes from techcom step)
    demand_com_list: list[str] = comb_dict.get('__demand_com_list__', [])
    if not demand_com_list:
        logger.warning("__demand_com_list__ missing; did you run techcom first?")
        demand_com_list = [f"D_{s}" for s in sector_list]

    # ---- GDP scaling dict from CER CEF GNZ ----
    # Build cumulative growth factors from the NRCan baseline year to each
    # period's data year (end-of-period convention: data_year = period + 5).
    nrcan_year: int = 2022  # must match the NRCan baseline used in base_2022
    end_years = [data_year(p, periods) for p in periods]
    all_gdp_years = sorted(set([nrcan_year]) | set(end_years))

    gdp_df = pop_df.copy()
    gdp_df = gdp_df[gdp_df['Year'].isin(all_gdp_years)]
    gdp_df = gdp_df[gdp_df['Variable'] == 'Real Gross Domestic Product ($2012 Millions)']
    gdp_df = gdp_df[gdp_df['Scenario'] == 'Global Net-zero']
    gdp_df = gdp_df.sort_values('Year').reset_index(drop=True)

    # gdp_dict[y] = GDP(y) / GDP(nrcan_year): cumulative growth from the NRCan base year
    gdp_base_rows = gdp_df[gdp_df['Year'] == nrcan_year]
    if gdp_base_rows.empty:
        logger.warning(
            "GDP data missing for NRCan base year %d; all scale factors will default to 1.0",
            nrcan_year,
        )
        gdp_base_val = None
    else:
        gdp_base_val = float(gdp_base_rows.iloc[0]['Value'])

    gdp_dict: dict[int, float] = {}
    for _, row in gdp_df.iterrows():
        year = int(row['Year'])
        val = float(row['Value'])
        gdp_dict[year] = (val / gdp_base_val) if gdp_base_val else 1.0

    # ---- Pull baseline (2022) demand by province for each demand commodity ----
    # The indices 2..11 correspond to the demand_com_list order in the original script.
    def _baseline_dict_for_year(year_str: str) -> dict[str, dict[str, float | None]]:
        d: dict[str, dict[str, float | None]] = {
            'AB': {}, 'ON': {}, 'MB': {}, 'QC': {}, 'BC': {}, 'SK': {}, 'ATL': {}
        }
        t = 0
        for x in range(2, 12):
            dem = demand_com_list[t]
            d['AB'][dem]  = _safe_loaded_value(loaded_df, 'AB', 2, year_str, x)
            d['ON'][dem]  = _safe_loaded_value(loaded_df, 'ON', 2, year_str, x)
            d['MB'][dem]  = _safe_loaded_value(loaded_df, 'MB', 2, year_str, x)
            d['QC'][dem]  = _safe_loaded_value(loaded_df, 'QC', 2, year_str, x)
            d['BC'][dem]  = _safe_loaded_value(loaded_df, 'BC', 2, year_str, x)
            d['SK'][dem]  = _safe_loaded_value(loaded_df, 'SK', 2, year_str, x)
            d['ATL'][dem] = _safe_loaded_value(loaded_df, 'ATL', 2, year_str, x)
            t += 1
        return d

    # Demand baseline (NRCan 2022), ExistingCapacity baseline (NRCan 2021)
    base_2022 = _baseline_dict_for_year('2022')
    base_2021 = _baseline_dict_for_year('2021')

    # ---- Build Demand rows across model periods ----
    dem_rows: list[list] = []
    for pro in province_list:
        for year in periods:
            dy = data_year(year, periods)
            # Growth factor from the start of this period to its end (data year)
            scale = float(gdp_dict.get(dy, 1.0))

            for dem in demand_com_list:
                notes = ''
                ref = ''
                val: float | None = None

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
                    split_val = _apply_atl_split(temp_val, dem, pro, atl_shares, dem_to_sec)
                    if split_val is None or split_val == 0.0:
                        continue
                    val = float(split_val) * scale
                    notes = (
                        f'GDP-scaled from NRCan 2022 ATL baseline to data year {dy} '
                        'using CER CEF Global Net-zero GDP growth and StatCan regional shares'
                    )
                    ref = 'I4'

                # Skip rows with no value
                if val in (None, ''):
                    continue
                if val == '0':
                    val = 0.0

                dem_rows.append([
                    pro,
                    int(year),
                    sector_abv + dem.lower(),
                    float(val),
                    'PJ',
                    notes,
                    ref,
                    1, 1, 2, 3, 2,
                    ids[pro]
                ])

    if dem_rows:
        dem_df = pd.DataFrame(dem_rows, columns=comb_dict['Demand'].columns)
        comb_dict['Demand'] = pd.concat([comb_dict['Demand'], dem_df], ignore_index=True)
        logger.info("Demand rows appended: %d", len(dem_rows))
    else:
        logger.warning("No Demand rows were generated.")

    # # ---- Build ExistingCapacity from previous year (2021) values ----
    # cap_rows: list[list] = []
    # cap_year = 2021  # previous to the 2022 baseline (kept from working script)

    # for pro in province_list:
    #     for sec in sector_list:
    #         dem_key = f"D_{sec}"

    #         if pro in ('AB', 'ON', 'BC', 'QC', 'MB', 'SK'):
    #             val = base_2021[pro].get(dem_key)
    #         elif pro in atl_pro:
    #             temp_val = base_2021['ATL'].get(dem_key)
    #             if temp_val in (None, 0.0):
    #                 continue
    #             split_val = _apply_atl_split(temp_val, dem_key, pro, atl_shares, dem_to_sec)
    #             if split_val is None or split_val == 0.0:
    #                 continue
    #             val = split_val
    #         else:
    #             val = None

    #         if val in (None, ''):
    #             continue
    #         if val == '0':
    #             val = 0.0

    #         ref = 'I1' if pro not in atl_pro else 'I1I3'
    #         notes = 'Existing capacity is taken from the NRCan comprehensive energy database, the previous value before demand'

    #         cap_rows.append([
    #             pro,
    #             sector_abv + sec,
    #             cap_year,
    #             float(val),
    #             'PJ',
    #             notes,
    #             ref,
    #             1, 1, 2, 3, 2,
    #             ids[pro]
    #         ])

    # if cap_rows:
    #     cap_df = pd.DataFrame(cap_rows, columns=comb_dict['ExistingCapacity'].columns)
    #     comb_dict['ExistingCapacity'] = pd.concat([comb_dict['ExistingCapacity'], cap_df], ignore_index=True)
    #     logger.info("ExistingCapacity rows appended: %d", len(cap_rows))
    # else:
    #     logger.warning("No ExistingCapacity rows were generated.")

    return comb_dict
