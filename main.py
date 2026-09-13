import os
import sqlite3
from pathlib import Path

import requests
import flet as ft


GITHUB_RELEASE_URL = (
    "https://github.com/bihoooo29-art/iraq-db-app/releases/download/v1.0.0"
)

DB_DIR = Path(os.getenv("FLET_APP_STORAGE_DATA", "."))
DB_DIR.mkdir(parents=True, exist_ok=True)


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


# الكلمات التي يبحث عنها التطبيق تلقائياً
NAME_KEYS = [
    "name",
    "fullname",
    "full_name",
    "person_name",
    "الاسم",
    "الاسم الكامل",
    "اسم",
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
    "رقم التموينية",
    "رقم التموينيه",
    "التموينية",
    "التموينيه",
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
    "تسلسل الفرد",
    "تسلسل",
]


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
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def find_column(column_names, keywords):
    normalized_columns = {
        column: normalize_text(column)
        for column in column_names
    }

    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
    ]

    # تطابق مباشر أولاً
    for column, normalized in normalized_columns.items():
        if normalized in normalized_keywords:
            return column

    # ثم تطابق جزئي
    for column, normalized in normalized_columns.items():
        for keyword in normalized_keywords:
            if keyword and (
                keyword in normalized or normalized in keyword
            ):
                return column

    return None


def find_best_table(cursor):
    tables = cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    if not tables:
        return None, None

    best_table = None
    best_columns = None
    best_score = -1

    for (table_name,) in tables:
        try:
            columns = cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            column_names = [column[1] for column in columns]

            if not column_names:
                continue

            score = 0

            if find_column(column_names, NAME_KEYS):
                score += 5

            if find_column(column_names, FAMILY_KEYS):
                score += 5

            if find_column(column_names, BIRTH_KEYS):
                score += 2

            if find_column(column_names, AGE_KEYS):
                score += 1

            if score > best_score:
                best_score = score
                best_table = table_name
                best_columns = column_names

        except Exception:
            continue

    return best_table, best_columns


def download_database(db_name, status):
    db_path = DB_DIR / db_name

    if db_path.exists():
        return db_path

    status.value = f"جاري تحميل {db_name}..."
    status.update()

    url = f"{GITHUB_RELEASE_URL}/{db_name}"

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=60,
        )
        response.raise_for_status()

        with open(db_path, "wb") as file:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    file.write(chunk)

        return db_path

    except Exception as error:
        if db_path.exists():
            db_path.unlink()

        raise Exception(
            f"فشل تحميل قاعدة البيانات: {error}"
        )


