# Assumptions and Sources

Every input used by `Params` in `src/mms_growth_model.py`, with where it comes from.

## Machine economics

| Parameter | Value | Source |
|---|---|---|
| Machine price | 400,000 ETB | Mezewir price |
| Throughput | 40 qt/hr | Mezewir base case |
| Hours per day | 6 | Mezewir financial model |
| Days per season | 50 | Mezewir financial model |
| Service fee | 70 ETB/quintal | Mezewir financial model |
| Operators per machine | 10 | Mezewir base case |
| Operator wage | 500 ETB/worker/day | Mezewir financial model |
| Fuel consumption | 1.65 L/hr | Mezewir financial model |
| Fuel price | 200 ETB/L | Mezewir financial model |
| Maintenance, season 1 | 8,000 ETB | 3 oil changes at 1.5 L and 1,450 ETB/L, plus one V-belt at 1,250 ETB |
| Maintenance escalation | 35% per year of machine age | Added assumption, not measured |

Derived per machine per season: 12,000 quintals, 840,000 ETB revenue,
250,000 ETB operator wages, 99,000 ETB fuel, **483,000 ETB net to the owner**.

## Promotion ladder

| Parameter | Value | Basis |
|---|---|---|
| Minimum service before eligibility | 2 seasons | Programme design choice |
| Promotion rate | 8% of eligible per year | Added assumption. Governed by credit availability and owner recommendation, not by operator ambition |
| Operator savings rate | 30% of wages | Added assumption |

An operator earning 25,000 ETB a season and saving 30 percent accumulates
15,000 ETB over two seasons, which becomes the down payment on their machine.

## Market reference

| Parameter | Value | Source |
|---|---|---|
| Amhara maize volume | 26,000,000 qt/season | CSA Agricultural Sample Survey 2021/22 (2014 E.C.), Vol. I, Area and Production of Major Crops, Private Peasant Holdings, Meher Season |
| Maize per smallholder | 17.75 qt | Same source, West Gojam maize row: 623,797 holders, 242,120.81 ha, 11,070,933.30 qt, yield 45.72 qt/ha |
| Households per machine | 676 | 12,000 / 17.75 |
| 20% coverage | 433 machines | 0.20 x 26,000,000 / 12,000 |
| 40% coverage | 867 machines | 0.40 x 26,000,000 / 12,000 |

The 17.75 figure is West Gojam, a high production zone, not a regional average.
If holdings elsewhere in Amhara are smaller, each machine serves more households
than modelled, so the farmer reach figure is conservative.

## Supply constraint

| Parameter | Value | Basis |
|---|---|---|
| Manufacturing capacity, year 1 | 50 machines | Mezewir current capacity |
| Capacity growth | 45% per year | Added assumption |

## Mechanisation context

| Finding | Value | Source |
|---|---|---|
| Agricultural activities mechanically operated, Amhara | 4.35% | Tesfaye and others, Benchmarking the Status of Agricultural Mechanization in Ethiopia, SSRN 3968527 |
| Same, Oromia / SNNP / Tigray | 12.1% / 4.38% / 3.48% | Same |
| Mechanically operated activities, maize, national | 5.20% | Same |
| Farmers using mechanisation services, national | about 9% | Berhane and others 2016, cited in Cogent Economics and Finance 10.1080/23322039.2023.2225328 |
| Households renting machinery who rent a maize sheller, West Gojjam | 28.54% | Cogent Food and Agriculture 10.1080/23311932.2024.2380123 |
| Threshing or shelling machine fabricators in Amhara | none reported | Getachew and others, AJFAND 2022, 10.18697/ajfand.111.22105 |

## Labour market context

| Finding | Value | Source |
|---|---|---|
| Rural unemployment rate, Ethiopia | 3.58% (2021) | Ethiopian labour force survey, reviewed in Journal of Youth Studies 10.1080/02673843.2024.2322564 |
| Rural employed who are underemployed | about 27% | CSA 2014, same review |
| Young people entering the workforce each year | 2 to 3 million | UNDP, same review |

Rural unemployment is low because unpaid family labour and self-employment
absorb most people. The measured problem is underemployment. This programme
converts underemployment into paid work and then into ownership. It should not
be described as reducing an unemployment rate.

## Independent evidence on mechanical shelling

| Finding | Source |
|---|---|
| Ethiopian maize sheller: NPV 8,227 USD, BCR 3.51, IRR 133% | Getachew and others, AJFAND 2022 |
| Motorised sheller cut shelling losses from 6.8% to 2.0% | Mutungi and others, in Food Security 10.1007/s12571-023-01365-5 |
| Traditional post harvest handling loses 15 to 20% of produce | Getachew and others, AJFAND 2022 |
| Hand shelling work rate about 10 kg/hr; 8 to 20 kg/hr with a hand tool | FAO t0522e and t1838e |

## Methods

| Method | Reference |
|---|---|
| Logistic adoption curve | Bass, F. M. (1969). A New Product Growth for Model Consumer Durables. Management Science 15(5), 215 to 227 |
| Monte Carlo simulation | Metropolis, N. and Ulam, S. (1949). The Monte Carlo Method. JASA 44(247), 335 to 341 |

## What the model does not include

- Inflation. All figures are constant 2026 birr.
- Cost of capital. Repayment is modelled at face value. A lease or loan carrying
  15 to 18 percent would reduce owner income by roughly 50,000 to 70,000 ETB
  over two seasons.
- Taxes, depreciation, machine replacement, and transport between sites.
- Currency risk. Prices are fixed in birr; USD figures convert at 170 ETB/USD
  and are indicative only.

## Co-financing (placeholder terms)

Defined in `src/financing.py`. **These are illustrative, not quoted terms.**

| Parameter | Default | Basis |
|---|---|---|
| Youth equity share | 5% (20,000 ETB) | roughly what an operator saves in two seasons |
| Partner fund share | 45% (180,000 ETB) | interest free, repaid over 2 seasons |
| Lease facility share | 50% (200,000 ETB) | placeholder |
| Lease rate | 14.5% nominal | placeholder, in the range Ethiopian capital goods finance companies have charged |
| Lease tenor | 3 seasons | placeholder |

Derived: lease payment 86,870 ETB a season, total interest 60,610 ETB, cost of
capital about 15 percent of the machine price. The one million birr milestone
moves from season 3 to season 4.

Replace all five parameters with the lessor's indicative terms before this
model informs any commitment. Candidate lessors in Amhara include Waliya
Capital Goods Finance Company and the Development Bank of Ethiopia lease
financing window, both of which have financed agricultural mechanisation and
favour locally manufactured equipment. Confirm current terms directly, as
published information may be out of date.

## Consistency note

The promotion ladder and the co-financing section use the same `FinancePlan`.
When an operator is promoted, their accumulated savings become the equity on
their own machine and the remaining principal is split between the partner fund
and the lease facility in the same proportion as the programme-level plan. This
means every figure in the README, the charts and the CSV outputs rests on one
set of financing assumptions rather than two.

Calling `promotion_ladder(p)` without a plan still returns the face-value path,
which is useful for isolating the effect of financing cost on its own.
