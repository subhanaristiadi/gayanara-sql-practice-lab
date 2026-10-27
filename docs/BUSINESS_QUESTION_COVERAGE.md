# Business-question coverage audit

This audit uses the supplied **Gayanara — Business Questions** catalog (62 numbered questions) and the current Practice Lab exercise definitions. The additions below are grouped into existing parent exercises so the parent navigation remains at 20 groups.

## Newly added exercises

| Exercise ID | New sub-exercise | Business-question coverage |
|---|---|---|
| ex-01-s4 | Missing Values Across Every Column | #50 |
| ex-04-s2 | Peak Month by Revenue, Orders, and Units | #2 |
| ex-05-s5 | City Revenue Contribution | #4 |
| ex-07-s3 | Brand Ranking by Revenue and Units | #9–10 |
| ex-08-s2 | High-Demand Products with Low Current Stock | #11 |
| ex-09-s3 | Product Price Band Sales Summary | #14 |
| ex-10-s3 | Revenue and Buying Customers by Gender and Age Group | #18 |
| ex-10-s4 | Purchases by Customer Profile City and Province | #19 |
| ex-10-s5 | High-Value Customer Ranking and Revenue Contribution | #17, #21 |
| ex-13-s3 | Monthly Promo vs No-Promo Order Volume | #30 (descriptive association only) |
| ex-13-s4 | Frequently Used Promo Codes with Lower AOV | #32 |
| ex-15-s4 | Order Status Mix by Courier | #37 |
| ex-15-s5 | High-Volume Cities with Elevated Return Rates | #35, #38 |
| ex-16-s5 | Review Rating by Product Category and Brand | #47 |
| ex-20-s4 | Executive Capstone: Evidence for Three Priority Actions | #62 |

## Coverage still requiring dedicated follow-up

These additions improve coverage but do not claim that all 62 questions are fully resolved as standalone exercises. The following still need dedicated treatment or a careful coverage check:

- **#41:** highest-rated products, with a minimum review-count threshold; current exercises focus more on low-rated products.
- **#45:** percentage of reviews with missing `review_text`.
- **#46:** recurring praise/complaint themes from review text; this requires text-based analysis and must not infer sentiment from missing text.
- **#48:** an explicit product/customer-experience prioritization exercise.
- **#54:** potential duplicate orders, order items, and reviews.
- **#55:** broader anomaly screening and documented rules for what qualifies as anomalous.
- **#56:** a five-insight executive synthesis grounded in previously calculated results.
- **#59:** an explicit growth-opportunity analysis; high-return locations are operational risk signals, not automatically growth opportunities.

The app also has existing exercises that overlap with several questions. Before declaring complete coverage, inspect each existing exercise's metric definition, output grain, and SQL to confirm that it fully answers the corresponding question.

## Settled business definitions

These three thresholds were ambiguous in the original exercise text and are now explicit in both the SQL and the exercise metadata.

| Exercise | Ambiguity | Settled rule |
|---|---|---|
| ex-07-s1, ex-07-s2, ex-19-s1 | Which raw category spellings are the same product category | `Accessories`/`Aksesoris` → `Aksesoris`; `Celana`/`Pants` → `Celana`; `Kemeja`/`Shirt` → `Kemeja`; `Dress`, `Jacket`/`Jaket`, `Kaos`, `T-Shirt` collapse by case. Raw values in `products` are never rewritten. |
| ex-08-s2 | What "high demand" means | At least 20 valid units sold, combined with the existing low-stock rule of 5 units or fewer. |
| ex-15-s5 | What "elevated return rate" means | Return rate strictly above the current national return rate computed from all orders in the same dataset, with at least 100 orders per location. |

Because the return-rate benchmark is computed from the data rather than hard-coded, ex-15-s5 stays meaningful if the dataset changes.

## Metric and interpretation safeguards

- Valid sales exclude `cancelled` and `returned` orders.
- Order-level revenue uses `orders.total_amount_idr`; product/brand revenue uses `order_items.subtotal_idr` on valid orders.
- Units sold uses `order_items.quantity` on valid orders.
- AOV is valid revenue divided by valid order count.
- Promo usage means `promo_code IS NOT NULL`. Observational comparisons do not prove causal uplift or profitability.
- `products.stock` is a current snapshot, not historical inventory.
- Customer profile city/province and shipping destination are different fields and must not be conflated.
- Return and cancellation rates must state their denominator; operational status mix uses all orders.
- The dataset does not support delivery duration/SLA or reliable profitability analysis.

## Implementation status

- [x] Added 15 sub-exercises to `index.html`.
- [x] Added corresponding reference query IDs to `reference_queries.json`.
- [x] Updated the README exercise count.
- [x] Run all new reference queries against sample data and reconcile output columns with `expectedOutput`.
- [ ] Run all reference queries against the deployed PostgreSQL database.
- [ ] Smoke-test the deployed app and automatic validation endpoint after deployment.
