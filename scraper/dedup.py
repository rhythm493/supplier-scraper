from __future__ import annotations

import logging
from difflib import SequenceMatcher

import pandas as pd

from scraper.validators import extract_domain

logger = logging.getLogger(__name__)


def deduplicate(df: pd.DataFrame, name_col: str = "Company Name", url_col: str = "Website") -> pd.DataFrame:
    initial_count = len(df)
    if initial_count == 0:
        return df

    df = df.copy()
    df["_domain"] = df[url_col].apply(lambda u: extract_domain(u) if pd.notna(u) else "")

    df = df.drop_duplicates(subset=["_domain"], keep="first")
    logger.info("Dedup by domain: %d → %d", initial_count, len(df))

    df = _fuzzy_dedup_names(df, name_col)
    logger.info("Final count after fuzzy dedup: %d", len(df))

    df = df.drop(columns=["_domain"])
    return df.reset_index(drop=True)


def _fuzzy_dedup_names(df: pd.DataFrame, name_col: str, threshold: float = 0.85) -> pd.DataFrame:
    if len(df) < 2:
        return df

    keep = [True] * len(df)

    for i in range(len(df)):
        if not keep[i]:
            continue
        name_i = str(df.iloc[i][name_col]).lower().strip()
        for j in range(i + 1, len(df)):
            if not keep[j]:
                continue
            name_j = str(df.iloc[j][name_col]).lower().strip()
            ratio = SequenceMatcher(None, name_i, name_j).ratio()
            if ratio >= threshold:
                keep[j] = False

    return df.loc[keep]
