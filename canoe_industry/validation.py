from __future__ import annotations
import sqlite3
from canoe_industry.common import setup_logging
from canoe_schema.v4_0.models import TimePeriod, Region, TimeSeason

logger = setup_logging()


def _check_periods(
    conn: sqlite3.Connection,
    future_periods: list[int],
    behavior: str,
) -> None:
    cur = conn.cursor()
    placeholders = ", ".join("?" * len(future_periods))
    cur.execute(
        f"SELECT period FROM {TimePeriod.__table_name__} "
        f"WHERE period IN ({placeholders}) AND flag != 'f'",
        future_periods,
    )
    wrong = {row[0] for row in cur.fetchall()}
    cur.execute(
        f"SELECT period FROM {TimePeriod.__table_name__} "
        f"WHERE period IN ({placeholders})",
        future_periods,
    )
    found = {row[0] for row in cur.fetchall()}
    missing = set(future_periods) - found
    problems = sorted(missing | wrong)
    if problems:
        msg = (
            f"Periods missing or not flagged 'f' in {TimePeriod.__table_name__}: "
            f"{problems}"
        )
        if behavior == "error":
            raise ValueError(msg)
        logger.warning(msg)


def _check_regions(
    conn: sqlite3.Connection,
    province_list: list[str],
    behavior: str,
) -> None:
    cur = conn.cursor()
    placeholders = ", ".join("?" * len(province_list))
    cur.execute(
        f"SELECT region FROM {Region.__table_name__} "
        f"WHERE region IN ({placeholders})",
        province_list,
    )
    found = {row[0] for row in cur.fetchall()}
    missing = sorted(set(province_list) - found)
    if missing:
        msg = f"Regions missing from {Region.__table_name__} table: {missing}"
        if behavior == "error":
            raise ValueError(msg)
        logger.warning(msg)


def _check_time_season(conn: sqlite3.Connection, behavior: str) -> None:
    """Verify canoe-base has seeded the time_season table (v4.0 replacement for SeasonLabel)."""
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TimeSeason.__table_name__}")
    count = cur.fetchone()[0]
    if count == 0:
        msg = (
            f"{TimeSeason.__table_name__} table is empty — "
            "canoe-base must seed the time structure before this module runs"
        )
        if behavior == "error":
            raise ValueError(msg)
        logger.warning(msg)


def validate_db_against_config(cfg, conn: sqlite3.Connection) -> None:
    _check_periods(conn, cfg.future_periods, cfg.validation_behavior)
    _check_regions(conn, cfg.province_list, cfg.validation_behavior)
    _check_time_season(conn, cfg.validation_behavior)
