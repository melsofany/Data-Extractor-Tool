"""
مستخرج بيانات شركات مصر — v2
-----------------------------------------------
الجديد:
  - استخراج الإيميل من موقع الشركة الرسمي (أهم تحسين)
  - 20 تصنيف بدلاً من 8
  - فلترة بالمحافظات
  - إعدادات من ملف config (categories + governorates)
  - حفظ كل الشركات (بغض النظر عن الإيميل) مع عمود "حالة التواصل"
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = "Egypt_Companies_Real_Data.xlsx"
BACKUP_FILE = "backup_temp.xlsx"
CONFIG_FILE = "/tmp/scraper_config.json"


# ===================== تحميل الإعدادات =====================
def _load_cfg():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

_CFG = _load_cfg()


# ===================== التصنيفات الكاملة =====================
CATEGORY_MAP = {
    # ── الحريق والسلامة ──────────────────────────────────────
    "fire-fighting":            "الصحة والسلامة ومقاومة الحريق",
    "fire fighting":            "الصحة والسلامة ومقاومة الحريق",
    "safety-equipment":         "الصحة والسلامة ومقاومة الحريق",
    "safety equipment":         "الصحة والسلامة ومقاومة الحريق",
    "health-safety":            "الصحة والسلامة ومقاومة الحريق",
    "fire-alarm":               "الصحة والسلامة ومقاومة الحريق",
    "fire alarm":               "الصحة والسلامة ومقاومة الحريق",
    "firefighting":             "الصحة والسلامة ومقاومة الحريق",
    "safety":                   "الصحة والسلامة ومقاومة الحريق",
    # ── الكهرباء ─────────────────────────────────────────────
    "electric-cables":          "الكهرباء والكابلات والأسلاك",
    "electrical-cables":        "الكهرباء والكابلات والأسلاك",
    "electrical-equipment":     "الكهرباء والكابلات والأسلاك",
    "electrical-supplies":      "الكهرباء والكابلات والأسلاك",
    "electrical-tools":         "الكهرباء والكابلات والأسلاك",
    "electricity":              "الكهرباء والكابلات والأسلاك",
    "wires":                    "الكهرباء والكابلات والأسلاك",
    "cables":                   "الكهرباء والكابلات والأسلاك",
    "electrical":               "الكهرباء والكابلات والأسلاك",
    "switchgear":               "الكهرباء والكابلات والأسلاك",
    "insulation":               "الكهرباء والكابلات والأسلاك",
    "lamps":                    "الكهرباء والكابلات والأسلاك",
    "lighting":                 "الكهرباء والكابلات والأسلاك",
    "generators":               "الكهرباء والكابلات والأسلاك",
    "solar":                    "الكهرباء والكابلات والأسلاك",
    # ── الميكانيكا ───────────────────────────────────────────
    "mechanical":               "الميكانيكا",
    "mechanical-equipment":     "الميكانيكا",
    "machine-parts":            "الميكانيكا",
    "machinery":                "الميكانيكا",
    # ── الإلكترونيات ─────────────────────────────────────────
    "electronic":               "الإلكترونيات",
    "electronics":              "الإلكترونيات",
    "consumer-electronics":     "الإلكترونيات",
    # ── النظافة ──────────────────────────────────────────────
    "cleaning-equipment":       "أدوات النظافة",
    "cleaning-supplies":        "أدوات النظافة",
    "cleaning-materials":       "أدوات النظافة",
    "cleaning-services":        "أدوات النظافة",
    "cleaning":                 "أدوات النظافة",
    # ── مطابخ فندقية ─────────────────────────────────────────
    "hotel-equipment":          "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "kitchen-equipment":        "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "catering-equipment":       "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "restaurants-equipment":    "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "restaurant-equipment":     "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    "catering":                 "معدات المطابخ الكبيرة الفندقية وقطع غيارها",
    # ── الأثاث المكتبي ───────────────────────────────────────
    "office-furniture":         "الأثاث المكتبي",
    "office-chairs":            "الأثاث المكتبي",
    "furniture":                "الأثاث المكتبي",
    "office-supplies":          "الأثاث المكتبي",
    # ── IT ───────────────────────────────────────────────────
    "information-technology":   "تكنولوجيا المعلومات (IT)",
    "information technology":   "تكنولوجيا المعلومات (IT)",
    "computers":                "تكنولوجيا المعلومات (IT)",
    "computer":                 "تكنولوجيا المعلومات (IT)",
    "software":                 "تكنولوجيا المعلومات (IT)",
    "it-solutions":             "تكنولوجيا المعلومات (IT)",
    "networking":               "تكنولوجيا المعلومات (IT)",
    "it":                       "تكنولوجيا المعلومات (IT)",
    # ── مواد البناء ──────────────────────────────────────────
    "construction":             "مواد البناء والمقاولات",
    "building-materials":       "مواد البناء والمقاولات",
    "contractors":              "مواد البناء والمقاولات",
    "construction-materials":   "مواد البناء والمقاولات",
    "cement":                   "مواد البناء والمقاولات",
    "steel":                    "مواد البناء والمقاولات",
    "iron-steel":               "مواد البناء والمقاولات",
    "tiles":                    "مواد البناء والمقاولات",
    "marble":                   "مواد البناء والمقاولات",
    "paints":                   "مواد البناء والمقاولات",
    "paint-and-coating":        "مواد البناء والمقاولات",
    "paint":                    "مواد البناء والمقاولات",
    "aluminum":                 "مواد البناء والمقاولات",
    "aluminium":                "مواد البناء والمقاولات",
    "wood":                     "مواد البناء والمقاولات",
    "glass":                    "مواد البناء والمقاولات",
    "flooring":                 "مواد البناء والمقاولات",
    "doors-windows":            "مواد البناء والمقاولات",
    "plumbing":                 "مواد البناء والمقاولات",
    # ── المعدات الطبية ───────────────────────────────────────
    "medical-equipment":        "المعدات الطبية والصيدلانية",
    "medical":                  "المعدات الطبية والصيدلانية",
    "pharmaceutical":           "المعدات الطبية والصيدلانية",
    "medical-supplies":         "المعدات الطبية والصيدلانية",
    "hospital-equipment":       "المعدات الطبية والصيدلانية",
    "medical-devices":          "المعدات الطبية والصيدلانية",
    "pharmaceuticals":          "المعدات الطبية والصيدلانية",
    "laboratories-medical":     "المعدات الطبية والصيدلانية",
    "laboratories":             "المعدات الطبية والصيدلانية",
    "lab":                      "المعدات الطبية والصيدلانية",
    # ── السيارات ─────────────────────────────────────────────
    "automotive":               "السيارات وقطع الغيار",
    "auto-parts":               "السيارات وقطع الغيار",
    "car-parts":                "السيارات وقطع الغيار",
    "cars-parts":               "السيارات وقطع الغيار",
    "spare-parts":              "السيارات وقطع الغيار",
    "vehicles":                 "السيارات وقطع الغيار",
    "car-accessories":          "السيارات وقطع الغيار",
    "automotive-service":       "السيارات وقطع الغيار",
    "cars-rentals":             "السيارات وقطع الغيار",
    "car-rentals":              "السيارات وقطع الغيار",
    "tires":                    "السيارات وقطع الغيار",
    # ── الأمن والمراقبة ──────────────────────────────────────
    "security":                 "الأمن والحراسة وأنظمة المراقبة",
    "security-systems":         "الأمن والحراسة وأنظمة المراقبة",
    "cctv":                     "الأمن والحراسة وأنظمة المراقبة",
    "surveillance":             "الأمن والحراسة وأنظمة المراقبة",
    "alarm-systems":            "الأمن والحراسة وأنظمة المراقبة",
    "access-control":           "الأمن والحراسة وأنظمة المراقبة",
    "security-cameras":         "الأمن والحراسة وأنظمة المراقبة",
    # ── التكييف والتبريد ──────────────────────────────────────
    "air-conditioning":         "التكييف والتبريد",
    "hvac":                     "التكييف والتبريد",
    "cooling":                  "التكييف والتبريد",
    "refrigeration":            "التكييف والتبريد",
    "ac-units":                 "التكييف والتبريد",
    # ── معالجة المياه ────────────────────────────────────────
    "water-treatment":          "معالجة المياه والصرف الصحي",
    "water-pumps":              "معالجة المياه والصرف الصحي",
    "pumps":                    "معالجة المياه والصرف الصحي",
    "water-systems":            "معالجة المياه والصرف الصحي",
    "sewage":                   "معالجة المياه والصرف الصحي",
    "sanitaryware":             "معالجة المياه والصرف الصحي",
    "sanitary":                 "معالجة المياه والصرف الصحي",
    "water":                    "معالجة المياه والصرف الصحي",
    # ── الطباعة والإعلان ─────────────────────────────────────
    "printing":                 "الطباعة والنشر والإعلان",
    "advertising":              "الطباعة والنشر والإعلان",
    "signage":                  "الطباعة والنشر والإعلان",
    "publishing":               "الطباعة والنشر والإعلان",
    "marketing":                "الطباعة والنشر والإعلان",
    # ── الأغذية والمشروبات ───────────────────────────────────
    "food":                     "الأغذية والمشروبات",
    "food-industry":            "الأغذية والمشروبات",
    "beverages":                "الأغذية والمشروبات",
    "food-products":            "الأغذية والمشروبات",
    "dairy":                    "الأغذية والمشروبات",
    "bakery":                   "الأغذية والمشروبات",
    "dairy-industry":           "الأغذية والمشروبات",
    "food-producers":           "الأغذية والمشروبات",
    "poultry":                  "الأغذية والمشروبات",
    "meat":                     "الأغذية والمشروبات",
    "spices":                   "الأغذية والمشروبات",
    # ── النسيج والملابس ──────────────────────────────────────
    "textile":                  "النسيج والملابس",
    "clothing":                 "النسيج والملابس",
    "garments":                 "النسيج والملابس",
    "fabrics":                  "النسيج والملابس",
    "fashion":                  "النسيج والملابس",
    "clothing-shops":           "النسيج والملابس",
    "tailors":                  "النسيج والملابس",
    "uniforms":                 "النسيج والملابس",
    # ── الشحن والنقل ─────────────────────────────────────────
    "shipping":                 "الشحن والنقل واللوجستيات",
    "logistics":                "الشحن والنقل واللوجستيات",
    "freight":                  "الشحن والنقل واللوجستيات",
    "transportation":           "الشحن والنقل واللوجستيات",
    "cargo":                    "الشحن والنقل واللوجستيات",
    "moving":                   "الشحن والنقل واللوجستيات",
    # ── الزراعة ──────────────────────────────────────────────
    "agriculture":              "الزراعة والري",
    "agricultural-equipment":   "الزراعة والري",
    "irrigation":               "الزراعة والري",
    "seeds":                    "الزراعة والري",
    "fertilizers":              "الزراعة والري",
    # ── العقارات ─────────────────────────────────────────────
    "real-estate":              "العقارات والمقاولات",
    "property":                 "العقارات والمقاولات",
    "real estate":              "العقارات والمقاولات",
}

# التصنيفات العربية المختارة (None = كل التصنيفات)
_sel_cats_raw = _CFG.get("categories")
SELECTED_CATS: set | None = set(_sel_cats_raw) if _sel_cats_raw else None


# ===================== المحافظات =====================
GOVERNORATE_KEYWORDS: dict[str, list[str]] = {
    "cairo":         ["cairo", "القاهرة", "قاهرة", "maadi", "heliopolis", "nasr city", "zamalek", "mohandeseen", "downtown cairo"],
    "alexandria":    ["alexandria", "الإسكندرية", "اسكندرية", "alex"],
    "giza":          ["giza", "الجيزة", "جيزة", "6th october", "sheikh zayed", "october city", "12 october"],
    "sharkia":       ["sharkia", "الشرقية", "شرقية", "zagazig", "10th ramadan"],
    "dakahlia":      ["dakahlia", "الدقهلية", "دقهلية", "mansoura"],
    "beheira":       ["beheira", "البحيرة", "بحيرة", "damanhour"],
    "gharbia":       ["gharbia", "الغربية", "غربية", "tanta"],
    "menoufia":      ["menoufia", "المنوفية", "منوفية", "shibin"],
    "qalyubia":      ["qalyubia", "القليوبية", "قليوبية", "banha", "obour", "10th ramadan"],
    "kafr-elsheikh": ["kafr el-sheikh", "kafr elsheikh", "كفر الشيخ", "kafr"],
    "damietta":      ["damietta", "دمياط"],
    "ismailia":      ["ismailia", "الإسماعيلية", "اسماعيلية"],
    "port-said":     ["port said", "بورسعيد", "port saeed"],
    "suez":          ["suez", "السويس"],
    "north-sinai":   ["north sinai", "شمال سيناء", "arish", "العريش"],
    "south-sinai":   ["south sinai", "جنوب سيناء", "sharm", "nuweiba"],
    "beni-suef":     ["beni suef", "بني سويف", "benisuef"],
    "faiyum":        ["faiyum", "fayoum", "الفيوم"],
    "minya":         ["minya", "المنيا", "minia"],
    "asyut":         ["asyut", "أسيوط", "assiut", "assuit"],
    "sohag":         ["sohag", "سوهاج"],
    "qena":          ["qena", "قنا"],
    "luxor":         ["luxor", "الأقصر"],
    "aswan":         ["aswan", "أسوان"],
    "red-sea":       ["red sea", "البحر الأحمر", "hurghada", "الغردقة", "safaga"],
    "matrouh":       ["matrouh", "مطروح", "marsa matrouh", "سيوة"],
    "new-valley":    ["new valley", "الوادي الجديد", "kharga"],
}

_sel_govs_raw = _CFG.get("governorates")
SELECTED_GOVS: list | None = _sel_govs_raw if _sel_govs_raw else None  # None = all


def matches_governorate(address: str | None) -> bool:
    if SELECTED_GOVS is None:
        return True
    if not address:
        return True  # لا نستطيع التحقق → نشملها
    addr_lower = address.lower()
    for gov in SELECTED_GOVS:
        for kw in GOVERNORATE_KEYWORDS.get(gov, [gov]):
            if kw.lower() in addr_lower:
                return True
    return False


def matches_category(cat: str | None) -> bool:
    if SELECTED_CATS is None:
        return True  # no filter → accept everything including uncategorized
    if cat is None:
        return False  # filter is active → reject uncategorized
    return cat in SELECTED_CATS


# ===================== الأنماط والثوابت =====================
MOBILE_RE  = re.compile(r'(?<!\d)(01[0-2,5]\d{8})(?!\d)')
EMAIL_RE   = re.compile(r'[\w.\-+]+@[\w.\-]+\.[a-z]{2,6}', re.I)
WA_RE      = re.compile(r'wa\.me/(\d{10,15})', re.I)
BAD_EMAILS = (
    'example', 'yourmail', 'test@', 'noreply', 'no-reply',
    'sentry', 'yellowpages', 'ypbeta', '@yellow.com',
    'support@', 'admin@', 'info@yellowpages', 'postmaster',
    'donotreply', 'webmaster@', 'abuse@',
)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0",
]


def hdrs():
    return {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8,ar;q=0.5",
    }


def clean_email(em: str | None) -> str | None:
    if not em:
        return None
    em = em.strip().lower().rstrip(".,;")
    if "@" not in em or len(em) < 6 or len(em) > 80:
        return None
    if any(b in em for b in BAD_EMAILS):
        return None
    # تجنب الإيميلات ذات التمديدات المشبوهة
    parts = em.split("@")
    if len(parts) != 2:
        return None
    domain = parts[1]
    if not re.match(r'^[\w.\-]+\.[a-z]{2,6}$', domain, re.I):
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


# ===================== استخراج الإيميل من موقع الشركة =====================
def scrape_website_for_email(url: str) -> str | None:
    """يزور الموقع الرسمي للشركة ويبحث عن إيميل"""
    try:
        r = requests.get(url, headers=hdrs(), timeout=12,
                         allow_redirects=True, stream=False)
        if r.status_code != 200:
            return None
        text = r.text

        # 1) mailto: الأكثر موثوقية
        for m in re.finditer(r'mailto:([^\s"\'<>?&]{4,80})', text, re.I):
            cand = clean_email(m.group(1))
            if cand:
                return cand

        # 2) بحث في النص الكامل بعد تحليل HTML
        soup = BeautifulSoup(text, "html.parser")
        page_text = soup.get_text(separator=" ")
        for m in EMAIL_RE.finditer(page_text):
            cand = clean_email(m.group(0))
            if cand:
                return cand

    except Exception:
        pass
    return None


# ===================== YellowPages: استخراج بيانات صفحة =====================
def extract_from_page(html: str, cid: int) -> dict | None:
    name = phone = email = address = category = website_url = None

    jsonld_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.I)

    for raw_j in jsonld_blocks:
        try:
            d = json.loads(raw_j.strip())
        except Exception:
            continue

        # breadcrumb → تصنيف
        if d.get("@type") == "WebPage":
            bc = d.get("breadcrumb", "").lower()
            for key, arabic in CATEGORY_MAP.items():
                if key in bc:
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

            # موقع الشركة الرسمي
            candidate = d.get("url") or d.get("sameAs") or ""
            if candidate and "yellowpages.com.eg" not in candidate and candidate.startswith("http"):
                website_url = candidate

    # تصنيف من روابط /category/ إن لم يُوجد
    if not category:
        for m in re.finditer(r'/category/([a-z0-9\-]+)', html):
            slug = m.group(1).lower()
            for key, arabic in CATEGORY_MAP.items():
                if key.replace(" ", "-") in slug or key in slug:
                    category = arabic
                    break
            if category:
                break

    # فلترة التصنيف
    if not matches_category(category):
        return None

    # فلترة المحافظة
    if not matches_governorate(address):
        return None

    # بحث إضافي عن إيميل بـ mailto:
    if not email:
        for m in re.finditer(r'mailto:([^\s"\'<>?&]{4,80})', html, re.I):
            cand = clean_email(m.group(1))
            if cand:
                email = cand
                break

    # ★ استخراج الإيميل من موقع الشركة (أهم تحسين)
    if not email and website_url:
        email = scrape_website_for_email(website_url)

    # WhatsApp
    whatsapp = None
    for m in WA_RE.finditer(html):
        num = m.group(1)
        if len(num) >= 10:
            norm = normalize_phone(num)
            if norm:
                whatsapp = norm
                break
    if not whatsapp and phone and MOBILE_RE.match(phone):
        whatsapp = phone

    # الاسم من <h1>
    if not name:
        h1_m = re.search(r'<h1[^>]*>([^<]{3,120})</h1>', html, re.I)
        if h1_m:
            name = BeautifulSoup(h1_m.group(1), "html.parser").get_text(strip=True)[:100]

    if not name:
        return None

    # حالة التواصل
    if email:
        contact_status = "✅ إيميل + " + ("واتساب" if whatsapp else "هاتف")
    elif whatsapp:
        contact_status = "📱 واتساب فقط"
    elif phone:
        contact_status = "☎ هاتف فقط"
    else:
        contact_status = "—"

    return {
        "Company Name":    name,
        "Phone":           phone,
        "WhatsApp":        whatsapp,
        "Email":           email,
        "Address":         address,
        "Website":         website_url,
        "Category":        category,
        "Contact Status":  contact_status,
        "Source":          "YellowPages",
        "URL":             f"https://www.yellowpages.com.eg/en/profile/x/{cid}",
    }


_blocked_count = 0


def scrape_yp_id(cid: int) -> dict | None:
    global _blocked_count
    url = f"https://www.yellowpages.com.eg/en/profile/x/{cid}"
    try:
        r = requests.get(url, headers=hdrs(), timeout=12)
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
    global _blocked_count
    _blocked_count = 0

    # تطبيق إعدادات Config
    workers     = _CFG.get("workers",   workers)
    sample_size = _CFG.get("id_count",  sample_size or 60_000)

    all_ids = list(range(id_start, id_end + 1))
    random.shuffle(all_ids)
    all_ids = all_ids[:sample_size]

    print(f"  🔢 IDs للفحص : {len(all_ids):,}")
    print(f"  ⚡ Threads    : {workers}")
    if SELECTED_GOVS:
        print(f"  📍 المحافظات  : {', '.join(SELECTED_GOVS)}")
    if SELECTED_CATS:
        print(f"  🏷️ التصنيفات  : {len(SELECTED_CATS)} تصنيف")

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
                em_flag = "📧" if res.get("Email") else "  "
                if len(companies) % 50 == 0:
                    elapsed = time.time() - start_t
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"  ✅ {len(companies):4d} شركة | فحص {processed:,} | {rate:.1f} req/s")
                    pd.DataFrame(companies).to_excel(BACKUP_FILE, index=False)

            if processed % 50 == 0:
                elapsed = time.time() - start_t
                rate = processed / elapsed if elapsed > 0 else 0
                with_email = sum(1 for c in companies if c.get("Email"))
                print(f"  ⏳ {len(companies):4d} شركة ({with_email} بإيميل) | فحص {processed:,} | {rate:.1f} req/s | محجوب: {_blocked_count}")

            if len(companies) >= max_companies:
                for f in futures:
                    f.cancel()
                break

            if _blocked_count >= 50 and _blocked_count != last_block_warn and _blocked_count % 50 == 0:
                last_block_warn = _blocked_count
                block_pct = int(_blocked_count / max(processed, 1) * 100)
                print(f"  ⚠️ [ERR] {_blocked_count} طلب محجوب ({block_pct}%)")
                if block_pct >= 80 and processed >= 200:
                    print("  ❌ [ERR] الموقع يحجب أكثر من 80% — إيقاف YellowPages")
                    for f in futures:
                        f.cancel()
                    break

    elapsed = time.time() - start_t
    with_email = sum(1 for c in companies if c.get("Email"))
    print(f"\n  📌 فحصنا {processed:,} ID خلال {elapsed:.0f}ث → {len(companies)} شركة")
    print(f"  📧 شركات بإيميل: {with_email}")
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
    ],
    "الكهرباء والكابلات والأسلاك": [
        'site:facebook.com "كابلات كهربائية" مصر',
        'site:facebook.com "electrical cables" egypt',
        'site:facebook.com "تجهيزات كهربائية" مصر',
    ],
    "الميكانيكا": [
        'site:facebook.com "قطع غيار ميكانيكية" مصر',
        'site:facebook.com "mechanical parts" egypt',
    ],
    "الإلكترونيات": [
        'site:facebook.com "إلكترونيات" مصر هاتف',
        'site:facebook.com "electronics company" egypt',
    ],
    "أدوات النظافة": [
        'site:facebook.com "معدات تنظيف" مصر',
        'site:facebook.com "cleaning equipment" egypt',
    ],
    "معدات المطابخ الكبيرة الفندقية وقطع غيارها": [
        'site:facebook.com "معدات مطابخ فندقية" مصر',
        'site:facebook.com "hotel kitchen equipment" egypt',
        'site:facebook.com "تجهيزات مطاعم" مصر',
    ],
    "الأثاث المكتبي": [
        'site:facebook.com "أثاث مكتبي" مصر',
        'site:facebook.com "office furniture" egypt',
    ],
    "تكنولوجيا المعلومات (IT)": [
        'site:facebook.com "IT company" egypt',
        'site:facebook.com "software company" egypt',
        'site:facebook.com "حلول تقنية" مصر',
    ],
    "مواد البناء والمقاولات": [
        'site:facebook.com "مواد بناء" مصر',
        'site:facebook.com "building materials" egypt',
        'site:facebook.com "مقاولات" مصر هاتف',
    ],
    "المعدات الطبية والصيدلانية": [
        'site:facebook.com "معدات طبية" مصر',
        'site:facebook.com "medical equipment" egypt',
        'site:facebook.com "أجهزة طبية" مصر',
    ],
    "السيارات وقطع الغيار": [
        'site:facebook.com "قطع غيار سيارات" مصر',
        'site:facebook.com "auto parts" egypt',
    ],
    "الأمن والحراسة وأنظمة المراقبة": [
        'site:facebook.com "كاميرات مراقبة" مصر',
        'site:facebook.com "security systems" egypt',
        'site:facebook.com "أنظمة إنذار" مصر',
    ],
    "التكييف والتبريد": [
        'site:facebook.com "تكييف" مصر هاتف',
        'site:facebook.com "air conditioning" egypt company',
    ],
    "معالجة المياه والصرف الصحي": [
        'site:facebook.com "معالجة مياه" مصر',
        'site:facebook.com "water treatment" egypt',
    ],
    "الطباعة والنشر والإعلان": [
        'site:facebook.com "طباعة" مصر هاتف',
        'site:facebook.com "printing company" egypt',
    ],
    "الأغذية والمشروبات": [
        'site:facebook.com "صناعة غذائية" مصر',
        'site:facebook.com "food company" egypt',
    ],
    "النسيج والملابس": [
        'site:facebook.com "مصنع ملابس" مصر',
        'site:facebook.com "textile factory" egypt',
    ],
    "الشحن والنقل واللوجستيات": [
        'site:facebook.com "شركة شحن" مصر',
        'site:facebook.com "logistics company" egypt',
    ],
    "الزراعة والري": [
        'site:facebook.com "معدات زراعية" مصر',
        'site:facebook.com "agricultural equipment" egypt',
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

        title = soup.find("title")
        name = ""
        if title:
            name = (title.text
                    .replace("| Facebook", "").replace("- Facebook", "")
                    .replace("|", "").replace("Facebook", "").strip())
        if not name or len(name) < 3:
            return None

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

        phone = None
        mob = MOBILE_RE.search(page_text)
        if mob:
            phone = mob.group(1)

        whatsapp = None
        wa_m = WA_RE.search(text)
        if wa_m:
            whatsapp = normalize_phone(wa_m.group(1))
        if not whatsapp and phone and MOBILE_RE.match(phone):
            whatsapp = phone

        address = None
        for pat in [
            r'(?:Address|العنوان|موقعنا)[:\s]+(.{5,120}?)(?:\n|[.،])',
            r'(?:يقع|مقر)[:\s]+(.{5,120}?)(?:\n|[.،])',
        ]:
            am = re.search(pat, page_text, re.I)
            if am:
                address = am.group(1).strip()
                break

        if email:
            contact_status = "✅ إيميل + " + ("واتساب" if whatsapp else "هاتف")
        elif whatsapp:
            contact_status = "📱 واتساب فقط"
        elif phone:
            contact_status = "☎ هاتف فقط"
        else:
            contact_status = "—"

        return {
            "Company Name":   name[:120],
            "Phone":          phone,
            "WhatsApp":       whatsapp,
            "Email":          email,
            "Address":        address,
            "Website":        None,
            "Category":       category,
            "Contact Status": contact_status,
            "Source":         "Facebook",
            "URL":            fb_url,
        }
    except Exception:
        return None


def run_facebook_scraper(max_per_cat: int = 40) -> list[dict]:
    # فقط التصنيفات المختارة
    active_queries = {
        cat: queries for cat, queries in FB_QUERIES.items()
        if matches_category(cat)
    }
    results = []
    for cat, queries in active_queries.items():
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


# ===================== الحفظ =====================
def save_excel(records: list[dict], path: str) -> None:
    cols = ["Company Name", "Phone", "WhatsApp", "Email",
            "Website", "Address", "Category", "Contact Status", "Source", "URL"]
    df = pd.DataFrame(records)
    df = df[[c for c in cols if c in df.columns]]
    for col in ("Phone", "WhatsApp"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: str(v).strip() if pd.notna(v) and str(v).strip() not in ("", "nan") else ""
            )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # الورقة الأولى: شركات بإيميل فقط
        with_email = df[df["Email"].notna() & (df["Email"] != "")]
        with_email.to_excel(writer, sheet_name="شركات بإيميل", index=False)
        # الورقة الثانية: كل الشركات
        df.to_excel(writer, sheet_name="كل الشركات", index=False)


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

    # ── إحصاء & حفظ ─────────────────────────────────────────────
    print(f"\n{'='*64}")
    if not all_records:
        print("❌ لا توجد بيانات!")
        return

    df = pd.DataFrame(all_records)
    raw_total = len(df)
    df.drop_duplicates(subset=["Company Name"], keep="first", inplace=True)
    after_dd = len(df)
    with_email = len(df[df["Email"].notna() & (df["Email"] != "")])

    save_excel(df.to_dict("records"), OUTPUT_FILE)

    print(f"\n  إجمالي الشركات      : {raw_total}")
    print(f"  بعد إزالة التكرار   : {after_dd}")
    print(f"  شركات بإيميل         : {with_email}")
    print(f"\n✅ الملف النهائي: {OUTPUT_FILE}")
    print("   الورقة 1: 'شركات بإيميل'")
    print("   الورقة 2: 'كل الشركات'")

    if "Category" in df.columns:
        print("\n📊 الفئات:")
        print(df["Category"].value_counts().to_string())


if __name__ == "__main__":
    main()
