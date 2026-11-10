# Kenya Loan Portfolio Risk Analysis

**Tools:** Python (Pandas, NumPy, Matplotlib) | Excel / Power BI (dashboard-ready CSV included)

> **Data disclosure:** All data in this project is **simulated**. It was generated with a Python script to resemble a Kenyan microfinance lender's loan book (counties, sectors, products, M-Pesa repayments, CRB-style scores). It contains no real customers, no real lender and no real CRB data. Findings describe the simulated portfolio only and are not claims about the real market.

## Business problem
A fictional Kenyan microfinance lender has KES 679M disbursed across 5,000 loans. Management wants to know **where credit risk is building, which borrower and loan characteristics predict non-performing loans (NPLs), and how much to provision**, so that lending policy can be tightened where it matters.

## Objectives
1. Clean a messy loan-system export.
2. Measure portfolio health with standard credit-risk KPIs (PAR30, NPL ratio, provisions).
3. Find which sectors, counties, products, credit-score bands and repayment burdens carry the most risk.
4. Recommend practical policy changes.

## Dataset (`data/`)
| File | Description |
|---|---|
| `raw_loans.csv` | 5,025 rows x 20 columns, as exported (includes the data-quality problems below) |
| `clean_loans.csv` | 5,000 loans after cleaning, with added risk columns (use this in Power BI) |

Key columns: `loan_id`, `disbursement_date`, `county` (18 counties), `business_sector`, `product` (Biashara, Kilimo, Chama Group, Emergency, Asset Finance, Salary Advance), `loan_amount_kes`, `term_months`, `interest_rate_flat_pct`, `monthly_income_kes`, `crb_score`, `collateral_type`, `repayment_channel` (M-Pesa Paybill, bank, cash, agent, payroll check-off), `outstanding_principal_kes`, `days_past_due`, `risk_class`, `loan_status`. Reporting date: 30 Sept 2025.

## Data cleaning
| Problem found | Fix |
|---|---|
| 25 duplicate rows | Removed |
| County spelling and spacing ("NAIROBI ", "Nairobi") | Trimmed and standardised |
| Gender coded as F / female / Female | Standardised to Female / Male |
| Two date formats mixed (yyyy-mm-dd and dd/mm/yyyy) | Converted to one date type |
| About 4% of monthly income missing | Filled with the sector median and flagged (`income_imputed`) |
| About 6% of CRB scores missing | Left missing and grouped as "No CRB score" (not guessed) |

## Metric definitions
- **PAR30:** outstanding principal more than 30 days past due, as a % of total outstanding principal.
- **NPL ratio:** outstanding principal more than 90 days past due, as a % of total outstanding principal.
- **Default rate:** share of all loans ever originated that are now more than 90 days past due (includes repaid loans, so cohorts compare fairly).
- **Repayment burden:** monthly installment divided by monthly income.
- **Provisions (illustrative):** Normal 1%, Watch 3%, Substandard 20%, Doubtful 50%, Loss 100%, approximating CBK prudential classes.

## Key findings
**Portfolio health:** outstanding principal is KES 296.8M. PAR30 is **20.3%** and the NPL ratio is **15.7%**. Estimated provisions are KES 34.4M, only **11.6%** of the book, below the NPL ratio, which signals a provisioning gap.

![Risk class mix](charts/risk_class_mix.png)

1. **Credit score is the strongest separator.** Loans with CRB scores of 300-500 default at **19.7%**, against **1.3%** for scores of 726-850. The 300-500 band holds 297 active loans worth KES 33.4M with a 33.4% NPL ratio.
   ![By score band](charts/npl_by_score_band.png)
2. **Affordability matters.** Loans where the installment is **over 35% of income** have a **12.2%** default rate, against **3.7%** when it is under 15%. These loans make up about 54% of the outstanding balance (KES 159.4M).
3. **Sector risk differs sharply.** Agriculture (30.7% NPL ratio), Services (23.8%) and Retail (22.6%) are the weakest. Transport (boda boda / matatu) carries the **largest exposure at KES 133.5M** with a 15.0% NPL ratio, so a shock there would hurt most.
   ![By sector](charts/npl_by_sector.png)
4. **County differences.** Kitui (32.2%), Kisii (27.7%) and Nyeri (24.8%) have the highest NPL ratios; Narok (6.6%), Uasin Gishu (8.3%) and Kericho (8.9%) the lowest. Several counties have fewer than 100 active loans, so treat county rankings as indicative.
   ![By county](charts/npl_by_county.png)
5. **Collateral and channel.** Personal-guarantor loans have a 25.2% NPL ratio and loans with no collateral 22.5%, versus 11.4% for logbook-secured and 16.4% for title-deed loans. Payroll check-off loans have the lowest default rate (1.0%).
6. **Cohort (vintage) effect.** Loans disbursed between 2023 Q3 and 2024 Q2 show default rates of 9.3-11.8%, above the later cohorts. The newest cohorts (2025 Q2-Q3) look clean mainly because they have not yet had time to default.
   ![Vintage](charts/npl_by_vintage.png)

## Recommendations
1. Set a minimum CRB score (or require extra security) for scores below 500, and tighten approval for 501-575.
2. Cap the installment-to-income ratio at about 35% for new loans.
3. Time agricultural repayments to harvest cycles, and review sector limits for agriculture, retail and services.
4. Set a concentration limit for transport lending and monitor it monthly.
5. Replace personal-guarantor-only lending with stronger security where the loan is above KES 150K.
6. Review the provisioning policy: the 11.6% coverage sits below the 15.7% NPL ratio.
7. Run county-level collection campaigns in Kitui, Kisii and Nyeri.

## Limitations
- The data is simulated, so relationships between variables were built in by design. The point of the project is the analytical workflow, not the specific numbers.
- Segments are analysed one at a time. A logistic regression or scorecard would be the next step to control for several factors at once.
- Provision rates are illustrative, not an official IFRS 9 or CBK calculation.
- Small counties and young cohorts have few observations.

## Learn the code
`loan_portfolio_analysis_notebook.ipynb` walks through the whole analysis step by step with explanations, a groupby primer, practice questions and interview prompts.

## How to run
```bash
pip install pandas numpy matplotlib
python scripts/01_generate_data.py        # builds data/raw_loans.csv
python scripts/02_clean_and_analyse.py    # builds clean data, tables/ and charts/
```
