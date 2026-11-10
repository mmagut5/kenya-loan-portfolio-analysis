"""
01_generate_data.py
Creates a SIMULATED loan portfolio for a fictional Kenyan microfinance lender.
No real customers, lender or CRB data is used. Every record is artificially generated.
Output: data/raw_loans.csv  (deliberately messy, like a real loan-system export)
"""
import numpy as np                      # numbers and random sampling
import pandas as pd                     # tables

rng = np.random.default_rng(2025)       # fixed seed so the data is reproducible
N = 5000                                # number of loans
REPORT_DATE = pd.Timestamp("2025-09-30")  # the date the portfolio is "reported" at
START, END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-08-31")

def pick(options, probs, size=N):
    """Randomly choose from a list using the given probabilities."""
    return rng.choice(options, size=size, p=np.array(probs) / np.sum(probs))

# ---------- 1. Borrower and location attributes ----------
counties = ["Nairobi", "Kiambu", "Nakuru", "Mombasa", "Kisumu", "Uasin Gishu", "Machakos", "Meru",
            "Nyeri", "Kakamega", "Kisii", "Bungoma", "Kitui", "Embu", "Kericho", "Narok", "Garissa", "Turkana"]
county_w = [20, 8, 8, 6, 6, 6, 5, 5, 4, 5, 4, 4, 3, 3, 3, 3, 2, 2]
# county risk adjustments (positive = riskier): remote / drought-prone areas higher, central Kenya lower
county_risk = dict(zip(counties, [0.10, -0.10, 0.0, 0.15, 0.10, -0.05, 0.05, -0.10,
                                  -0.30, 0.10, 0.05, 0.10, 0.25, -0.10, -0.05, 0.20, 0.40, 0.45]))
county = pick(counties, county_w)

customer_id = ["CUST-%05d" % i for i in rng.integers(1, 4300, N)]   # some repeat borrowers
age = np.clip(rng.normal(36, 9, N), 21, 65).round().astype(int)
gender = pick(["Female", "Male"], [52, 48])

# ---------- 2. Sector, product, loan terms ----------
sectors = ["Retail (Duka / Mama Mboga)", "Agriculture", "Transport (Boda Boda / Matatu)", "Jua Kali / Manufacturing",
           "Services (Salon / Barber / Cyber)", "Hospitality & Food", "Private Education", "Salaried Employee"]
sector_w = [27, 17, 13, 9, 11, 8, 3, 12]
sector_risk = dict(zip(sectors, [0.0, 0.25, 0.35, 0.10, -0.10, 0.40, -0.30, -0.60]))
sector = pick(sectors, sector_w)

# which product each sector typically borrows
product_map = {
    sectors[0]: (["Biashara Loan", "Chama Group Loan", "Emergency Loan"], [78, 14, 8]),
    sectors[1]: (["Kilimo Loan", "Chama Group Loan", "Emergency Loan"], [80, 14, 6]),
    sectors[2]: (["Asset Finance", "Biashara Loan", "Emergency Loan"], [55, 38, 7]),
    sectors[3]: (["Biashara Loan", "Asset Finance", "Emergency Loan"], [75, 17, 8]),
    sectors[4]: (["Biashara Loan", "Chama Group Loan", "Emergency Loan"], [72, 18, 10]),
    sectors[5]: (["Biashara Loan", "Asset Finance", "Emergency Loan"], [75, 15, 10]),
    sectors[6]: (["Biashara Loan", "Asset Finance"], [70, 30]),
    sectors[7]: (["Salary Advance", "Emergency Loan"], [88, 12]),
}
product = np.empty(N, dtype=object)
for s, (opts, w) in product_map.items():
    idx = np.where(sector == s)[0]
    product[idx] = pick(opts, w, len(idx))

prod_cfg = {  # median amount (KES), terms (months), flat annual interest range (%)
    "Biashara Loan":    (100_000, [6, 9, 12, 18, 24], (18, 30)),
    "Kilimo Loan":      (80_000,  [6, 9, 12],         (14, 22)),
    "Chama Group Loan": (40_000,  [6, 12],            (20, 28)),
    "Emergency Loan":   (20_000,  [3, 6],             (28, 40)),
    "Asset Finance":    (400_000, [24, 36, 48],       (16, 24)),
    "Salary Advance":   (60_000,  [3, 6, 12],         (14, 20)),
}
amount, term, rate = np.zeros(N), np.zeros(N, dtype=int), np.zeros(N)
for p, (med, terms, (lo, hi)) in prod_cfg.items():
    idx = np.where(product == p)[0]
    amount[idx] = rng.lognormal(np.log(med), 0.55, len(idx))
    term[idx] = rng.choice(terms, len(idx))
    rate[idx] = rng.uniform(lo, hi, len(idx)).round(1)
amount = np.clip((amount / 1000).round() * 1000, 5_000, 3_000_000)

# ---------- 3. Income, credit score, collateral, repayment channel ----------
income_med = dict(zip(sectors, [45_000, 35_000, 55_000, 50_000, 40_000, 60_000, 90_000, 85_000]))
income = np.array([rng.lognormal(np.log(income_med[s]), 0.45) for s in sector])
income = (income / 500).round() * 500
score = np.clip(rng.normal(610, 90, N) + np.where(sector == sectors[7], 30, 0), 300, 850).round().astype(int)  # CRB-style score

collateral = np.empty(N, dtype=object)
for i in range(N):
    p = product[i]
    if p == "Asset Finance":   collateral[i] = "Logbook"
    elif p == "Salary Advance": collateral[i] = "Payroll Check-off"
    elif p == "Chama Group Loan": collateral[i] = "Group Guarantee"
    elif p == "Biashara Loan":  collateral[i] = rng.choice(["None", "Chattels / Stock", "Personal Guarantor", "Title Deed"], p=[.35, .30, .25, .10])
    elif p == "Kilimo Loan":    collateral[i] = rng.choice(["None", "Personal Guarantor", "Title Deed"], p=[.30, .50, .20])
    else:                       collateral[i] = rng.choice(["None", "Personal Guarantor"], p=[.70, .30])

