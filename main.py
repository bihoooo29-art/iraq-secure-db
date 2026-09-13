import os
import sqlite3
from pathlib import Path

import requests
import flet as ft


# =========================================================
# إعدادات التطبيق
# =========================================================

GITHUB_RELEASE_URL = (
    "https://github.com/bihoooo29-art/iraq-db-app/releases/download/v1.0.0"
)

# تخزين قواعد البيانات داخل مساحة التطبيق في Android
DB_DIR = Path(os.getenv("FLET_APP_STORAGE_DATA", "."))
DB_DIR.mkdir(parents=True, exist_ok=True)

BACKGROUND_IMAGE = "bg.jpg"
RESULT_IMAGE = "bg.jpg"

GREEN = "#26d95b"
GREEN_LIGHT = "#70ff96"
GREEN_BRIGHT = "#54ff82"
GREEN_SOFT = "#72ff9b"
GREEN_DARK = "#1b8f3b"
PANEL_BG = "#CC070C09"
FIELD_BG = "#101711"
CARD_BG = "#0b120d"
DARK_BG = "#050806"


# =========================================================
# المحافظات
# =========================================================

PROVINCES = [
    ("baghdad", "بغداد"),
    ("basrah", "البصرة"),
    ("ninawa", "نينوى"),
    ("erbil", "أربيل"),
    ("sulaymaniyah", "السليمانية"),
    ("kirkuk", "كركوك"),
    ("najaf", "النجف الأشرف"),
    ("karbalaa", "كربلاء المقدسة"),
    ("babylon", "بابل"),
    ("alanbar", "الأنبار"),
    ("dhiqar", "ذي قار"),
    ("duhok", "دهوك"),
    ("diyala", "ديالى"),
    ("mesan", "ميسان"),
    ("muthana", "المثنى"),
    ("qadisiya", "القادسية"),
    ("salahaldeen", "صلاح الدين"),
    ("wasit", "واسط"),
    ("balad", "بلد"),
]


# =========================================================
# أسماء الحقول المحتملة
# =========================================================

NAME_KEYS = [
    "name",
    "fullname",
    "full_name",
    "person_name",
    "person",
    "الاسم",
    "الاسم الكامل",
    "اسم",
    "اسم الشخص",
]

BIRTH_KEYS = [
    "birth",
    "birthdate",
    "birth_date",
    "dob",
    "year",
    "birth_year",
    "مواليد",
    "المواليد",
    "تاريخ الميلاد",
    "سنة الميلاد",
]

AGE_KEYS = [
    "age",
    "العمر",
]

FAMILY_KEYS = [
    "family",
    "family_id",
    "family_no",
    "family_number",
    "household",
    "household_id",
    "household_no",
    "ration",
    "ration_number",
    "ration_no",
    "rationcard",
    "ration_card",
    "ration_id",
    "رقم التموينية",
    "رقم التموينيه",
    "التموينية",
    "التموينيه",
    "رقم البطاقة التموينية",
    "البطاقة التموينية",
]

JOB_KEYS = [
    "job",
    "occupation",
    "work",
    "profession",
    "الوظيفة",
    "المهنة",
]

SEQUENCE_KEYS = [
    "sequence",
    "seq",
    "member_no",
    "member_number",
    "person_no",
    "person_number",
    "تسلسل الفرد",
    "تسلسل",
    "رقم الفرد",
]


# =========================================================
# أدوات مساعدة
# =========================================================

def normalize_text(value):
    if value is None:
        return ""

    text = str(value).strip().lower()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "_": "",
        "-": "",
        " ": "",
        "\t": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def quote_identifier(value):
    """
    حماية أسماء الجداول والأعمدة عند وضعها داخل SQL.
    """
    return '"' + str(value).replace('"', '""') + '"'


