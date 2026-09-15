import os
import re
import sqlite3
from pathlib import Path
from datetime import date

import flet as ft


# ============================================================
# إعدادات التطبيق
# ============================================================

APP_TITLE = "منظومة بيانات العراق"
TELEGRAM_URL = "https://t.me/UB_515"

GREEN = "#00FF7F"
CYAN = "#00F0FF"
BG = "#020D10"
PANEL = "#03181A"
FIELD = "#041E20"
WHITE = "#F7FFF9"
MUTED = "#9BB0B0"

# مجلد assets الذي يدخل داخل APK
ASSETS_DIR = Path(
    os.environ.get("FLET_ASSETS_DIR", "assets")
).resolve()

DB_DIR = ASSETS_DIR / "databases"

# صورة الجوكر الموجودة في assets/bg.jpg
JOKER_IMAGE = ASSETS_DIR / "bg.jpg"

# إذا عندك خلفية منفصلة للواجهة يمكن وضعها هنا
UI_BACKGROUND = ASSETS_DIR / "ui_background.png"


# ============================================================
# المحافظات
# ============================================================

PROVINCES = [
    ("بغداد", "baghdad.db"),
    ("الأنبار", "alanbar.db"),
    ("بابل", "babylon.db"),
    ("البصرة", "basrah.db"),
    ("ذي قار", "dhiqar.db"),
    ("القادسية", "qadisiyah.db"),
    ("ديالى", "diyala.db"),
    ("دهوك", "duhok.db"),
    ("أربيل", "erbil.db"),
    ("كربلاء", "karbalaa.db"),
    ("كركوك", "kirkuk.db"),
    ("ميسان", "maysan.db"),
    ("المثنى", "muthanna.db"),
    ("النجف", "najaf.db"),
    ("نينوى", "nineveh.db"),
    ("صلاح الدين", "salahaldeen.db"),
    ("السليمانية", "sulaymaniyah.db"),
    ("واسط", "wasit.db"),
    ("حلبجة", "halabja.db"),
]


# ============================================================
# أدوات النص
# ============================================================

def norm(value):
    if value is None:
        return ""

    text = str(value).strip().lower()

    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = text.replace("ى", "ي")

    text = re.sub(r"\s+", " ", text)

    return text


def clean_text(value):
    if value is None:
        return "None"

    text = str(value).strip()

    return text if text else "None"


# ============================================================
# SQLite
# ============================================================

def safe_connect(db_path):
    """
    فتح قاعدة البيانات للقراءة فقط.
    """
    uri = f"file:{db_path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=10
    )


