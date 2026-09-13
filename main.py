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


def download_database(db_name, status):
    db_path = DB_DIR / db_name

    if db_path.exists():
        return db_path

    status.value = f"جاري تحميل {db_name}..."
    status.update()

    url = f"{GITHUB_RELEASE_URL}/{db_name}"

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        with open(db_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

        return db_path

    except Exception as e:
        if db_path.exists():
            db_path.unlink()

        raise Exception(f"فشل تحميل قاعدة البيانات: {e}")


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
        label_style=ft.TextStyle(color="#7dff9e"),
        text_style=ft.TextStyle(color="white"),
        bgcolor="#101711",
        filled=True,
    )

    search_field = ft.TextField(
        label="كلمة البحث",
        hint_text="اكتب الاسم أو الرقم أو أي معلومة...",
        border_color="#26d95b",
        focused_border_color="#54ff82",
        label_style=ft.TextStyle(color="#7dff9e"),
        text_style=ft.TextStyle(color="white"),
        cursor_color="#54ff82",
        bgcolor="#101711",
        filled=True,
        prefix_icon=ft.Icons.SEARCH,
    )

    def show_message(title, message):
        dialog = ft.AlertDialog(
            title=ft.Text(title, color="#70ff96"),
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

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def show_instructions(e):
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, color="#45ff78"),
                    ft.Text("تعليمات", color="#70ff96"),
                ]
            ),
            content=ft.Text(
                "تم تطوير بواسطة هاشم ❤️\n\n"
                "أي شي تحتاجونه من برمجة تعال بس لا تجي وجيبك فارغ هههههه 😂",
                color="white",
                size=16,
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
        page.launch_url("https://t.me/UB_515")

    def search_data(e):
        results.controls.clear()
        page.update()

        province = province_dropdown.value
        keyword = search_field.value.strip()

        if not province:
            show_message("تنبيه", "يرجى اختيار المحافظة أولاً.")
            return

        db_name = f"{province}.db"

        try:
            db_path = download_database(db_name, status)

            status.value = "جاري البحث..."
            status.update()

            connection = sqlite3.connect(
                str(db_path),
                check_same_thread=False,
            )

            cursor = connection.cursor()

            tables = cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            if not tables:
                connection.close()
                show_message("خطأ", "لم يتم العثور على جدول داخل قاعدة البيانات.")
                return

            table_name = tables[0][0]

            columns = cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            column_names = [column[1] for column in columns]

            if not column_names:
                connection.close()
                show_message("خطأ", "لم يتم العثور على أعمدة في قاعدة البيانات.")
                return

            if keyword:
                conditions = " OR ".join(
                    f'CAST("{column}" AS TEXT) LIKE ?'
                    for column in column_names
                )

                query = (
                    f'SELECT * FROM "{table_name}" '
                    f"WHERE {conditions} LIMIT 100"
                )

                params = [f"%{keyword}%"] * len(column_names)

                rows = cursor.execute(query, params).fetchall()

            else:
                rows = cursor.execute(
                    f'SELECT * FROM "{table_name}" LIMIT 50'
                ).fetchall()

            connection.close()

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
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )

                status.value = "انتهى البحث — لا توجد نتائج"
                page.update()
                return

            for index, row in enumerate(rows, start=1):
                data_text = []

                for column, value in zip(column_names, row):
                    if value is not None and str(value).strip():
                        data_text.append(
                            f"{column}: {value}"
                        )

                results.controls.append(
                    ft.Container(
                        padding=15,
                        border=ft.border.all(1, "#1fbd4d"),
                        border_radius=12,
                        bgcolor="#0b120d",
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.FINGERPRINT,
                                            color="#54ff82",
                                        ),
                                        ft.Text(
                                            f"نتيجة رقم {index}",
                                            color="#72ff9b",
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                ),
                                ft.Divider(color="#1c6d34"),
                                ft.Text(
                                    "\n".join(data_text),
                                    color="white",
                                    size=14,
                                    selectable=True,
                                ),
                            ],
                            spacing=8,
                        ),
                    )
                )

            status.value = f"تم العثور على {len(rows)} نتيجة"
            page.update()

        except Exception as error:
            status.value = "حدث خطأ"
            page.update()
            show_message("خطأ", str(error))

    # خلفية البرنامج
    background = ft.Image(
        src="bg.jpg",
        expand=True,
        fit=ft.ImageFit.COVER,
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
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
            shape=ft.RoundedRectangleBorder(radius=12),
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
                    side=ft.BorderSide(1, "#26d95b"),
                ),
            ),
            ft.OutlinedButton(
                "تعليمات",
                icon=ft.Icons.INFO_OUTLINE,
                on_click=show_instructions,
                style=ft.ButtonStyle(
                    color="#70ff96",
                    side=ft.BorderSide(1, "#26d95b"),
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

    # صورة bg.jpg تظهر أيضاً فوق قسم النتائج
    result_image = ft.Container(
        height=150,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Image(
            src="bg.jpg",
            width=float("inf"),
            height=150,
            fit=ft.ImageFit.COVER,
        ),
    )

    panel = ft.Container(
        expand=True,
        margin=12,
        padding=18,
        border_radius=20,
        bgcolor="#CC070C09",
        border=ft.border.all(1, "#1b8f3b"),
        content=ft.Column(
            [
                header,
                ft.Divider(color="#1b8f3b"),
                province_dropdown,
                search_field,
                search_button,
                buttons,
                status,
                ft.Divider(color="#1b8f3b"),
                result_header,
                result_image,
                results,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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


ft.run(main, assets_dir=".")
