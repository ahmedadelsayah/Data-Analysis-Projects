import pandas as pd
import numpy as np
from pathlib import Path

# FIX 1: paths relative to the script folder (D:\Eraa soft\clean data)
BASE = Path(__file__).resolve().parent

# Read files
Sales = pd.read_csv(BASE / 'Sales.csv')
Products = pd.read_csv(BASE / 'products_catalog.csv')
customers = pd.read_csv(BASE / 'customers_master.csv')
prescriptions = pd.read_csv(BASE / 'prescriptions_log.csv')


# Sales
Sales = Sales.drop_duplicates()
Sales = Sales.drop(columns=['Promo Code(excel)'])

# FIX 2: keep sale_date as a real datetime (saved as YYYY-MM-DD at the end)
Sales['sale_date'] = pd.to_datetime(
    Sales['sale_date'],
    format='%d/%m/%Y',
    errors='coerce'
)
print('Bad sale_date values:', Sales['sale_date'].isna().sum())

Sales['promo_code'] = Sales['notes'].str.extract(
    r'Promo code (\w+) applied at checkout'
)[0]

# FIX 3: rows with no discount are not "loyalty_tier"
Sales['discount_reason'] = np.select(
    [
        Sales['discount_pct'].eq(0),
        Sales['promo_code'].notna(),
        Sales['notes'].str.contains('competitor', case=False, na=False),
    ],
    ['none', 'promo_code', 'price_match'],
    default='loyalty_tier'
)


# Products
Products['pack_size'] = Products['pack_info'].str.extract(
    r'Pack: ([^|/]+)'
)[0].str.strip()

Products['strength'] = Products['pack_info'].str.extract(
    r'Strength: ([^|/]+)'
)[0].str.strip()

Products['form'] = Products['pack_info'].str.extract(
    r'Form: ([^|/]+)'
)[0].str.strip()


# Sales calculations
# FIX 4: one row per product_id so the merge cannot duplicate sales rows
cost_lookup = Products[['product_id', 'cost_price']].drop_duplicates('product_id')
print('Duplicate product_id in catalog:', len(Products) - len(cost_lookup))

rows_before = len(Sales)
Sales = Sales.merge(
    cost_lookup,
    on='product_id',
    how='left',
    validate='m:1'
)
assert len(Sales) == rows_before, 'merge changed the number of sales rows'
print('Sales rows without a matching product:', Sales['cost_price'].isna().sum())

Sales['total_amount'] = (
    Sales['quantity'] *
    Sales['unit_price'] *
    (1 - Sales['discount_pct'] / 100)
)

Sales['cost_amount'] = Sales['quantity'] * Sales['cost_price']

Sales['profit'] = (
    Sales['total_amount'] -
    Sales['cost_amount']
)

Sales['margin_pct'] = (
    Sales['profit'] /
    Sales['total_amount'] * 100
)

num_cols = Sales.select_dtypes('number').columns
Sales[num_cols] = Sales[num_cols].round(2)


# Prescriptions
# FIX 5: strip every repeated "Dr." prefix (was leaving "Dr. Dr. Lee")
prescriptions['doctor_name'] = (
    'Dr. ' +
    prescriptions['doctor_name']
    .str.replace(r'(?i)^(?:\s*dr\.?\s*)+', '', regex=True)
    .str.strip()
    .str.title()
)

# FIX 6: strip spaces before mapping so ' BID' / 'PRN ' are caught
prescriptions['dosage'] = prescriptions['dosage'].str.strip().replace({
    'PRN': 'As needed',
    'as needed': 'As needed',
    'BID': 'Twice daily',
    'Twice a day': 'Twice daily',
    '2x daily': 'Twice daily',
    '1x daily': 'Once daily',
    '1 tab/day': '1 tablet daily',
    'Inject once weekly': '1 injection weekly',
    'inj 1x/wk': '1 injection weekly',
    '5ml q6h': '5 ml every 6 hours'
})


# Customers
customers['loyalty_tier'] = customers['notes'].str.extract(
    r'(Silver|Gold|Platinum)'
)[0]

customers['loyalty_since'] = customers['notes'].str.extract(
    r'loyalty since (\d{4})'
)[0]

customers['city'] = (
    customers['city']
    .str.split(',')
    .str[0]
    .str.strip()
    .str.title()
)

# FIX 7: empty / missing phones stay NA instead of all collapsing into one '' value
customers['phone'] = (
    customers['phone']
    .astype('string')
    .str.replace(r'\D', '', regex=True)
    .replace('', pd.NA)
)

# FIX 8: only drop duplicates among customers that HAVE a phone number
dup_phone = customers['phone'].notna() & customers.duplicated('phone', keep='first')
print('Customers dropped as duplicate phone:', dup_phone.sum())
customers = customers[~dup_phone]


# Save files
Sales.to_csv(BASE / 'Sales_cleaned.csv', index=False, date_format='%Y-%m-%d')
Products.to_csv(BASE / 'products_cleaned.csv', index=False)
customers.to_csv(BASE / 'customers_cleaned.csv', index=False)
prescriptions.to_csv(BASE / 'prescriptions_cleaned.csv', index=False)

print('Done!')

# (The PySpark validation template was removed: it only runs inside Databricks, Phase 3.)


# =====================================================================
# VALIDATION (Phase 2) - runs on the cleaned tables above
# Outputs: validation_report.csv + referential_integrity_report.csv
# =====================================================================
TODAY = pd.Timestamp.today().normalize()


def find_csv(*keywords):
    """First raw csv in BASE whose name contains one of the keywords."""
    for p in sorted(BASE.glob('*.csv')):
        n = p.name.lower()
        if 'cleaned' in n or 'report' in n:
            continue
        if any(k in n for k in keywords):
            return p
    return None


