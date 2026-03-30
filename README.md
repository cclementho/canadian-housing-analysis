# Canadian Housing Affordability Analysis

My generation is being priced out of Canadian cities. This project uses real Statistics Canada data to quantify exactly how that happened — which markets moved fastest, when affordability broke down, and how much worse things got after COVID.

It combines new housing price data with median household income to show not just that prices rose, but that they outpaced what people actually earn. The findings are fed into the Gemini API to generate a plain-English market summary, because most stakeholders don't read raw tables.

---

## What it does

- Loads two Statistics Canada datasets into a SQLite database
- Uses SQL to answer four core questions about Canadian housing affordability
- Builds interactive Plotly charts showing price trends, appreciation, and affordability over time
- Calls the Gemini API to generate an analyst-style summary of the key findings

---

## Tech stack

- Python
- SQLite
- SQL
- Pandas
- Plotly
- Gemini API
- Jupyter

---

## Data sources

Both datasets are free from Statistics Canada:

- **Table 18-10-0205-01** — New Housing Price Index (monthly, by city)
- **Table 11-10-0190-01** — Median After-Tax Income (annual, by city)

Download both CSVs and place them in the project folder before running `setup_db.py`.

- [Table 18-10-0205-01 — New Housing Price Index](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810020501)
- [Table 11-10-0190-01 — Median After-Tax Income](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110019001)

---

## How to run it

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/housing-analysis
cd housing-analysis
```

**2. Install dependencies**
```bash
pip install jupyter pandas plotly google-generativeai
```

**3. Add the Stats Can CSVs to the project folder**

Download from Statistics Canada (links above) and place `18100205.csv` and `11100190.csv` in the root of the project.

**4. Build the database**
```bash
python setup_db.py
```

This creates `housing.db` with two tables and an affordability view.

**5. Get a Gemini API key**

Go to [aistudio.google.com](https://aistudio.google.com), sign in with your Google account, and create a free API key.

**6. Set your API key**
```bash
export GEMINI_API_KEY="your-key-here"
```

**7. Open the notebook**
```bash
jupyter notebook housing_analysis.ipynb
```

Run all cells from top to bottom.

---

## Cities covered

Toronto, Vancouver, Calgary, Edmonton, Montreal, Ottawa, Winnipeg


## Key findings

- Ottawa had the fastest price appreciation of any city from 2010 to 2023 at +79%, which most people wouldn't guess
- Montreal jumped 17% in a single year during 2021, the sharpest COVID-era spike of any market
- Edmonton is the only city where prices have broadly kept pace with income growth
- Every other major market has seen prices outrun incomes, some by a significant margin