def table_names(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def columns(conn, table):
    table = table.replace('"', '""')

    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


def quote_ident(value):
    return '"' + str(value).replace('"', '""') + '"'


# ============================================================
# أسماء الحقول المحتملة
# ============================================================

ALIASES = {

    "family": [
        "رقم التموينية",
        "رقم البطاقه التموينيه",
        "التموينية",
        "تموينية",
        "ration",
        "ration_no",
        "ration_number",
        "ration_card",
        "card_no",
        "card_number",
        "family_no",
        "family_number",
        "household_no",
        "household_number",
        "household",
        "family_id",
        "familyid",
    ],

    "name": [
        "الاسم",
        "اسم",
        "الاسم الكامل",
        "اسم الشخص",
        "name",
        "full_name",
        "fullname",
        "person_name",
    ],

    "birth": [
        "المواليد",
        "مواليد",
        "تاريخ الميلاد",
        "تاريخ المولد",
        "birth",
        "birth_year",
        "year_of_birth",
        "dob",
        "date_of_birth",
        "birthdate",
    ],

    "job": [
        "الوظيفة",
        "المهنة",
        "العمل",
        "occupation",
        "job",
        "work",
        "profession",
    ],

    "gender": [
        "الجنس",
        "النوع",
        "gender",
        "sex",
    ],

    "sequence": [
        "تسلسل الفرد",
        "تسلسل",
        "تسلسل الشخص",
        "رقم الفرد",
        "member_no",
        "member_number",
        "sequence",
        "seq",
        "person_no",
        "person_number",
    ],

    "id": [
        "المعرف",
        "معرف",
        "رقم المعرف",
        "الرقم الوطني",
        "رقم البطاقة",
        "id",
        "person_id",
        "national_id",
        "identifier",
    ],

    "province": [
        "المحافظة",
        "province",
        "governorate",
    ],
}


def find_alias_column(cols, aliases):
    normalized = {
        norm(column): column
        for column in cols
    }

    # تطابق مباشر
    for alias in aliases:

        key = norm(alias)

        if key in normalized:
            return normalized[key]

    # تطابق جزئي
    for column in cols:

        column_norm = norm(column)

        for alias in aliases:

            alias_norm = norm(alias)

            if (
                alias_norm
                and (
                    alias_norm in column_norm
                    or column_norm in alias_norm
                )
            ):
                return column

    return None


def field_map(cols):
    return {
        key: find_alias_column(cols, aliases)
        for key, aliases in ALIASES.items()
    }


# ============================================================
# البحث
# ============================================================

def search_database(db_path, query, max_hits=30):

    results = []

    try:
        conn = safe_connect(db_path)

    except Exception:
        return results

    try:

        for table in table_names(conn):

            try:

                cols = columns(conn, table)

                if not cols:
                    continue

                fmap = field_map(cols)

                candidate_cols = []

                # نبحث أولاً في أهم الحقول
                for key in (
                    "family",
                    "name",
                    "birth",
                    "id"
                ):

                    column = fmap.get(key)

                    if column and column not in candidate_cols:
                        candidate_cols.append(column)

                # إذا لم نجد حقول معروفة
                # نبحث في جميع الأعمدة
                if not candidate_cols:
                    candidate_cols = cols

                where_parts = []
                params = []

                for column in candidate_cols:

                    where_parts.append(
                        f"CAST({quote_ident(column)} AS TEXT) LIKE ?"
                    )

                    params.append(
                        f"%{query}%"
                    )

                sql = (
                    f"SELECT * FROM {quote_ident(table)} "
                    f"WHERE {' OR '.join(where_parts)} "
                    f"LIMIT ?"
                )

                rows = conn.execute(
                    sql,
                    (*params, max_hits)
                ).fetchall()

                for row in rows:

                    results.append(
                        {
                            "table": table,
                            "columns": cols,
                            "row": row,
                            "fields": fmap,
                        }
                    )

                    if len(results) >= max_hits:
                        return results

            except Exception:
                continue

    finally:
        conn.close()

    return results


# ============================================================
# استخراج البيانات
# ============================================================

def get_field(hit, key):

    fmap = hit.get("fields", {})
    cols = hit.get("columns", [])
    row = hit.get("row", ())

    column = fmap.get(key)

    if column and column in cols:

        index = cols.index(column)

        return row[index]

    return None


def extract_family_number(hit):

    value = get_field(hit, "family")

    if clean_text(value) != "None":
        return str(value).strip()

    cols = hit.get("columns", [])
    row = hit.get("row", ())

    for column in cols:

        column_norm = norm(column)

        if any(
            word in column_norm
            for word in [
                "تمويني",
                "ration",
                "family",
                "household"
            ]
        ):

            value = row[cols.index(column)]

            if clean_text(value) != "None":
                return str(value).strip()

    return None


def year_from_value(value):

    if value is None:
        return None

    text = str(value)

    match = re.search(
        r"(18|19|20)\d{2}",
        text
    )

    if not match:
        return None

    return int(match.group())


def calculate_age(value):

    year = year_from_value(value)

    if not year:
        return "None"

    current_year = date.today().year

    age = current_year - year

    return str(max(0, age))


# ============================================================
# جلب جميع أفراد العائلة
# ============================================================

def family_rows(
    db_path,
    family_number,
    source_hit=None,
    limit=100
):

    results = []
    seen = set()

    try:
        conn = safe_connect(db_path)

    except Exception:
        return results

    try:

        tables = []

        if source_hit and source_hit.get("table"):
            tables.append(source_hit["table"])

        for table in table_names(conn):

            if table not in tables:
                tables.append(table)

        for table in tables:

            try:

                cols = columns(
                    conn,
                    table
                )

                fmap = field_map(cols)

                family_column = fmap.get("family")

                # محاولة إضافية
                if not family_column:

                    for column in cols:

                        column_norm = norm(column)

                        if any(
                            word in column_norm
                            for word in [
                                "تمويني",
                                "ration",
                                "family",
                                "household"
                            ]
                        ):

                            family_column = column
                            break

                if not family_column:
                    continue

                sql = (
                    f"SELECT * FROM {quote_ident(table)} "
                    f"WHERE CAST("
                    f"{quote_ident(family_column)} "
                    f"AS TEXT) = ? "
                    f"LIMIT ?"
                )

                rows = conn.execute(
                    sql,
                    (
                        str(family_number),
                        limit
                    )
                ).fetchall()

                for row in rows:

                    key = (
                        table,
                        tuple(
                            "" if value is None
                            else str(value)
                            for value in row
                        )
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    results.append(
                        {
                            "table": table,
                            "columns": cols,
                            "row": row,
                            "fields": fmap,
                        }
                    )

                    if len(results) >= limit:
                        return results

            except Exception:
                continue

    finally:
        conn.close()

    return results


def find_db_for_province(province):

    for name, filename in PROVINCES:

        if name == province:
            return DB_DIR / filename

    return None


# ============================================================
# عنصر سطر النتيجة
# ============================================================

def result_line(label, value):

    return ft.Container(

        # الشفافية هنا فقط على معلومات النتيجة
        bgcolor="#03191A99",

        border=ft.border.all(
            1,
            "#00FF7F66"
        ),

        border_radius=10,

        padding=ft.padding.symmetric(
            horizontal=10,
            vertical=6
        ),

        content=ft.Row(

            spacing=8,

            vertical_alignment=(
                ft.CrossAxisAlignment.START
            ),

            controls=[

                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    color=GREEN,
                    size=18,
                ),

                ft.Text(
                    f"{label}: {clean_text(value)}",
                    color=WHITE,
                    size=16,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.RIGHT,
                    expand=True,
                ),
            ],
        ),
    )


# ============================================================
# بطاقة البحث العادي
# ============================================================

def cyber_result_card(hit, index):

    fields = [

        (
            "رقم التموينية",
            get_field(hit, "family")
        ),

        (
            "الاسم",
            get_field(hit, "name")
        ),

        (
            "المواليد",
            get_field(hit, "birth")
        ),

        (
            "العمر",
            calculate_age(
                get_field(hit, "birth")
            )
        ),

        (
            "الوظيفة",
            get_field(hit, "job")
        ),

        (
            "تسلسل الفرد",
            get_field(hit, "sequence")
        ),
    ]

    gender = get_field(
        hit,
        "gender"
    )

    province = get_field(
        hit,
        "province"
    )

    person_id = get_field(
        hit,
        "id"
    )

    if gender is not None:
        fields.insert(
            4,
            ("الجنس", gender)
        )

    if province is not None:
        fields.insert(
            5,
            ("المحافظة", province)
        )

    if person_id is not None:
        fields.append(
            ("المعرف", person_id)
        )

    info = ft.Column(

        spacing=6,

        controls=[

            ft.Text(
                f"نتيجة {index}",
                color=CYAN,
                size=19,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),

            *[
                result_line(
                    label,
                    value
                )
                for label, value in fields
            ],
        ],
    )

    # صورة الجوكر واضحة بالكامل
    # لا توجد شفافية هنا
    if JOKER_IMAGE.exists():

        joker = ft.Image(
            src="bg.jpg",
            width=150,
            height=150,
            fit=ft.ImageFit.COVER,
            opacity=1.0,
        )

    else:

        joker = ft.Container(
            width=150,
            height=150,
            bgcolor="#031313",
            alignment=ft.alignment.center,
            content=ft.Icon(
                ft.Icons.SECURITY,
                color=GREEN,
                size=64,
            ),
        )

    return ft.Container(

        padding=14,

        margin=ft.margin.only(
            bottom=12
        ),

        bgcolor="#03191A",

        border=ft.border.all(
            2,
            GREEN
        ),

        border_radius=24,

        content=ft.Row(

            spacing=14,

            controls=[
                joker,

                ft.Container(
                    expand=True,
                    content=info,
                ),
            ],
        ),
    )


# ============================================================
# التطبيق
# ============================================================

def main(page: ft.Page):

    page.title = APP_TITLE
    page.rtl = True
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0
    page.scroll = ft.ScrollMode.AUTO

    # ========================================================
    # المحافظة
    # ========================================================

    province_dd = ft.Dropdown(

        value="بغداد",

        options=[
            ft.dropdown.Option(name)
            for name, _ in PROVINCES
        ],

        text_size=17,
        color=WHITE,
        bgcolor=FIELD,

        border_color=GREEN,
        focused_border_color=GREEN,

        border_width=2,
        border_radius=18,

        content_padding=ft.padding.symmetric(
            horizontal=18,
            vertical=12
        ),

        expand=True,
    )

    # ========================================================
    # البحث
    # ========================================================

    search_field = ft.TextField(

        hint_text="الاسم، الرقم، أو المعرف...",

        hint_style=ft.TextStyle(
            color="#789090",
            size=16
        ),

        text_style=ft.TextStyle(
            color=WHITE,
            size=17
        ),

        cursor_color=GREEN,

        border_color=GREEN,
        focused_border_color=GREEN,

        border_width=2,
        border_radius=18,

        bgcolor=FIELD,

        prefix_icon=ft.Icons.SEARCH,
        prefix_icon_color=GREEN,

        text_align=ft.TextAlign.RIGHT,

        expand=True,
    )

    # ========================================================
    # منطقة النتائج
    # ========================================================

    results_column = ft.Column(

        spacing=0,

        horizontal_alignment=(
            ft.CrossAxisAlignment.STRETCH
        ),
    )

    results_title = ft.Text(

        "سجل النتائج والبيانات المسترجعة:",

        color=CYAN,

        size=20,

        weight=ft.FontWeight.BOLD,

        text_align=ft.TextAlign.RIGHT,
    )

    status_text = ft.Text(

        "",

        color=MUTED,

        size=14,

        text_align=ft.TextAlign.CENTER,
    )

    # ========================================================
    # أدوات داخل التطبيق
    # ========================================================

    def selected_db():
        return find_db_for_province(
            province_dd.value
        )

    # ========================================================
    # عرض صورة الجوكر عند بداية التطبيق
    # ========================================================

    def clear_results():

        results_column.controls.clear()

        if JOKER_IMAGE.exists():

            results_column.controls.append(

                ft.Container(

                    height=320,

                    border=ft.border.all(
                        2,
                        GREEN
                    ),

                    border_radius=22,

                    padding=8,

                    clip_behavior=(
                        ft.ClipBehavior.HARD_EDGE
                    ),

                    content=ft.Image(

                        src="bg.jpg",

                        # الصورة واضحة بالكامل
                        opacity=1.0,

                        fit=ft.ImageFit.COVER,

                        width=float("inf"),

                        height=300,
                    ),
                )
            )

        else:

            results_column.controls.append(

                ft.Container(

                    height=320,

                    border=ft.border.all(
                        2,
                        GREEN
                    ),

                    border_radius=22,

                    alignment=ft.alignment.center,

                    content=ft.Icon(
                        ft.Icons.SECURITY,
                        color=GREEN,
                        size=96,
                    ),
                )
            )

    # ========================================================
    # البحث الشامل
    # ========================================================

    def start_search(e=None):

        query = (
            search_field.value or ""
        ).strip()

        db_path = selected_db()

        if not query:

            status_text.value = (
                "اكتب كلمة البحث أولاً."
            )

            page.update()
            return

        if (
            not db_path
            or not db_path.exists()
        ):

            status_text.value = (
                "ملف قاعدة البيانات غير موجود."
            )

            page.update()
            return

        status_text.value = (
            "جارِ البحث..."
        )

        results_column.controls.clear()

        page.update()

        hits = search_database(
            db_path,
            query,
            max_hits=30
        )

        if not hits:

            status_text.value = (
                "لم يتم العثور على نتائج."
            )

            clear_results()

            page.update()
            return

        status_text.value = (
            f"تم العثور على {len(hits)} نتيجة."
        )

        results_column.controls.extend(

            [
                cyber_result_card(
                    hit,
                    index
                )

                for index, hit
                in enumerate(
                    hits,
                    1
                )
            ]
        )

        page.update()

    # ========================================================
    # جلب العائلة
    # ========================================================

    def fetch_family(e=None):

        query = (
            search_field.value or ""
        ).strip()

        db_path = selected_db()

        if not query:

            status_text.value = (
                "اكتب رقم التموينية أو اسم أحد أفراد العائلة أولاً."
            )

            page.update()
            return

        if (
            not db_path
            or not db_path.exists()
        ):

            status_text.value = (
                "قاعدة البيانات غير موجودة."
            )

            page.update()
            return

        status_text.value = (
            "جارِ جلب العائلة..."
        )

        results_column.controls.clear()

        page.update()

        # أولاً نبحث عن الشخص
        first_hits = search_database(
            db_path,
            query,
            max_hits=20
        )

        if not first_hits:

            status_text.value = (
                "لم يتم العثور على الشخص أو رقم التموينية."
            )

            page.update()
            return

        family_number = None
        source_hit = None

        for hit in first_hits:

            candidate = extract_family_number(
                hit
            )

            if candidate:

                family_number = candidate
                source_hit = hit

                break

        if not family_number:

            status_text.value = (
                "تم العثور على النتيجة، "
                "لكن لم أستطع تحديد رقم التموينية."
            )

            page.update()
            return

        # جلب كل أفراد نفس العائلة
        family = family_rows(

            db_path,

            family_number,

            source_hit=source_hit,

            limit=100
        )

        if not family:

            status_text.value = (
                f"رقم التموينية {family_number} موجود، "
                "لكن لم أجد بقية أفراد العائلة."
            )

            page.update()
            return

        # ====================================================
        # ترتيب أفراد العائلة حسب التسلسل
        # ====================================================

        def seq_key(hit):

            value = get_field(
                hit,
                "sequence"
            )

            if value is None:
                return 999999

            match = re.search(
                r"\d+",
                str(value)
            )

            if match:
                return int(
                    match.group()
                )

            return 999999

        family.sort(
            key=seq_key
        )

        # ====================================================
        # معلومات أفراد العائلة
        # ====================================================

        member_controls = []

        for index, hit in enumerate(
            family,
            1
        ):

            sequence = get_field(
                hit,
                "sequence"
            )

            if (
                sequence is None
                or clean_text(sequence) == "None"
            ):
                sequence = index

            name = get_field(
                hit,
                "name"
            )

            birth = get_field(
                hit,
                "birth"
            )

            job = get_field(
                hit,
                "job"
            )

            gender = get_field(
                hit,
                "gender"
            )

            province = get_field(
                hit,
                "province"
            )

            person_id = get_field(
                hit,
                "id"
            )

            # -----------------------------------------------
            # هذه المعلومات شفافة فقط
            # -----------------------------------------------

            fields = [

                (
                    "رقم التموينية",
                    family_number
                ),

                (
                    "الاسم",
                    name
                ),

                (
                    "المواليد",
                    birth
                ),

                (
                    "العمر",
                    calculate_age(birth)
                ),

                (
                    "الوظيفة",
                    job
                ),

                (
                    "تسلسل الفرد",
                    sequence
                ),
            ]

            if gender is not None:

                fields.insert(
                    4,
                    (
                        "الجنس",
                        gender
                    )
                )

            if province is not None:

                fields.insert(
                    5,
                    (
                        "المحافظة",
                        province
                    )
                )

            if person_id is not None:

                fields.append(
                    (
                        "المعرف",
                        person_id
                    )
                )

            # بطاقة الفرد
            # شفافة حتى تبقى صورة الجوكر واضحة خلفها
            member_card = ft.Container(

                padding=12,

                margin=ft.margin.only(
                    bottom=10
                ),

                bgcolor="#03191A99",

                border=ft.border.all(
                    1,
                    "#00FF7F88"
                ),

                border_radius=16,

                content=ft.Column(

                    spacing=5,

                    controls=[

                        ft.Text(

                            f"فرد {index}",

                            color=GREEN,

                            size=17,

                            weight=ft.FontWeight.BOLD,

                            text_align=(
                                ft.TextAlign.RIGHT
                            ),
                        ),

                        *[
                            result_line(
                                label,
                                value
                            )

                            for label, value
                            in fields
                        ],
                    ],
                ),
            )

            member_controls.append(
                member_card
            )

        # ====================================================
        # عنوان جلب العائلة
        # ====================================================

        family_header = ft.Container(

            padding=12,

            margin=ft.margin.only(
                bottom=10
            ),

            # شفاف
            bgcolor="#021416AA",

            border=ft.border.all(
                1,
                "#00F0FF88"
            ),

            border_radius=16,

            content=ft.Column(

                spacing=4,

                controls=[

                    ft.Text(

                        "جلب العائلة",

                        color=CYAN,

                        size=22,

                        weight=ft.FontWeight.BOLD,

                        text_align=(
                            ft.TextAlign.RIGHT
                        ),
                    ),

                    ft.Text(

                        f"رقم التموينية: {family_number}",

                        color=WHITE,

                        size=18,

                        weight=ft.FontWeight.BOLD,

                        text_align=(
                            ft.TextAlign.RIGHT
                        ),
                    ),
                ],
            ),
        )

        # ====================================================
        # طبقة المعلومات الشفافة
        # ====================================================

        family_overlay = ft.Container(

            padding=14,

            content=ft.Column(

                spacing=0,

                scroll=ft.ScrollMode.AUTO,

                controls=[

                    family_header,

                    *member_controls,

                    ft.Container(

                        padding=12,

                        # شفاف
                        bgcolor="#021416AA",

                        border=ft.border.all(
                            1,
                            "#00FF7F88"
                        ),

                        border_radius=15,

                        content=ft.Text(

                            f"• عدد الأفراد: ({len(family)})",

                            color=GREEN,

                            size=20,

                            weight=ft.FontWeight.BOLD,

                            text_align=(
                                ft.TextAlign.RIGHT
                            ),
                        ),
                    ),
                ],
            ),
        )

        # ====================================================
        # صورة الجوكر
        #
        # مهم:
        # opacity = 1.0
        #
        # لا توجد أي شفافية للصورة.
        # ====================================================

        if JOKER_IMAGE.exists():

            joker_background = ft.Container(

                expand=True,

                border_radius=22,

                clip_behavior=(
                    ft.ClipBehavior.HARD_EDGE
                ),

                content=ft.Image(

                    src="bg.jpg",

                    # الصورة كاملة وواضحة
                    opacity=1.0,

                    fit=ft.ImageFit.COVER,

                    expand=True,
                ),
            )

        else:

            joker_background = ft.Container(

                expand=True,

                bgcolor="#031313",

                border_radius=22,

                alignment=ft.alignment.center,

                content=ft.Icon(

                    ft.Icons.SECURITY,

                    color=GREEN,

                    size=90,
                ),
            )

        # ====================================================
        # النتيجة النهائية
        #
        # الصورة تحت
        # المعلومات الشفافة فوقها
        # ====================================================

        family_result = ft.Container(

            height=650,

            margin=ft.margin.only(
                bottom=18
            ),

            border=ft.border.all(
                2,
                GREEN
            ),

            border_radius=24,

            clip_behavior=(
                ft.ClipBehavior.HARD_EDGE
            ),

            content=ft.Stack(

                expand=True,

                controls=[

                    # 1 - صورة الجوكر
                    joker_background,

                    # 2 - معلومات العائلة الشفافة
                    family_overlay,
                ],
            ),
        )

        results_column.controls.append(
            family_result
        )

        status_text.value = (

            f"تم جلب عائلة رقم "
            f"{family_number} "
            f"— عدد الأفراد: "
            f"{len(family)}"
        )

        page.update()

    # ========================================================
    # جلب السكن
    # ========================================================

    def fetch_housing(e=None):

        query = (
            search_field.value or ""
        ).strip()

        db_path = selected_db()

        if not query:

            status_text.value = (
                "اكتب كلمة البحث أولاً."
            )

            page.update()
            return

        if (
            not db_path
            or not db_path.exists()
        ):

            status_text.value = (
                "قاعدة البيانات غير موجودة."
            )

            page.update()
            return

        status_text.value = (
            "جارِ جلب معلومات السكن..."
        )

        results_column.controls.clear()

        page.update()

        hits = search_database(
            db_path,
            query,
            max_hits=30
        )

        if not hits:

            status_text.value = (
                "لم يتم العثور على بيانات سكن."
            )

            page.update()
            return

        for index, hit in enumerate(
            hits,
            1
        ):

            cols = hit["columns"]
            row = hit["row"]

            lines = []

            preferred = [

                "المحافظة",
                "province",
                "governorate",

                "القضاء",
                "الناحية",
                "المنطقة",
                "المحلة",

                "الزقاق",
                "الدار",
                "العنوان",

                "address",
                "district",
                "subdistrict",
            ]

            used = set()

            for wanted in preferred:

                for column in cols:

                    if (
                        norm(column)
                        == norm(wanted)
                        and column not in used
                    ):

                        lines.append(

                            result_line(
                                column,
                                row[
                                    cols.index(
                                        column
                                    )
                                ]
                            )
                        )

                        used.add(column)

            if not lines:

                for column, value in zip(
                    cols,
                    row
                ):

                    lines.append(

                        result_line(
                            column,
                            value
                        )
                    )

                    if len(lines) >= 12:
                        break

            results_column.controls.append(

                ft.Container(

                    padding=14,

                    margin=ft.margin.only(
                        bottom=10
                    ),

                    bgcolor="#03191A",

                    border=ft.border.all(
                        2,
                        GREEN
                    ),

                    border_radius=22,

                    content=ft.Column(

                        spacing=6,

                        controls=[

                            ft.Text(

                                f"بيانات السكن — نتيجة {index}",

                                color=CYAN,

                                size=19,

                                weight=ft.FontWeight.BOLD,

                                text_align=(
                                    ft.TextAlign.RIGHT
                                ),
                            ),

                            *lines,
                        ],
                    ),
                )
            )

        status_text.value = (
            f"تم العثور على {len(hits)} "
            "نتيجة للسكن."
        )

        page.update()

    # ========================================================
    # التعليمات
    # ========================================================

    def close_dialog(dialog):

        dialog.open = False

        page.update()

    def show_instructions(e=None):

        dialog = ft.AlertDialog(

            modal=True,

            bgcolor="#03181A",

            title=ft.Text(

                "تعليمات",

                color=GREEN,

                weight=ft.FontWeight.BOLD,

                text_align=(
                    ft.TextAlign.RIGHT
                ),
            ),

            content=ft.Container(

                width=340,

                content=ft.Text(

                    "1) اختر المحافظة.\n"
                    "2) اكتب الاسم أو الرقم أو المعرف.\n"
                    "3) اضغط بدء البحث الشامل للبحث العام.\n"
                    "4) استخدم جلب العائلة لإظهار أفراد نفس رقم التموينية.\n"
                    "5) استخدم جلب السكن لعرض بيانات السكن المتوفرة.",

                    color=WHITE,

                    size=16,

                    text_align=(
                        ft.TextAlign.RIGHT
                    ),
                ),
            ),

            actions=[

                ft.TextButton(

                    "إغلاق",

                    on_click=lambda e:
                    close_dialog(dialog),

                    style=ft.ButtonStyle(
                        color=GREEN
                    ),
                )
            ],
        )

        page.dialog = dialog

        dialog.open = True

        page.update()

    # ========================================================
    # المطور
    # ========================================================

    def open_developer(e=None):

        page.launch_url(
            TELEGRAM_URL
        )

    # ========================================================
    # القائمة الجانبية
    # ========================================================

    def close_drawer(e=None):

        drawer.open = False

        page.update()

    drawer = ft.NavigationDrawer(

        bgcolor="#031313",

        controls=[

            ft.Container(

                padding=20,

                content=ft.Column(

                    spacing=14,

                    controls=[

                        ft.Text(

                            APP_TITLE,

                            color=GREEN,

                            size=20,

                            weight=ft.FontWeight.BOLD,

                            text_align=(
                                ft.TextAlign.RIGHT
                            ),
                        ),

                        ft.Divider(
                            color=GREEN
                        ),

                        ft.ListTile(

                            leading=ft.Icon(
                                ft.Icons.CODE,
                                color=GREEN
                            ),

                            title=ft.Text(

                                "المطور",

                                color=WHITE,

                                size=17,

                                text_align=(
                                    ft.TextAlign.RIGHT
                                ),
                            ),

                            on_click=open_developer,
                        ),

                        ft.ListTile(

                            leading=ft.Icon(
                                ft.Icons.INFO_OUTLINE,
                                color=GREEN
                            ),

                            title=ft.Text(

                                "تعليمات",

                                color=WHITE,

                                size=17,

                                text_align=(
                                    ft.TextAlign.RIGHT
                                ),
                            ),

                            on_click=show_instructions,
                        ),
                    ],
                ),
            )
        ],
    )

    page.drawer = drawer

    def open_drawer(e=None):

        drawer.open = True

        page.update()

    # ========================================================
    # الهيدر
    # ========================================================

    menu_button = ft.IconButton(

        icon=ft.Icons.MENU,

        icon_color=WHITE,

        icon_size=34,

        tooltip="القائمة",

        on_click=open_drawer,
    )

    header = ft.Container(

        padding=ft.padding.only(
            left=18,
            right=18,
            top=16,
            bottom=16
        ),

        content=ft.Row(

            alignment=(
                ft.MainAxisAlignment
                .SPACE_BETWEEN
            ),

            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            controls=[

                # الثلاث خطوط
                menu_button,

                ft.Row(

                    spacing=10,

                    vertical_alignment=(
                        ft.CrossAxisAlignment.CENTER
                    ),

                    controls=[

                        ft.Icon(

                            ft.Icons.SHIELD,

                            color=GREEN,

                            size=42,
                        ),

                        ft.Text(

                            APP_TITLE,

                            color=GREEN,

                            size=25,

                            weight=(
                                ft.FontWeight.BOLD
                            ),

                            text_align=(
                                ft.TextAlign.CENTER
                            ),
                        ),
                    ],
                ),

                ft.Icon(

                    ft.Icons.SEARCH,

                    color=WHITE,

                    size=34,
                ),
            ],
        ),
    )

    # ========================================================
    # زر البحث
    # ========================================================

    search_button = ft.ElevatedButton(

        content=ft.Row(

            alignment=(
                ft.MainAxisAlignment.CENTER
            ),

            spacing=12,

            controls=[

                ft.Icon(
                    ft.Icons.SEARCH,
                    color="#00110A",
                    size=30
                ),

                ft.Text(

                    "بدء البحث الشامل",

                    color="#00110A",

                    size=23,

                    weight=(
                        ft.FontWeight.BOLD
                    ),
                ),
            ],
        ),

        style=ft.ButtonStyle(

            bgcolor=GREEN,

            color="#00110A",

            shape=ft.RoundedRectangleBorder(
                radius=20
            ),

            padding=ft.padding.symmetric(
                vertical=18,
                horizontal=20
            ),
        ),

        on_click=start_search,

        width=650,
    )

    # ========================================================
    # زر جلب العائلة
    # ========================================================

    family_button = ft.ElevatedButton(

        text="جلب العائلة",

        style=ft.ButtonStyle(

            bgcolor="#073A28",

            color=WHITE,

            side=ft.BorderSide(
                2,
                GREEN
            ),

            shape=ft.RoundedRectangleBorder(
                radius=18
            ),

            padding=ft.padding.symmetric(
                vertical=14,
                horizontal=24
            ),
        ),

        on_click=fetch_family,

        expand=True,
    )

    # ========================================================
    # زر جلب السكن
    # ========================================================

    housing_button = ft.ElevatedButton(

        text="جلب السكن",

        style=ft.ButtonStyle(

            bgcolor="#073A28",

            color=WHITE,

            side=ft.BorderSide(
                2,
                GREEN
            ),

            shape=ft.RoundedRectangleBorder(
                radius=18
            ),

            padding=ft.padding.symmetric(
                vertical=14,
                horizontal=24
            ),
        ),

        on_click=fetch_housing,

        expand=True,
    )

    # ========================================================
    # التعليمات
    # ========================================================

    instructions_button = ft.OutlinedButton(

        content=ft.Row(

            alignment=(
                ft.MainAxisAlignment.CENTER
            ),

            controls=[

                ft.Icon(
                    ft.Icons.INFO,
                    color=WHITE,
                    size=25
                ),

                ft.Text(

                    "تعليمات",

                    color=WHITE,

                    size=18,

                    weight=(
                        ft.FontWeight.BOLD
                    ),
                ),
            ],
        ),

        style=ft.ButtonStyle(

            side=ft.BorderSide(
                2,
                GREEN
            ),

            shape=ft.RoundedRectangleBorder(
                radius=18
            ),

            padding=ft.padding.symmetric(
                vertical=13,
                horizontal=18
            ),
        ),

        on_click=show_instructions,

        expand=True,
    )

    # ========================================================
    # المطور
    # ========================================================

    developer_button = ft.OutlinedButton(

        content=ft.Row(

            alignment=(
                ft.MainAxisAlignment.CENTER
            ),

            controls=[

                ft.Icon(
                    ft.Icons.CODE,
                    color=WHITE,
                    size=25
                ),

                ft.Text(

                    "المطور",

                    color=WHITE,

                    size=18,

                    weight=(
                        ft.FontWeight.BOLD
                    ),
                ),
            ],
        ),

        style=ft.ButtonStyle(

            side=ft.BorderSide(
                2,
                GREEN
            ),

            shape=ft.RoundedRectangleBorder(
                radius=18
            ),

            padding=ft.padding.symmetric(
                vertical=13,
                horizontal=18
            ),
        ),

        on_click=open_developer,

        expand=True,
    )

    # ========================================================
    # اللوحة الرئيسية
    # ========================================================

    panel = ft.Container(

        margin=ft.margin.symmetric(
            horizontal=14,
            vertical=10
        ),

        padding=ft.padding.symmetric(
            horizontal=20,
            vertical=24
        ),

        bgcolor="#021619",

        border=ft.border.all(
            2,
            GREEN
        ),

        border_radius=30,

        shadow=ft.BoxShadow(

            blur_radius=24,

            spread_radius=2,

            color="#003E28",

            offset=ft.Offset(0, 0),
        ),

        content=ft.Column(

            spacing=14,

            horizontal_alignment=(
                ft.CrossAxisAlignment.STRETCH
            ),

            controls=[

                ft.Text(

                    "اختر المحافظة المستهدفة",

                    color=GREEN,

                    size=21,

                    weight=(
                        ft.FontWeight.BOLD
                    ),

                    text_align=(
                        ft.TextAlign.RIGHT
                    ),
                ),

                province_dd,

                ft.Text(

                    "كلمة البحث",

                    color=GREEN,

                    size=21,

                    weight=(
                        ft.FontWeight.BOLD
                    ),

                    text_align=(
                        ft.TextAlign.RIGHT
                    ),
                ),

                search_field,

                search_button,

                ft.Row(

                    spacing=14,

                    controls=[
                        instructions_button,
                        developer_button,
                    ],
                ),

                # أزرار العمليات الإضافية
                ft.Row(

                    spacing=14,

                    controls=[
                        family_button,
                        housing_button,
                    ],
                ),

                ft.Text(

                    "اضغط على زر المطور للتواصل",

                    color="#8EA1A1",

                    size=16,

                    italic=True,

                    text_align=(
                        ft.TextAlign.CENTER
                    ),
                ),

                ft.Divider(

                    height=20,

                    thickness=1,

                    color=GREEN,
                ),

                results_title,

                status_text,

                # هنا تظهر صورة الجوكر
                # وهنا تظهر نتائج البحث
                results_column,
            ],
        ),
    )

    # ========================================================
    # الصورة الأولى
    # ========================================================

    clear_results()

    # ========================================================
    # خلفية الواجهة
    # ========================================================

    if UI_BACKGROUND.exists():

        background = ft.Image(

            src="ui_background.png",

            fit=ft.ImageFit.COVER,

            expand=True,
        )

    else:

        background = ft.Container(

            bgcolor=BG,

            expand=True,
        )

    # ========================================================
    # Stack النهائي
    # ========================================================

    content = ft.Stack(

        expand=True,

        controls=[

            ft.Container(

                content=background,

                expand=True,
            ),

            ft.Column(

                spacing=0,

                scroll=ft.ScrollMode.AUTO,

                controls=[

                    header,

                    panel,
                ],
            ),
        ],
    )

    page.add(content)


# ============================================================
# تشغيل التطبيق
# ============================================================

if __name__ == "__main__":

    ft.run(
        main,
        assets_dir=str(ASSETS_DIR)
    )
