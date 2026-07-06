"""
Sumwon Studios — Data Processor
Reads 4 CSV files, outputs clean JSON for the dashboard
"""
import csv, io, re, json
from datetime import datetime
from collections import defaultdict


def parse_num(s):
    if not s or s.strip() in ('', '-', '\u2014', 'null', '#N/A', 'N/A'):
        return None
    s = s.strip()
    neg = s.startswith('(') and s.endswith(')')
    s = re.sub(r'[\$,\(\)%]', '', s).strip()
    try:
        v = float(s)
        return -v if neg else v
    except:
        return None


def read_csv(file_bytes):
    """Read a UTF-16-LE tab-delimited CSV from bytes."""
    content = file_bytes.decode('utf-16-le')
    return list(csv.reader(io.StringIO(content), delimiter='\t'))


def date_to_week(ds):
    try:
        d = datetime.strptime(ds.strip(), '%d %B %Y')
        return f"{d.year}-W{d.isocalendar()[1]:02d}"
    except:
        return None


def process_files(table1_bytes, table2_bytes, cohort_bytes, webshop_bytes):
    """
    Process all 4 uploaded files and return dashboard JSON.
    Returns dict with keys: weeks, brands, display, data
    """

    # ── TABLE 2: SHEIN + Platform revenue ──────────────────
    t2 = read_csv(table2_bytes)
    shein = defaultdict(lambda: defaultdict(lambda: {
        'sr': 0, 'sp': 0, 'wr': 0, 'wp': 0, 'us': 0, 'uw': 0
    }))
    all_wks = set()

    for r in t2[1:]:
        if len(r) < 9:
            continue
        yr, wk, brand, ctry, site = r[0], r[1], r[2], r[3], r[4]
        ns, units, rrp, pc2 = r[5], r[6], r[7], r[8]
        if brand in ('Grand Total', '') or wk in ('Total', ''):
            continue
        period = f'{yr}-{wk}'
        all_wks.add(period)
        ns_v = parse_num(ns) or 0
        pc2_v = parse_num(pc2) or 0
        u_v = parse_num(units) or 0
        if site == 'shein':
            shein[period][brand]['sr'] += ns_v
            shein[period][brand]['sp'] += pc2_v
            shein[period][brand]['us'] += u_v
        elif site == 'platform':
            shein[period][brand]['wr'] += ns_v
            shein[period][brand]['wp'] += pc2_v
            shein[period][brand]['uw'] += u_v

    # ── COHORT: Hit rate ────────────────────────────────────
    cohort = read_csv(cohort_bytes)
    hr = defaultdict(lambda: defaultdict(lambda: {
        'l': 0, 'h': 0, 'nl': 0, 'nh': 0
    }))

    for r in cohort[1:]:
        if len(r) < 18:
            continue
        yr, wk, brand, orig = r[0], r[1], r[2], r[7]
        if brand in ('Total', '') or wk in ('Total', ''):
            continue
        period = f'{yr}-{wk}'
        l = parse_num(r[13]) or 0
        h = parse_num(r[16]) or 0
        hr[period][brand]['l'] += l
        hr[period][brand]['h'] += h
        if orig == 'New':
            hr[period][brand]['nl'] += l
            hr[period][brand]['nh'] += h

    # ── TABLE 1: Inventory ──────────────────────────────────
    t1 = read_csv(table1_bytes)
    inv = defaultdict(lambda: defaultdict(lambda: {
        'ivw': 0, 'units': 0
    }))

    for r in t1[1:]:
        if len(r) < 21:
            continue
        yr, wk, brand = r[0], r[1], r[2]
        if brand in ('Grand Total', '') or wk in ('Total', ''):
            continue
        period = f'{yr}-{wk}'
        inv[period][brand]['units'] += parse_num(r[12]) or 0
        inv[period][brand]['ivw'] += parse_num(r[19]) or 0

    # ── WEBSHOP pivot ───────────────────────────────────────
    ws = read_csv(webshop_bytes)
    wk_keys = [date_to_week(d) for d in ws[1][2:-1]]

    KEY_METRICS = [
        'Spending', 'Active Users', 'CR%', 'ROAS_before_returns',
        'ROAS_after_returns', 'Net_sales_before_returns', 'Net_sales_target',
        'Net_sales target Completion Rate', 'Orders', 'Sold_items', 'AOV',
        'ITO', 'ASP', 'TDR%', 'PC_II%', 'PC_II', 'PC_II_target',
        'PC_II target Completion Rate', 'Net_Sales_after_returns',
        'New_customers', 'Return_customers', 'Return_customers%',
        'CAC', 'CAC (Digital Marketing)', 'Coupon_value'
    ]

    SITE_TO_BRAND = {
        'Missguided':     'MISSGUIDED',
        'SUMWON':         'SUMWON - Women',
        'Sumwonstudios':  'SUMWON - Women',
        'KIZN':           'KIZN',
        'AiiRZ':          'AiiRZ',
    }
    BRAND_TO_SITE = {
        'MISSGUIDED':     'Missguided',
        'AiiRZ':          'AiiRZ',
        'KIZN':           'KIZN',
        'SUMWON - Women': 'Sumwonstudios',
    }

    # All webshop sites shown separately in the webshop section
    WEB_SITE_NAMES = {
        'Missguided':    'Missguided',
        'SUMWON':        'Sumwon',
        'Sumwonstudios': 'Sumwon Studios',
        'KIZN':          'KIZN',
        'AiiRZ':         'AiiRZ',
    }

    web = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
    curr_site = None
    for r in ws[2:]:
        site = r[0].strip() if r[0] else None
        if site and site != 'Grand Total':
            curr_site = site
        metric = r[1].strip() if len(r) > 1 else ''
        if not curr_site or metric not in KEY_METRICS:
            continue
        for i, wk in enumerate(wk_keys):
            if wk and i + 2 < len(r):
                web[wk][curr_site][metric] = parse_num(r[i + 2])

    # ── COMPILE ─────────────────────────────────────────────
    BRANDS = [
        'MISSGUIDED', 'MISSGUIDED - Playboy', 'AiiRZ',
        'SUMWON - Women', 'SUMWON - Men', 'SUMWON - Kids', 'SUMWON - Playboy',
        'BABYPHAT', 'KIZN', 'KSTM'
    ]
    DISPLAY = {
        'MISSGUIDED':           'Missguided',
        'MISSGUIDED - Playboy': 'Playboy x MSG',
        'AiiRZ':                'AiiRZ',
        'SUMWON - Women':       'Sumwon Women',
        'SUMWON - Men':         'Sumwon Men',
        'SUMWON - Kids':        'Sumwon Kids',
        'SUMWON - Playboy':     'Playboy x SWM',
        'BABYPHAT':             'Baby Phat',
        'KIZN':                 'KIZN',
        'KSTM':                 'KSTM',
    }

    sorted_wks = sorted(
        all_wks,
        key=lambda x: (int(x.split('-')[0]), int(x.split('-W')[1]))
    )

    # Find latest week with hit rate data
    hr_wk = None
    for wk in reversed(sorted_wks):
        if any(hr[wk][b]['l'] > 0 for b in BRANDS):
            hr_wk = wk
            break

    data = {}
    for wk in sorted_wks:
        data[wk] = {}
        for brand in BRANDS:
            s = shein[wk][brand]
            h = hr[wk][brand]
            iv = inv[wk][brand]
            hrt = round(h['h'] / h['l'] * 100, 1) if h['l'] else None
            hrn = round(h['nh'] / h['nl'] * 100, 1) if h['nl'] else None
            r_launched = h['l'] - h['nl']
            r_hits     = h['h'] - h['nh']
            hrl = round(r_hits / r_launched * 100, 1) if r_launched else None
            cover = round(iv['ivw'] / (iv['units'] / 7), 1) if iv['units'] > 0 else None

            site_name = BRAND_TO_SITE.get(brand)
            wd = web[wk].get(site_name, {}) if site_name else {}

            data[wk][brand] = {
                'd': DISPLAY.get(brand, brand),
                'sr':  round(s['sr'], 0),
                'sp':  round(s['sp'], 0),
                'spp': round(s['sp'] / s['sr'] * 100, 1) if s['sr'] else 0,
                'wr':  round(s['wr'], 0),
                'wp':  round(s['wp'], 0),
                'wpp': round(s['wp'] / s['wr'] * 100, 1) if s['wr'] else 0,
                'hrt': hrt, 'hrn': hrn, 'hrl': hrl,
                'skl': round(h['l'], 0), 'skl_n': round(h['nl'], 0), 'skl_r': round(r_launched, 0),
                'ivw': round(iv['ivw'], 0),
                'cvd': cover,
                'w_rev':    wd.get('Net_sales_before_returns'),
                'w_rev_ar': wd.get('Net_Sales_after_returns'),
                'w_tgt':    wd.get('Net_sales_target'),
                'w_tgt_cr': wd.get('Net_sales target Completion Rate'),
                'w_spend':  wd.get('Spending'),
                'w_roas':   wd.get('ROAS_before_returns'),
                'w_roas_ar':wd.get('ROAS_after_returns'),
                'w_cac':    wd.get('CAC'),
                'w_cac_dm': wd.get('CAC (Digital Marketing)'),
                'w_orders': wd.get('Orders'),
                'w_items':  wd.get('Sold_items'),
                'w_aov':    wd.get('AOV'),
                'w_ito':    wd.get('ITO'),
                'w_asp':    wd.get('ASP'),
                'w_cr':     wd.get('CR%'),
                'w_tdr':    wd.get('TDR%'),
                'w_pc2pct': wd.get('PC_II%'),
                'w_pc2':    wd.get('PC_II'),
                'w_pc2tgt': wd.get('PC_II_target'),
                'w_new_cust':wd.get('New_customers'),
                'w_ret_cust':wd.get('Return_customers'),
                'w_users':  wd.get('Active Users'),
            }

    # Build webshop site data separately (each site as its own row)
    webshop_sites_data = {}
    for wk in sorted_wks:
        webshop_sites_data[wk] = {}
        for site_key, site_display in WEB_SITE_NAMES.items():
            wd = web[wk].get(site_key, {})
            webshop_sites_data[wk][site_key] = {
                'display':    site_display,
                'w_rev':      wd.get('Net_sales_before_returns'),
                'w_rev_ar':   wd.get('Net_Sales_after_returns'),
                'w_tgt':      wd.get('Net_sales_target'),
                'w_tgt_cr':   wd.get('Net_sales target Completion Rate'),
                'w_spend':    wd.get('Spending'),
                'w_roas':     wd.get('ROAS_before_returns'),
                'w_roas_ar':  wd.get('ROAS_after_returns'),
                'w_cac':      wd.get('CAC'),
                'w_cac_dm':   wd.get('CAC (Digital Marketing)'),
                'w_orders':   wd.get('Orders'),
                'w_aov':      wd.get('AOV'),
                'w_ito':      wd.get('ITO'),
                'w_cr':       wd.get('CR%'),
                'w_tdr':      wd.get('TDR%'),
                'w_pc2pct':   wd.get('PC_II%'),
                'w_pc2':      wd.get('PC_II'),
                'w_users':    wd.get('Active Users'),
                'w_new_cust': wd.get('New_customers'),
                'w_ret_cust': wd.get('Return_customers'),
            }

    return {
        'weeks':        sorted_wks,
        'brands':       BRANDS,
        'display':      DISPLAY,
        'web_sites':    list(WEB_SITE_NAMES.keys()),
        'web_display':  WEB_SITE_NAMES,
        'hr_wk':        hr_wk or (sorted_wks[-3] if len(sorted_wks) >= 3 else sorted_wks[0]),
        'updated':      datetime.utcnow().strftime('%d %b %Y %H:%M UTC'),
        'data':         data,
        'webshop':      webshop_sites_data,
    }