def main(page: ft.Page):
    page.title = "منظومة بيانات العراق"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#050806"

    status = ft.Text(
        "جاهز للبحث",
        size=13,
        color="#72ff9b",
        text_align=ft.TextAlign.CENTER,
    )

    results = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    province_dropdown = ft.Dropdown(
        label="اختر المحافظة",
        hint_text="اختر المحافظة",
        options=[
            ft.dropdown.Option(key, text)
            for key, text in PROVINCES
        ],
        border_color="#26d95b",
        focused_border_color="#54ff82",
        label_style=ft.TextStyle(
            color="#7dff9e"
        ),
        text_style=ft.TextStyle(
            color="white"
        ),
        bgcolor="#101711",
        filled=True,
    )

    search_field = ft.TextField(
        label="كلمة البحث",
        hint_text="الاسم الثلاثي أو الثنائي، الرقم أو المعرف...",
        border_color="#26d95b",
        focused_border_color="#54ff82",
        label_style=ft.TextStyle(
            color="#7dff9e"
        ),
        text_style=ft.TextStyle(
            color="white"
        ),
        cursor_color="#54ff82",
        bgcolor="#101711",
        filled=True,
        prefix_icon=ft.Icons.SEARCH,
    )

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def show_message(title, message):
        dialog = ft.AlertDialog(
            title=ft.Text(
                title,
                color="#70ff96",
            ),
            content=ft.Text(
                message,
                color="white",
                text_align=ft.TextAlign.RIGHT,
            ),
            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda e: close_dialog(dialog),
                )
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_instructions(e):
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE,
                        color="#45ff78",
                    ),
                    ft.Text(
                        "تعليمات",
                        color="#70ff96",
                    ),
                ]
            ),
            content=ft.Text(
                "اكتب الاسم الثلاثي أو الثنائي "
                "أو الرقم أو المعرف ثم اضغط بدء البحث الشامل.\n\n"
                "إذا ظهرت نتيجة لها رقم تموينية، "
                "يمكنك الضغط على «جلب العائلة» "
                "لعرض أفراد العائلة المرتبطين بنفس الرقم.\n\n"
                "تم التطوير بواسطة هاشم ❤️",
                color="white",
                size=15,
                text_align=ft.TextAlign.RIGHT,
            ),
            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda e: close_dialog(dialog),
                )
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_developer(e):
        page.launch_url(
            "https://t.me/UB_515"
        )

    def make_family_view(
        connection,
        table_name,
        column_names,
        family_column,
        family_value,
    ):
        family_results = ft.Column(
            spacing=8,
        )

        try:
            rows = connection.execute(
                f'SELECT * FROM "{table_name}" '
                f'WHERE CAST("{family_column}" AS TEXT) = ? '
                f"LIMIT 200",
                [str(family_value)],
            ).fetchall()

        except Exception:
            rows = []

        if not rows:
            family_results.controls.append(
                ft.Text(
                    "لم يتم العثور على أفراد مرتبطين بهذا الرقم.",
                    color="white",
                    size=14,
                )
            )
            return family_results

        name_column = find_column(
            column_names,
            NAME_KEYS,
        )

        birth_column = find_column(
            column_names,
            BIRTH_KEYS,
        )

        age_column = find_column(
            column_names,
            AGE_KEYS,
        )

        sequence_column = find_column(
            column_names,
            SEQUENCE_KEYS,
        )

        for index, row in enumerate(rows, start=1):
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

            sequence = (
                row_data.get(sequence_column)
                if sequence_column
                else index
            )

            member_lines = []

            member_lines.append(
                f"• الاسم: {name if name not in (None, '') else 'غير متوفر'}"
            )

            if birth not in (None, ""):
                member_lines.append(
                    f"• المواليد: {birth}"
                )

            if age not in (None, ""):
                member_lines.append(
                    f"• العمر: {age}"
                )

            if sequence not in (None, ""):
                member_lines.append(
                    f"• تسلسل الفرد: {sequence}"
                )

            family_results.controls.append(
                ft.Container(
                    padding=12,
                    border=ft.border.all(
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
                    ),
                )
            )

        family_results.controls.append(
            ft.Container(
                margin=ft.margin.only(top=5),
                padding=12,
                border_radius=10,
                bgcolor="#102016",
                content=ft.Text(
                    f"عدد الأفراد: ({len(rows)})",
                    color="#70ff96",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )

        return family_results

    def show_family(
        connection,
        table_name,
        column_names,
        family_column,
        family_value,
    ):
        family_view = make_family_view(
            connection,
            table_name,
            column_names,
            family_column,
            family_value,
        )

        dialog = ft.AlertDialog(
            title=ft.Text(
                f"بيانات العائلة — {family_value}",
                color="#70ff96",
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                width=500,
                height=500,
                content=ft.Column(
                    [
                        ft.Text(
                            f"رقم التموينية: {family_value}",
                            color="#54ff82",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(
                            color="#1b8f3b"
                        ),
                        family_view,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda e: close_dialog(dialog),
                )
            ],
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    def create_result_card(
        connection,
        table_name,
        column_names,
        row,
        index,
    ):
        row_data = dict(
            zip(column_names, row)
        )

        name_column = find_column(
            column_names,
            NAME_KEYS,
        )

        birth_column = find_column(
            column_names,
            BIRTH_KEYS,
        )

        age_column = find_column(
            column_names,
            AGE_KEYS,
        )

        family_column = find_column(
            column_names,
            FAMILY_KEYS,
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
                        color="#54ff82",
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
                )
            )

        if age not in (None, ""):
            info_controls.append(
                ft.Text(
                    f"العمر: {age}",
                    color="#b8ffc9",
                    size=14,
                )
            )

        if family_value not in (None, ""):
            info_controls.append(
                ft.Text(
                    f"رقم التموينية: {family_value}",
                    color="#72ff9b",
                    size=14,
                )
            )

            family_button = ft.OutlinedButton(
                "جلب العائلة",
                icon=ft.Icons.GROUP,
                on_click=lambda e,
                fc=connection,
                tn=table_name,
                cn=column_names,
                fcol=family_column,
                fval=family_value: show_family(
                    fc,
                    tn,
                    cn,
                    fcol,
                    fval,
                ),
                style=ft.ButtonStyle(
                    color="#70ff96",
                    side=ft.BorderSide(
                        1,
                        "#26d95b",
                    ),
                ),
            )

            info_controls.append(
                ft.Container(
                    margin=ft.margin.only(top=5),
                    content=family_button,
                )
            )

        return ft.Container(
            padding=15,
            border=ft.border.all(
                1,
                "#1fbd4d",
            ),
            border_radius=12,
            bgcolor="#0b120d",
            content=ft.Column(
                info_controls,
                spacing=8,
            ),
        )

    def search_data(e):
        results.controls.clear()
        page.update()

        province = province_dropdown.value
        keyword = search_field.value.strip()

        if not province:
            show_message(
                "تنبيه",
                "يرجى اختيار المحافظة أولاً.",
            )
            return

        if not keyword:
            show_message(
                "تنبيه",
                "اكتب الاسم أو الرقم أو المعرف أولاً.",
            )
            return

        db_name = f"{province}.db"

        connection = None

        try:
            db_path = download_database(
                db_name,
                status,
            )

            status.value = "جاري البحث..."
            status.update()

            connection = sqlite3.connect(
                str(db_path),
                check_same_thread=False,
            )

            cursor = connection.cursor()

            table_name, column_names = find_best_table(
                cursor
            )

            if not table_name or not column_names:
                show_message(
                    "خطأ",
                    "لم يتم العثور تلقائياً على جدول بيانات مناسب.",
                )
                return

            name_column = find_column(
                column_names,
                NAME_KEYS,
            )

            family_column = find_column(
                column_names,
                FAMILY_KEYS,
            )

            # نبحث أولاً في عمود الاسم إذا تم اكتشافه.
            rows = []

            if name_column:
                rows = cursor.execute(
                    f'SELECT * FROM "{table_name}" '
                    f'WHERE CAST("{name_column}" AS TEXT) LIKE ? '
                    f"LIMIT 100",
                    [f"%{keyword}%"],
                ).fetchall()

            # إذا لم نجد نتائج بالاسم، نبحث في كل الأعمدة.
            if not rows:
                conditions = " OR ".join(
                    f'CAST("{column}" AS TEXT) LIKE ?'
                    for column in column_names
                )

                query = (
                    f'SELECT * FROM "{table_name}" '
                    f"WHERE {conditions} LIMIT 100"
                )

                params = [
                    f"%{keyword}%"
                    for _ in column_names
                ]

                rows = cursor.execute(
                    query,
                    params,
                ).fetchall()

            if not rows:
                results.controls.append(
                    ft.Container(
                        padding=20,
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.SEARCH_OFF,
                                    size=45,
                                    color="#58ff85",
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

            for index, row in enumerate(
                rows,
                start=1,
            ):
                results.controls.append(
                    create_result_card(
                        connection,
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
            status.value = "حدث خطأ"
            page.update()

            show_message(
                "خطأ",
                str(error),
            )

        # لا نغلق الاتصال هنا، لأن أزرار جلب العائلة
        # تحتاج الاتصال عند الضغط عليها.

    # الخلفية
    background = ft.Image(
        src="bg.jpg",
        expand=True,
        fit=ft.BoxFit.COVER,
    )

    dark_overlay = ft.Container(
        expand=True,
        bgcolor="#D9050806",
    )

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
                color="#72ff9b",
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=(
            ft.CrossAxisAlignment.CENTER
        ),
        spacing=3,
    )

    search_button = ft.ElevatedButton(
        "بدء البحث الشامل",
        icon=ft.Icons.SEARCH,
        on_click=search_data,
        height=52,
        style=ft.ButtonStyle(
            bgcolor="#15943a",
            color="white",
            shape=ft.RoundedRectangleBorder(
                radius=12
            ),
        ),
    )

    buttons = ft.Row(
        [
            ft.OutlinedButton(
                "المطور",
                icon=ft.Icons.CODE,
                on_click=open_developer,
                style=ft.ButtonStyle(
                    color="#70ff96",
                    side=ft.BorderSide(
                        1,
                        "#26d95b",
                    ),
                ),
            ),
            ft.OutlinedButton(
                "تعليمات",
                icon=ft.Icons.INFO_OUTLINE,
                on_click=show_instructions,
                style=ft.ButtonStyle(
                    color="#70ff96",
                    side=ft.BorderSide(
                        1,
                        "#26d95b",
                    ),
                ),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    result_header = ft.Row(
        [
            ft.Icon(
                ft.Icons.DATABASE,
                color="#54ff82",
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

    # صورة الجوكر أسفل قسم النتائج
    result_image = ft.Container(
        height=150,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Image(
            src="bg.jpg",
            width=float("inf"),
            height=150,
            fit=ft.BoxFit.COVER,
        ),
    )

    panel = ft.Container(
        expand=True,
        margin=12,
        padding=18,
        border_radius=20,
        bgcolor="#CC070C09",
        border=ft.border.all(
            1,
            "#1b8f3b",
        ),
        content=ft.Column(
            [
                header,
                ft.Divider(
                    color="#1b8f3b"
                ),
                province_dropdown,
                search_field,
                search_button,
                buttons,
                status,
                ft.Divider(
                    color="#1b8f3b"
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


ft.run(
    main,
    assets_dir=".",
)
