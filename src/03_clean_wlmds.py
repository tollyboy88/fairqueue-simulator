"""
03_clean_wlmds.py
-----------------
Build fairness signals from the WLMDS demographic data.

Fairness gap (per demographic group, per provider):
    share_of_long_waits  = group long-wait count  / total long-wait count
    share_of_all_waits   = group all-wait count    / total all-wait count
    fairness_gap         = share_of_long_waits - share_of_all_waits   (pp, /100)

Outputs:
    data/interim/wlmds_cleaned/wlmds_fairness.parquet        (provider-level scores)
    data/interim/wlmds_cleaned/wlmds_fairness_detail.parquet (group-level, for app)
    data/processed/wlmds_fairness.parquet                    (copy)

Notes:
    WLMDS is a single snapshot ("to 26 April 2026"), so fairness is treated as a
    structural per-provider measure applied across all RTT months.
    Long wait = "Over 52 Weeks"; all waits = "Total".
"""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import RAW, INTERIM, PROCESSED  # noqa

GEO = RAW / "wlmds" / "WLMDS" / "WLMDS-Demographics-Geography-to-26-April-2026-v1.csv"
LONG_BAND = "Over 52 Weeks"
ALL_BAND = "Total"


def gaps_for(df_metric: pd.DataFrame) -> pd.DataFrame:
    """Given rows for one provider+metric, return per-category gap table."""
    allw = df_metric[df_metric["Waiting Bands"] == ALL_BAND].groupby("Category")["Count"].sum()
    longw = df_metric[df_metric["Waiting Bands"] == LONG_BAND].groupby("Category")["Count"].sum()
    cats = sorted(set(allw.index) | set(longw.index))
    allw = allw.reindex(cats).fillna(0.0)
    longw = longw.reindex(cats).fillna(0.0)
    tot_all, tot_long = allw.sum(), longw.sum()
    if tot_all == 0 or tot_long == 0:
        return pd.DataFrame()
    share_all = allw / tot_all
    share_long = longw / tot_long
    gap = share_long - share_all
    return pd.DataFrame({
        "Category": cats,
        "share_all": share_all.values,
        "share_long": share_long.values,
        "fairness_gap": gap.values,
    })


def main():
    g = pd.read_csv(GEO)
    g["Count"] = pd.to_numeric(g["Count"], errors="coerce").fillna(0)
    # provider-level rows only (exclude England + region aggregates)
    prov = g[g["Geography"].isin(["NHS ACUTE", "INDEPENDENT SECTOR", "OTHER"])].copy()

    summary_rows, detail_rows = [], []
    for code, gp in prov.groupby("Code"):
        name = gp["Name"].iloc[0]
        rec = {"provider_code": code, "provider_name": name}
        for metric, key in [("IMD", "fairness_deprivation_score"),
                            ("Ethnicity", "fairness_ethnicity_score"),
                            ("Age", "fairness_age_score"),
                            ("Sex", "fairness_sex_score")]:
            tbl = gaps_for(gp[gp["Metric"] == metric])
            if tbl.empty:
                rec[key] = 0.0
                continue
            tbl.insert(0, "metric", metric)
            tbl.insert(0, "provider_code", code)
            detail_rows.append(tbl)
            if metric == "Sex":
                # absolute over-representation difference (|gap| is symmetric)
                rec[key] = float(tbl["fairness_gap"].abs().max())
            else:
                rec[key] = float(tbl["fairness_gap"].clip(lower=0).max())
        # missing-demographic = share of 'Not known' ethnicity among all waiters
        eth_all = gp[(gp["Metric"] == "Ethnicity") & (gp["Waiting Bands"] == ALL_BAND)]
        tot = eth_all["Count"].sum()
        unknown = eth_all[eth_all["Category"].str.contains("not known", case=False, na=False)]["Count"].sum()
        rec["missing_demographic_score"] = float(unknown / tot) if tot else 0.0
        summary_rows.append(rec)

    summary = pd.DataFrame(summary_rows)
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()

    INTERIM.joinpath("wlmds_cleaned").mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    summary.to_parquet(INTERIM / "wlmds_cleaned" / "wlmds_fairness.parquet", index=False)
    summary.to_parquet(PROCESSED / "wlmds_fairness.parquet", index=False)
    detail.to_parquet(INTERIM / "wlmds_cleaned" / "wlmds_fairness_detail.parquet", index=False)

    print(f"Providers with fairness scores: {len(summary)}")
    print(summary[["fairness_deprivation_score", "fairness_ethnicity_score",
                   "fairness_age_score", "fairness_sex_score",
                   "missing_demographic_score"]].describe().round(3).to_string())
    print("\nTop 5 deprivation over-representation:")
    print(summary.nlargest(5, "fairness_deprivation_score")[
        ["provider_code", "provider_name", "fairness_deprivation_score"]].to_string(index=False))


if __name__ == "__main__":
    main()
