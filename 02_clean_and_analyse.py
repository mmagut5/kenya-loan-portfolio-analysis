"""
02_clean_and_analyse.py
Cleans the raw (simulated) loan export, calculates portfolio risk metrics and saves tables + charts.
Inputs : data/raw_loans.csv
Outputs: data/clean_loans.csv, tables/*.csv, charts/*.png
"""
import pandas as pd                     # tables
import numpy as np                      # numbers
import matplotlib                       # charts
matplotlib.use("Agg")                   # draw charts without opening a window
import matplotlib.pyplot as plt

# ======================= 1. LOAD =======================
raw = pd.read_csv("data/raw_loans.csv", keep_default_na=False, na_values=[""])   # keep_default_na=False so the word "None" (no collateral) is NOT treated as missing
print("Raw rows:", len(raw))

# ======================= 2. CLEAN =======================
df = raw.drop_duplicates().copy()                                   # remove exact duplicate rows
print("After removing duplicate rows:", len(df))

df["county"] = df["county"].str.strip().str.title()                  # "NAIROBI " -> "Nairobi"
df["gender"] = df["gender"].str.strip().str.lower().str[0].map({"f": "Female", "m": "Male"})  # F/female -> Female

slash = df["disbursement_date"].str.contains("/")                    # two date formats were mixed together
df.loc[slash, "disbursement_date"] = pd.to_datetime(df.loc[slash, "disbursement_date"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
df["disbursement_date"] = pd.to_datetime(df["disbursement_date"])

# missing income: fill with the median income of the same business sector (and flag it)
df["income_imputed"] = df["monthly_income_kes"].isna()
df["monthly_income_kes"] = df["monthly_income_kes"].fillna(df.groupby("business_sector")["monthly_income_kes"].transform("median"))
# missing CRB score: keep as missing (do NOT guess), group them as "No CRB score" later
df["disbursement_quarter"] = df["disbursement_date"].dt.to_period("Q").astype(str)

# ======================= 3. NEW COLUMNS =======================
df["installment_kes"] = df["loan_amount_kes"] * (1 + df["interest_rate_flat_pct"] / 100 * df["term_months"] / 12) / df["term_months"]
df["installment_to_income"] = df["installment_kes"] / df["monthly_income_kes"]     # repayment burden
df["score_band"] = pd.cut(df["crb_score"], [0, 500, 575, 650, 725, 900],
                          labels=["300-500", "501-575", "576-650", "651-725", "726-850"]).astype(object).fillna("No CRB score")
df["burden_band"] = pd.cut(df["installment_to_income"], [0, .15, .25, .35, 10],
                           labels=["Under 15%", "15-25%", "25-35%", "Over 35%"])
df["size_band"] = pd.cut(df["loan_amount_kes"], [0, 50_000, 150_000, 500_000, 5_000_000],
                         labels=["Up to 50K", "50K-150K", "150K-500K", "Over 500K"])
df["is_npl"] = df["days_past_due"] > 90          # non-performing: more than 90 days past due
df["is_par30"] = df["days_past_due"] > 30        # portfolio at risk: more than 30 days past due
df.to_csv("data/clean_loans.csv", index=False)

# ======================= 4. PORTFOLIO KPIs =======================
active = df[df["loan_status"] == "Active"]                          # loans with a balance outstanding
bal = active["outstanding_principal_kes"].sum()
kpi = {
    "Loans disbursed": len(df),
    "Total disbursed (KES M)": round(df["loan_amount_kes"].sum() / 1e6, 1),
    "Active loans": len(active),
    "Outstanding principal (KES M)": round(bal / 1e6, 1),
    "PAR30 (% of outstanding)": round(active.loc[active.is_par30, "outstanding_principal_kes"].sum() / bal * 100, 1),
    "NPL ratio (% of outstanding)": round(active.loc[active.is_npl, "outstanding_principal_kes"].sum() / bal * 100, 1),
}
# illustrative provisioning rates by risk class (approximating CBK prudential guidelines)
prov_rate = {"Normal": 0.01, "Watch": 0.03, "Substandard": 0.20, "Doubtful": 0.50, "Loss": 1.00}
active = active.assign(provision=active["outstanding_principal_kes"] * active["risk_class"].map(prov_rate))
kpi["Estimated provisions (KES M)"] = round(active["provision"].sum() / 1e6, 1)
kpi["Provision coverage (% of outstanding)"] = round(active["provision"].sum() / bal * 100, 1)
kpi["Default rate (% of all loans originated)"] = round(df["is_npl"].mean() * 100, 1)
pd.Series(kpi).to_csv("tables/portfolio_kpis.csv", header=["value"])
print("\n--- PORTFOLIO KPIs ---"); print(pd.Series(kpi).to_string())

# ======================= 5. RISK BY SEGMENT =======================
def segment(col, min_loans=0):
    """NPL ratio (by balance) and default share (by count) for each group in `col`."""
    g = active.groupby(col, observed=True)
    out = pd.DataFrame({
        "active_loans": g.size(),
        "outstanding_kes_m": g["outstanding_principal_kes"].sum() / 1e6,
        "npl_ratio_pct": g.apply(lambda x: x.loc[x.is_npl, "outstanding_principal_kes"].sum() / x["outstanding_principal_kes"].sum() * 100),
        "par30_pct": g.apply(lambda x: x.loc[x.is_par30, "outstanding_principal_kes"].sum() / x["outstanding_principal_kes"].sum() * 100),
    })
    # share of ALL loans originated in the segment that are now NPL (includes loans already repaid, so no survivorship bias)
    out["default_rate_pct"] = df.groupby(col, observed=True)["is_npl"].mean() * 100
    out = out.round(1)
    out = out[out["active_loans"] >= min_loans]
    out.to_csv(f"tables/npl_by_{col}.csv")
    return out

seg = {c: segment(c, 20) for c in ["business_sector", "county", "product", "score_band", "collateral_type",
                                   "repayment_channel", "burden_band", "size_band", "gender", "disbursement_quarter"]}
for name, t in seg.items():
    print(f"\n--- NPL by {name} ---"); print(t.sort_values("npl_ratio_pct", ascending=False).to_string())

# ======================= 6. CHARTS =======================
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
NAVY, RED, GREY = "#1F3A5F", "#C0392B", "#9AA5B1"
avg = kpi["NPL ratio (% of outstanding)"]

def barh(table, title, fname, order_by="npl_ratio_pct"):
    t = table.sort_values(order_by)
    fig, ax = plt.subplots(figsize=(8, max(3, 0.42 * len(t) + 1.2)))
    bars = ax.barh(t.index.astype(str), t["npl_ratio_pct"], color=[RED if v > avg else NAVY for v in t["npl_ratio_pct"]])
    ax.axvline(avg, color=GREY, ls="--", lw=1); ax.text(avg, len(t) - 0.4, f" Portfolio {avg}%", color="#555", fontsize=8, va="bottom")
    for b, v in zip(bars, t["npl_ratio_pct"]): ax.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v}%", va="center", fontsize=8)
    ax.set_xlabel("NPL ratio (% of outstanding principal)"); ax.set_title(title, loc="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.005, "Simulated data - for portfolio demonstration only", fontsize=7, color="#777")
    fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(f"charts/{fname}.png", dpi=160); plt.close(fig)

barh(seg["business_sector"], "NPL ratio by business sector", "npl_by_sector")
barh(seg["county"], "NPL ratio by county (counties with 20+ active loans)", "npl_by_county")
barh(seg["score_band"], "NPL ratio by CRB score band", "npl_by_score_band")
barh(seg["collateral_type"], "NPL ratio by collateral type", "npl_by_collateral")
barh(seg["repayment_channel"], "NPL ratio by repayment channel", "npl_by_channel")

# risk class mix (balance)
rc = active.groupby("risk_class")["outstanding_principal_kes"].sum().reindex(prov_rate.keys()) / 1e6
fig, ax = plt.subplots(figsize=(7, 4)); bars = ax.bar(rc.index, rc.values, color=[NAVY, GREY, "#E59866", RED, "#7B241C"])
for b, v in zip(bars, rc.values): ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontsize=9)
ax.set_ylabel("Outstanding principal (KES millions)"); ax.set_title("Outstanding balance by risk class", loc="left", fontweight="bold", fontsize=11)
fig.text(0.01, 0.005, "Simulated data - for portfolio demonstration only", fontsize=7, color="#777")
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig("charts/risk_class_mix.png", dpi=160); plt.close(fig)

# vintage: NPL by disbursement quarter (only cohorts with 20+ active loans)
# Uses ALL loans originated each quarter (not just active ones) so repaid loans are counted and the cohorts compare fairly.
v = df.groupby("disbursement_quarter")["is_npl"].mean().mul(100).round(1)
fig, ax = plt.subplots(figsize=(8, 4)); ax.plot(v.index, v.values, marker="o", color=NAVY)
for x, y in zip(v.index, v.values): ax.text(x, y + 0.3, f"{y}%", ha="center", fontsize=8)
ax.set_ylabel("% of loans originated that are now NPL"); plt.xticks(rotation=45)
ax.set_title("Default rate by disbursement quarter (vintage)", loc="left", fontweight="bold", fontsize=11)
fig.text(0.01, 0.005, "Simulated data - for portfolio demonstration only", fontsize=7, color="#777")
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig("charts/npl_by_vintage.png", dpi=160); plt.close(fig)
print("\nDone. Tables in /tables, charts in /charts, cleaned data in /data/clean_loans.csv")
