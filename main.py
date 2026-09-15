import os
import sqlite3
from pathlib import Path

import flet as ft


# =========================================================
# المسارات
# =========================================================

PROJECT_DIR = Path(__file__).parent.resolve()

DEFAULT_ASSETS_DIR = PROJECT_DIR / "assets"

ASSETS_DIR = Path(
    os.environ.get(
        "FLET_ASSETS_DIR",
        str(DEFAULT_ASSETS_DIR)
    )
).resolve()

DB_DIR = ASSETS_DIR / "databases"

JOKER_IMAGE = ASSETS_DIR / "bg.jpg"


# =========================================================
# ألوان التصميم
# =========================================================

BG = "#020B0A"
PANEL = "#031413"
PANEL_2 = "#061D19"

NEON = "#00FF88"
NEON_2 = "#00E676"
NEON_DARK = "#008F5A"

CYAN = "#00E5FF"

WHITE = "#F5F5F5"
GRAY = "#9AA7A4"

RED = "#FF4D4D"


# =========================================================
# المحافظات
# =========================================================

PROVINCES = [
    ("بغداد", "baghdad.db"),
    ("الأنبار", "alanbar.db"),
    ("بابل", "babylon.db"),
    ("البصرة", "basra.db"),
    ("ذي قار", "dhiqar.db"),
    ("القادسية", "qadisiyah.db"),
    ("ديالى", "diyala.db"),
    ("دهوك", "duhok.db"),
    ("أربيل", "erbil.db"),
    ("كربلاء", "karbala.db"),
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


# =========================================================
# كلمات التعرف على الحقول
# =========================================================

NAME_WORDS = [
    "name",
    "fullname",
    "full_name",
    "person",
    "اسم",
    "الاسم",
    "الاسم الكامل",
    "اسم الشخص",
]

ID_WORDS = [
    "id",
    "identifier",
    "identity",
    "national",
    "national_id",
    "civil",
    "nid",
    "رقم",
    "رقم الهوية",
    "الهوية",
    "البطاقة",
]

PHONE_WORDS = [
    "phone",
    "mobile",
    "telephone",
    "tel",
    "رقم الهاتف",
    "الهاتف",
    "الموبايل",
]

ADDRESS_WORDS = [
    "address",
    "location",
    "street",
    "district",
    "area",
    "عنوان",
    "العنوان",
    "السكن",
    "المحلة",
    "القضاء",
    "الناحية",
]

GENDER_WORDS = [
    "gender",
    "sex",
    "جنس",
    "الجنس",
]

DATE_WORDS = [
    "date",
    "birth",
    "birthday",
    "dob",
    "تاريخ",
    "تاريخ الميلاد",
    "الميلاد",
]

TABLE_WORDS = [
    "table",
    "جدول",
    "نوع",
    "category",
    "department",
    "قسم",
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
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def contains_keyword(column_name, keywords):
    col = normalize_text(column_name)

    for word in keywords:
        if normalize_text(word) in col:
            return True

    return False


def safe_value(value):
    if value is None:
        return ""

    return str(value).strip()


def open_database(db_path):
    """
    فتح قاعدة SQLite للقراءة فقط.
    """

    uri = f"file:{db_path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=20,
    )


def get_tables(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )

    return [row[0] for row in cursor.fetchall()]


def get_columns(connection, table_name):
    cursor = connection.cursor()

    cursor.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    return [row[1] for row in cursor.fetchall()]


def find_best_column(columns, keywords):
    for column in columns:
        if contains_keyword(column, keywords):
            return column

    return None


def quote_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


# =========================================================
# البحث داخل قاعدة البيانات
# =========================================================

def search_database(db_path, province_name, search_text, max_results=30):

    results = []

    if not db_path.exists():
        return results

    connection = None

    try:
        connection = open_database(db_path)

        tables = get_tables(connection)

        if not tables:
            return results

        search_normalized = normalize_text(search_text)

        for table in tables:

            try:
                columns = get_columns(connection, table)

                if not columns:
                    continue

                name_column = find_best_column(
                    columns,
                    NAME_WORDS
                )

                id_column = find_best_column(
                    columns,
                    ID_WORDS
                )

                phone_column = find_best_column(
                    columns,
                    PHONE_WORDS
                )

                address_column = find_best_column(
                    columns,
                    ADDRESS_WORDS
                )

                gender_column = find_best_column(
                    columns,
                    GENDER_WORDS
                )

                date_column = find_best_column(
                    columns,
                    DATE_WORDS
                )

                table_column = find_best_column(
                    columns,
                    TABLE_WORDS
                )

                # -----------------------------------------
                # تحديد الأعمدة التي سيبحث فيها التطبيق
                # -----------------------------------------

                search_columns = []

                preferred = [
                    name_column,
                    id_column,
                    phone_column,
                    address_column,
                ]

                for col in preferred:
                    if col and col not in search_columns:
                        search_columns.append(col)

                # إذا ما وجد أعمدة معروفة، يبحث في كل الأعمدة النصية
                if not search_columns:
                    search_columns = columns

                # -----------------------------------------
                # بناء الاستعلام
                # -----------------------------------------

                where_parts = []
                params = []

                if search_normalized:

                    for column in search_columns:

                        where_parts.append(
                            f"LOWER(CAST({quote_identifier(column)} AS TEXT)) LIKE ?"
                        )

                        params.append(
                            f"%{search_normalized}%"
                        )

                else:
                    # إذا البحث فارغ لا نريد جلب آلاف السجلات
                    continue

                where_sql = " OR ".join(where_parts)

                sql = f"""
                    SELECT *
                    FROM {quote_identifier(table)}
                    WHERE {where_sql}
                    LIMIT ?
                """

                params.append(max_results)

                cursor = connection.cursor()

                cursor.execute(
                    sql,
                    params
                )

                rows = cursor.fetchall()

                returned_columns = [
                    description[0]
                    for description in cursor.description
                ]

                for row in rows:

                    record = dict(
                        zip(
                            returned_columns,
                            row
                        )
                    )

                    results.append({
                        "province": province_name,
                        "table": safe_value(table),
                        "name": safe_value(
                            record.get(name_column)
                            if name_column
                            else ""
                        ),
                        "id": safe_value(
                            record.get(id_column)
                            if id_column
                            else ""
                        ),
                        "phone": safe_value(
                            record.get(phone_column)
                            if phone_column
                            else ""
                        ),
                        "address": safe_value(
                            record.get(address_column)
                            if address_column
                            else ""
                        ),
                        "gender": safe_value(
                            record.get(gender_column)
                            if gender_column
                            else ""
                        ),
                        "date": safe_value(
                            record.get(date_column)
                            if date_column
                            else ""
                        ),
                        "category": safe_value(
                            record.get(table_column)
                            if table_column
                            else ""
                        ),
                        "raw": record,
                    })

                    if len(results) >= max_results:
                        return results

            except Exception:
                continue

    except Exception:
        return results

    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

    return results


# =========================================================
# البحث في جميع المحافظات
# =========================================================

def perform_search(province_name, search_text):

    search_text = search_text.strip()

    if not search_text:
        return []

    if province_name == "كل المحافظات":

        all_results = []

        for name, filename in PROVINCES:

            db_path = DB_DIR / filename

            found = search_database(
                db_path,
                name,
                search_text,
                max_results=15
            )

            all_results.extend(found)

            if len(all_results) >= 100:
                break

        return all_results[:100]

    selected = None

    for name, filename in PROVINCES:
        if name == province_name:
            selected = filename
            break

    if not selected:
        return []

    db_path = DB_DIR / selected

    return search_database(
        db_path,
        province_name,
        search_text,
        max_results=100
    )


# =========================================================
# أيقونة المعلومة
# =========================================================

def info_row(icon_name, title, value):

    if not value:
        return None

    return ft.Row(
        controls=[
            ft.Icon(
                name=icon_name,
                color=NEON,
                size=21,
            ),

            ft.Text(
                title,
                color=NEON,
                size=15,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),

            ft.Text(
                value,
                color=WHITE,
                size=15,
                expand=True,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
    )


# =========================================================
# بطاقة نتيجة
# =========================================================

def result_card(result):

    rows = []

    row = info_row(
        ft.Icons.TABLE_CHART,
        "الجدول:",
        result.get("table", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.PERSON,
        "الاسم:",
        result.get("name", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.BADGE,
        "رقم الهوية:",
        result.get("id", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.PHONE,
        "الهاتف:",
        result.get("phone", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.LOCATION_ON,
        "المحافظة:",
        result.get("province", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.HOME,
        "العنوان:",
        result.get("address", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.WC,
        "الجنس:",
        result.get("gender", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.CALENDAR_MONTH,
        "التاريخ:",
        result.get("date", "")
    )

    if row:
        rows.append(row)

    row = info_row(
        ft.Icons.FOLDER,
        "القسم:",
        result.get("category", "")
    )

    if row:
        rows.append(row)

    # -----------------------------------------------------
    # صورة الجوكر
    # -----------------------------------------------------

    if JOKER_IMAGE.exists():

        joker = ft.Image(
            src="bg.jpg",
            width=190,
            height=210,
            fit=ft.ImageFit.COVER,
            border_radius=12,
        )

    else:

        # بديل مرسوم داخل التطبيق
        joker = ft.Container(
            width=190,
            height=210,
            border=ft.Border.all(
                2,
                NEON
            ),
            border_radius=12,
            bgcolor="#00120E",
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Icon(
                        name=ft.Icons.SECURITY,
                        color=NEON,
                        size=70,
                    ),

                    ft.Text(
                        "◉  ◉",
                        color=NEON,
                        size=25,
                        weight=ft.FontWeight.BOLD,
                    ),

                    ft.Text(
                        "╲  ╱",
                        color=NEON,
                        size=25,
                        weight=ft.FontWeight.BOLD,
                    ),

                    ft.Text(
                        "CYBER",
                        color=NEON,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
            ),
        )

    return ft.Container(
        margin=ft.margin.only(
            top=8,
            bottom=8,
        ),

        padding=12,

        border=ft.Border.all(
            2,
            NEON,
        ),

        border_radius=18,

        bgcolor="#02100E",

        content=ft.Row(
            controls=[
                joker,

                ft.Container(
                    expand=True,
                    padding=ft.padding.only(
                        left=8,
                        right=8,
                    ),
                    content=ft.Column(
                        controls=rows,
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


# =========================================================
# التطبيق
# =========================================================

def main(page: ft.Page):

    page.title = "منظومة بيانات العراق"

    page.bgcolor = BG

    page.padding = 0

    page.spacing = 0

    page.rtl = True

    page.scroll = ft.ScrollMode.AUTO

    # -----------------------------------------------------
    # المتغيرات
    # -----------------------------------------------------

    selected_province = "بغداد"

    # -----------------------------------------------------
    # SnackBar
    # -----------------------------------------------------

    def show_message(message):

        page.snack_bar = ft.SnackBar(
            content=ft.Text(
                message,
                color=WHITE,
                text_align=ft.TextAlign.RIGHT,
            ),
            bgcolor="#08231C",
        )

        page.snack_bar.open = True

        page.update()

    # -----------------------------------------------------
    # تعليمات
    # -----------------------------------------------------

    def show_instructions(e=None):

        dialog = ft.AlertDialog(
            modal=True,

            title=ft.Text(
                "تعليمات",
                color=NEON,
                text_align=ft.TextAlign.RIGHT,
            ),

            content=ft.Container(
                width=340,

                content=ft.Text(
                    "1. اختر المحافظة المستهدفة.\n\n"
                    "2. اكتب الاسم أو الرقم أو المعرف.\n\n"
                    "3. اضغط على «بدء البحث الشامل».\n\n"
                    "4. ستظهر النتائج الموجودة داخل قواعد البيانات المحلية.\n\n"
                    "قواعد البيانات مدمجة داخل التطبيق ولا تحتاج إلى تحميل أثناء التشغيل.",
                    color=WHITE,
                    size=15,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ),

            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda e: close_dialog(),
                )
            ],
        )

        page.dialog = dialog

        dialog.open = True

        page.update()

    def close_dialog():

        if page.dialog:
            page.dialog.open = False
            page.update()

    # -----------------------------------------------------
    # المطور
    # -----------------------------------------------------

    def open_developer(e=None):

        page.launch_url(
            "https://t.me/UB_515"
        )

    # -----------------------------------------------------
    # القائمة الجانبية
    # -----------------------------------------------------

    drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(
                height=110,
                bgcolor="#03100E",
                padding=20,
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            name=ft.Icons.SECURITY,
                            color=NEON,
                            size=45,
                        ),

                        ft.Text(
                            "منظومة بيانات العراق",
                            color=NEON,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),

            ft.Divider(
                color=NEON_DARK,
                height=1,
            ),

            ft.NavigationDrawerDestination(
                label="المطور",
                icon=ft.Icons.CODE,
            ),

            ft.NavigationDrawerDestination(
                label="تعليمات",
                icon=ft.Icons.INFO_OUTLINE,
            ),
        ],
    )

    page.drawer = drawer

    def drawer_change(e):

        index = e.control.selected_index

        if index == 0:
            open_developer()

        elif index == 1:
            show_instructions()

        e.control.selected_index = -1

        page.drawer.open = False

        page.update()

    drawer.on_change = drawer_change

    # -----------------------------------------------------
    # زر القائمة ☰
    # -----------------------------------------------------

    menu_button = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color=NEON,
        icon_size=31,
        tooltip="القائمة",
        on_click=lambda e: open_drawer(),
    )

    def open_drawer():

        page.drawer.open = True

        page.update()

    # -----------------------------------------------------
    # اختيار المحافظة
    # -----------------------------------------------------

    province_options = [
        ft.dropdown.Option(
            "كل المحافظات"
        )
    ]

    for name, _ in PROVINCES:

        province_options.append(
            ft.dropdown.Option(name)
        )

    province_dropdown = ft.Dropdown(
        value=selected_province,

        options=province_options,

        text_style=ft.TextStyle(
            color=WHITE,
            size=17,
            weight=ft.FontWeight.BOLD,
        ),

        border_color=NEON,

        focused_border_color=NEON,

        bgcolor="#031815",

        border_radius=15,

        content_padding=16,

        text_align=ft.TextAlign.RIGHT,

        on_change=lambda e: update_province(
            e.control.value
        ),
    )

    def update_province(value):

        nonlocal selected_province

        selected_province = value

    # -----------------------------------------------------
    # حقل البحث
    # -----------------------------------------------------

    search_field = ft.TextField(

        hint_text="الاسم، الرقم، أو المعرف...",

        hint_style=ft.TextStyle(
            color="#72817D",
            size=15,
        ),

        text_style=ft.TextStyle(
            color=WHITE,
            size=17,
        ),

        text_align=ft.TextAlign.RIGHT,

        rtl=True,

        border_color=NEON,

        focused_border_color=NEON,

        cursor_color=NEON,

        bgcolor="#031815",

        border_radius=15,

        content_padding=16,

        prefix_icon=ft.Icons.SEARCH,

        on_submit=lambda e: start_search(),
    )

    # -----------------------------------------------------
    # منطقة النتائج
    # -----------------------------------------------------

    results_column = ft.Column(
        controls=[],
        spacing=0,
    )

    result_title = ft.Text(
        "سجل النتائج والبيانات المسترجعة:",
        color=CYAN,
        size=20,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.RIGHT,
    )

    result_count = ft.Text(
        "",
        color=NEON,
        size=16,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.RIGHT,
    )

    # -----------------------------------------------------
    # بدء البحث
    # -----------------------------------------------------

    def start_search():

        text = search_field.value.strip()

        if not text:

            show_message(
                "اكتب الاسم أو الرقم أو المعرف أولاً."
            )

            return

        results_column.controls.clear()

        result_count.value = "جاري البحث..."

        page.update()

        try:

            results = perform_search(
                selected_province,
                text,
            )

        except Exception as ex:

            results = []

            show_message(
                f"حدث خطأ أثناء البحث: {ex}"
            )

        if results:

            result_count.value = (
                f"تم العثور على {len(results)} نتيجة"
            )

            for item in results:
                results_column.controls.append(
                    result_card(item)
                )

        else:

            result_count.value = (
                "لم يتم العثور على نتائج مطابقة"
            )

            results_column.controls.append(
                ft.Container(
                    padding=25,

                    border=ft.Border.all(
                        1,
                        NEON_DARK,
                    ),

                    border_radius=15,

                    bgcolor="#03110F",

                    content=ft.Column(
                        controls=[
                            ft.Icon(
                                name=ft.Icons.SEARCH_OFF,
                                color=GRAY,
                                size=45,
                            ),

                            ft.Text(
                                "لا توجد نتائج مطابقة للبحث.",
                                color=WHITE,
                                size=17,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                )
            )

        page.update()

    # -----------------------------------------------------
    # زر البحث
    # -----------------------------------------------------

    search_button = ft.Container(

        height=72,

        border_radius=18,

        bgcolor=NEON,

        ink=True,

        on_click=lambda e: start_search(),

        content=ft.Row(
            controls=[
                ft.Icon(
                    name=ft.Icons.SEARCH,
                    color="#00120D",
                    size=34,
                ),

                ft.Text(
                    "بدء البحث الشامل",
                    color="#00120D",
                    size=23,
                    weight=ft.FontWeight.BOLD,
                ),
            ],

            alignment=ft.MainAxisAlignment.CENTER,

            vertical_alignment=ft.CrossAxisAlignment.CENTER,

            spacing=10,
        ),
    )

    # -----------------------------------------------------
    # أزرار التعليمات والمطور
    # -----------------------------------------------------

    instructions_button = ft.Container(

        height=62,

        expand=True,

        border=ft.Border.all(
            2,
            NEON,
        ),

        border_radius=18,

        bgcolor="#031815",

        ink=True,

        on_click=show_instructions,

        content=ft.Row(
            controls=[
                ft.Icon(
                    name=ft.Icons.INFO,
                    color=WHITE,
                    size=28,
                ),

                ft.Text(
                    "تعليمات",
                    color=WHITE,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
            ],

            alignment=ft.MainAxisAlignment.CENTER,

            spacing=10,
        ),
    )

    developer_button = ft.Container(

        height=62,

        expand=True,

        border=ft.Border.all(
            2,
            NEON,
        ),

        border_radius=18,

        bgcolor="#031815",

        ink=True,

        on_click=open_developer,

        content=ft.Row(
            controls=[
                ft.Icon(
                    name=ft.Icons.CODE,
                    color=WHITE,
                    size=30,
                ),

                ft.Text(
                    "المطور",
                    color=WHITE,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
            ],

            alignment=ft.MainAxisAlignment.CENTER,

            spacing=10,
        ),
    )

    # -----------------------------------------------------
    # الهيدر
    # -----------------------------------------------------

    header = ft.Container(

        padding=ft.padding.only(
            left=18,
            right=18,
            top=12,
            bottom=12,
        ),

        border=ft.Border(
            bottom=ft.BorderSide(
                1,
                NEON_DARK,
            )
        ),

        content=ft.Row(

            controls=[

                menu_button,

                ft.Container(
                    expand=True,

                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                name=ft.Icons.SECURITY,
                                color=NEON,
                                size=55,
                            ),

                            ft.Text(
                                "منظومة بيانات العراق",
                                color=NEON,
                                size=25,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],

                        alignment=ft.MainAxisAlignment.CENTER,

                        vertical_alignment=ft.CrossAxisAlignment.CENTER,

                        spacing=10,
                    ),
                ),

                ft.Icon(
                    name=ft.Icons.SHIELD,
                    color=NEON_DARK,
                    size=35,
                ),
            ],

            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # -----------------------------------------------------
    # عنوان المحافظة
    # -----------------------------------------------------

    province_label = ft.Text(
        "اختر المحافظة المستهدفة",
        color=NEON,
        size=19,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.RIGHT,
    )

    search_label = ft.Text(
        "كلمة البحث",
        color=NEON,
        size=19,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.RIGHT,
    )

    # -----------------------------------------------------
    # المحتوى الرئيسي
    # -----------------------------------------------------

    main_panel = ft.Container(

        margin=ft.margin.only(
            left=18,
            right=18,
            top=25,
            bottom=35,
        ),

        padding=20,

        bgcolor="#02110F",

        border=ft.Border.all(
            2,
            NEON_DARK,
        ),

        border_radius=30,

        content=ft.Column(

            controls=[

                province_label,

                province_dropdown,

                ft.Container(
                    height=10
                ),

                search_label,

                search_field,

                ft.Container(
                    height=14
                ),

                search_button,

                ft.Container(
                    height=14
                ),

                ft.Row(
                    controls=[
                        developer_button,
                        instructions_button,
                    ],

                    spacing=14,
                ),

                ft.Container(
                    height=10
                ),

                ft.Text(
                    "اضغط على زر المطور للتواصل",
                    color="#84938F",
                    size=15,
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                ),

                ft.Divider(
                    color=NEON_DARK,
                    thickness=1,
                    height=30,
                ),

                result_title,

                ft.Container(
                    height=8
                ),

                result_count,

                ft.Container(
                    height=8
                ),

                results_column,
            ],

            spacing=7,

            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    # -----------------------------------------------------
    # الخلفية العامة
    # -----------------------------------------------------

    background = ft.Container(

        expand=True,

        bgcolor=BG,

        content=ft.Column(

            controls=[

                header,

                main_panel,

            ],

            spacing=0,

            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    page.add(background)


# =========================================================
# تشغيل التطبيق
# =========================================================

ft.run(
    main,
    assets_dir="assets",
)