def find_column(column_names, keywords):
    normalized_columns = {
        column: normalize_text(column)
        for column in column_names
    }

    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
    ]

    # تطابق كامل
    for column, normalized in normalized_columns.items():
        if normalized in normalized_keywords:
            return column

    # تطابق جزئي
    for column, normalized in normalized_columns.items():
        for keyword in normalized_keywords:
            if keyword and (
                keyword in normalized
                or normalized in keyword
            ):
                return column

    return None


def get_column_map(column_names):
    return {
        "name": find_column(column_names, NAME_KEYS),
        "birth": find_column(column_names, BIRTH_KEYS),
        "age": find_column(column_names, AGE_KEYS),
        "family": find_column(column_names, FAMILY_KEYS),
        "job": find_column(column_names, JOB_KEYS),
        "sequence": find_column(column_names, SEQUENCE_KEYS),
    }


def is_numeric_text(value):
    if value is None:
        return False

    text = str(value).strip()

    if not text:
        return False

    return text.isdigit()


# =========================================================
# اكتشاف أفضل جدول
# =========================================================

def find_best_table(cursor):
    tables = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()

    if not tables:
        return None, None

    best_table = None
    best_columns = None
    best_score = -1

    for (table_name,) in tables:
        try:
            columns = cursor.execute(
                f"PRAGMA table_info({quote_identifier(table_name)})"
            ).fetchall()

            column_names = [
                column[1]
                for column in columns
            ]

            if not column_names:
                continue

            detected = get_column_map(column_names)

            score = 0

            if detected["name"]:
                score += 10

            if detected["family"]:
                score += 8

            if detected["birth"]:
                score += 3

            if detected["age"]:
                score += 2

            if detected["job"]:
                score += 1

            if detected["sequence"]:
                score += 1

            if score > best_score:
                best_score = score
                best_table = table_name
                best_columns = column_names

        except Exception:
            continue

    return best_table, best_columns


# =========================================================
# تحميل قاعدة البيانات من GitHub Releases
# =========================================================

def download_database(db_name, status):
    db_path = DB_DIR / db_name

    if db_path.exists() and db_path.stat().st_size > 0:
        return db_path

    status.value = f"جاري تحميل {db_name}..."
    status.update()

    url = f"{GITHUB_RELEASE_URL}/{db_name}"

    temp_path = DB_DIR / f"{db_name}.download"

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=(20, 300),
            headers={
                "User-Agent": "Iraq-Database-App"
            },
        )

        response.raise_for_status()

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    file.write(chunk)

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise Exception("الملف الذي تم تحميله فارغ.")

        temp_path.replace(db_path)

        return db_path

    except Exception as error:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

        raise Exception(
            f"فشل تحميل قاعدة البيانات:\n{error}"
        )


# =========================================================
# البحث داخل SQLite
# =========================================================

