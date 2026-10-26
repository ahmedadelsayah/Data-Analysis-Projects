# P1 Sales Dashboard (Excel)

An interactive **Excel dashboard** built on four years of retail sales data (2014–2017). It uses a Power Query + Power Pivot data model, PivotTables, PivotCharts, and slicers to analyze **customers, products, and orders** across three dashboard sheets.

> **Tools:** Excel · Power Query · Power Pivot (Data Model) · PivotTables & PivotCharts · Slicers

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Headline Numbers](#headline-numbers)
3. [Workbook Structure](#workbook-structure)
4. [Dashboards](#dashboards)
5. [Dataset](#dataset)
6. [How to Use](#how-to-use)
7. [Notes and Possible Improvements](#notes-and-possible-improvements)

---

## Project Overview

The goal is to give a quick, visual answer to common sales questions:

- How much do we sell, what does it cost, and what profit do we make?
- Who are our customers, and where are they (state, city, region, segment)?
- Which products, categories, and sub-categories sell the most?
- How do shipping mode, discounts, and customer segment affect orders and profit?

---

## Headline Numbers

| KPI | Value |
|-----|------:|
| Total Sales | $2,394,385 |
| Total Cost | $2,094,745 |
| Total Profit | $299,640 |
| Profit % (as shown in the report) | 14.30% |
| Total Orders | 5,009 |
| Total Customers | 793 |
| Total Products sold | 1,862 |
| Segments / States / Cities | 3 / 41 / 252 |
| Categories / Sub-Categories | 3 / 17 |
| Period covered | 3 Jan 2014 – 30 Dec 2017 |

---

## Workbook Structure

| Sheet | Role |
|-------|------|
| `Orders` | Fact table: 10,330 order lines (order and ship dates, ship mode, customer, product, sales, quantity, discount, cost, profit). Also carries customer and product attributes. |
| `Customers` | Customer dimension: 793 customers (name, segment, country, city, state, region). |
| `Products` | Product dimension: 1,894 products (category, sub-category, product name). |
| `Sheet1` | Working sheet: all KPI pivots, chart pivots, and the PivotCharts that feed the dashboards, plus the full set of 8 slicers. |
| `Sheet7` | Helper pivot: product count by sub-category. |
| `D.Customers` | **Dashboard:** customers |
| `D.Products` | **Dashboard:** products |
| `D.Orders` | **Dashboard:** orders, sales, and profit |

The three source sheets are Excel tables loaded through **Power Query** and kept in the workbook **Data Model**, so the pivots and slicers all share the same data.

---

## Dashboards

### D.Customers: *Sales Dashboard (Customers)*

- **KPI cards:** Total Customers, Total Segments, Total States, Total Cities
- **Charts:** Customers by State, Customers by Segment, Customers by City, Customers by Region, Top Customers by Order Count
- **Slicers:** Region, Segment, State

### D.Products: *Sales Dashboard (Products)*

- **KPI cards:** Total Product, Number of distinct Categories, Number of distinct Sub-Categories
- **Charts:** Product Count by Sub-Category, Top Products by Quantity, Top Products by Sales, Sub-Categories per Category
- **Slicers:** Category, Sub-Category

### D.Orders: orders, sales, and profit

- **KPI cards:** Total Orders, Total Sales, Total Cost, Total Profit, Profit %
- **Charts:** Orders over time, Top 5 Orders by Cost, Orders by Ship Mode, Average Discount by Category, Profit by Category, Orders by Segment & Category
- **Slicers:** Order Date (Year), Category, Ship Mode, Segment

---

## Dataset

**Orders** (one row per product line in an order)

| Column | Description |
|--------|-------------|
| Order ID, Order Date, Ship Date, Ship Mode | Order and shipping info (Standard, Second, First Class, Same Day) |
| Customer ID, Product ID | Keys to `Customers` and `Products` |
| Sales, Quantity, Discount, Cost | Transaction values |
| Profit | `Sales - Cost` |
| Customers.* / Products.* | Customer and product attributes merged into the table by Power Query |

**Customers:** Customer ID, Customer Name, Segment, Country, City, State, Region
**Products:** Product ID, Category, Sub-Category, Product Name

---

## How to Use

1. Open `P1_Sales_dashboard.xlsx` in desktop **Excel** (2016 or later is recommended, since slicers and the Data Model need it).
2. Go to one of the dashboard sheets: `D.Customers`, `D.Products`, or `D.Orders`.
3. Click the slicers to filter. Hold **Ctrl** to select several values, and use the clear-filter icon to reset.
4. To refresh after changing the source tables, use **Data → Refresh All**.

---

## Notes and Possible Improvements

- **Profit % definition:** the report shows 14.30%, which equals `Profit / Cost`. Profit divided by Sales is about 12.5%. If you mean profit margin, consider changing the formula or renaming the KPI to "Markup %".
- **KPI cards may not react to slicers:** the KPI boxes on the dashboards appear to be static text rather than cell-linked shapes. Linking each one to its KPI pivot cell would make them update with the filters.
- **Profit is stored as values** in the `Orders` table (not a formula), so it will not update if Sales or Cost are edited.
- Several charts show **top-N** results (for example the top five states and cities), so they do not represent every state or city.
- `Sheet1` and `Sheet7` are generic names. Renaming them (for example `Pivots_Calc`) would make the workbook easier to maintain.
- Add screenshots of the three dashboards to this README (for example in an `images/` folder) to make the project easier to review.
