
import os
import sqlite3
import requests
import flet as ft

# مسار تخزين قواعد البيانات في الهاتف
DB_DIR = "." 

# رابط الإصدار على غيت هب
GITHUB_RELEASE_URL = "https://github.com/bihoooo29-art/iraq-db-app/releases/download/v1.0.0"

def main(page: ft.Page):
    page.title = "منظومة بيانات العراق - @UB_515"
    page.rtl = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK

    provinces = [
        {"key": "baghdad", "text": "بغداد"},
        {"key": "basrah", "text": "البصرة"},
        {"key": "ninawa", "text": "نينوى"},
        {"key": "erbil", "text": "أربيل"},
        {"key": "sulaymaniyah", "text": "السليمانية"},
        {"key": "kirkuk", "text": "كركوك"},
        {"key": "najaf", "text": "النجف الأشرف"},
        {"key": "karbalaa", "text": "كربلاء المقدسة"},
        {"key": "babylon", "text": "بابل"},
        {"key": "alanbar", "text": "الأنبار"},
        {"key": "dhiqar", "text": "ذي قار"},
        {"key": "duhok", "text": "دهوك"},
        {"key": "diyala", "text": "ديالى"},
        {"key": "mesan", "text": "ميسان"},
        {"key": "muthana", "text": "المثنى"},
        {"key": "qadisiya", "text": "القادسية"},
        {"key": "sahaldeen", "text": "صلاح الدين"},
        {"key": "wasit", "text": "واسط"},
        {"key": "balad", "text": "بلد"}
    ]

    selected_province = ft.Dropdown(
        label="اختر المحافظة المستهدفة",
        hint_text="اختر المحافظة للبحث في بياناتها",
        options=[ft.dropdown.Option(key=p["key"], text=p["text"]) for p in provinces],
        width=340,
        border_color=ft.colors.GREEN_400,
        focused_border_color=ft.colors.GREEN_ACCENT,
        label_style=ft.TextStyle(color=ft.colors.GREEN_300)
    )

    search_box = ft.TextField(
        label="كلمة البحث (الاسم، الرقم، أو المعرف...)",
        hint_text="اكتب للبحث داخل قاعدة البيانات...",
        width=340,
        rtl=True,
        border_color=ft.colors.GREEN_400,
        focused_border_color=ft.colors.GREEN_ACCENT,
        label_style=ft.TextStyle(color=ft.colors.GREEN_300)
    )

    results_list = ft.ListView(expand=1, spacing=12, padding=15, auto_scroll=True)

    def search_data(e):
        province_val = selected_province.value
        if not province_val:
            results_list.controls.clear()
            results_list.controls.append(
                ft.Text("⚠️ يرجى اختيار المحافظة أولاً قبل البدء بالبحث!", color=ft.colors.RED_400, weight=ft.FontWeight.BOLD)
            )
            page.update()
            return

        db_name = f"{province_val}.db"
        db_path = os.path.join(DB_DIR, db_name)

        if not os.path.exists(db_path):
            try:
                results_list.controls.clear()
                results_list.controls.append(
                    ft.Text(f"📥 قاعدة البيانات غير موجودة محلياً. جاري تحميل ({db_name}) من السحاب لأول مرة...", color=ft.colors.YELLOW)
                )
                page.update()

                download_url = f"{GITHUB_RELEASE_URL}/{db_name}"
                response = requests.get(download_url, stream=True)
                
                if response.status_code == 200:
                    with open(db_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                else:
                    results_list.controls.clear()
                    results_list.controls.append(
                        ft.Text(f"❌ فشل التحميل من السحاب. رمز الخطأ: {response.status_code}", color=ft.colors.RED_400)
                    )
                    page.update()
                    return
            except Exception as dl_ex:
                results_list.controls.clear()
                results_list.controls.append(
                    ft.Text(f"❌ حدث خطأ أثناء تحميل الملف: {dl_ex}", color=ft.colors.RED_400)
                )
                page.update()
                return

        try:
            results_list.controls.clear()
            results_list.controls.append(ft.Text("🔄 جاري البحث في قواعد البيانات...", color=ft.colors.YELLOW))
            page.update()

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                results_list.controls.clear()
                results_list.controls.append(ft.Text("⚠️ قاعدة البيانات الحالية فارغة أو لا تحتوي على جدول رئيسي.", color=ft.colors.YELLOW))
                conn.close()
                page.update()
                return

            table_name = tables[0][0]
            query_text = search_box.value.strip()

            cursor.execute(f"PRAGMA table_info(`{table_name}`);")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            if query_text:
                where_clause = " OR ".join([f"`{col}` LIKE ?" for col in column_names])
                sql = f"SELECT * FROM `{table_name}` WHERE {where_clause} LIMIT 100;"
                params = [f"%{query_text}%" for _ in column_names]
                cursor.execute(sql, params)
            else:
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 50;")

            rows = cursor.fetchall()
            conn.close()

            results_list.controls.clear()
            
            if not rows:
                results_list.controls.append(
                    ft.Text("🔍 لم يتم العثور على أي نتائج مطابقة للبحث.", color=ft.colors.YELLOW_ACCENT)
                )
            else:
                results_list.controls.append(
                    ft.Text(f"✅ تم العثور على ({len(rows)}) نتيجة:", color=ft.colors.GREEN_ACCENT, weight=ft.FontWeight.BOLD)
                )
                
                for row in rows:
                    formatted_data = "\n".join([f"{column_names[i]}: {row[i]}" for i in range(len(row)) if row[i] is not None])
                    
                    results_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(formatted_data, rtl=True, color=ft.colors.GREEN_200, size=13),
                                ]),
                                padding=12,
                                bgcolor=ft.colors.BLACK54
                            ),
                            elevation=5
                        )
                    )
            page.update()

        except Exception as ex:
            results_list.controls.clear()
            results_list.controls.append(
                ft.Text(f"❌ حدث خطأ تقني أثناء الاستعلام: {ex}", color=ft.colors.RED_400)
            )
            page.update()

    search_button = ft.ElevatedButton(
        text="بدء البحث الشامل", 
        icon=ft.icons.SEARCH, 
        on_click=search_data,
        width=340,
        color=ft.colors.BLACK,
        bgcolor=ft.colors.GREEN_ACCENT
    )

    developer_button = ft.TextButton(
        text="المطور: اضغط هنا للتواصل (@UB_515)",
        icon=ft.icons.CODE,
        on_click=lambda _: page.launch_url("https://t.me/UB_515")
    )

    page.add(
        ft.Column([
            ft.Row([
                ft.Icon(ft.icons.SECURITY, color=ft.colors.GREEN_ACCENT, size=28),
                ft.Text("منظومة بيانات العراق الأمنية", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_ACCENT),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(color=ft.colors.GREEN_800),
            selected_province,
            search_box,
            search_button,
            developer_button,
            ft.Divider(color=ft.colors.GREEN_800),
            ft.Text("سجل النتائج والبيانات المسترجعة:", weight=ft.FontWeight.BOLD, color=ft.colors.WHITE70, size=12),
            results_list
        ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
    )

# تم تصحيح السطر الأخير هنا ليعمل بسلاسة تامة
ft.app(target=main)