channel = np.where(product == "Salary Advance", "Payroll Check-off",
          rng.choice(["M-Pesa Paybill", "Bank Transfer", "Cash at Branch", "Agent Banking"], N, p=[.70, .10, .12, .08]))

# ---------- 4. Disbursement date ----------
span = (END - START).days
disb = START + pd.to_timedelta((span * rng.beta(1.5, 1.0, N)).astype(int), unit="D")  # more recent lending

# ---------- 5. Probability of default (the hidden "truth" behind the data) ----------
inst = amount * (1 + rate / 100 * term / 12) / term          # flat-rate monthly installment
burden = inst / income                                       # installment as share of monthly income
coll_risk = {"None": .25, "Personal Guarantor": 0, "Group Guarantee": -.10, "Chattels / Stock": -.15,
             "Logbook": -.30, "Title Deed": -.50, "Payroll Check-off": -.50}
chan_risk = {"Cash at Branch": .30, "Agent Banking": .10, "M-Pesa Paybill": 0, "Bank Transfer": -.15, "Payroll Check-off": -.40}
macro = np.where((disb >= "2023-07-01") & (disb <= "2024-06-30"), 0.35, 0.0)   # tough cost-of-living cohort
logit = (-3.0
         + np.array([sector_risk[s] for s in sector]) + np.array([county_risk[c] for c in county])
         + np.array([coll_risk[c] for c in collateral]) + np.array([chan_risk[c] for c in channel])
         + np.where(product == "Emergency Loan", 0.5, 0) - (score - 600) / 100 * 1.0
         + np.clip(2.5 * (burden - 0.25), -0.5, 1.5) + macro + np.where(age < 25, 0.2, 0)
         + np.where(gender == "Female", -0.12, 0) + rng.normal(0, 0.5, N))
p_default = 1 / (1 + np.exp(-logit))
will_default = rng.random(N) < p_default

# ---------- 6. Repayment behaviour up to the reporting date ----------
days_elapsed = np.asarray((REPORT_DATE - disb).days)   # plain numpy array
due_now = np.minimum(np.floor(days_elapsed / 30.4375).astype(int), term)   # installments that have fallen due
paid_inst = due_now.copy()
dpd = np.zeros(N, dtype=int)
for i in range(N):
    if will_default[i]:
        k = min(int(np.floor(term[i] * rng.beta(1.2, 2.5))), term[i] - 1)    # installments paid before stopping
        first_missed = disb[i] + pd.Timedelta(days=(k + 1) * 30.4375)
        if first_missed <= REPORT_DATE:                                       # the default has actually occurred
            paid_inst[i] = k
            dpd[i] = (REPORT_DATE - first_missed).days
    elif due_now[i] < term[i]:                                                # still-running healthy loan: some late payers
        u = rng.random()
        if u < 0.12:   dpd[i] = rng.integers(1, 31)
        elif u < 0.15: dpd[i] = rng.integers(31, 91)

closed = (paid_inst >= term) & (dpd == 0)
outstanding = np.where(closed, 0.0, amount * (1 - paid_inst / term)).round(0)
risk_class = pd.cut(dpd, [-1, 30, 90, 180, 360, 10_000],
                    labels=["Normal", "Watch", "Substandard", "Doubtful", "Loss"]).astype(str)

df = pd.DataFrame({
    "loan_id": ["KE-LN-%06d" % i for i in range(1, N + 1)], "customer_id": customer_id,
    "disbursement_date": disb, "county": county, "gender": gender, "age": age,
    "business_sector": sector, "product": product, "loan_amount_kes": amount.astype(int),
    "term_months": term, "interest_rate_flat_pct": rate, "monthly_income_kes": income.astype(int),
    "crb_score": score, "collateral_type": collateral, "repayment_channel": channel,
    "installments_paid": paid_inst, "outstanding_principal_kes": outstanding.astype(int),
    "days_past_due": dpd, "risk_class": risk_class,
    "loan_status": np.where(closed, "Closed", "Active"),
}).sort_values("disbursement_date").reset_index(drop=True)
df["loan_id"] = ["KE-LN-%06d" % i for i in range(1, N + 1)]

# ---------- 7. Make it messy like a real system export ----------
raw = df.copy()
raw["disbursement_date"] = raw["disbursement_date"].dt.strftime("%Y-%m-%d")
slash = rng.random(N) < 0.12                                   # 12% of dates in dd/mm/yyyy
raw.loc[slash, "disbursement_date"] = pd.to_datetime(df.loc[slash, "disbursement_date"]).dt.strftime("%d/%m/%Y")
messy = rng.random(N) < 0.08                                   # inconsistent county spelling / spaces
raw.loc[messy, "county"] = raw.loc[messy, "county"].str.upper()
raw.loc[rng.random(N) < 0.05, "county"] = raw["county"] + " "
raw["gender"] = raw["gender"].map(lambda g: rng.choice([g, g[0], g.lower()], p=[.85, .08, .07]))
raw.loc[rng.random(N) < 0.04, "monthly_income_kes"] = np.nan   # missing income
raw.loc[rng.random(N) < 0.06, "crb_score"] = np.nan            # no CRB record found
raw = pd.concat([raw, raw.sample(25, random_state=1)]).sample(frac=1, random_state=2).reset_index(drop=True)  # 25 duplicate rows
raw.to_csv("data/raw_loans.csv", index=False)
print("Saved data/raw_loans.csv with", len(raw), "rows")