def load_optional(label, *keywords):
    p = find_csv(*keywords)
    if p is None:
        print(f'[SKIP] {label}: no matching csv found in {BASE}')
        return None
    print(f'[LOAD] {label}: {p.name}')
    return pd.read_csv(p)


# Tables that are not part of the cleaning above (loaded as-is if found)
stores = load_optional('dim_store', 'store')
employees = load_optional('dim_employee', 'employee', 'staff')
stock = load_optional('fact_stock', 'stock', 'inventory')

issues = []
fk_rows = []


def has(df, *cols):
    return df is not None and all(c in df.columns for c in cols)


def row_ids(df, mask, id_col):
    if id_col in df.columns:
        return df.loc[mask, id_col].tolist()
    return df.index[mask].tolist()


def add_issues(table, ids, rule, severity):
    issues.extend(
        {'row_id': i, 'table': table, 'rule_violated': rule, 'severity': severity}
        for i in ids
    )


def check_fk(child_name, child, ccol, parent_name, parent, pcol, id_col):
    if not (has(child, ccol) and has(parent, pcol)):
        print(f'[SKIP] FK {child_name}.{ccol} -> {parent_name}.{pcol}: table or column missing')
        return
    ok = child[ccol].isin(parent[pcol])
    fk_rows.append({
        'table_pair': f'{child_name}.{ccol} -> {parent_name}.{pcol}',
        'total_rows': len(ok),
        'match_pct': round(ok.mean() * 100, 2),
        'orphan_count': int((~ok).sum()),
    })
    add_issues(child_name, row_ids(child, ~ok, id_col),
               f'FK orphan: {ccol} not found in {parent_name}', 'ERROR')


# ---- 1. Cross-table integrity (FK) ----
check_fk('fact_sales', Sales, 'product_id', 'dim_product', Products, 'product_id', 'sale_id')
check_fk('fact_sales', Sales, 'store_id', 'dim_store', stores, 'store_id', 'sale_id')
check_fk('fact_sales', Sales, 'customer_id', 'dim_customer', customers, 'customer_id', 'sale_id')
check_fk('fact_prescriptions', prescriptions, 'customer_id', 'dim_customer', customers,
         'customer_id', 'prescription_id')

# ---- 2. Business rules ----
# discount_pct and margin_pct are in percent (e.g. 12.5), so the limits are 50 and 80
if has(Sales, 'margin_pct', 'discount_pct', 'quantity'):
    add_issues('fact_sales', row_ids(Sales, Sales['margin_pct'] < 0, 'sale_id'),
               'margin_pct < 0 (sold below cost)', 'WARN')
    add_issues('fact_sales', row_ids(Sales, Sales['margin_pct'] > 80, 'sale_id'),
               'margin_pct > 80', 'WARN')
    add_issues('fact_sales', row_ids(Sales, Sales['discount_pct'] > 50, 'sale_id'),
               'discount_pct > 50 (policy ceiling)', 'ERROR')
    add_issues('fact_sales', row_ids(Sales, Sales['quantity'] < 0, 'sale_id'),
               'negative quantity', 'ERROR')

if has(employees, 'position', 'is_pharmacist'):
    is_pharmacist_position = employees['position'].astype(str).str.strip().str.lower().eq('pharmacist')
    flag_one = pd.to_numeric(employees['is_pharmacist'], errors='coerce').fillna(0).eq(1)
    add_issues('dim_employee', row_ids(employees, is_pharmacist_position & ~flag_one, 'employee_id'),
               "position = Pharmacist but is_pharmacist = 0", 'ERROR')
    add_issues('dim_employee', row_ids(employees, ~is_pharmacist_position & flag_one, 'employee_id'),
               "is_pharmacist = 1 but position <> Pharmacist", 'ERROR')

if has(stock, 'expiry_date', 'quantity'):
    expiry = pd.to_datetime(stock['expiry_date'], errors='coerce')
    qty = pd.to_numeric(stock['quantity'], errors='coerce')
    add_issues('fact_stock', row_ids(stock, (expiry < TODAY) & (qty > 0), 'stock_id'),
               'expired (expiry_date < today) but quantity > 0', 'ERROR')

if has(stock, 'quantity', 'reorder_level', 'below_reorder_flag'):
    qty = pd.to_numeric(stock['quantity'], errors='coerce')
    reorder = pd.to_numeric(stock['reorder_level'], errors='coerce')
    flagged = stock['below_reorder_flag'].astype(str).str.strip().str.lower().isin(['true', '1', '1.0'])
    add_issues('fact_stock', row_ids(stock, (qty <= reorder) & ~flagged, 'stock_id'),
               'quantity <= reorder_level but below_reorder_flag = 0', 'WARN')

# ---- 3. Reports ----
report = pd.DataFrame(issues, columns=['row_id', 'table', 'rule_violated', 'severity'])
report.to_csv(BASE / 'validation_report.csv', index=False)

fk_df = pd.DataFrame(fk_rows, columns=['table_pair', 'total_rows', 'match_pct', 'orphan_count'])
fk_df.to_csv(BASE / 'referential_integrity_report.csv', index=False)

print('\n===== Referential integrity =====')
print(fk_df.to_string(index=False) if len(fk_df) else 'No FK pair could be checked')

print('\n===== Rule violations =====')
if len(report):
    print(report.groupby(['table', 'rule_violated', 'severity']).size().to_string())
else:
    print('No violations found')

# ---- 4. Gate: every FK pair must have a join success rate above 99% ----
failed = fk_df[fk_df['match_pct'] <= 99]
if len(failed):
    raise SystemExit('\nVALIDATION FAILED - FK match rate must be above 99%:\n'
                     + failed.to_string(index=False))
print('\nVALIDATION PASSED (FK gate)')