def search_database(
    connection,
    table_name,
    column_names,
    keyword,
):
    """
    البحث الذكي:
    1. الاسم
    2. رقم التموينية
    3. الحقول المهمة
    4. جميع الحقول كحل أخير
    """

    table_sql = quote_identifier(table_name)
    keyword = str(keyword).strip()

    detected = get_column_map(column_names)

    name_column = detected["name"]
    family_column = detected["family"]

    # -----------------------------------------------------
    # البحث بالاسم
    # -----------------------------------------------------

    if name_column:
        column_sql = quote_identifier(name_column)

        query = (
            f"SELECT * FROM {table_sql} "
            f"WHERE CAST({column_sql} AS TEXT) LIKE ? "
            f"LIMIT 100"
        )

        rows = connection.execute(
            query,
            [f"%{keyword}%"],
        ).fetchall()

        if rows:
            return rows

    # -----------------------------------------------------
    # البحث برقم التموينية
    # -----------------------------------------------------

    if family_column:
        family_sql = quote_identifier(family_column)

        rows = connection.execute(
            f"""
            SELECT *
            FROM {table_sql}
            WHERE CAST({family_sql} AS TEXT) LIKE ?
            LIMIT 100
            """,
            [f"%{keyword}%"],
        ).fetchall()

        if rows:
            return rows

        # إذا كان الرقم يحتوي أصفاراً بالبداية
        # وSQLite مخزنه كرقم صحيح
        if is_numeric_text(keyword):
            numeric_value = int(keyword)

            rows = connection.execute(
                f"""
                SELECT *
                FROM {table_sql}
                WHERE CAST({family_sql} AS INTEGER) = ?
                LIMIT 100
                """,
                [numeric_value],
            ).fetchall()

            if rows:
                return rows

    # -----------------------------------------------------
    # البحث في الحقول المهمة فقط
    # -----------------------------------------------------

    important_columns = []

    for key in [
        "birth",
        "age",
        "job",
        "sequence",
    ]:
        column = detected.get(key)

        if column and column not in important_columns:
            important_columns.append(column)

    if important_columns:
        conditions = " OR ".join(
            f"CAST({quote_identifier(column)} AS TEXT) LIKE ?"
            for column in important_columns
        )

        query = (
            f"SELECT * FROM {table_sql} "
            f"WHERE {conditions} "
            f"LIMIT 100"
        )

        params = [
            f"%{keyword}%"
            for _ in important_columns
        ]

        rows = connection.execute(
            query,
            params,
        ).fetchall()

        if rows:
            return rows

    # -----------------------------------------------------
    # بحث شامل في جميع الأعمدة
    # -----------------------------------------------------

    conditions = " OR ".join(
        f"CAST({quote_identifier(column)} AS TEXT) LIKE ?"
        for column in column_names
    )

    query = (
        f"SELECT * FROM {table_sql} "
        f"WHERE {conditions} "
        f"LIMIT 100"
    )

    params = [
        f"%{keyword}%"
        for _ in column_names
    ]

    return connection.execute(
        query,
        params,
    ).fetchall()


# =========================================================
# التطبيق
# =========================================================

