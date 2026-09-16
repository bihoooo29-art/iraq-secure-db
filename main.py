import os
import re
import sqlite3
import asyncio
import urllib.request
from pathlib import Path
from datetime import date

import flet as ft


APP_TITLE = "منظومة بيانات العراق"
TELEGRAM_URL = "https://t.me/UB_515"

GREEN = "#00FF7F"
CYAN = "#00F0FF"
BG = "#020D10"
PANEL = "#03181A"
FIELD = "#041E20"
WHITE = "#F7FFF9"
MUTED = "#9BB0B0"


ASSETS_DIR = Path(
    os.environ.get("FLET_ASSETS_DIR", "assets")
).resolve()


# =========================
# تخزين قواعد البيانات
# =========================

DB_DIR = Path(
    os.environ.get(
        "FLET_APP_STORAGE_CACHE",
        str(Path.home() / ".iraq_secure_db_cache")
    )
)

DB_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# bg.jpg = صورة النتائج فقط
JOKER_IMAGE = ASSETS_DIR / "bg.jpg"

# menu_background.png = خلفية القائمة فقط
MENU_BACKGROUND = ASSETS_DIR / "menu_background.png"


GITHUB_RELEASE_URL = (
    "https://github.com/"
    "bihoooo29-art/iraq-secure-db/"
    "releases/latest/download"
)


PROVINCES = [
    ("الأنبار", "alanbar.db"),
    ("بابل", "babylon.db"),
    ("بغداد", "baghdad.db"),
    ("بلد", "balad.db"),
    ("البصرة", "basrah.db"),
    ("ذي قار", "dhiqar.db"),
    ("ديالى", "diyala.db"),
    ("دهوك", "duhok.db"),
    ("أربيل", "erbil.db"),
    ("كربلاء", "karbalaa.db"),
    ("كركوك", "kirkuk.db"),
    ("ميسان", "mesan.db"),
    ("المثنى", "muthana.db"),
    ("النجف", "najaf.db"),
    ("نينوى", "nineveh.db"),
    ("القادسية", "qadisiya.db"),
    ("صلاح الدين", "salahaldeen.db"),
    ("السليمانية", "sulaymaniyah.db"),
    ("واسط", "wasit.db"),
]


PROVINCE_FILES = dict(PROVINCES)


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


def quote_ident(value):
    return '"' + str(value).replace('"', '""') + '"'


def get_db_filename(province):
    return PROVINCE_FILES.get(province)


def get_local_db_path(province):
    filename = get_db_filename(province)

    if not filename:
        return None

    return DB_DIR / filename


def get_cloud_db_url(filename):
    return f"{GITHUB_RELEASE_URL}/{filename}"


def download_db_for_province(province):
    filename = get_db_filename(province)

    if not filename:
        return None

    local_path = DB_DIR / filename

    if local_path.exists():
        try:
            if local_path.stat().st_size > 0:
                return local_path
        except Exception:
            pass

    temp_path = DB_DIR / f"{filename}.part"
    url = get_cloud_db_url(filename)

    try:
        if temp_path.exists():
            temp_path.unlink()
    except Exception:
        pass

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            with open(
                temp_path,
                "wb"
            ) as output:

                while True:
                    chunk = response.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    output.write(chunk)

        if not temp_path.exists():
            return None

        if temp_path.stat().st_size <= 0:
            temp_path.unlink()
            return None

        temp_path.replace(local_path)

        return local_path

    except Exception:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        return None


async def find_db_for_province(province):
    local_path = get_local_db_path(province)

    if local_path and local_path.exists():
        try:
            if local_path.stat().st_size > 0:
                return local_path
        except Exception:
            pass

    return await asyncio.to_thread(
        download_db_for_province,
        province
    )


def safe_connect(db_path):
    db_path = Path(db_path).resolve()

    uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=30,
        check_same_thread=False
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
    rows = conn.execute(
        f'PRAGMA table_info({quote_ident(table)})'
    ).fetchall()

    return [row[1] for row in rows]


