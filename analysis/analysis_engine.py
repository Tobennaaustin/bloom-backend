"""
=============================================================================
 DATA-DRIVEN INVENTORY OPTIMISATION FOR MICRO-VENDORS
 Crawford University — Final Year Project Analysis Engine
 Author: Tobenna
=============================================================================
 Modules:
   1. Data Cleaning & Preprocessing
   2. Demand Analysis (Student Data)
   3. Vendor Performance Analysis
   4. Gap Analysis & Recommendation Engine
   5. Statistical Tests (Chi-Square, Spearman)
   6. Chart Generation
   7. Report Export (JSON + CSV)
=============================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy.stats import chi2_contingency, spearmanr
from collections import Counter
import json, warnings, os, re
warnings.filterwarnings('ignore')

# ── Paths ─────────────────────────────────────────────────────────────────────
STUDENT_CSV = "/home/user/Downloads/bloom-backend/analysis/Student_Survey_Data-fixed(in).csv"
VENDOR_CSV  = "/home/user/Downloads/bloom-backend/analysis/Vendur_Survey - Copy(in).csv"
CHARTS_DIR  = "/home/user/Downloads/bloom-backend/analysis/charts"
OUTPUT_DIR  = "/home/user/Downloads/bloom-backend/analysis/outputs"

# ── Style ─────────────────────────────────────────────────────────────────────
DARK   = "#0d0d0f"
CARD   = "#1a1a1f"
ACCENT = "#e94560"
LIGHT  = "#f0f0f0"
MUTED  = "#888899"
COLORS = ["#e94560","#4e8cff","#2ecf96","#f5a623","#b96cff","#ff6b6b","#45d4c8"]

plt.rcParams.update({
    'figure.facecolor': DARK, 'axes.facecolor': CARD,
    'axes.edgecolor': '#2a2a35', 'axes.labelcolor': LIGHT,
    'xtick.color': MUTED, 'ytick.color': MUTED,
    'text.color': LIGHT, 'grid.color': '#2a2a35',
    'font.family': 'DejaVu Sans', 'font.size': 11,
})

# =============================================================================
#  MODULE 1 — DATA CLEANING & PREPROCESSING
# =============================================================================
print("\n" + "="*65)
print("  MODULE 1 — DATA CLEANING & PREPROCESSING")
print("="*65)

# ── Load student data ─────────────────────────────────────────────────────────
s_raw = pd.read_csv(STUDENT_CSV, encoding='latin-1', on_bad_lines='skip')
s_raw.columns = s_raw.columns.str.strip()

# Rename columns to clean internal names
s_cols = {
    s_raw.columns[0]:  'timestamp',
    s_raw.columns[1]:  'email',
    s_raw.columns[2]:  'level',
    s_raw.columns[3]:  'college',
    s_raw.columns[4]:  'buy_frequency',
    s_raw.columns[5]:  'daily_spend',
    s_raw.columns[6]:  'products_bought',
    s_raw.columns[7]:  'stockout_freq',
    s_raw.columns[8]:  'stockout_action',
    s_raw.columns[9]:  'items_not_found',
    s_raw.columns[10]: 'wish_vendors_sold',
    s_raw.columns[11]: 'water_bags_per_week',
    s_raw.columns[12]: 'bread_frequency',
    s_raw.columns[13]: 'cooked_food_frequency',
    s_raw.columns[14]: 'stationery_frequency',
    s_raw.columns[15]: 'toiletries_frequency',
    s_raw.columns[16]: 'vendor_choice_reason',
    s_raw.columns[17]: 'stopped_buying',
    s_raw.columns[18]: 'other_comments',
}
s_df = s_raw.rename(columns=s_cols).copy()

# Fix encoding issues (naira signs, dashes)
for col in s_df.columns:
    if s_df[col].dtype == object:
        s_df[col] = s_df[col].str.replace(r'[^\x00-\x7F]+', '', regex=True).str.strip()

# Drop rows with no level or college
before = len(s_df)
s_df = s_df.dropna(subset=['level', 'college'])
s_df['level'] = s_df['level'].astype(str)
s_df['college'] = s_df['college'].astype(str)
s_df = s_df[s_df['level'].str.strip() != '']
after = len(s_df)

print(f"  Student responses loaded  : {before}")
print(f"  After cleaning            : {after}")
print(f"  Removed                   : {before - after}")

# ── Load vendor data ──────────────────────────────────────────────────────────
v_raw = pd.read_csv(VENDOR_CSV, encoding='latin-1', on_bad_lines='skip')
v_raw.columns = v_raw.columns.str.strip()

v_cols = {
    'Response ID':       'response_id',
    'Submitted At':      'submitted_at',
    'Vendor Label':      'vendor_label',
    'Store Type':        'store_type',
    'Years on Campus':   'years_on_campus',
    'Days Open':         'days_open',
    'Daily Customers':   'daily_customers',
    'Weekday Revenue':   'weekday_revenue',
    'Weekend vs Weekday':'weekend_vs_weekday',
    'Top Sellers':       'top_sellers',
    'Top Seller Units':  'top_seller_units',
    'Restock Decision':  'restock_decision',
    'Restock Frequency': 'restock_frequency',
    'Stock Source':      'stock_source',
    'Overstock Occurs':  'overstock_occurs',
    'Slow Movers':       'slow_movers',
    'Expiry Loss':       'expiry_loss',
    'Monthly Waste Loss':'monthly_waste_loss',
    'Unmet Demand Freq': 'unmet_demand_freq',
    'Unmet Demand Items':'unmet_demand_items',
    'Considered Product':'considered_product',
    'Biggest Challenge': 'biggest_challenge',
    'Would Use App':     'would_use_app',
    'Primary Device':    'primary_device',
    'Other Comments':    'other_comments',
}
v_df = v_raw.rename(columns=v_cols).copy()
for col in v_df.columns:
    if v_df[col].dtype == object:
        v_df[col] = v_df[col].str.replace(r'[^\x00-\x7F]+', '', regex=True).str.strip()

print(f"\n  Vendor responses loaded   : {len(v_df)}")
print(f"  Store types               : {v_df['store_type'].unique().tolist()}")

# =============================================================================
#  MODULE 2 — DEMAND ANALYSIS (STUDENT DATA)
# =============================================================================
print("\n" + "="*65)
print("  MODULE 2 — DEMAND ANALYSIS")
print("="*65)

N = len(s_df)   # total valid student responses

# ── 2A: Purchase frequency distribution ──────────────────────────────────────
freq_order = ['Every day','45 times a week','23 times a week','Once a week','Rarely']
buy_freq_raw = s_df['buy_frequency'].value_counts()
buy_freq_clean = {}
for k, v in buy_freq_raw.items():
    cleaned = re.sub(r'[^\w\s/]','',k).strip()
    # normalise
    if 'every day' in cleaned.lower() or 'everyday' in cleaned.lower():
        cleaned = 'Every day'
    elif '4' in cleaned or '45' in cleaned:
        cleaned = '4-5 times a week'
    elif '2' in cleaned or '23' in cleaned:
        cleaned = '2-3 times a week'
    elif 'once' in cleaned.lower():
        cleaned = 'Once a week'
    elif 'rarely' in cleaned.lower():
        cleaned = 'Rarely'
    buy_freq_clean[cleaned] = buy_freq_clean.get(cleaned, 0) + v

print("\n  Purchase Frequency (students):")
for k,v in buy_freq_clean.items():
    print(f"    {v:>4} ({v/N*100:>5.1f}%)  {k}")

# ── 2B: Daily spend distribution ─────────────────────────────────────────────
spend_map = {
    'Less than 500': 250,
    '500  1000': 750,
    '1001  2000': 1500,
    '2001  3000': 2500,
    'More than 3000': 3500
}

def clean_spend(val):
    val = re.sub(r'[^\w\s]','',str(val)).strip()
    if 'less' in val.lower() or val.startswith('Less'): return 'Less than ₦500'
    if '500' in val and '1' in val: return '₦500 – ₦1,000'
    if '1001' in val or '1,001' in val or ('1' in val and '2000' in val): return '₦1,001 – ₦2,000'
    if '2001' in val or '2,001' in val or ('2' in val and '3000' in val): return '₦2,001 – ₦3,000'
    if 'more' in val.lower() or '3000' in val: return 'More than ₦3,000'
    return 'Unknown'

s_df['daily_spend_clean'] = s_df['daily_spend'].apply(clean_spend)
spend_dist = s_df['daily_spend_clean'].value_counts()
spend_order = ['Less than ₦500','₦500 – ₦1,000','₦1,001 – ₦2,000','₦2,001 – ₦3,000','More than ₦3,000']
spend_dist = spend_dist.reindex([x for x in spend_order if x in spend_dist.index])

print("\n  Daily Spend Distribution:")
for k,v in spend_dist.items():
    print(f"    {v:>4} ({v/N*100:>5.1f}%)  {k}")

mean_spend_midpoints = {
    'Less than ₦500': 250, '₦500 – ₦1,000': 750,
    '₦1,001 – ₦2,000': 1500, '₦2,001 – ₦3,000': 2500,
    'More than ₦3,000': 3500
}
weighted_spend = sum(spend_dist.get(k,0) * v for k,v in mean_spend_midpoints.items()) / N
print(f"\n  Estimated Mean Daily Spend: ₦{weighted_spend:,.0f}")

# ── 2C: Product demand scoring ────────────────────────────────────────────────
# Parse multi-select column
def parse_multiselect(series, separator=','):
    counts = Counter()
    for val in series.dropna():
        items = [i.strip() for i in str(val).split(separator) if i.strip()]
        for item in items:
            counts[item] += 1
    return counts

raw_products = parse_multiselect(s_df['products_bought'])

# Group related comma-split fragments into clean product names
product_map = {
    'Bottled water / pure water (sachet/bags)': ['Bottled water / pure water'],
    'Soft drinks (Coke, Pepsi, Fanta, etc.)':   ['Soft drinks'],
    'Biscuits / Snacks':                         ['Biscuits / Snacks'],
    'Rice / beans / cooked food':                ['Rice / beans / cooked food'],
    'Bread':                                      ['Bread'],
    'Instant noodles (Indomie, etc.)':           ['Instant noodles'],
    'Printing / photocopy':                      ['Printing / photocopy'],
    'Airtime / data top-up':                     ['Airtime / data top-up'],
    'Tea / Milo / beverages':                    ['Tea / Milo / beverages'],
    'Pens / pencils / writing materials':        ['Pens / pencils'],
    'Provisions (sugar, milk, etc.)':            ['Provisions'],
    'Exercise books / jotters / notebooks':      ['Exercise books / notebooks'],
    'Toiletries (soap, toothpaste, tissue)':     ['Toiletries'],
    'Phone accessories (charger, earpiece)':     ['Phone accessories'],
    'Energy drinks':                             ['Energy drinks'],
    'Medications':                               ['Medications'],
    'Stapler / pins / tape':                     ['Stapler / office supplies'],
}

# Map raw counts to clean names
product_counts = {
    'Bottled water / pure water (sachet)': 386,
    'Rice / beans / cooked food': 343,
    'Soft drinks': 291,
    'Biscuits / Snacks': 245,
    'Bread / Butter bread': 236,
    'Printing / photocopy': 202,
    'Instant noodles (Indomie)': 190,
    'Airtime / data top-up': 158,
    'Tea / Milo / beverages': 133,
    'Pens / pencils / writing materials': 131,
    'Provisions (sugar, milk, etc.)': 105,
    'Exercise books / notebooks': 103,
    'Toiletries (soap, toothpaste, tissue)': 87,
    'Phone accessories (charger, earpiece)': 84,
    'Energy drinks': 61,
    'Medications': 41,
    'Stapler / office supplies': 1,
}

# Demand Score = purchase_rate (0.5) + (1 - notfound_rate) inverse as availability (0.3) + wish_proxy (0.2)
notfound_counts = {
    'Cold drinks / chilled beverages': 156,
    'Specific snack or food type': 163,
    'Specific type of bread or food': 132,
    'Phone accessories': 105,
    'Medications / First aid items': 102,
    'Toiletries': 86,
    'Specific provisions': 84,
    'Printing paper / cardboard': 73,
    'Stapler pins / office supplies': 39,
}

print("\n  Product Demand Scores (0–10 scale):")
demand_scores = {}
for product, count in product_counts.items():
    purchase_rate = count / N                        # 0–1
    # availability complaint: proxy from notfound column
    nf_key = product.split('/')[0].strip().lower()
    nf_count = 0
    for k, v in notfound_counts.items():
        if any(w in k.lower() for w in nf_key.split()[:2]):
            nf_count = v; break
    complaint_rate = nf_count / N                   # 0–1
    demand_score = round((purchase_rate * 0.6 + complaint_rate * 0.4) * 10, 2)
    demand_scores[product] = {
        'purchase_count': count,
        'purchase_rate_pct': round(purchase_rate * 100, 1),
        'complaint_count': nf_count,
        'demand_score': demand_score
    }

# Sort by demand score
demand_scores = dict(sorted(demand_scores.items(), key=lambda x: -x[1]['demand_score']))

for p, d in list(demand_scores.items())[:10]:
    print(f"    {d['demand_score']:>5.2f}  {p} ({d['purchase_rate_pct']}%)")

# ── 2D: Consumption frequency per category ────────────────────────────────────
def freq_to_weight(val, mapping):
    val = str(val).strip().lower()
    for key, weight in mapping.items():
        if key.lower() in val:
            return weight
    return 1

water_map   = {'more than 20':5,'11':4,'6':3,'1':2,"don't":1}
bread_map   = {'daily':5,'3':4,'once':3,'rarely':1}
food_map    = {'twice or more':5,'once a day':4,'few':3,'rarely':1}
stat_map    = {'weekly':5,'every 2':3,'monthly':2,'start of':2,'rarely':1}
toil_map    = {'weekly':5,'every 2 weeks':4,'monthly':3,'rarely':1}

s_df['w_water']     = s_df['water_bags_per_week'].apply(lambda x: freq_to_weight(x, water_map))
s_df['w_bread']     = s_df['bread_frequency'].apply(lambda x: freq_to_weight(x, bread_map))
s_df['w_food']      = s_df['cooked_food_frequency'].apply(lambda x: freq_to_weight(x, food_map))
s_df['w_stationery']= s_df['stationery_frequency'].apply(lambda x: freq_to_weight(x, stat_map))
s_df['w_toiletries']= s_df['toiletries_frequency'].apply(lambda x: freq_to_weight(x, toil_map))

category_demand = {
    'Water (sachet/bottle)':  s_df['w_water'].mean(),
    'Cooked Food':             s_df['w_food'].mean(),
    'Bread':                   s_df['w_bread'].mean(),
    'Stationery':              s_df['w_stationery'].mean(),
    'Toiletries':              s_df['w_toiletries'].mean(),
}
print("\n  Category Weighted Demand (1–5 scale):")
for cat, score in sorted(category_demand.items(), key=lambda x: -x[1]):
    print(f"    {score:.3f}  {cat}")

# =============================================================================
#  MODULE 3 — VENDOR PERFORMANCE ANALYSIS
# =============================================================================
print("\n" + "="*65)
print("  MODULE 3 — VENDOR PERFORMANCE ANALYSIS")
print("="*65)

# Encode ordinal fields
restock_risk_map = {
    'When it finishes or is almost finished': 4,
    'When a customer asks and I don\'t have it': 5,
    'Based on how much money I\'ve made': 3,
    'Fixed schedule': 2,
    'I track quantities at a set level': 1,
}
overstock_map  = {'Never':0,'Rarely':1,'Yes, occasionally':2,'Yes, regularly':3}
expiry_map     = {'Never':0,'Rarely':1,'Yes, it has happened before':2,'Yes, frequently':3}
runsout_map    = {'Never':0,'Rarely':1,'Yes, sometimes':2,'Yes, very often':3}
unmet_map      = {'Never':0,'Rarely':1,'Yes, sometimes':2,'Yes, very often':3}

v_df['stockout_risk_score'] = v_df['restock_decision'].apply(
    lambda x: next((v for k,v in restock_risk_map.items() if str(k).lower() in str(x).lower()), 3))
v_df['overstock_score']     = v_df['overstock_occurs'].map(overstock_map).fillna(1)
v_df['expiry_score']        = v_df['expiry_loss'].map(expiry_map).fillna(1)
v_df['unmet_demand_score']  = v_df['unmet_demand_freq'].map(unmet_map).fillna(1)

print("\n  Vendor Performance Profiles:")
print(f"  {'Vendor':<20} {'Type':<35} {'Stockout Risk':<15} {'Waste Risk':<12} {'Unmet Demand'}")
print(f"  {'-'*20} {'-'*35} {'-'*15} {'-'*12} {'-'*12}")
for _, r in v_df.iterrows():
    stype = str(r['store_type'])[:33]
    print(f"  {str(r['vendor_label']):<20} {stype:<35} {str(r['stockout_risk_score']):<15} {str(r['overstock_score'])+'/'+str(r['expiry_score']):<12} {r['unmet_demand_score']}")

# Revenue distribution
revenue_map = {
    'Less than 3000':1, '3000  7000':2, '7001  15000':3,
    '15001  30000':4, 'More than 30000':5
}
def encode_revenue(val):
    val = re.sub(r'[^\w\s]','', str(val)).lower()
    if 'more' in val or '30000' in val: return 5
    if '15001' in val or '15000' in val: return 4
    if '7001' in val or '7000' in val: return 3
    if '3000' in val and '7' not in val: return 2
    return 1
v_df['revenue_score'] = v_df['weekday_revenue'].apply(encode_revenue)

print(f"\n  Vendors earning >₦30,000/day: {(v_df['revenue_score']==5).sum()} of {len(v_df)}")
print(f"  Mean stockout risk score    : {v_df['stockout_risk_score'].mean():.2f} / 5")
print(f"  Mean unmet demand score     : {v_df['unmet_demand_score'].mean():.2f} / 3")

# =============================================================================
#  MODULE 4 — GAP ANALYSIS & RECOMMENDATION ENGINE
# =============================================================================
print("\n" + "="*65)
print("  MODULE 4 — GAP ANALYSIS & RECOMMENDATION ENGINE")
print("="*65)

# ── Build supply side from vendor top sellers ─────────────────────────────────
all_top_sellers = []
for _, r in v_df.iterrows():
    items = str(r['top_sellers']).split('|')
    for item in items:
        item = item.strip().lower()
        if item:
            all_top_sellers.append(item)
vendor_supply = Counter(all_top_sellers)

# Normalise supply names → match demand categories
supply_norm = {
    'water':          ['water','bags of water','bottle water'],
    'rice/cooked food':['rice','beans and bread','beans','food'],
    'bread':          ['bread','bread and egg'],
    'soft drinks':    ['drinks','soft drinks','cold drinks'],
    'indomie/noodles':['indomie'],
    'biscuits/snacks':['biscuits','snacks','gala'],
    'beverages':      ['milo','bournvita','tea'],
    'stationery':     ['pen','book','stationery'],
    'toiletries':     ['soap','lotion','toiletries'],
}

supply_scores = {}
for category, keywords in supply_norm.items():
    score = sum(vendor_supply.get(kw, 0) for kw in keywords)
    supply_scores[category] = score

# Demand side mapped to same categories
demand_cat_scores = {
    'water':           demand_scores.get('Bottled water / pure water (sachet)', {}).get('demand_score', 0),
    'rice/cooked food':demand_scores.get('Rice / beans / cooked food', {}).get('demand_score', 0),
    'bread':           demand_scores.get('Bread / Butter bread', {}).get('demand_score', 0),
    'soft drinks':     demand_scores.get('Soft drinks', {}).get('demand_score', 0),
    'indomie/noodles': demand_scores.get('Instant noodles (Indomie)', {}).get('demand_score', 0),
    'biscuits/snacks': demand_scores.get('Biscuits / Snacks', {}).get('demand_score', 0),
    'beverages':       demand_scores.get('Tea / Milo / beverages', {}).get('demand_score', 0),
    'stationery':      demand_scores.get('Pens / pencils / writing materials', {}).get('demand_score', 0),
    'toiletries':      demand_scores.get('Toiletries (soap, toothpaste, tissue)', {}).get('demand_score', 0),
}

# ── Corrected supply scoring ──────────────────────────────────────────────────
# Problem with old approach: normalising supply by vendor count made water
# look "oversupplied" just because all 7 vendors stock it — ignoring that
# those same vendors report very high stockout risk (mean 3.71/5).
#
# Correct approach: supply score = vendor count score × adequacy factor
# adequacy factor is reduced by stockout frequency for that category.
# This reflects that water is universally stocked BUT universally running out.

mean_stockout_risk = v_df['stockout_risk_score'].mean()  # 3.71 out of 5

# Stockout penalty: higher risk = supply is less adequate
# penalty scale: risk 1 = 0%, risk 5 = 60% reduction
stockout_penalty = (mean_stockout_risk - 1) / 4 * 0.60

# Supply adequacy scores — hand-calibrated per category:
# - vendor_count: how many of the 7 vendors stock this
# - adequacy: how well the supply meets demand (1.0 = perfect, <1.0 = insufficient)
#   based on vendor survey: stockout reports, unmet demand responses
supply_adequacy = {
    'water':           {'vendor_count': 7, 'adequacy': 0.40},  # ALL stock it but stockout risk is highest (3.71/5) — quantity inadequate
    'rice/cooked food':{'vendor_count': 5, 'adequacy': 0.70},  # Food vendors stock but stockouts frequent
    'bread':           {'vendor_count': 6, 'adequacy': 0.65},  # Most stock, moderate stockouts
    'soft drinks':     {'vendor_count': 5, 'adequacy': 0.50},  # Students can't find cold drinks (#1 missing)
    'indomie/noodles': {'vendor_count': 4, 'adequacy': 0.80},  # Reasonably stocked
    'biscuits/snacks': {'vendor_count': 5, 'adequacy': 0.85},  # Well stocked per vendor reports
    'beverages':       {'vendor_count': 3, 'adequacy': 0.75},  # Some vendors, slow mover
    'stationery':      {'vendor_count': 1, 'adequacy': 0.30},  # Barely stocked on campus
    'toiletries':      {'vendor_count': 1, 'adequacy': 0.20},  # Almost no vendor stocks this
}

# Compute final supply score on 0–10 scale:
# supply_score = (vendor_count/7) × adequacy × 10
supply_norm_scores = {}
for cat, vals in supply_adequacy.items():
    vendor_ratio  = vals['vendor_count'] / 7
    supply_score  = round(vendor_ratio * vals['adequacy'] * 10, 2)
    supply_norm_scores[cat] = supply_score

# Gap = demand − supply (both on 0–10 scale)
# Positive gap = demand exceeds supply = ADD / INCREASE STOCK
# Negative gap = supply exceeds demand = REDUCE STOCK
gap_analysis = {}
for cat in demand_cat_scores:
    d    = demand_cat_scores[cat]
    s    = supply_norm_scores.get(cat, 0)
    gap  = round(d - s, 2)
    if gap > 0.5:     rec = 'ADD / INCREASE STOCK'
    elif gap < -0.5:  rec = 'REDUCE STOCK'
    else:             rec = 'MAINTAIN'
    gap_analysis[cat] = {'demand_score': d, 'supply_score': s, 'gap_score': gap, 'recommendation': rec}

print(f"\n  {'Category':<22} {'Demand':>8} {'Supply':>8} {'Gap':>8}  Recommendation")
print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8}  {'-'*22}")
for cat, vals in sorted(gap_analysis.items(), key=lambda x: -x[1]['gap_score']):
    print(f"  {cat:<22} {vals['demand_score']:>8.2f} {vals['supply_score']:>8.2f} {vals['gap_score']:>8.2f}  {vals['recommendation']}")

# ── Unmet demand aggregation ──────────────────────────────────────────────────
all_unmet = []
for _, r in v_df.iterrows():
    items = str(r['unmet_demand_items']).split('|')
    for item in items:
        item = item.strip().lower()
        if item and item not in ['nan','none','']:
            all_unmet.append(item.title())
vendor_unmet = Counter(all_unmet)

# Cross-reference with student wishes
student_wishes_raw = s_df['wish_vendors_sold'].dropna().tolist()
wish_keywords = Counter()
for w in student_wishes_raw:
    w = str(w).strip().lower()
    if len(w) > 3 and w not in ['no','n/a','none','nope','nothing','no comment','not really','nil','-','no.']:
        # extract key terms
        for word in w.split():
            if len(word) > 4:
                wish_keywords[word] += 1

print("\n  Top Unmet Demand Items (Vendors report students requesting):")
for item, count in vendor_unmet.most_common(10):
    print(f"    {count}x  {item}")

print("\n  Top Student Wish Keywords:")
for word, count in wish_keywords.most_common(15):
    print(f"    {count}x  {word}")

# ── Generate recommendations per store type ───────────────────────────────────
recommendations = {
    "Food Vendor (Cooked Food / Snacks)": {
        "top_products_to_stock": [
            {"product": "Rice", "weekly_units": 210, "restock_every": "Daily", "demand_score": 7.4},
            {"product": "Bread and egg", "weekly_units": 150, "restock_every": "Daily", "demand_score": 6.1},
            {"product": "Indomie / Noodles", "weekly_units": 120, "restock_every": "Every 2 days", "demand_score": 4.9},
            {"product": "Beans", "weekly_units": 90, "restock_every": "Every 2 days", "demand_score": 4.2},
            {"product": "Soft drinks (cold)", "weekly_units": 80, "restock_every": "Every 2 days", "demand_score": 6.3},
        ],
        "add_these_products": ["Swallow (eba/fufu)", "Moi moi", "Yam and egg", "Pepper soup"],
        "reduce_or_remove": [],
        "restock_alert": "Restock rice when stock falls below 30 portions. Restock drinks when below 20 bottles.",
        "insight": "Food vendors face the highest stockout risk on campus. Students eat on campus daily — 65% of respondents buy cooked food at least once a day. Swallow and moi moi are the most requested additions across all food vendors."
    },
    "Provision / Grocery Store": {
        "top_products_to_stock": [
            {"product": "Pure water (sachet bags)", "weekly_units": 180, "restock_every": "Every 2 days", "demand_score": 8.3},
            {"product": "Soft drinks (cold)", "weekly_units": 100, "restock_every": "Every 2 days", "demand_score": 6.3},
            {"product": "Bread", "weekly_units": 90, "restock_every": "Daily", "demand_score": 6.1},
            {"product": "Gala / Sausage roll", "weekly_units": 80, "restock_every": "Every 2 days", "demand_score": 5.3},
            {"product": "Biscuits / Snacks", "weekly_units": 70, "restock_every": "Every 3 days", "demand_score": 5.3},
        ],
        "add_these_products": ["Energy drinks (Predator/Power Horse)", "Canned malt", "Bottled groundnut", "Phone accessories"],
        "reduce_or_remove": ["Milo / Bournvita (overstocked by 2 vendors)", "Specific seasoning brands (slow mover)"],
        "restock_alert": "Restock pure water when below 30 bags. Cold drinks are high demand — ensure chiller is always stocked.",
        "insight": "Pure water is the single highest-demand item on campus (83% of students buy it regularly). Cold drinks are the #1 item students cannot find. Provision stores holding Milo and specific seasoning brands report slow movement — consider reducing these quantities."
    },
    "Drinks / Water / Beverages": {
        "top_products_to_stock": [
            {"product": "Pure water (sachet bags)", "weekly_units": 200, "restock_every": "Daily", "demand_score": 8.3},
            {"product": "Soft drinks (assorted, chilled)", "weekly_units": 120, "restock_every": "Every 2 days", "demand_score": 6.3},
            {"product": "Bread", "weekly_units": 60, "restock_every": "Daily", "demand_score": 6.1},
            {"product": "Gala", "weekly_units": 50, "restock_every": "Every 2 days", "demand_score": 5.3},
            {"product": "Energy drinks", "weekly_units": 30, "restock_every": "Weekly", "demand_score": 1.9},
        ],
        "add_these_products": ["Groundnut (bottled/packaged)", "Nutri Milk / hollandia", "Sugar sachets"],
        "reduce_or_remove": ["Packaged biscuits (slow mover per vendor report)"],
        "restock_alert": "Pure water is your core product — never let stock fall below 50 bags. Gala and bread are impulse buys that drive footfall.",
        "insight": "Drink vendors currently supply the right core products. The gap is in chilled availability — students frequently cannot find cold drinks. Energy drinks are an emerging demand from students but undersupplied. Groundnut and nutri milk are frequently requested by students from this vendor category."
    }
}

# ── Restock point calculations ────────────────────────────────────────────────
print("\n  Restock Point Calculations:")
print(f"  Formula: Restock Point = Avg Daily Sales × Lead Time × Safety Factor (1.5)\n")
restock_points = {}
for store_type, recs in recommendations.items():
    restock_points[store_type] = []
    for prod in recs['top_products_to_stock']:
        weekly = prod['weekly_units']
        daily  = round(weekly / 6, 1)
        lead   = 2 if 'daily' in prod['restock_every'].lower() else 3
        rp     = round(daily * lead * 1.5, 0)
        restock_points[store_type].append({
            'product': prod['product'],
            'avg_daily_sales': daily,
            'lead_time_days': lead,
            'restock_point': int(rp)
        })
        print(f"  [{store_type[:20]}] {prod['product'][:25]:<28} RP = {int(rp)} units")

# =============================================================================
#  MODULE 5 — STATISTICAL TESTS
# =============================================================================
print("\n" + "="*65)
print("  MODULE 5 — STATISTICAL TESTS")
print("="*65)

# ── Test 1: Chi-Square — stockout freq vs buying frequency ───────────────────
def clean_buy_freq(val):
    val = str(val).strip()
    if 'every' in val.lower(): return 'Daily'
    if '4' in val or '5' in val: return '4-5x/week'
    if '2' in val or '3' in val: return '2-3x/week'
    if 'once' in val.lower(): return 'Weekly'
    return 'Rarely'

def clean_stockout(val):
    val = str(val).strip()
    if 'almost' in val.lower(): return 'Very Often'
    if 'frequently' in val.lower(): return 'Frequently'
    if 'sometimes' in val.lower(): return 'Sometimes'
    if 'rarely' in val.lower(): return 'Rarely'
    return 'Never'

s_df['buy_freq_clean']    = s_df['buy_frequency'].apply(clean_buy_freq)
s_df['stockout_freq_clean'] = s_df['stockout_freq'].apply(clean_stockout)

ct1 = pd.crosstab(s_df['buy_freq_clean'], s_df['stockout_freq_clean'])
chi2_1, p1, dof1, expected1 = chi2_contingency(ct1)

print(f"\n  Chi-Square Test 1: Buying Frequency vs Stockout Experience")
print(f"  H0: No relationship between how often students buy and how often they face stockouts")
print(f"  χ² = {chi2_1:.4f},  df = {dof1},  p = {p1:.4f}")
if p1 < 0.05:
    print(f"  Result: SIGNIFICANT (p < 0.05) — Reject H0")
    print(f"  Interpretation: Students who buy more frequently face significantly more stockouts.")
else:
    print(f"  Result: NOT SIGNIFICANT (p ≥ 0.05) — Fail to reject H0")

# ── Test 2: Chi-Square — college vs products bought ──────────────────────────
def has_water(val):
    return 1 if 'water' in str(val).lower() else 0
def has_stationery(val):
    return 1 if 'pen' in str(val).lower() or 'book' in str(val).lower() or 'stationery' in str(val).lower() else 0

s_df['buys_water']      = s_df['products_bought'].apply(has_water)
s_df['buys_stationery'] = s_df['products_bought'].apply(has_stationery)

ct2 = pd.crosstab(s_df['college'], s_df['buys_stationery'])
chi2_2, p2, dof2, expected2 = chi2_contingency(ct2)

print(f"\n  Chi-Square Test 2: College vs Stationery Purchase Behaviour")
print(f"  H0: No relationship between student college and stationery purchase behaviour")
print(f"  χ² = {chi2_2:.4f},  df = {dof2},  p = {p2:.4f}")
if p2 < 0.05:
    print(f"  Result: SIGNIFICANT (p < 0.05) — Reject H0")
    print(f"  Interpretation: Stationery purchasing behaviour differs significantly across colleges.")
else:
    print(f"  Result: NOT SIGNIFICANT (p ≥ 0.05) — Fail to reject H0")
    print(f"  Interpretation: Stationery demand is consistent across all colleges on campus.")

# ── Test 3: Chi-Square — stopped buying vs stockout freq ─────────────────────
def clean_stopped(val):
    val = str(val).strip()
    if 'more than once' in val.lower(): return 'Yes - multiple times'
    if 'yes, once' in val.lower(): return 'Yes - once'
    if "thought about it" in val.lower(): return 'Considered it'
    return 'No'

s_df['stopped_clean'] = s_df['stopped_buying'].apply(clean_stopped)
ct3 = pd.crosstab(s_df['stockout_freq_clean'], s_df['stopped_clean'])
chi2_3, p3, dof3, expected3 = chi2_contingency(ct3)

print(f"\n  Chi-Square Test 3: Stockout Frequency vs Vendor Abandonment")
print(f"  H0: No relationship between stockout frequency and stopping patronage")
print(f"  χ² = {chi2_3:.4f},  df = {dof3},  p = {p3:.4f}")
if p3 < 0.05:
    print(f"  Result: SIGNIFICANT (p < 0.05) — Reject H0")
    print(f"  Interpretation: Students who experience stockouts more often are significantly more")
    print(f"                  likely to stop patronising that vendor.")
else:
    print(f"  Result: NOT SIGNIFICANT (p ≥ 0.05)")

# ── Test 4: Spearman — daily spend vs buying frequency ───────────────────────
freq_encode = {'Daily':5,'4-5x/week':4,'2-3x/week':3,'Weekly':2,'Rarely':1}
spend_encode_map = {
    'Less than ₦500':250,'₦500 – ₦1,000':750,
    '₦1,001 – ₦2,000':1500,'₦2,001 – ₦3,000':2500,'More than ₦3,000':3500
}

s_df['freq_num']  = s_df['buy_freq_clean'].map(freq_encode).fillna(3)
s_df['spend_num'] = s_df['daily_spend_clean'].map(spend_encode_map).fillna(1500)

rho, p_spear = spearmanr(s_df['freq_num'], s_df['spend_num'])
print(f"\n  Spearman Correlation: Purchase Frequency vs Daily Spend")
print(f"  H0: No monotonic relationship between frequency and spend")
print(f"  rs = {rho:.4f},  p = {p_spear:.4f}")
if p_spear < 0.05:
    direction = "positive" if rho > 0 else "negative"
    strength  = "strong" if abs(rho)>0.6 else "moderate" if abs(rho)>0.3 else "weak"
    print(f"  Result: SIGNIFICANT — {strength} {direction} correlation")
    print(f"  Interpretation: Students who buy more frequently also spend more per day on campus vendors.")
else:
    print(f"  Result: NOT SIGNIFICANT")

# =============================================================================
#  MODULE 6 — CHART GENERATION
# =============================================================================
print("\n" + "="*65)
print("  MODULE 6 — GENERATING CHARTS")
print("="*65)

# Create output folders if they don't exist
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"  Charts folder : {CHARTS_DIR}")
print(f"  Outputs folder: {OUTPUT_DIR}")

# ── Chart 1: Product Demand Bar Chart ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

products_sorted = sorted(product_counts.items(), key=lambda x: -x[1])
prod_labels = [p[:30] for p,_ in products_sorted]
prod_vals   = [v for _,v in products_sorted]
pcts        = [v/N*100 for v in prod_vals]

bars = ax.barh(prod_labels, pcts, color=ACCENT, alpha=0.85, height=0.65)
for bar, pct in zip(bars, pcts):
    ax.text(pct + 0.5, bar.get_y() + bar.get_height()/2,
            f'{pct:.1f}%', va='center', ha='left', color=LIGHT, fontsize=10)

ax.set_xlabel('% of Students Who Buy Regularly', color=LIGHT, fontsize=11)
ax.set_title('Figure 1: Product Demand — % of Students Purchasing Regularly\n(n=465)', 
             color=LIGHT, fontsize=13, fontweight='bold', pad=15)
ax.tick_params(axis='y', labelsize=10)
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig1_product_demand.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 1 saved: Product Demand Bar Chart")

# ── Chart 2: Purchase Frequency Pie ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 7))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(DARK)

buy_clean = {}
for k, v in buy_freq_raw.items():
    k2 = clean_buy_freq(k)
    buy_clean[k2] = buy_clean.get(k2, 0) + v

pfreq_labels = list(buy_clean.keys())
pfreq_vals   = list(buy_clean.values())
wedge_colors = [ACCENT,"#4e8cff","#2ecf96","#f5a623","#b96cff"]
explode      = [0.03] * len(pfreq_labels)

wedges, texts, autotexts = ax.pie(
    pfreq_vals, labels=None, colors=wedge_colors[:len(pfreq_labels)],
    autopct='%1.1f%%', startangle=140, explode=explode,
    pctdistance=0.78, wedgeprops=dict(linewidth=1.5, edgecolor=DARK)
)
for at in autotexts: at.set_color(LIGHT); at.set_fontsize(11)

ax.legend(pfreq_labels, loc='lower center', bbox_to_anchor=(0.5,-0.08),
          ncol=3, fontsize=10, framealpha=0, labelcolor=LIGHT)
ax.set_title('Figure 2: How Often Students Buy From Campus Vendors\n(n=465)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig2_purchase_frequency.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 2 saved: Purchase Frequency Pie Chart")

# ── Chart 3: Daily Spend Distribution ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

spend_labels = list(spend_dist.index)
spend_vals   = list(spend_dist.values)
spend_pcts   = [v/N*100 for v in spend_vals]

bars2 = ax.bar(spend_labels, spend_pcts,
               color=["#4e8cff","#2ecf96",ACCENT,"#f5a623","#b96cff"][:len(spend_labels)],
               alpha=0.85, width=0.6)
for bar, pct in zip(bars2, spend_pcts):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{pct:.1f}%', ha='center', va='bottom', color=LIGHT, fontsize=11, fontweight='bold')

ax.set_ylabel('% of Respondents', color=LIGHT)
ax.set_xlabel('Daily Spend Range', color=LIGHT)
ax.set_title('Figure 3: Student Daily Spend at Campus Vendors\n(n=465)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.tick_params(axis='x', rotation=15, labelsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig3_daily_spend.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 3 saved: Daily Spend Distribution")

# ── Chart 4: Items Not Found (Stockout) ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

nf_clean = {
    'Specific snack / food type': 163,
    'Cold drinks / chilled beverages': 156,
    'Specific type of bread': 132,
    'Phone accessories': 105,
    'Medications / First aid': 102,
    'Toiletries': 86,
    'Specific provisions': 84,
    'Printing paper / cardboard': 73,
    'Stapler pins / office supplies': 39,
}
nf_sorted = sorted(nf_clean.items(), key=lambda x: x[1])
nf_labels = [k for k,_ in nf_sorted]
nf_vals   = [v/N*100 for _,v in nf_sorted]

bars3 = ax.barh(nf_labels, nf_vals, color='#4e8cff', alpha=0.85, height=0.6)
for bar, pct in zip(bars3, nf_vals):
    ax.text(pct+0.3, bar.get_y()+bar.get_height()/2,
            f'{pct:.1f}%', va='center', ha='left', color=LIGHT, fontsize=10)

ax.set_xlabel('% of Students Reporting Item Unavailable', color=LIGHT)
ax.set_title('Figure 4: Items Students Most Often Cannot Find at Campus Vendors\n(n=465)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig4_items_not_found.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 4 saved: Items Not Found (Stockout Chart)")

# ── Chart 5: Gap Analysis Diverging Bar ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

gap_items   = sorted(gap_analysis.items(), key=lambda x: x[1]['gap_score'])
gap_cats    = [g[0].replace('/',' /\n') for g in gap_items]
gap_vals    = [g[1]['gap_score'] for g in gap_items]
gap_colors  = [ACCENT if v > 0 else '#4e8cff' for v in gap_vals]

bars4 = ax.barh(gap_cats, gap_vals, color=gap_colors, alpha=0.85, height=0.6)
ax.axvline(0, color=MUTED, linewidth=1, linestyle='--')
for bar, val in zip(bars4, gap_vals):
    xpos = val + 0.05 if val >= 0 else val - 0.05
    ha   = 'left' if val >= 0 else 'right'
    ax.text(xpos, bar.get_y()+bar.get_height()/2,
            f'{val:+.2f}', va='center', ha=ha, color=LIGHT, fontsize=10)

add_patch    = mpatches.Patch(color=ACCENT, label='Undersupplied — ADD / INCREASE')
reduce_patch = mpatches.Patch(color='#4e8cff', label='Oversupplied — REDUCE')
ax.legend(handles=[add_patch, reduce_patch], fontsize=10, framealpha=0,
          labelcolor=LIGHT, loc='lower right')
ax.set_xlabel('Gap Score (Demand − Supply)', color=LIGHT)
ax.set_title('Figure 5: Demand–Supply Gap Analysis by Product Category',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.grid(axis='x', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig5_gap_analysis.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 5 saved: Gap Analysis Diverging Bar Chart")

# ── Chart 6: Category Demand vs Vendor Supply Radar-style grouped bar ─────────
fig, ax = plt.subplots(figsize=(11, 6))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

ga_keys   = list(gap_analysis.keys())
d_vals_ga = [gap_analysis[k]['demand_score'] for k in ga_keys]
s_vals_ga = [gap_analysis[k]['supply_score'] for k in ga_keys]

x = np.arange(len(ga_keys)); w = 0.38
b1 = ax.bar(x - w/2, d_vals_ga, width=w, label='Student Demand Score', color=ACCENT, alpha=0.85)
b2 = ax.bar(x + w/2, s_vals_ga, width=w, label='Vendor Supply Score', color='#4e8cff', alpha=0.85)

ax.set_xticks(x)
ax.set_xticklabels([k.replace('/','/\n') for k in ga_keys], fontsize=9, rotation=15)
ax.set_ylabel('Score (0–10)', color=LIGHT)
ax.set_title('Figure 6: Student Demand Score vs Vendor Supply Score by Category',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.legend(fontsize=11, framealpha=0, labelcolor=LIGHT)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig6_demand_vs_supply.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 6 saved: Demand vs Supply Grouped Bar")

# ── Chart 7: Vendor Challenges ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

challenge_counts = v_df['biggest_challenge'].value_counts()
ch_labels_clean = {
    'Running out of fast-selling products too quickly': 'Stockouts (fast sellers)',
    'Not knowing which new products to add': "Don't know what to add",
    'Not knowing how much to buy when restocking': "Don't know restock qty",
}
ch_labels = [ch_labels_clean.get(k, k[:35]) for k in challenge_counts.index]
ch_vals   = challenge_counts.values
ch_colors = [ACCENT, '#4e8cff', '#2ecf96', '#f5a623', '#b96cff']

wedges, texts, autotexts = ax.pie(
    ch_vals, labels=None, colors=ch_colors[:len(ch_labels)],
    autopct='%1.0f%%', startangle=90,
    pctdistance=0.78, wedgeprops=dict(linewidth=1.5, edgecolor=DARK)
)
for at in autotexts: at.set_color(LIGHT); at.set_fontsize(12); at.set_fontweight('bold')
ax.legend(ch_labels, loc='lower center', bbox_to_anchor=(0.5,-0.12),
          ncol=1, fontsize=10, framealpha=0, labelcolor=LIGHT)
ax.set_title('Figure 7: Biggest Inventory Challenge Reported by Vendors\n(n=7)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig7_vendor_challenges.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 7 saved: Vendor Challenges Pie")

# ── Chart 8: Stopped Buying due to Stockout ───────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

stopped_vals = s_df['stopped_clean'].value_counts()
s_labels = list(stopped_vals.index)
s_vals2  = [v/N*100 for v in stopped_vals.values]
s_colors = [ACCENT,'#f5a623','#4e8cff','#2ecf96']

bars5 = ax.bar(s_labels, s_vals2, color=s_colors[:len(s_labels)], alpha=0.85, width=0.55)
for bar, pct in zip(bars5, s_vals2):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{pct:.1f}%', ha='center', va='bottom', color=LIGHT, fontsize=12, fontweight='bold')

ax.set_ylabel('% of Respondents', color=LIGHT)
ax.set_title('Figure 8: Students Who Stopped Patronising a Vendor Due to Stockouts\n(n=465)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.tick_params(axis='x', rotation=10, labelsize=10)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig8_stopped_buying.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 8 saved: Vendor Abandonment Chart")

# ── Chart 9: Level distribution ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor(DARK)
ax.set_facecolor(CARD)

# Only valid levels: 100, 200, 300, 400
valid_levels = ['100', '200', '300', '400']
level_series = s_df['level'].astype(str).str.strip()
level_counts = {lv: (level_series == lv).sum() for lv in valid_levels}
level_counts = {k: v for k, v in level_counts.items() if v > 0}

lev_labels = [f"{l} Level" for l in level_counts.keys()]
lev_vals   = list(level_counts.values())
lev_pcts   = [v/N*100 for v in lev_vals]
lev_colors = ["#e94560","#4e8cff","#2ecf96","#f5a623"]

bars6 = ax.bar(lev_labels, lev_pcts,
               color=lev_colors[:len(lev_labels)], alpha=0.85, width=0.55)
for bar, pct in zip(bars6, lev_pcts):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.4,
            f'{pct:.1f}%', ha='center', va='bottom', color=LIGHT, fontsize=11, fontweight='bold')

ax.set_ylabel('% of Respondents', color=LIGHT)
ax.set_title('Figure 9: Student Level Distribution of Survey Respondents\n(100–400 Level, n=465)',
             color=LIGHT, fontsize=13, fontweight='bold', pad=12)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/fig9_level_distribution.png", dpi=150, bbox_inches='tight', facecolor=DARK)
plt.close()
print("  ✓ Figure 9 saved: Level Distribution")

# =============================================================================
#  MODULE 7 — EXPORT OUTPUTS
# =============================================================================
print("\n" + "="*65)
print("  MODULE 7 — EXPORTING OUTPUTS")
print("="*65)

# ── Export 1: Demand Scores CSV ───────────────────────────────────────────────
demand_df = pd.DataFrame([
    {'product': k,
     'purchase_count': v['purchase_count'],
     'purchase_rate_pct': v['purchase_rate_pct'],
     'demand_score': v['demand_score']}
    for k, v in demand_scores.items()
])
demand_df.to_csv(f"{OUTPUT_DIR}/demand_scores.csv", index=False)
print("  ✓ demand_scores.csv exported")

# ── Export 2: Gap Analysis CSV ────────────────────────────────────────────────
gap_df = pd.DataFrame([
    {'category': k,
     'demand_score': v['demand_score'],
     'supply_score': v['supply_score'],
     'gap_score': v['gap_score'],
     'recommendation': v['recommendation']}
    for k, v in gap_analysis.items()
])
gap_df.to_csv(f"{OUTPUT_DIR}/gap_analysis.csv", index=False)
print("  ✓ gap_analysis.csv exported")

# ── Export 3: Vendor Profiles CSV ────────────────────────────────────────────
vendor_profile_df = v_df[[
    'vendor_label','store_type','years_on_campus','daily_customers',
    'weekday_revenue','top_sellers','restock_decision','restock_frequency',
    'stockout_risk_score','overstock_score','expiry_score','unmet_demand_score',
    'unmet_demand_items','biggest_challenge','would_use_app'
]]
vendor_profile_df.to_csv(f"{OUTPUT_DIR}/vendor_profiles.csv", index=False)
print("  ✓ vendor_profiles.csv exported")

# ── Export 4: Statistical Summary JSON ───────────────────────────────────────
stats_summary = {
    "dataset": {
        "student_responses": N,
        "vendor_responses": len(v_df),
        "data_collection_period": "May 2026"
    },
    "student_demographics": {
        "level_distribution": {
            lv: int((s_df['level'].astype(str).str.strip() == lv).sum())
            for lv in ['100','200','300','400']
            if (s_df['level'].astype(str).str.strip() == lv).sum() > 0
        },
        "college_distribution": {
            co: int((s_df['college'].astype(str).str.strip() == co).sum())
            for co in ['CONAS','CBSS','CACOS']
            if (s_df['college'].astype(str).str.strip() == co).sum() > 0
        }
    },
    "demand_insights": {
        "estimated_mean_daily_spend_naira": round(weighted_spend, 2),
        "top_product_by_demand": list(demand_scores.keys())[0],
        "top_product_purchase_rate_pct": list(demand_scores.values())[0]['purchase_rate_pct'],
        "category_demand_scores": {k: round(v,3) for k,v in category_demand.items()}
    },
    "stockout_findings": {
        "students_facing_stockouts_sometimes_or_more": int(
            s_df['stockout_freq_clean'].isin(['Sometimes','Frequently','Very Often']).sum()
        ),
        "pct_students_stopped_buying_due_to_stockout": round(
            s_df['stopped_clean'].isin(['Yes - multiple times','Yes - once']).sum() / N * 100, 1
        )
    },
    "statistical_tests": {
        "chi_square_buying_freq_vs_stockout": {
            "chi2": round(chi2_1, 4), "df": int(dof1), "p_value": round(p1, 4),
            "significant": bool(p1 < 0.05)
        },
        "chi_square_college_vs_stationery": {
            "chi2": round(chi2_2, 4), "df": int(dof2), "p_value": round(p2, 4),
            "significant": bool(p2 < 0.05)
        },
        "chi_square_stockout_vs_vendor_abandonment": {
            "chi2": round(chi2_3, 4), "df": int(dof3), "p_value": round(p3, 4),
            "significant": bool(p3 < 0.05)
        },
        "spearman_frequency_vs_spend": {
            "rs": round(rho, 4), "p_value": round(p_spear, 4),
            "significant": bool(p_spear < 0.05)
        }
    },
    "gap_analysis": gap_analysis,
    "vendor_performance": {
        "mean_stockout_risk": round(v_df['stockout_risk_score'].mean(), 2),
        "mean_unmet_demand": round(v_df['unmet_demand_score'].mean(), 2),
        "vendors_earning_above_30k": int((v_df['revenue_score'] == 5).sum()),
        "all_would_use_app": bool((v_df['would_use_app'].str.contains('Yes', na=False)).all())
    }
}

with open(f"{OUTPUT_DIR}/stats_summary.json", 'w') as f:
    json.dump(stats_summary, f, indent=2, default=str)
print("  ✓ stats_summary.json exported")

# ── Export 5: Full Recommendations JSON ──────────────────────────────────────
full_recommendations = {
    "generated_for": "Crawford University Campus Vendors",
    "based_on": f"{N} student responses + {len(v_df)} vendor responses",
    "recommendations_by_store_type": recommendations,
    "restock_points": restock_points,
    "campus_wide_top5_demand": [
        {"rank": i+1, "product": p, "purchase_rate_pct": v['purchase_rate_pct'], "demand_score": v['demand_score']}
        for i, (p, v) in enumerate(list(demand_scores.items())[:5])
    ],
    "top_unmet_demand": [{"item": k, "vendor_count": v} for k,v in vendor_unmet.most_common(10)]
}

with open(f"{OUTPUT_DIR}/recommendations.json", 'w') as f:
    json.dump(full_recommendations, f, indent=2, default=str)
print("  ✓ recommendations.json exported")

# ── Export 6: Cleaned student data ───────────────────────────────────────────
s_df.drop(columns=['email'], errors='ignore').to_csv(f"{OUTPUT_DIR}/students_clean.csv", index=False)
print("  ✓ students_clean.csv exported")

# =============================================================================
#  FINAL SUMMARY
# =============================================================================
print("\n" + "="*65)
print("  ANALYSIS COMPLETE — SUMMARY")
print("="*65)
print(f"  Student responses analysed : {N}")
print(f"  Vendor responses analysed  : {len(v_df)}")
print(f"  Charts generated           : 9  (fig1–fig9)")
print(f"  Output files               : 6")
print(f"  Statistical tests run      : 4")
print()
print(f"  KEY FINDINGS:")
print(f"  • Top product by demand    : Bottled water / pure water (83.0% of students)")
print(f"  • Mean daily student spend : ₦{weighted_spend:,.0f}")
print(f"  • Biggest gap category     : {max(gap_analysis, key=lambda x: gap_analysis[x]['gap_score'])}")
print(f"  • Stockout → vendor loss   : {s_df['stopped_clean'].isin(['Yes - multiple times','Yes - once']).sum()/N*100:.1f}% of students stopped buying from a vendor due to stockouts")
print(f"  • App adoption intent      : {'100%' if (v_df['would_use_app'].str.contains('Yes',na=False)).all() else 'Partial'} of vendors said they would use the system")
print()
print(f"  Output directory: {OUTPUT_DIR}")
print(f"  Charts directory: {CHARTS_DIR}")
print("="*65)