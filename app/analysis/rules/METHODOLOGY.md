# Scoring Methodology — Human-Readable Reference

This file describes **what each rating band means** in the analysis engine, so anyone
(new developer, curious reader, or future-us tuning the model) can see the rules at a
glance without reading Python.

> **Source of truth is still the code.** All thresholds below are copied from the
> per-sector Python files (e.g. [`commercial_bank.py`](commercial_bank.py),
> [`hydro_power.py`](hydro_power.py)). If you change a number, change it
> **in the Python file** — this document is a mirror for humans, not for the engine.
> After changing thresholds, update this file too and bump `methodology_version` in
> the sector rules (currently `1.0` for both sectors).

Contents:
1. [How scoring works](#how-scoring-works)
2. [Overall rating scale](#overall-rating-scale)
3. [Category weights](#category-weights-balanced-profile)
4. [Profile overrides](#profile-overrides)
5. [Sector: Commercial Banks](#sector-commercial-banks) — every metric + bands
6. [Sector: Hydro Power](#sector-hydro-power) — every metric + bands
7. [How to change a rule](#how-to-change-a-rule)

---

## How scoring works

```
raw metric value  →  matches a Band  →  metric score (0–100)
                                          ↓
                            weighted inside its category
                                          ↓
                              category score (0–100)
                                          ↓
              weighted by profile → overall / quality / valuation
```

- **Direction** — each metric is either `HIGHER_IS_BETTER` (e.g. ROE) or
  `LOWER_IS_BETTER` (e.g. NPL). The bands are written accordingly.
- **Bands** — five ordered buckets; the first that contains the value wins.
  Each band awards a fixed score: excellent = 100, good = 80, fair = 60,
  weak = 40, very_weak = 20.
- **Missing data** — a metric with no value gets a neutral **50** (labelled
  `unknown`) so it neither helps nor hurts the overall score.
- **Metric weights** — normalised inside their category. Category weights are
  normalised across the whole sector.

## Overall rating scale

Applied to the final 0–100 score (`base.py::rating_from_score`).

| Score        | Rating       |
|--------------|--------------|
| **≥ 85**     | excellent    |
| **70 – 84**  | good         |
| **55 – 69**  | fair         |
| **40 – 54**  | weak         |
| **< 40**     | very_weak    |

## Category weights (balanced profile)

For Commercial Banks. Facets: **Q** = counted in the "Company Quality" score,
**V** = counted in the "Valuation" score.

| Category           | Weight | Facet |
|--------------------|-------:|:-----:|
| Profitability      | 0.18   | Q     |
| Growth             | 0.15   | Q     |
| Asset Quality      | 0.15   | Q     |
| Capital Strength   | 0.12   | Q     |
| Efficiency         | 0.08   | Q     |
| Dividend           | 0.07   | Q     |
| Valuation          | 0.25   | V     |

## Profile overrides

Selecting a non-default profile in the app re-weights the categories. Any category
not listed inherits nothing — the override map fully replaces the balanced weights
for that profile.

| Category         | balanced | quality | growth | dividend | risk | valuation |
|------------------|---------:|--------:|-------:|---------:|-----:|----------:|
| Profitability    | 0.18     | 0.22    | 0.22   | 0.18     | 0.15 | 0.16      |
| Growth           | 0.15     | 0.16    | 0.30   | 0.06     | 0.06 | 0.12      |
| Asset Quality    | 0.15     | 0.20    | 0.13   | 0.13     | 0.28 | 0.13      |
| Capital Strength | 0.12     | 0.16    | 0.10   | 0.12     | 0.22 | 0.10      |
| Efficiency       | 0.08     | 0.10    | 0.05   | 0.06     | 0.08 | 0.07      |
| Dividend         | 0.07     | 0.08    | 0.05   | 0.30     | 0.06 | 0.07      |
| Valuation        | 0.25     | 0.08    | 0.15   | 0.15     | 0.15 | 0.35      |

---

## Sector: Commercial Banks

_Values shown in **%** unless otherwise noted. Bands are read top→bottom; the first that contains the value wins._

### Profitability

#### ROE — Return on Equity  (higher is better, weight 1.0)
*How efficiently the bank generates profit from shareholder equity.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 18%        | 100   |
| Good       | 14% – 18%    | 80    |
| Fair       | 10% – 14%    | 60    |
| Weak       | 6% – 10%     | 40    |
| Very weak  | < 6%         | 20    |

#### ROA — Return on Assets  (higher is better, weight 0.7)
*How efficiently total assets are turned into profit — broader than ROE.*

| Band       | Range          | Score |
|------------|----------------|------:|
| Excellent  | ≥ 1.8%         | 100   |
| Good       | 1.4% – 1.8%    | 80    |
| Fair       | 1.0% – 1.4%    | 60    |
| Weak       | 0.6% – 1.0%    | 40    |
| Very weak  | < 0.6%         | 20    |

#### NIM — Net Interest Margin  (higher is better, weight 0.6)
*Spread between interest earned on loans and interest paid on deposits.*

| Band       | Range          | Score |
|------------|----------------|------:|
| Excellent  | ≥ 4.5%         | 100   |
| Good       | 3.5% – 4.5%    | 80    |
| Fair       | 2.8% – 3.5%    | 60    |
| Weak       | 2.2% – 2.8%    | 40    |
| Very weak  | < 2.2%         | 20    |

### Growth

#### Net Profit Growth (YoY)  (higher is better, weight 1.0)
*Sustained profit growth suggests business momentum.*

| Band       | Range         | Score |
|------------|---------------|------:|
| Excellent  | ≥ 20%         | 100   |
| Good       | 10% – 20%     | 80    |
| Fair       | 3% – 10%      | 60    |
| Weak       | −5% – 3%      | 40    |
| Very weak  | < −5%         | 20    |

#### EPS Growth (YoY)  (higher is better, weight 0.9)
*Per-share earnings improvement — matters because share count can change via bonus/right issues.*

| Band       | Range         | Score |
|------------|---------------|------:|
| Excellent  | ≥ 18%         | 100   |
| Good       | 8% – 18%      | 80    |
| Fair       | 2% – 8%       | 60    |
| Weak       | −5% – 2%      | 40    |
| Very weak  | < −5%         | 20    |

### Asset Quality

#### NPL — Non-Performing Loans  (lower is better, weight 1.0)
*High NPL forces provisioning and hurts distributable profit.*

| Band       | Range         | Score |
|------------|---------------|------:|
| Excellent  | ≤ 2%          | 100   |
| Good       | 2% – 3%       | 80    |
| Fair       | 3% – 5%       | 60    |
| Weak       | 5% – 6%       | 40    |
| Very weak  | > 6%          | 20    |

#### Provision Coverage  (higher is better, weight 0.6)
*Reserves set aside against potentially bad loans.*

| Band       | Range           | Score |
|------------|-----------------|------:|
| Excellent  | ≥ 120%          | 100   |
| Good       | 100% – 120%     | 80    |
| Fair       | 80% – 100%      | 60    |
| Weak       | 60% – 80%       | 40    |
| Very weak  | < 60%           | 20    |

### Capital Strength

#### CAR — Capital Adequacy Ratio  (higher is better, weight 1.0)
*Capital cushion against risk-weighted assets. NRB floor is ~11%; anything near the floor leaves no buffer.*

| Band       | Range            | Score |
|------------|------------------|------:|
| Excellent  | ≥ 14%            | 100   |
| Good       | 12.5% – 14%      | 80    |
| Fair       | 11.5% – 12.5%    | 60    |
| Weak       | 11% – 11.5%      | 40    |
| Very weak  | < 11%            | 20    |

#### CD Ratio — Credit-to-Deposit  (lower is better, weight 0.4)
*Regulatory ceiling ~90%; healthier well below.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≤ 82%        | 100   |
| Good       | 82% – 85%    | 80    |
| Fair       | 85% – 88%    | 60    |
| Weak       | 88% – 90%    | 40    |
| Very weak  | > 90%        | 20    |

### Efficiency

#### Cost of Fund  (lower is better, weight 0.8)
*Lower cost of funds improves the interest spread.*

| Band       | Range         | Score |
|------------|---------------|------:|
| Excellent  | ≤ 4.5%        | 100   |
| Good       | 4.5% – 5.5%   | 80    |
| Fair       | 5.5% – 6.5%   | 60    |
| Weak       | 6.5% – 7.5%   | 40    |
| Very weak  | > 7.5%        | 20    |

#### Base Rate  (lower is better, weight 0.4)
*A lower base rate suggests cheaper funding and supports loan competitiveness.*

| Band       | Range         | Score |
|------------|---------------|------:|
| Excellent  | ≤ 6.5%        | 100   |
| Good       | 6.5% – 7.5%   | 80    |
| Fair       | 7.5% – 8.5%   | 60    |
| Weak       | 8.5% – 9.5%   | 40    |
| Very weak  | > 9.5%        | 20    |

### Dividend

#### Dividend Yield  (higher is better, weight 1.0)
*Total dividend (cash + bonus) relative to market price.*

| Band       | Range      | Score |
|------------|------------|------:|
| Excellent  | ≥ 8%       | 100   |
| Good       | 5% – 8%    | 80    |
| Fair       | 3% – 5%    | 60    |
| Weak       | 1% – 3%    | 40    |
| Very weak  | < 1%       | 20    |

#### Distributable Profit / Share  (higher is better, weight 0.8, unit **Rs**)
*How much the company can realistically pay as dividend.*

| Band       | Range              | Score |
|------------|--------------------|------:|
| Excellent  | ≥ Rs 25            | 100   |
| Good       | Rs 15 – Rs 25      | 80    |
| Fair       | Rs 8 – Rs 15       | 60    |
| Weak       | Rs 2 – Rs 8        | 40    |
| Very weak  | < Rs 2             | 20    |

### Valuation

#### P/E Ratio  (lower is better, weight 1.0, unit **x**)
*Lower P/E generally = cheaper relative to earnings.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≤ 10x        | 100   |
| Good       | 10x – 15x    | 80    |
| Fair       | 15x – 20x    | 60    |
| Weak       | 20x – 25x    | 40    |
| Very weak  | > 25x        | 20    |

#### P/B Ratio  (lower is better, weight 1.0, unit **x**)
*Compares market price to book value; very high P/B may indicate optimistic pricing.*

| Band       | Range          | Score |
|------------|----------------|------:|
| Excellent  | ≤ 1.2x         | 100   |
| Good       | 1.2x – 1.8x    | 80    |
| Fair       | 1.8x – 2.5x    | 60    |
| Weak       | 2.5x – 3.2x    | 40    |
| Very weak  | > 3.2x         | 20    |

---

## Sector: Hydro Power

_Values shown in **%** unless otherwise noted (D/E and interest coverage are **x**). Bands are read top→bottom; the first that contains the value wins._

Hydropower is capital-intensive and project-driven: financials are dominated by leverage during construction, then swing to strong margins and dividends once the plant is commissioned and debt is paid down. Bands reflect that reality rather than mechanically reusing bank thresholds.

### Category weights (balanced profile)

| Category         | Weight | Facet |
|------------------|-------:|:-----:|
| Profitability    | 0.20   | Q     |
| Growth           | 0.15   | Q     |
| Financial Risk   | 0.20   | Q     |
| Operations       | 0.10   | Q     |
| Dividend         | 0.10   | Q     |
| Valuation        | 0.25   | V     |

### Profile overrides (Hydro Power)

| Category        | balanced | quality | growth | dividend | risk | valuation |
|-----------------|---------:|--------:|-------:|---------:|-----:|----------:|
| Profitability   | 0.20     | 0.24    | 0.20   | 0.18     | 0.15 | 0.18      |
| Growth          | 0.15     | 0.16    | 0.30   | 0.12     | 0.15 | 0.12      |
| Financial Risk  | 0.20     | 0.22    | 0.15   | 0.15     | 0.30 | 0.15      |
| Operations      | 0.10     | 0.14    | 0.10   | 0.10     | 0.15 | 0.10      |
| Dividend        | 0.10     | 0.14    | 0.10   | 0.30     | 0.10 | 0.10      |
| Valuation       | 0.25     | 0.10    | 0.15   | 0.15     | 0.15 | 0.35      |

### Profitability

#### ROE — Return on Equity  (higher is better, weight 1.0)
*Mature plants generate strong ROE once project debt is paid down.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 20%        | 100   |
| Good       | 14% – 20%    | 80    |
| Fair       | 10% – 14%    | 60    |
| Weak       | 6% – 10%     | 40    |
| Very weak  | < 6%         | 20    |

#### ROA — Return on Assets  (higher is better, weight 0.7)
*Hydropower is asset-heavy, so ROA runs lower than banking. Trend matters more than absolute number.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 8%         | 100   |
| Good       | 5% – 8%      | 80    |
| Fair       | 3% – 5%      | 60    |
| Weak       | 1.5% – 3%    | 40    |
| Very weak  | < 1.5%       | 20    |

#### Net Profit Margin  (higher is better, weight 0.7)
*Fuel cost is zero and revenue comes from a fixed PPA tariff — operational plants earn very high margins.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 45%        | 100   |
| Good       | 30% – 45%    | 80    |
| Fair       | 20% – 30%    | 60    |
| Weak       | 10% – 20%    | 40    |
| Very weak  | < 10%        | 20    |

### Growth

#### Net Profit Growth (YoY)  (higher is better, weight 1.0)
*Growth comes from tariff revisions, new units, or improved hydrology. Year-to-year swings are normal because of monsoon variance.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 25%        | 100   |
| Good       | 12% – 25%    | 80    |
| Fair       | 3% – 12%     | 60    |
| Weak       | −8% – 3%     | 40    |
| Very weak  | < −8%        | 20    |

#### EPS Growth (YoY)  (higher is better, weight 0.9)
*Per-share earnings improvement — matters because bonus/right issues are common.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 20%        | 100   |
| Good       | 8% – 20%     | 80    |
| Fair       | 2% – 8%      | 60    |
| Weak       | −8% – 2%     | 40    |
| Very weak  | < −8%        | 20    |

### Financial Risk

#### Debt-to-Equity  (lower is better, weight 1.0, unit **x**)
*Hydro projects are debt-funded, so leverage matters more than in most sectors. Very high D/E raises refinancing risk if hydrology or tariffs disappoint.*

| Band       | Range          | Score |
|------------|----------------|------:|
| Excellent  | ≤ 0.8x         | 100   |
| Good       | 0.8x – 1.5x    | 80    |
| Fair       | 1.5x – 2.5x    | 60    |
| Weak       | 2.5x – 3.5x    | 40    |
| Very weak  | > 3.5x         | 20    |

#### Interest Coverage  (higher is better, weight 0.9, unit **x**)
*Operating profit ÷ interest expense. Below 1.5x, the company is barely earning enough to service its debt.*

| Band       | Range          | Score |
|------------|----------------|------:|
| Excellent  | ≥ 6x           | 100   |
| Good       | 4x – 6x        | 80    |
| Fair       | 2.5x – 4x      | 60    |
| Weak       | 1.5x – 2.5x    | 40    |
| Very weak  | < 1.5x         | 20    |

### Operations

#### Plant Load Factor  (higher is better, weight 1.0)
*Fraction of rated capacity actually generated over the year. Nepali run-of-river plants typically sit in the 40–60% range.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 60%        | 100   |
| Good       | 50% – 60%    | 80    |
| Fair       | 40% – 50%    | 60    |
| Weak       | 30% – 40%    | 40    |
| Very weak  | < 30%        | 20    |

### Dividend

#### Dividend Yield  (higher is better, weight 1.0)
*Total dividend (cash + bonus) relative to market price. Mature hydros with paid-down debt often pay meaningfully.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 8%         | 100   |
| Good       | 5% – 8%      | 80    |
| Fair       | 3% – 5%      | 60    |
| Weak       | 1% – 3%      | 40    |
| Very weak  | < 1%         | 20    |

#### Payout Ratio  (higher is better, weight 0.6)
*Share of earnings paid out as dividend. Newer projects reinvest more (low payout), matured ones return more to shareholders.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≥ 60%        | 100   |
| Good       | 40% – 60%    | 80    |
| Fair       | 20% – 40%    | 60    |
| Weak       | 5% – 20%     | 40    |
| Very weak  | < 5%         | 20    |

### Valuation

#### P/E Ratio  (lower is better, weight 1.0, unit **x**)
*Hydropower P/E is often elevated when the market prices in future project completion.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≤ 12x        | 100   |
| Good       | 12x – 18x    | 80    |
| Fair       | 18x – 25x    | 60    |
| Weak       | 25x – 35x    | 40    |
| Very weak  | > 35x        | 20    |

#### P/B Ratio  (lower is better, weight 1.0, unit **x**)
*Very high P/B may indicate an optimistically priced expansion story.*

| Band       | Range        | Score |
|------------|--------------|------:|
| Excellent  | ≤ 1.2x       | 100   |
| Good       | 1.2x – 2.0x  | 80    |
| Fair       | 2.0x – 3.0x  | 60    |
| Weak       | 3.0x – 4.5x  | 40    |
| Very weak  | > 4.5x       | 20    |

---

## How to change a rule

1. Edit the relevant `MetricRule` in [`commercial_bank.py`](commercial_bank.py) —
   change the `Band(...)` `min`/`max` bounds, or the metric/category weights.
2. Update the matching table in this file so the two stay in sync.
3. Bump `methodology_version` in `COMMERCIAL_BANK_RULES` (bottom of the same
   Python file). Historical analyses embed the version they were generated with,
   so bumping is important for audit-ability.
4. Restart the backend — rules are read at import time.

### Adding a new metric

1. Add a `MetricRule(...)` inside the `METRICS` tuple with a fresh `key`.
2. Ensure the ingestion path populates that key on `FinancialMetric.metric_key`
   for the relevant companies — otherwise the metric will always score as
   `unknown` (50).
3. Add a section to this file so the rule is visible.

### Adding a new sector

1. Create `app/analysis/rules/<sector>.py` mirroring the layout of
   `commercial_bank.py` — its own `CATEGORIES`, `METRICS`, and
   `PROFILE_OVERRIDES`.
2. Register it in `app/analysis/rules/__init__.py::SECTOR_RULES`.
3. Add a matching section to this document.

---

_Disclaimer: bands are informed by common Nepalese sector norms (for banks: NRB CAR floor, typical NPL / ROE / NIM ranges; for hydro: PPA-tariff economics, run-of-river PLF ranges, project-financing leverage) but are **not** regulatory recommendations. The whole point of this file is that they are easy to tune — treat them as a starting reference and refine as real data accumulates._