def find_alias_column(cols, aliases):
    normalized = {
        norm(column): column
        for column in cols
    }

    for alias in aliases:
        key = norm(alias)

        if key in normalized:
            return normalized[key]

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

                for key in (
                    "family",
                    "name",
                    "birth",
                    "id"
                ):
                    column = fmap.get(key)

                    if column and column not in candidate_cols:
                        candidate_cols.append(column)

                if not candidate_cols:
                    candidate_cols = cols

                where_parts = []
                params = []

                search_value = str(query).strip()

                for column in candidate_cols:
                    where_parts.append(
                        f"CAST({quote_ident(column)} AS TEXT) LIKE ?"
                    )

                    params.append(
                        f"%{search_value}%"
                    )

                if not where_parts:
                    continue

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


def get_field(hit, key):
    fmap = hit.get(
        "fields",
        {}
    )

    cols = hit.get(
        "columns",
        []
    )

    row = hit.get(
        "row",
        ()
    )

    column = fmap.get(key)

    if column and column in cols:
        index = cols.index(column)
        return row[index]

    return None


def extract_family_number(hit):
    value = get_field(
        hit,
        "family"
    )

    if clean_text(value) != "None":
        return str(value).strip()

    cols = hit.get(
        "columns",
        []
    )

    row = hit.get(
        "row",
        ()
    )

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
            value = row[
                cols.index(column)
            ]

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
            tables.append(
                source_hit["table"]
            )

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
                family_column = fmap.get(
                    "family"
                )

                if not family_column:
                    for column in cols:
                        column_norm = norm(
                            column
                        )

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


def result_line(label, value):
    return ft.Container(
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
            vertical_alignment=ft.CrossAxisAlignment.START,
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
        content=info,
    )