def main(page: ft.Page):

    # -----------------------------------------------------
    # إعداد الصفحة
    # -----------------------------------------------------

    page.title = "منظومة بيانات العراق"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = DARK_BG

    # -----------------------------------------------------
    # حالة البحث
    # -----------------------------------------------------

    status = ft.Text(
        "جاهز للبحث",
        size=13,
        color=GREEN_SOFT,
        text_align=ft.TextAlign.CENTER,
    )

    results = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    # -----------------------------------------------------
    # نمط حدود الحقول - Flet الحديث
    # -----------------------------------------------------

    field_border = {
        ft.ControlState.DEFAULT: ft.OutlineInputBorder(
            border_radius=10,
            side=ft.BorderSide(
                width=1,
                color=GREEN,
            ),
        ),
        ft.ControlState.FOCUSED: ft.OutlineInputBorder(
            border_radius=10,
            side=ft.BorderSide(
                width=2,
                color=GREEN_BRIGHT,
            ),
        ),
    }

    # -----------------------------------------------------
    # اختيار المحافظة
    # -----------------------------------------------------

    province_dropdown = ft.Dropdown(
        label="اختر المحافظة",
        hint_text="اختر المحافظة",
        value="baghdad",
        options=[
            ft.DropdownOption(
                key=key,
                text=name,
            )
            for key, name in PROVINCES
        ],
        border=field_border,
        label_style=ft.TextStyle(
            color="#7dff9e"
        ),
        text_style=ft.TextStyle(
            color="white"
        ),
        bgcolor=FIELD_BG,
        filled=True,
    )

    # -----------------------------------------------------
    # حقل البحث
    # -----------------------------------------------------

    search_field = ft.TextField(
        label="كلمة البحث",
        hint_text=(
            "الاسم الثلاثي أو الثنائي، "
            "الرقم أو المعرف..."
        ),
        border=field_border,
        label_style=ft.TextStyle(
            color="#7dff9e"
        ),
        text_style=ft.TextStyle(
            color="white"
        ),
        cursor_color=GREEN_BRIGHT,
        bgcolor=FIELD_BG,
        filled=True,
        prefix_icon=ft.Icons.SEARCH,
    )

    # =====================================================
    # النوافذ المنبثقة
    # =====================================================

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    def show_message(title, message):

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                title,
                color=GREEN_LIGHT,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Text(
                message,
                color="white",
                text_align=ft.TextAlign.RIGHT,
                selectable=True,
            ),
            actions=[
                ft.TextButton(
                    content="إغلاق",
                    on_click=close_dialog,
                )
            ],
        )

        page.show_dialog(dialog)

    # -----------------------------------------------------
    # التعليمات
    # -----------------------------------------------------

    def show_instructions(e):

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE,
                        color=GREEN_BRIGHT,
                    ),
                    ft.Text(
                        "تعليمات",
                        color=GREEN_LIGHT,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            content=ft.Text(
                "اختر المحافظة أولاً، ثم اكتب "
                "الاسم الثلاثي أو الثنائي أو الرقم "
                "أو المعرف واضغط «بدء البحث الشامل».\n\n"
                "إذا ظهرت نتيجة تحتوي على رقم تموينية، "
                "اضغط «جلب العائلة» لعرض الأشخاص "
                "المرتبطين بنفس الرقم.\n\n"
                "تم التطوير بواسطة هاشم ❤️",
                color="white",
                size=15,
                text_align=ft.TextAlign.RIGHT,
                selectable=True,
            ),
            actions=[
                ft.TextButton(
                    content="إغلاق",
                    on_click=close_dialog,
                )
            ],
        )

        page.show_dialog(dialog)

    # -----------------------------------------------------
    # المطور
    # -----------------------------------------------------

    async def open_developer(e):
        try:
            launcher = ft.UrlLauncher()
            await launcher.launch_url(
                "https://t.me/UB_515"
            )
        except Exception as error:
            show_message(
                "تعذر فتح الرابط",
                str(error),
            )

    # =====================================================
    # عرض أفراد العائلة
    # =====================================================

    def make_family_view(
        db_path,
        table_name,
        column_names,
        family_column,
        family_value,
    ):

        family_results = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        connection = None

        try:
            connection = sqlite3.connect(
                str(db_path),
                check_same_thread=False,
            )

            family_sql = quote_identifier(
                family_column
            )

            table_sql = quote_identifier(
                table_name
            )

            value_text = str(family_value).strip()

            # البحث أولاً كنص
            rows = connection.execute(
                f"""
                SELECT *
                FROM {table_sql}
                WHERE CAST({family_sql} AS TEXT) = ?
                LIMIT 200
                """,
                [value_text],
            ).fetchall()

            # إذا كان الرقم مخزناً كرقم بدون الأصفار
            if not rows and is_numeric_text(value_text):
                rows = connection.execute(
                    f"""
                    SELECT *
                    FROM {table_sql}
                    WHERE CAST({family_sql} AS INTEGER) = ?
                    LIMIT 200
                    """,
                    [int(value_text)],
                ).fetchall()

        except Exception:
            rows = []

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

        if not rows:
            family_results.controls.append(
                ft.Container(
                    padding=20,
                    content=ft.Text(
                        "لم يتم العثور على أفراد مرتبطين بهذا الرقم.",
                        color="white",
                        size=14,
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )

            return family_results

        detected = get_column_map(column_names)

        name_column = detected["name"]
        birth_column = detected["birth"]
        age_column = detected["age"]
        job_column = detected["job"]
        sequence_column = detected["sequence"]

        for index, row in enumerate(
            rows,
            start=1,
        ):

            row_data = dict(
                zip(column_names, row)
            )

            name = (
                row_data.get(name_column)
                if name_column
                else None
            )

            birth = (
                row_data.get(birth_column)
                if birth_column
                else None
            )

            age = (
                row_data.get(age_column)
                if age_column
                else None
            )

            job = (
                row_data.get(job_column)
                if job_column
                else None
            )

            sequence = (
                row_data.get(sequence_column)
                if sequence_column
                else index
            )

            member_lines = []

            member_lines.append(
                "• رقم التموينية: "
                + str(family_value)
            )

            member_lines.append(
                "• الاسم: "
                + (
                    str(name)
                    if name not in (None, "")
                    else "غير متوفر"
                )
            )

            if birth not in (None, ""):
                member_lines.append(
                    f"• المواليد: {birth}"
                )

            if age not in (None, ""):
                member_lines.append(
                    f"• العمر: {age}"
                )

            if job not in (None, ""):
                member_lines.append(
                    f"• الوظيفة: {job}"
                )

            if sequence not in (None, ""):
                member_lines.append(
                    f"• تسلسل الفرد: {sequence}"
                )

            family_results.controls.append(
                ft.Container(
                    padding=12,
                    border=ft.Border.all(
                        1,
                        "#176c31",
                    ),
                    border_radius=10,
                    bgcolor="#08100b",
                    content=ft.Text(
                        "\n".join(member_lines),
                        color="white",
                        size=14,
                        selectable=True,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                )
            )

        family_results.controls.append(
            ft.Container(
                margin=ft.Margin(top=5),
                padding=12,
                border_radius=10,
                bgcolor="#102016",
                content=ft.Text(
                    f"عدد الأفراد: ({len(rows)})",
                    color=GREEN_LIGHT,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )

        return family_results

    # =====================================================
    # نافذة العائلة
    # =====================================================

    def show_family(
        db_path,
        table_name,
        column_names,
        family_column,
        family_value,
    ):

        family_view = make_family_view(
            db_path,
            table_name,
            column_names,
            family_column,
            family_value,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                f"بيانات العائلة — {family_value}",
                color=GREEN_LIGHT,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                width=500,
                height=500,
                content=ft.Column(
                    [
                        ft.Text(
                            f"رقم التموينية: {family_value}",
                            color=GREEN_BRIGHT,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(
                            color=GREEN_DARK
                        ),
                        family_view,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton(
                    content="إغلاق",
                    on_click=close_dialog,
                )
            ],
        )

        page.show_dialog(dialog)

    # =====================================================
    # بطاقة النتيجة
    # =====================================================

    def create_result_card(
        db_path,
        table_name,
        column_names,
        row,
        index,
    ):

        row_data = dict(
            zip(column_names, row)
        )

        detected = get_column_map(column_names)

        name_column = detected["name"]
        birth_column = detected["birth"]
        age_column = detected["age"]
        family_column = detected["family"]

        name = (
            row_data.get(name_column)
            if name_column
            else None
        )

        birth = (
            row_data.get(birth_column)
            if birth_column
            else None
        )

        age = (
            row_data.get(age_column)
            if age_column
            else None
        )

        family_value = (
            row_data.get(family_column)
            if family_column
            else None
        )

        info_controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.PERSON,
                        color=GREEN_BRIGHT,
                    ),
                    ft.Text(
                        str(
                            name
                            if name not in (None, "")
                            else f"نتيجة رقم {index}"
                        ),
                        color="white",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        selectable=True,
                    ),
                ],
            )
        ]

        if birth not in (None, ""):
            info_controls.append(
                ft.Text(
                    f"المواليد: {birth}",
                    color="#b8ffc9",
                    size=14,
                    selectable=True,
                )
            )

        if age not in (None, ""):
            info_controls.append(
                ft.Text(
                    f"العمر: {age}",
                    color="#b8ffc9",
                    size=14,
                    selectable=True,
                )
            )

        if family_value not in (None, ""):

            info_controls.append(
                ft.Text(
                    f"رقم التموينية: {family_value}",
                    color=GREEN_SOFT,
                    size=14,
                    selectable=True,
                )
            )

            family_button = ft.OutlinedButton(
                content="جلب العائلة",
                icon=ft.Icons.GROUP,
                on_click=lambda e,
                dp=db_path,
                tn=table_name,
                cn=column_names,
                fc=family_column,
                fv=family_value: show_family(
                    dp,
                    tn,
                    cn,
                    fc,
                    fv,
                ),
                style=ft.ButtonStyle(
                    color=GREEN_LIGHT,
                    side=ft.BorderSide(
                        width=1,
                        color=GREEN,
                    ),
                ),
            )

            info_controls.append(
                ft.Container(
                    margin=ft.Margin(top=5),
                    content=family_button,
                )
            )

        return ft.Container(
            padding=15,
            border=ft.Border.all(
                1,
                "#1fbd4d",
            ),
            border_radius=12,
            bgcolor=CARD_BG,
            content=ft.Column(
                info_controls,
                spacing=8,
            ),
        )

    # =====================================================
    # تنفيذ البحث
    # =====================================================

    def search_data(e):

        results.controls.clear()

        status.value = "جاري تجهيز البحث..."
        page.update()

        province = province_dropdown.value
        keyword = (
            search_field.value.strip()
            if search_field.value
            else ""
        )

        # -------------------------------------------------
        # التحقق
        # -------------------------------------------------

        if not province:
            status.value = "يرجى اختيار المحافظة"
            page.update()

            show_message(
                "تنبيه",
                "يرجى اختيار المحافظة أولاً.",
            )
            return

        if not keyword:
            status.value = "اكتب كلمة البحث"
            page.update()

            show_message(
                "تنبيه",
                "اكتب الاسم أو الرقم أو المعرف أولاً.",
            )
            return

        db_name = f"{province}.db"

        connection = None

        try:

            # -------------------------------------------------
            # تحميل القاعدة
            # -------------------------------------------------

            db_path = download_database(
                db_name,
                status,
            )

            status.value = "جاري فتح قاعدة البيانات..."
            page.update()

            # -------------------------------------------------
            # فتح SQLite
            # -------------------------------------------------

            connection = sqlite3.connect(
                str(db_path),
                check_same_thread=False,
            )

            # تحسين القراءة
            connection.execute(
                "PRAGMA query_only = ON"
            )

            cursor = connection.cursor()

            # -------------------------------------------------
            # اكتشاف الجدول
            # -------------------------------------------------

            table_name, column_names = find_best_table(
                cursor
            )

            if not table_name or not column_names:
                raise Exception(
                    "لم يتم العثور تلقائياً على جدول بيانات مناسب."
                )

            status.value = "جاري البحث..."
            page.update()

            # -------------------------------------------------
            # البحث
            # -------------------------------------------------

            rows = search_database(
                connection,
                table_name,
                column_names,
                keyword,
            )

            # -------------------------------------------------
            # لا توجد نتائج
            # -------------------------------------------------

            if not rows:

                results.controls.append(
                    ft.Container(
                        padding=20,
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.SEARCH_OFF,
                                    size=45,
                                    color=GREEN_BRIGHT,
                                ),
                                ft.Text(
                                    "لم يتم العثور على نتائج",
                                    size=18,
                                    color="white",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=(
                                ft.CrossAxisAlignment.CENTER
                            ),
                        ),
                    )
                )

                status.value = (
                    "انتهى البحث — لا توجد نتائج"
                )

                page.update()
                return

            # -------------------------------------------------
            # عرض النتائج
            # -------------------------------------------------

            for index, row in enumerate(
                rows,
                start=1,
            ):

                results.controls.append(
                    create_result_card(
                        db_path,
                        table_name,
                        column_names,
                        row,
                        index,
                    )
                )

            status.value = (
                f"تم العثور على {len(rows)} نتيجة"
            )

            page.update()

        except Exception as error:

            status.value = "حدث خطأ أثناء البحث"
            page.update()

            show_message(
                "خطأ",
                str(error),
            )

        finally:

            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    # =====================================================
    # الخلفية
    # =====================================================

    background = ft.Image(
        src=BACKGROUND_IMAGE,
        expand=True,
        fit=ft.BoxFit.COVER,
    )

    dark_overlay = ft.Container(
        expand=True,
        bgcolor="#D9050806",
    )

    # =====================================================
    # الهيدر
    # =====================================================

    header = ft.Column(
        [
            ft.Container(
                padding=10,
                content=ft.Icon(
                    ft.Icons.SHIELD,
                    size=58,
                    color="#4dff7c",
                ),
            ),

            ft.Text(
                "منظومة بيانات العراق",
                size=28,
                weight=ft.FontWeight.BOLD,
                color="white",
                text_align=ft.TextAlign.CENTER,
            ),

            ft.Text(
                "نظام البحث الشامل في قواعد البيانات",
                size=13,
                color=GREEN_SOFT,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=(
            ft.CrossAxisAlignment.CENTER
        ),
        spacing=3,
    )

    # =====================================================
    # زر البحث الرئيسي
    # =====================================================

    search_button = ft.Button(
        content="بدء البحث الشامل",
        icon=ft.Icons.SEARCH,
        on_click=search_data,
        height=52,
        style=ft.ButtonStyle(
            bgcolor=GREEN_DARK,
            color="white",
            shape=ft.RoundedRectangleBorder(
                radius=12
            ),
        ),
    )

    # =====================================================
    # أزرار المطور والتعليمات
    # =====================================================

    buttons = ft.Row(
        [
            ft.OutlinedButton(
                content="المطور",
                icon=ft.Icons.CODE,
                on_click=open_developer,
                style=ft.ButtonStyle(
                    color=GREEN_LIGHT,
                    side=ft.BorderSide(
                        width=1,
                        color=GREEN,
                    ),
                ),
            ),

            ft.OutlinedButton(
                content="تعليمات",
                icon=ft.Icons.INFO_OUTLINE,
                on_click=show_instructions,
                style=ft.ButtonStyle(
                    color=GREEN_LIGHT,
                    side=ft.BorderSide(
                        width=1,
                        color=GREEN,
                    ),
                ),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # =====================================================
    # عنوان النتائج
    # =====================================================

    result_header = ft.Row(
        [
            ft.Icon(
                ft.Icons.STORAGE,
                color=GREEN_BRIGHT,
            ),

            ft.Text(
                "سجل النتائج والبيانات المستخرجة",
                size=19,
                weight=ft.FontWeight.BOLD,
                color="white",
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # =====================================================
    # صورة الجوكر أسفل النتائج
    # =====================================================

    result_image = ft.Container(
        height=150,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Image(
            src=RESULT_IMAGE,
            expand=True,
            height=150,
            fit=ft.BoxFit.COVER,
        ),
    )

    # =====================================================
    # اللوحة الرئيسية
    # =====================================================

    panel = ft.Container(
        expand=True,
        margin=12,
        padding=18,
        border_radius=20,
        bgcolor=PANEL_BG,
        border=ft.Border.all(
            1,
            GREEN_DARK,
        ),
        content=ft.Column(
            [
                header,

                ft.Divider(
                    color=GREEN_DARK
                ),

                province_dropdown,

                search_field,

                search_button,

                buttons,

                status,

                ft.Divider(
                    color=GREEN_DARK
                ),

                result_header,

                results,

                result_image,
            ],
            horizontal_alignment=(
                ft.CrossAxisAlignment.STRETCH
            ),
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    # =====================================================
    # تشغيل الواجهة
    # =====================================================

    page.add(
        ft.Stack(
            [
                background,
                dark_overlay,

                ft.SafeArea(
                    expand=True,
                    content=panel,
                ),
            ],
            expand=True,
        )
    )


# =========================================================
# تشغيل Flet
# =========================================================

ft.run(
    main,
    assets_dir=".",
)
