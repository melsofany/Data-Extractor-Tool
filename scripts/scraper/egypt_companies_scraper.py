"""
مستخرج بيانات شركات مصر — النسخة النهائية
------------------------------------------------------
المصادر:
  1. yellowpages.com.eg — JSON-LD + تعداد IDs موازي
  2. Facebook             — عبر Bing
الشرط : كل شركة لازم يكون عندها إيميل أو واتساب (رقم موبايل مصري 01X)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = "Egypt_Companies_Real_Data.xlsx"
BACKUP_FILE = "backup_temp.xlsx"

# ===================== فئات مستهدفة =====================
CATEGORY_MAP = {
    "fire-fighting":              "الصحة والسلامة ومقاومة الحريق",
    "fire fighting":              "الصحة والسلامة ومقاومة الحريق",
    "safety-equipment":           "الصحة والسلامة ومقاومة الحريق",
    "safety equipment":           "الصحة والسلامة ومقاومة الحريق",
    "health-safety":              "الصحة والسلامة ومقاومة الحريق",
    "fire-alarm":                 "الصحة والسلامة ومقاومة الحريق",
    "fire alarm":                 "الصحة والسلامة ومقاومة الحريق",
    "electric-cables":            "الكهرباء والكابلات والأسلاك",
    "electrical-cables":          "الكهرباء والكابلات والأسلاك",
    "electrical-equipment":       "الكهرباء والكابلات والأسلاك",
    "electrical-supplies":        "الكهرباء والكابلات والأسلاك",
    "electrical-tools":           "الكهرباء والكابلات والأسلاك",
    "electricity":                "الكهرباء والكابلات والأسلاك",
    "wires":                      "الكهرباء والكابلات والأسلاك",
    "cables":                     "الكهرباء والكابلات والأسلاك",
    "mechanical":                 "الميكانيكا",
    "mechanical-equipment":       "الميكانيكا",
    "electronic":                 "الإلكترونيات",
    "electronics":                "الإلكترونيات",
    "cleaning-equipment":         "أدوات النظافة",
    "cleaning-supplies":          "أدوات النظافة",
    "cleaning-materials":         "أدوات النظافة",
    "cleaning-services":          "أدوات النظافة",
    "hotel-equipment":            "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "kitchen-equipment":          "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "catering-equipment":         "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "restaurants-equipment":      "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "restaurant-equipment":       "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "office-furniture":           "الأثاث المكتبي",
    "office-chairs":              "الأثاث المكتبي",
    "furniture":                  "الأثاث المكتبي",
    "information-technology":     "تكنولوجيا المعلومات (IT)",
    "information technology":     "تكنولوجيا المعلومات (IT)",
    "computers":                  "تكنولوجيا المعلومات (IT)",
    "computer":                   "تكنولوجيا المعلومات (IT)",
    "software":                   "تكنولوجيا المعلومات (IT)",
    "it-solutions":               "تكنولوجيا المعلومات (IT)",
    "networking":                 "تكنولوجيا المعلومات (IT)",
}

MOBILE_RE  = re.compile(r'(?<!\d)(01[0-2,5]\d{8})(?!\d)')
EMAIL_RE   = re.compile(r'[\w.\-]+@[\w.\-]+\.\w{2,6}')
WA_RE      = re.compile(r'wa\.me/(\d{10,15})', re.I)
BAD_EMAILS = ('example', 'yourmail', 'test@', 'noreply', 'sentry',
              'yellowpages', 'ypbeta', '@yellow.com', 'support@', 'admin@')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0",
]


def hdrs():
    return {"User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8,ar;q=0.5"}


def clean_email(em: str | None) -> str | None:
    if not em:
        return None
    em = em.strip().lower()
    if "@" not in em or len(em) < 6:
        return None
    if any(b in em for b in BAD_EMAILS):
        return None
    return em


def normalize_phone(ph: str | None) -> str | None:
    if not ph:
        return None
    digits = re.sub(r"\D", "", ph)
    if digits.startswith("20") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        return digits
    if len(digits) == 10 and digits.startswith("1"):
        return "0" + digits
    return digits if len(digits) >= 7 else None


# ===================== YellowPages =====================
def extract_from_page(html: str, cid: int) -> dict | None:
    """استخرج البيانات من HTML صفحة بروفايل YP"""
    # — من JSON-LD —
    name = phone = email = address = category = None

    jsonld_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.I)

    for raw_j in jsonld_blocks:
        try:
            d = json.loads(raw_j.strip())
        except Exception:
            continue

        # breadcrumb → فئة
        if d.get("@type") == "WebPage":
            bc = d.get("breadcrumb", "")
            bc_lower = bc.lower()
            for key, arabic in CATEGORY_MAP.items():
                if key in bc_lower:
                    category = arabic
                    break

        # LocalBusiness → بيانات الشركة
        if d.get("@type") == "LocalBusiness":
            name    = d.get("name", "").strip() or None
            raw_ph  = d.get("telephone", "")
            phone   = normalize_phone(raw_ph)
            em      = d.get("email", "")
            email   = clean_email(em)
            addr    = d.get("address") or {}
            street  = addr.get("streetAddress", "").strip()
            city    = addr.get("addressLocality", "").strip()
            address = ", ".join(filter(None, [street, city])) or None

    # إن لم تُعثر على الفئة من breadcrumb WebPage → نبحث في روابط /category/
    if not category:
        for m in re.finditer(r'/category/([a-z0-9\-]+)', html):
            slug = m.group(1).lower()
            for key, arabic in CATEGORY_MAP.items():
                if key.replace(" ", "-") in slug or key in slug:
                    category = arabic
                    break
            if category:
                break

    if not category:
        return None

    # — بحث إضافي عن إيميل في mailto: —
    if not email:
        for m in re.finditer(r'mailto:([^\s"\'<>?&]{4,80})', html, re.I):
            cand = clean_email(m.group(1))
            if cand:
                email = cand
                break

    # — بحث عن WhatsApp مباشر (wa.me/01XXXXXXXXX) —
    whatsapp = None
    for m in WA_RE.finditer(html):
        num = m.group(1)
        if len(num) >= 10 and "?" not in num:
            norm = normalize_phone(num)
            if norm:
                whatsapp = norm
                break

    # — إذا الرقم موبايل مصري → يصلح WhatsApp —
    if not whatsapp and phone and MOBILE_RE.match(phone):
        whatsapp = phone

    # الاسم من <h1> إن لم يُوجد في JSON-LD
    if not name:
        h1_m = re.search(r'<h1[^>]*>([^<]{3,120})</h1>', html, re.I)
        if h1_m:
            name = BeautifulSoup(h1_m.group(1), "html.parser").get_text(strip=True)[:100]

    if not name:
        return None

    return {
        "Company Name": name,
        "Phone":        phone,
        "WhatsApp":     whatsapp,
        "Email":        email,
        "Address":      address,
        "Category":     category,
        "Source":       "YellowPages",
        "URL":          f"https://www.yellowpages.com.eg/en/profile/x/{cid}",
    }


_blocked_count = 0  # عداد مشترك لطلبات 403


def scrape_yp_id(cid: int) -> dict | None:
    global _blocked_count
    url = f"https://www.yellowpages.com.eg/en/profile/x/{cid}"
    try:
        r = requests.get(url, headers=hdrs(), timeout=10)
        if r.status_code == 403:
            _blocked_count += 1
            return None
        if r.status_code in (404, 410) or len(r.text) < 5000:
            return None
        if r.status_code != 200:
            return None
        return extract_from_page(r.text, cid)
    except Exception:
        return None


def run_yp_scraper(
    max_companies: int = 5000,
    workers: int = 20,
    id_start: int = 300_000,
    id_end: int = 720_000,
    sample_size: int | None = None,
) -> list[dict]:
    """يجمع شركات من YP بالتوازي"""
    global _blocked_count
    _blocked_count = 0

    all_ids = list(range(id_start, id_end + 1))
    random.shuffle(all_ids)
    if sample_size:
        all_ids = all_ids[:sample_size]

    print(f"  🔢 IDs للفحص : {len(all_ids):,}")
    print(f"  ⚡ Threads    : {workers}")

    companies: list[dict] = []
    processed = 0
    start_t = time.time()
    last_block_warn = 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(scrape_yp_id, cid): cid for cid in all_ids}
        for fut in as_completed(futures):
            processed += 1
            res = fut.result()
            if res:
                companies.append(res)
                if len(companies) % 50 == 0:
                    elapsed = time.time() - start_t
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"  ✅ {len(companies):4d} شركة | فحص {processed:,} | {rate:.1f} req/s")
                    pd.DataFrame(companies).to_excel(BACKUP_FILE, index=False)
                if len(companies) >= max_companies:
                    for f in futures:
                        f.cancel()
                    break

            # تقرير تقدم كل 1000 طلب
            if processed % 1000 == 0:
                elapsed = time.time() - start_t
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"  ⏳ {len(companies):4d} شركة | فحص {processed:,} | {rate:.1f} req/s | محجوب: {_blocked_count}")

            # تحذير مبكر إذا كان الموقع يحجب الطلبات
            if _blocked_count >= 50 and _blocked_count != last_block_warn and _blocked_count % 50 == 0:
                last_block_warn = _blocked_count
                block_pct = int(_blocked_count / max(processed, 1) * 100)
                print(f"  ⚠️ [ERR] الموقع يحجب الطلبات — {_blocked_count} طلب محجوب ({block_pct}% من الإجمالي)")
                if block_pct >= 80 and processed >= 200:
                    print(f"  ❌ [ERR] الموقع يحجب أكثر من 80% من الطلبات — YellowPages يمنع السكريبت حالياً")
                    for f in futures:
                        f.cancel()
                    break

    elapsed = time.time() - start_t
    print(f"\n  📌 فحصنا {processed:,} ID خلال {elapsed:.0f}ث → {len(companies)} شركة في الفئات")
    if _blocked_count > 0:
        print(f"  ⚠️ طلبات محجوبة (403): {_blocked_count}")
    return companies


# ===================== Facebook via Bing =====================
FB_QUERIES: dict[str, list[str]] = {
    "الصحة والسلامة ومقاومة الحريق": [
        'site:facebook.com "معدات إطفاء" مصر',
        'site:facebook.com "fire fighting equipment" egypt',
        'site:facebook.com "أجهزة حريق" مصر',
        'site:facebook.com "fire alarm" egypt company',
        'site:facebook.com "سلامة وحريق" مصر',
    ],
    "الكهرباء والكابلات والأسلاك": [
        'site:facebook.com "كابلات كهربائية" مصر',
        'site:facebook.com "electrical cables" egypt',
        'site:facebook.com "تجهيزات كهربائية" مصر',
        'site:facebook.com "electrical supplies" egypt',
    ],
    "الميكانيكا": [
        'site:facebook.com "ميكانيكا" مصر هاتف',
        'site:facebook.com "mechanical parts" egypt',
        'site:facebook.com "قطع غيار ميكانيكية" مصر',
    ],
    "الإلكترونيات": [
        'site:facebook.com "إلكترونيات" مصر هاتف',
        'site:facebook.com "electronics company" egypt',
        'site:facebook.com "أجهزة إلكترونية" مصر',
    ],
    "أدوات النظافة": [
        'site:facebook.com "معدات تنظيف" مصر',
        'site:facebook.com "cleaning equipment" egypt',
        'site:facebook.com "مستلزمات نظافة" مصر',
    ],
    "معدات المطابخ الكبيرة الفندقية وقطع غيارها": [
        'site:facebook.com "معدات مطابخ فندقية" مصر',
        'site:facebook.com "hotel kitchen equipment" egypt',
        'site:facebook.com "تجهيزات مطاعم" مصر',
        'site:facebook.com "catering equipment" egypt',
    ],
    "الأثاث المكتبي": [
        'site:facebook.com "أثاث مكتبي" مصر',
        'site:facebook.com "office furniture" egypt',
        'site:facebook.com "furniture company" egypt',
    ],
    "تكنولوجيا المعلومات (IT)": [
        'site:facebook.com "تكنولوجيا معلومات" مصر',
        'site:facebook.com "IT company" egypt',
        'site:facebook.com "software company" egypt',
        'site:facebook.com "حلول تقنية" مصر',
    ],
}


def bing_fb_urls(query: str, n: int = 8) -> list[str]:
    try:
        r = requests.get(
            "https://www.bing.com/search",
            params={"q": query, "count": n},
            headers={**hdrs(), "Accept-Language": "ar,en;q=0.8"},
            timeout=15,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if "facebook.com/" not in h:
                continue
            clean = re.sub(r"\?.*", "", h).rstrip("/")
            slug = clean.split("facebook.com/")[-1]
            if (len(slug) > 2
                    and not any(x in slug.lower() for x in
                                ("search", "login", "policies", "help", "sharer", "share"))):
                if clean not in urls:
                    urls.append(clean)
            if len(urls) >= n:
                break
        return urls
    except Exception:
        return []


def scrape_fb_about(fb_url: str, category: str) -> dict | None:
    try:
        about_url = fb_url.rstrip("/") + "/about"
        r = requests.get(about_url, headers=hdrs(), timeout=15)
        if r.status_code != 200:
            return None
        text = r.text
        soup = BeautifulSoup(text, "html.parser")
        page_text = soup.get_text(separator=" ")

        # اسم الصفحة
        title = soup.find("title")
        name = ""
        if title:
            name = (title.text
                    .replace("| Facebook", "").replace("- Facebook", "")
                    .replace("|", "").replace("Facebook", "").strip())
        if not name or len(name) < 3:
            return None

        # إيميل
        email = None
        for m in re.finditer(r'mailto:([^\s"\'<>?&]{4,80})', text, re.I):
            cand = clean_email(m.group(1))
            if cand:
                email = cand
                break
        if not email:
            for m in EMAIL_RE.finditer(page_text):
                cand = clean_email(m.group(0))
                if cand:
                    email = cand
                    break

        # هاتف
        phone = None
        mob = MOBILE_RE.search(page_text)
        if mob:
            phone = mob.group(1)

        # WhatsApp
        whatsapp = None
        wa_m = WA_RE.search(text)
        if wa_m:
            whatsapp = normalize_phone(wa_m.group(1))
        if not whatsapp and phone and MOBILE_RE.match(phone):
            whatsapp = phone

        # عنوان
        address = None
        for pat in [
            r'(?:Address|العنوان|موقعنا)[:\s]+(.{5,120}?)(?:\n|[.،])',
            r'(?:يقع|مقر)[:\s]+(.{5,120}?)(?:\n|[.،])',
        ]:
            am = re.search(pat, page_text, re.I)
            if am:
                address = am.group(1).strip()
                break

        return {
            "Company Name": name[:120],
            "Phone":        phone,
            "WhatsApp":     whatsapp,
            "Email":        email,
            "Address":      address,
            "Category":     category,
            "Source":       "Facebook",
            "URL":          fb_url,
        }
    except Exception:
        return None


def run_facebook_scraper(max_per_cat: int = 40) -> list[dict]:
    results = []
    for cat, queries in FB_QUERIES.items():
        cat_res = []
        seen_urls: set[str] = set()
        for q in queries:
            time.sleep(random.uniform(1.0, 2.5))
            urls = bing_fb_urls(q, n=8)
            for url in urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                time.sleep(random.uniform(0.8, 1.8))
                data = scrape_fb_about(url, cat)
                if data:
                    cat_res.append(data)
                    wa = data.get("WhatsApp") or "—"
                    em = data.get("Email") or "—"
                    print(f"    📘 {data['Company Name'][:35]:35} WA:{wa} EM:{em}")
            if len(cat_res) >= max_per_cat:
                break
        results.extend(cat_res)
        print(f"  ✅ {cat}: {len(cat_res)} شركة (Facebook)")
    return results


# ===================== فلتر & حفظ =====================
def has_valid_contact(rec: dict) -> bool:
    em = str(rec.get("Email") or "").strip()
    wa = re.sub(r"\D", "", str(rec.get("WhatsApp") or ""))
    return ("@" in em) or (len(wa) >= 9)


def save_excel(records: list[dict], path: str) -> None:
    cols = ["Company Name", "Phone", "WhatsApp", "Email",
            "Address", "Category", "Source", "URL"]
    df = pd.DataFrame(records)
    df = df[[c for c in cols if c in df.columns]]
    # Preserve leading zeros — save phone/WhatsApp as strings
    for col in ("Phone", "WhatsApp"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: str(v).strip() if pd.notna(v) and str(v).strip() not in ("", "nan") else ""
            )
    df.to_excel(path, index=False, engine="openpyxl")


# ===================== main =====================
def main():
    print("=" * 64)
    print("  مستخرج بيانات شركات مصر — YellowPages + Facebook")
    print("=" * 64)

    all_records: list[dict] = []

    # ── YellowPages ────────────────────────────────────────────
    print("\n🟡 YellowPages — تعداد بالـ ID:")
    yp = run_yp_scraper(
        max_companies=5000,
        workers=20,
        id_start=300_000,
        id_end=720_000,
        sample_size=60_000,   # عينة عشوائية من النطاق
    )
    all_records.extend(yp)
    print(f"\n✅ YellowPages: {len(yp)} شركة")
    if all_records:
        save_excel(all_records, BACKUP_FILE)

    # ── Facebook ────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print("🔵 Facebook عبر Bing:")
    fb = run_facebook_scraper(max_per_cat=40)
    all_records.extend(fb)
    print(f"\n✅ Facebook: {len(fb)} شركة")
    if all_records:
        save_excel(all_records, BACKUP_FILE)

    # ── إحصاء & فلترة ───────────────────────────────────────────
    print(f"\n{'='*64}")
    print("📋 الفلترة النهائية...")

    if not all_records:
        print("❌ لا توجد بيانات!")
        return

    df = pd.DataFrame(all_records)
    raw_total = len(df)
    df.drop_duplicates(subset=["Company Name"], keep="first", inplace=True)
    after_dd = len(df)

    valid = [r for r in df.to_dict("records") if has_valid_contact(r)]
    after_filter = len(valid)

    save_excel(valid, OUTPUT_FILE)

    print(f"\n  إجمالي                : {raw_total}")
    print(f"  بعد إزالة التكرار     : {after_dd}")
    print(f"  بعد فلترة إيميل/WA    : {after_filter}")
    print(f"\n✅ الملف النهائي: {OUTPUT_FILE}")

    df_out = pd.DataFrame(valid)
    if "Source" in df_out.columns:
        print("\n📊 المصادر:")
        print(df_out["Source"].value_counts().to_string())
    if "Category" in df_out.columns:
        print("\n📊 الفئات:")
        print(df_out["Category"].value_counts().to_string())


if __name__ == "__main__":
    main()