def main(page: ft.Page):
    page.title = APP_TITLE
    page.rtl = True
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0
    page.scroll = ft.ScrollMode.AUTO

    history_items = []

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

    results_column = ft.Column(
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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

    page_title = ft.Text(
        APP_TITLE,
        color=GREEN,
        size=25,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    async def selected_db():
        province = province_dd.value

        filename = get_db_filename(
            province
        )

        if not filename:
            return None

        local_path = get_local_db_path(
            province
        )

        if local_path and local_path.exists():
            try:
                if local_path.stat().st_size > 0:
                    return local_path
            except Exception:
                pass

        status_text.value = (
            f"جارِ تنزيل {filename} من السحابة..."
        )

        page.update()

        db_path = await find_db_for_province(
            province
        )

        return db_path

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
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Image(
                        src="bg.jpg",
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

    async def start_search(e=None):
        query = (
            search_field.value or ""
        ).strip()

        if not query:
            status_text.value = (
                "اكتب كلمة البحث أولاً."
            )

            page.update()
            return

        status_text.value = (
            "جاري تجهيز قاعدة البيانات..."
        )

        results_column.controls.clear()

        page.update()

        db_path = await selected_db()

        if not db_path or not db_path.exists():
            filename = get_db_filename(
                province_dd.value
            )

            status_text.value = (
                f"تعذر تنزيل ملف قاعدة البيانات: "
                f"{filename}"
            )

            page.update()
            return

        status_text.value = (
            f"جارِ البحث داخل {db_path.name}..."
        )

        page.update()

        hits = await asyncio.to_thread(
            search_database,
            db_path,
            query,
            30
        )

        if not hits:
            status_text.value = (
                f"لم يتم العثور على نتائج داخل "
                f"{db_path.name}."
            )

            clear_results()

            page.update()
            return

        history_items.append(
            {
                "query": query,
                "province": province_dd.value,
                "count": len(hits),
            }
        )

        status_text.value = (
            f"تم العثور على {len(hits)} نتيجة "
            f"داخل {db_path.name}."
        )

        results_column.controls.extend(
            [
                cyber_result_card(
                    hit,
                    index
                )
                for index, hit in enumerate(
                    hits,
                    1
                )
            ]
        )

        page.update()

    async def fetch_family(e=None):
        query = (
            search_field.value or ""
        ).strip()

        if not query:
            status_text.value = (
                "اكتب رقم التموينية أو اسم أحد أفراد العائلة أولاً."
            )

            page.update()
            return

        status_text.value = (
            "جاري تجهيز قاعدة البيانات..."
        )

        results_column.controls.clear()

        page.update()

        db_path = await selected_db()

        if not db_path or not db_path.exists():
            filename = get_db_filename(
                province_dd.value
            )

            status_text.value = (
                f"تعذر تنزيل قاعدة البيانات: "
                f"{filename}"
            )

            page.update()
            return

        status_text.value = (
            f"جارِ البحث داخل {db_path.name}..."
        )

        page.update()

        first_hits = await asyncio.to_thread(
            search_database,
            db_path,
            query,
            20
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

        family = await asyncio.to_thread(
            family_rows,
            db_path,
            family_number,
            source_hit,
            100
        )

        if not family:
            status_text.value = (
                f"رقم التموينية {family_number} موجود، "
                "لكن لم أجد بقية أفراد العائلة."
            )

            page.update()
            return

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
                ),
            )

            member_controls.append(
                member_card
            )

        family_header = ft.Container(
            padding=12,
            margin=ft.margin.only(
                bottom=10
            ),
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
                        text_align=ft.TextAlign.RIGHT,
                    ),
                    ft.Text(
                        f"رقم التموينية: {family_number}",
                        color=WHITE,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                    ft.Text(
                        f"قاعدة البيانات: {db_path.name}",
                        color=MUTED,
                        size=14,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
            ),
        )

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
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ),
                ],
            ),
        )

        if JOKER_IMAGE.exists():
            joker_background = ft.Container(
                expand=True,
                border_radius=22,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Image(
                    src="bg.jpg",
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
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Stack(
                expand=True,
                controls=[
                    joker_background,
                    family_overlay,
                ],
            ),
        )

        results_column.controls.append(
            family_result
        )

        status_text.value = (
            f"تم جلب عائلة رقم {family_number} "
            f"من {db_path.name} "
            f"— عدد الأفراد: {len(family)}"
        )

        page.update()

    async def fetch_housing(e=None):
        query = (
            search_field.value or ""
        ).strip()

        if not query:
            status_text.value = (
                "اكتب كلمة البحث أولاً."
            )

            page.update()
            return

        status_text.value = (
            "جاري تجهيز قاعدة البيانات..."
        )

        results_column.controls.clear()

        page.update()

        db_path = await selected_db()

        if not db_path or not db_path.exists():
            filename = get_db_filename(
                province_dd.value
            )

            status_text.value = (
                f"تعذر تنزيل قاعدة البيانات: "
                f"{filename}"
            )

            page.update()
            return

        status_text.value = (
            f"جارِ البحث داخل {db_path.name}..."
        )

        page.update()

        hits = await asyncio.to_thread(
            search_database,
            db_path,
            query,
            30
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
                        norm(column) == norm(wanted)
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
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            ft.Text(
                                f"قاعدة البيانات: {db_path.name}",
                                color=MUTED,
                                size=14,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            *lines,
                        ],
                    ),
                )
            )

        status_text.value = (
            f"تم العثور على {len(hits)} "
            f"نتيجة للسكن داخل {db_path.name}."
        )

        page.update()

    def show_instructions(e=None):
        dialog = ft.AlertDialog(
            modal=True,
            bgcolor="#03181A",
            title=ft.Text(
                "تعليمات",
                color=GREEN,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),
            content=ft.Container(
                width=340,
                content=ft.Text(
                    "اختر المحافظة ثم اكتب الاسم أو الرقم أو المعرف واضغط بدء البحث الشامل.",
                    color=WHITE,
                    size=16,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ),
            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda e: close_dialog(dialog),
                    style=ft.ButtonStyle(
                        color=GREEN
                    ),
                )
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def open_developer(e=None):
        page.launch_url(
            TELEGRAM_URL
        )

    def show_home(e=None):
        drawer.open = False

        page_title.value = APP_TITLE

        search_field.hint_text = (
            "الاسم، الرقم، أو المعرف..."
        )

        search_button_text.value = (
            "بدء البحث الشامل"
        )

        status_text.value = ""

        clear_results()

        page.update()

    def show_history(e=None):
        drawer.open = False

        page_title.value = "سجل الأسماء"

        results_column.controls.clear()

        if not history_items:
            results_column.controls.append(
                ft.Container(
                    padding=30,
                    border=ft.border.all(
                        2,
                        GREEN
                    ),
                    border_radius=22,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        "لا يوجد سجل بحث حالياً.",
                        color=WHITE,
                        size=20,
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )

        else:
            for index, item in enumerate(
                reversed(history_items),
                1
            ):
                results_column.controls.append(
                    ft.Container(
                        padding=15,
                        margin=ft.margin.only(
                            bottom=10
                        ),
                        bgcolor="#03191A",
                        border=ft.border.all(
                            2,
                            GREEN
                        ),
                        border_radius=20,
                        content=ft.Column(
                            spacing=7,
                            controls=[
                                ft.Text(
                                    f"بحث {index}",
                                    color=CYAN,
                                    size=19,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                result_line(
                                    "الاسم أو الرقم",
                                    item["query"]
                                ),
                                result_line(
                                    "المحافظة",
                                    item["province"]
                                ),
                                result_line(
                                    "عدد النتائج",
                                    item["count"]
                                ),
                            ],
                        ),
                    )
                )

        status_text.value = (
            f"عدد عمليات البحث المسجلة: "
            f"{len(history_items)}"
        )

        page.update()

    def show_zain(e=None):
        drawer.open = False

        page_title.value = "بحث رقم زين"

        search_field.hint_text = (
            "أدخل رقم زين..."
        )

        search_field.value = ""

        search_button_text.value = (
            "بحث رقم زين"
        )

        results_column.controls.clear()

        results_column.controls.append(
            ft.Container(
                padding=30,
                border=ft.border.all(
                    2,
                    GREEN
                ),
                border_radius=22,
                alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.PHONE,
                            color=GREEN,
                            size=70,
                        ),
                        ft.Text(
                            "بحث رقم زين",
                            color=CYAN,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "ملفات أرقام زين غير مضافة حالياً.",
                            color=WHITE,
                            size=17,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            )
        )

        status_text.value = (
            "بانتظار إضافة ملفات أرقام زين."
        )

        page.update()

    def show_asiacell(e=None):
        drawer.open = False

        page_title.value = "بحث رقم آسياسيل"

        search_field.hint_text = (
            "أدخل رقم آسياسيل..."
        )

        search_field.value = ""

        search_button_text.value = (
            "بحث رقم آسياسيل"
        )

        results_column.controls.clear()

        results_column.controls.append(
            ft.Container(
                padding=30,
                border=ft.border.all(
                    2,
                    GREEN
                ),
                border_radius=22,
                alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.PHONE,
                            color=GREEN,
                            size=70,
                        ),
                        ft.Text(
                            "بحث رقم آسياسيل",
                            color=CYAN,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "ملفات أرقام آسياسيل غير مضافة حالياً.",
                            color=WHITE,
                            size=17,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            )
        )

        status_text.value = (
            "بانتظار إضافة ملفات أرقام آسياسيل."
        )

        page.update()

    def open_drawer(e=None):
        drawer.open = True
        page.update()


    # =========================
    # القائمة الجانبية ☰
    # =========================

    if MENU_BACKGROUND.exists():

        menu_background = ft.Image(
            src="menu_background.png",
            fit=ft.ImageFit.COVER,
            expand=True,
        )

        menu_overlay = ft.Container(
            expand=True,
            bgcolor="#020D10CC",
        )

    else:

        menu_background = ft.Container(
            expand=True,
            bgcolor="#031313",
        )

        menu_overlay = ft.Container(
            expand=True,
            bgcolor="#020D10AA",
        )


    menu_items = ft.Column(
        spacing=12,
        controls=[
            ft.Text(
                APP_TITLE,
                color=GREEN,
                size=23,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),

            ft.Divider(
                color=GREEN
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.HOME,
                    color=GREEN
                ),
                title=ft.Text(
                    "الرئيسية",
                    color=WHITE,
                    size=18,
                    text_align=ft.TextAlign.RIGHT
                ),
                on_click=show_home,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.HISTORY,
                    color=GREEN
                ),
                title=ft.Text(
                    "سجل الأسماء",
                    color=WHITE,
                    size=18,
                    text_align=ft.TextAlign.RIGHT
                ),
                on_click=show_history,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.PHONE,
                    color=GREEN
                ),
                title=ft.Text(
                    "بحث رقم زين",
                    color=WHITE,
                    size=18,
                    text_align=ft.TextAlign.RIGHT
                ),
                on_click=show_zain,
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.PHONE,
                    color=GREEN
                ),
                title=ft.Text(
                    "بحث رقم آسياسيل",
                    color=WHITE,
                    size=18,
                    text_align=ft.TextAlign.RIGHT
                ),
                on_click=show_asiacell,
            ),

            ft.Divider(
                color="#00FF7F55"
            ),

            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.SEND,
                    color="#29A9EA"
                ),
                title=ft.Text(
                    "المطور",
                    color=WHITE,
                    size=18,
                    text_align=ft.TextAlign.RIGHT
                ),
                on_click=open_developer,
            ),
        ],
    )


    drawer_content = ft.Stack(
        expand=True,
        controls=[
            menu_background,
            menu_overlay,
            ft.Container(
                padding=20,
                content=menu_items,
                expand=True,
            ),
        ],
    )


    drawer = ft.NavigationDrawer(
        bgcolor="#031313",
        controls=[
            ft.Container(
                expand=True,
                content=drawer_content,
            )
        ],
    )


    page.drawer = drawer


    menu_button = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color=WHITE,
        icon_size=34,
        tooltip="القائمة",
        on_click=open_drawer,
    )


    search_button_text = ft.Text(
        "بدء البحث الشامل",
        color="#00110A",
        size=23,
        weight=ft.FontWeight.BOLD,
    )


    header = ft.Container(
        padding=ft.padding.only(
            left=18,
            right=18,
            top=16,
            bottom=16
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                menu_button,

                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.SHIELD,
                            color=GREEN,
                            size=42,
                        ),

                        page_title,
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


    search_button = ft.ElevatedButton(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Icon(
                    ft.Icons.SEARCH,
                    color="#00110A",
                    size=30
                ),

                search_button_text,
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
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,

            controls=[
                ft.Text(
                    "اختر المحافظة المستهدفة",
                    color=GREEN,
                    size=21,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT,
                ),

                province_dd,

                ft.Text(
                    "كلمة البحث",
                    color=GREEN,
                    size=21,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT,
                ),

                search_field,

                search_button,

                ft.Text(
                    "اضغط على زر ☰ لفتح القائمة",
                    color="#8EA1A1",
                    size=16,
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                ),

                ft.Divider(
                    height=20,
                    thickness=1,
                    color=GREEN,
                ),

                results_title,

                status_text,

                results_column,
            ],
        ),
    )


    clear_results()


    # =========================
    # الخلفية الرئيسية
    # =========================

    content = ft.Column(
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            header,
            panel,
        ],
    )


    page.add(content)


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR)
    )
