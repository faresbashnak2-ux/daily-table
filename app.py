import hmac
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st

from database import (
    IntegrityError,
    individuals_between,
    init_db,
    menu_between,
    rating_for,
    rename_profile,
    save_menu,
    save_rating,
    stats_between,
    users,
)


def setting(name, default=None):
    """Read a setting from Streamlit Secrets, with environment fallback."""
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        value = None
    if value is not None:
        return str(value)
    return os.getenv(name, default)


st.set_page_config(
    page_title="Daily Table | المائدة اليومية",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SITE_ACCESS_CODE = setting("SITE_ACCESS_CODE")
ADMIN_PIN = setting("ADMIN_PIN")
try:
    APP_TIMEZONE = ZoneInfo(setting("APP_TIMEZONE", "Asia/Beirut"))
except ZoneInfoNotFoundError:
    APP_TIMEZONE = ZoneInfo("UTC")

STRINGS = {
    "hero_title": ("Daily Table", "المائدة اليومية"),
    "hero_subtitle": (
        "Weekly menu • Daily feedback • Better meals over time",
        "قائمة أسبوعية • تقييم يومي • وجبات أفضل مع مرور الوقت",
    ),
    "access_title": ("Enter Daily Table", "الدخول إلى المائدة اليومية"),
    "access_help": (
        "Enter the shared access code provided by the administrator.",
        "أدخل رمز الدخول المشترك الذي زوّدك به المسؤول.",
    ),
    "access_code": ("Access code", "رمز الدخول"),
    "enter_site": ("Enter website", "دخول الموقع"),
    "wrong_access_code": ("Incorrect access code.", "رمز الدخول غير صحيح."),
    "access_not_configured": (
        "Site access is not configured. Add SITE_ACCESS_CODE to Streamlit Secrets.",
        "لم يتم إعداد رمز دخول الموقع. أضف SITE_ACCESS_CODE إلى أسرار Streamlit.",
    ),
    "logout": ("Log out", "تسجيل الخروج"),
    "db_error": ("The app could not connect to PostgreSQL.", "تعذر اتصال التطبيق بقاعدة PostgreSQL."),
    "db_help": (
        "Check DATABASE_URL in Streamlit Secrets, then restart the app.",
        "تحقق من DATABASE_URL في أسرار Streamlit، ثم أعد تشغيل التطبيق.",
    ),
    "tab_profile": ("👤 Profile", "👤 الملف الشخصي"),
    "tab_menu": ("📅 Weekly menu", "📅 قائمة الأسبوع"),
    "tab_rate": ("⭐ Rate today", "⭐ قيّم اليوم"),
    "tab_admin": ("📊 Admin", "📊 الإدارة"),
    "choose_profile": ("Choose your profile", "اختر ملفك الشخصي"),
    "profile_help": (
        "Tap your name. No additional profile password is required.",
        "اضغط على اسمك. لا يلزم إدخال رمز إضافي للملف الشخصي.",
    ),
    "current_profile": ("Current profile", "الملف الحالي"),
    "weekly_menu": ("This week's menu", "قائمة هذا الأسبوع"),
    "today": ("TODAY", "اليوم"),
    "menu_missing": ("Menu not entered yet.", "لم تُدخل قائمة الطعام بعد."),
    "rate_title": ("Rate today's experience", "قيّم تجربة اليوم"),
    "choose_first": ("Choose your profile first.", "اختر ملفك الشخصي أولاً."),
    "today_missing": ("Today's menu has not been entered yet.", "لم تُدخل قائمة طعام اليوم بعد."),
    "already_rated": (
        "You already rated today. A new submission will replace your previous rating.",
        "لقد قيّمت وجبة اليوم. سيستبدل التقييم الجديد تقييمك السابق.",
    ),
    "rating_scale": ("1 star = poor • 5 stars = excellent", "نجمة واحدة = ضعيف • 5 نجوم = ممتاز"),
    "food_choice": ("Food choice", "اختيار الوجبة"),
    "taste": ("Taste", "المذاق"),
    "cleanliness": ("Cleanliness", "النظافة"),
    "service": ("Service", "الخدمة"),
    "comment": ("Comment (optional)", "تعليق (اختياري)"),
    "comment_placeholder": (
        "What was good? What should improve?",
        "ما الذي أعجبك؟ وما الذي يجب تحسينه؟",
    ),
    "submit_rating": ("Submit today's rating", "إرسال تقييم اليوم"),
    "rate_all": ("Please rate all four categories.", "يرجى تقييم الفئات الأربع كلها."),
    "rating_saved": ("Thank you — your rating was saved.", "شكراً — تم حفظ تقييمك."),
    "admin_title": ("Admin dashboard", "لوحة الإدارة"),
    "admin_pin": ("Admin PIN", "رمز الإدارة"),
    "unlock": ("Unlock admin", "فتح لوحة الإدارة"),
    "wrong_pin": ("Incorrect PIN.", "رمز الإدارة غير صحيح."),
    "pin_private": ("Keep the admin PIN private.", "حافظ على سرية رمز الإدارة."),
    "admin_not_configured": (
        "Admin access is not configured. Add ADMIN_PIN to Streamlit Secrets.",
        "لم يتم إعداد دخول الإدارة. أضف ADMIN_PIN إلى أسرار Streamlit.",
    ),
    "admin_active": ("Admin access active", "تم فتح صلاحيات الإدارة"),
    "lock": ("Lock admin", "إقفال لوحة الإدارة"),
    "overview": ("Overview", "نظرة عامة"),
    "daily_details": ("Daily details", "التفاصيل اليومية"),
    "menu_editor": ("Menu editor", "محرر القائمة"),
    "profiles": ("Profiles", "الملفات الشخصية"),
    "week_containing": ("Week containing", "الأسبوع الذي يتضمن"),
    "no_week_ratings": ("No ratings yet for this week.", "لا توجد تقييمات لهذا الأسبوع بعد."),
    "week_overall": ("Week overall", "المعدل الأسبوعي"),
    "avg_taste": ("Average taste", "متوسط المذاق"),
    "avg_cleanliness": ("Average cleanliness", "متوسط النظافة"),
    "responses": ("Responses", "عدد التقييمات"),
    "daily_average": ("Daily average", "المتوسط اليومي"),
    "no_ratings": ("No ratings yet.", "لا توجد تقييمات بعد."),
    "all_days": ("All days", "كل الأيام"),
    "filter_day": ("Filter day", "تصفية حسب اليوم"),
    "download_csv": ("Download CSV", "تنزيل ملف CSV"),
    "date": ("Date", "التاريخ"),
    "english_fields": ("English menu", "القائمة بالإنجليزية"),
    "arabic_fields": ("Arabic menu", "القائمة بالعربية"),
    "main_dish": ("Main dish", "الطبق الرئيسي"),
    "side_dish": ("Side dish", "الطبق الجانبي"),
    "salad": ("Salad", "السلطة"),
    "dessert": ("Dessert / extra", "الحلوى / إضافة"),
    "notes": ("Notes", "ملاحظات"),
    "save_menu": ("Save menu", "حفظ القائمة"),
    "main_required": (
        "Enter the main dish in at least one language.",
        "أدخل الطبق الرئيسي بلغة واحدة على الأقل.",
    ),
    "menu_saved": ("Menu saved.", "تم حفظ القائمة."),
    "profile": ("Profile", "الملف الشخصي"),
    "rename_profile": ("Rename profile", "تغيير اسم الملف الشخصي"),
    "save_profile": ("Save profile name", "حفظ اسم الملف الشخصي"),
    "empty_name": ("Profile name cannot be empty.", "لا يمكن أن يكون الاسم فارغاً."),
    "profile_updated": ("Profile updated.", "تم تحديث الملف الشخصي."),
    "name_exists": ("That name already exists.", "هذا الاسم موجود مسبقاً."),
}

AR_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
AR_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]
AR_COLUMNS = {
    "Date": "التاريخ",
    "User": "المستخدم",
    "Responses": "عدد التقييمات",
    "Food choice": "اختيار الوجبة",
    "Taste": "المذاق",
    "Cleanliness": "النظافة",
    "Service": "الخدمة",
    "Overall": "المعدل العام",
    "Comment": "التعليق",
}

st.markdown("""
<style>
:root { --radius: 18px; }
.block-container {
  max-width: 1120px;
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}
[data-testid="stSidebar"] { min-width: 280px; }
.hero {
  padding: 1.1rem 1.2rem;
  border: 1px solid rgba(128,128,128,.18);
  border-radius: 22px;
  margin-bottom: 1rem;
}
.st-key-profile_grid button {
  min-height: 64px;
  border-radius: 16px !important;
  font-weight: 650 !important;
}
@media (max-width: 640px) {
  .st-key-profile_grid [data-testid="stButton"] {
    flex: 1 0 100% !important;
    width: 100% !important;
  }
  .st-key-profile_grid [data-testid="stButton"] button {
    width: 100% !important;
  }
}
.small-note { opacity: .72; font-size: .9rem; }
div[data-testid="stMetric"] {
  border: 1px solid rgba(128,128,128,.18);
  padding: 12px;
  border-radius: 14px;
}
hr { margin-top: .75rem; margin-bottom: .75rem; }
</style>
""", unsafe_allow_html=True)

for key, value in {
    "user_id": None,
    "user_name": None,
    "admin_ok": False,
    "site_authenticated": False,
    "language": "English",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

language = st.selectbox("Language / اللغة", ["English", "العربية"], key="language")
is_ar = language == "العربية"


def tr(key):
    return STRINGS[key][1 if is_ar else 0]


if is_ar:
    st.markdown("""
    <style>
    .block-container { direction: rtl; text-align: right; }
    .block-container input, .block-container textarea { direction: rtl; text-align: right; }
    .block-container button, .block-container label, .block-container p,
    .block-container h1, .block-container h2, .block-container h3,
    .block-container h4 { text-align: right; }
    [data-testid="stFeedback"] { direction: ltr; }
    </style>
    """, unsafe_allow_html=True)


def render_hero():
    direction = "rtl" if is_ar else "ltr"
    st.markdown(
        f"""
        <div class="hero" dir="{direction}">
          <h2 style="margin:0;">🍽️ {tr('hero_title')}</h2>
          <div class="small-note">{tr('hero_subtitle')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if not st.session_state.site_authenticated:
    render_hero()
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.subheader(tr("access_title"))
        st.caption(tr("access_help"))

        if not SITE_ACCESS_CODE:
            st.error(tr("access_not_configured"))
        else:
            with st.form("site_access_form", clear_on_submit=True):
                supplied_code = st.text_input(tr("access_code"), type="password")
                submitted = st.form_submit_button(tr("enter_site"), use_container_width=True)

            if submitted:
                if hmac.compare_digest(supplied_code, SITE_ACCESS_CODE):
                    st.session_state.site_authenticated = True
                    st.rerun()
                else:
                    st.error(tr("wrong_access_code"))
    st.stop()

logout_column = st.columns([5, 1])[1]
with logout_column:
    if st.button(tr("logout"), use_container_width=True):
        st.session_state.site_authenticated = False
        st.session_state.admin_ok = False
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.rerun()


def monday(day):
    return day - timedelta(days=day.weekday())


def day_label(day):
    if is_ar:
        return f"{AR_WEEKDAYS[day.weekday()]}، {day.day} {AR_MONTHS[day.month - 1]}"
    return day.strftime("%A, %d %B")


def week_label(start, end):
    if is_ar:
        return f"{start.day} {AR_MONTHS[start.month - 1]} – {end.day} {AR_MONTHS[end.month - 1]} {end.year}"
    return f"{start.strftime('%d %B')} – {end.strftime('%d %B %Y')}"


def menu_value(item, key):
    """Use the selected language, falling back to the other when blank."""
    if not item:
        return ""
    if is_ar:
        return item.get(f"{key}_ar") or item.get(key) or ""
    return item.get(key) or item.get(f"{key}_ar") or ""


try:
    init_db()
except Exception:
    st.error(tr("db_error"))
    st.info(tr("db_help"))
    st.stop()

today = datetime.now(APP_TIMEZONE).date()
week_start = monday(today)
week_end = week_start + timedelta(days=6)
weekly_menu = menu_between(week_start, week_end)

render_hero()

tabs = st.tabs([
    tr("tab_profile"),
    tr("tab_menu"),
    tr("tab_rate"),
    tr("tab_admin"),
])

# ---------------- Profile ----------------
with tabs[0]:
    st.subheader(tr("choose_profile"))
    st.caption(tr("profile_help"))

    # Keep the original profile-slot order even after names are edited. A
    # wrapping horizontal container preserves that same sequence on mobile;
    # unlike st.columns, it never groups every fourth profile together.
    all_users = sorted(users(), key=lambda row: row["id"])
    with st.container(
        key="profile_grid",
        horizontal=True,
        wrap=True,
        horizontal_alignment="center",
        gap="small",
    ):
        for row in all_users:
            prefix = "✓" if st.session_state.user_id == row["id"] else "👤"
            if st.button(
                f"{prefix} {row['name']}",
                key=f"profile_{row['id']}",
                width=220,
            ):
                st.session_state.user_id = row["id"]
                st.session_state.user_name = row["name"]
                st.rerun()

    if st.session_state.user_id:
        st.success(f"{tr('current_profile')}: **{st.session_state.user_name}**")

# ---------------- Weekly menu ----------------
with tabs[1]:
    left, right = st.columns([3, 1])
    with left:
        st.subheader(tr("weekly_menu"))
        st.caption(week_label(week_start, week_end))
    with right:
        if st.session_state.user_name:
            st.info(f"👤 {st.session_state.user_name}")

    for offset in range(7):
        menu_day = week_start + timedelta(days=offset)
        item = weekly_menu.get(menu_day.isoformat())
        with st.container(border=True):
            badge = f" • 🟢 {tr('today')}" if menu_day == today else ""
            st.markdown(f"**{day_label(menu_day)}{badge}**")
            if item:
                st.markdown(f"### {menu_value(item, 'main_dish')}")
                details = [
                    ("🍚", menu_value(item, "side_dish")),
                    ("🥗", menu_value(item, "salad")),
                    ("🍰", menu_value(item, "dessert")),
                ]
                details = [f"{icon} {value}" for icon, value in details if value]
                if details:
                    st.caption(" • ".join(details))
                notes = menu_value(item, "notes")
                if notes:
                    st.caption(notes)
            else:
                st.caption(tr("menu_missing"))

# ---------------- Rate today ----------------
with tabs[2]:
    st.subheader(tr("rate_title"))

    if not st.session_state.user_id:
        st.warning(tr("choose_first"))
    else:
        today_menu = weekly_menu.get(today.isoformat())
        if today_menu:
            st.markdown(f"### {menu_value(today_menu, 'main_dish')}")
            details = [
                menu_value(today_menu, "side_dish"),
                menu_value(today_menu, "salad"),
                menu_value(today_menu, "dessert"),
            ]
            details = [value for value in details if value]
            if details:
                st.caption(" • ".join(details))
        else:
            st.info(tr("today_missing"))

        old_rating = rating_for(st.session_state.user_id, today.isoformat())
        if old_rating:
            st.info(tr("already_rated"))

        st.caption(tr("rating_scale"))
        form_key = f"rating_{st.session_state.user_id}_{today.isoformat()}"
        with st.form(form_key):
            left, right = st.columns(2)
            with left:
                st.markdown(f"**{tr('food_choice')}**")
                choice = st.feedback("stars", key=f"choice_{form_key}")
                st.markdown(f"**{tr('taste')}**")
                taste = st.feedback("stars", key=f"taste_{form_key}")
            with right:
                st.markdown(f"**{tr('cleanliness')}**")
                clean = st.feedback("stars", key=f"clean_{form_key}")
                st.markdown(f"**{tr('service')}**")
                service = st.feedback("stars", key=f"service_{form_key}")

            comment = st.text_area(
                tr("comment"),
                value=old_rating["comment"] if old_rating and old_rating.get("comment") else "",
                placeholder=tr("comment_placeholder"),
                max_chars=500,
                key=f"comment_{form_key}",
            )

            if st.form_submit_button(tr("submit_rating"), use_container_width=True):
                values = [choice, taste, clean, service]
                if any(value is None for value in values):
                    st.error(tr("rate_all"))
                else:
                    save_rating(
                        st.session_state.user_id,
                        today.isoformat(),
                        [value + 1 for value in values],
                        comment.strip(),
                    )
                    st.success(tr("rating_saved"))

# ---------------- Admin ----------------
with tabs[3]:
    st.subheader(tr("admin_title"))

    if not st.session_state.admin_ok:
        if not ADMIN_PIN:
            st.error(tr("admin_not_configured"))
        else:
            pin = st.text_input(tr("admin_pin"), type="password", key="admin_pin")
            if st.button(tr("unlock")):
                if hmac.compare_digest(pin, ADMIN_PIN):
                    st.session_state.admin_ok = True
                    st.rerun()
                else:
                    st.error(tr("wrong_pin"))
            st.caption(tr("pin_private"))
    else:
        st.success(tr("admin_active"))
        if st.button(tr("lock")):
            st.session_state.admin_ok = False
            st.rerun()

        admin_tabs = st.tabs([
            tr("overview"),
            tr("daily_details"),
            tr("menu_editor"),
            tr("profiles"),
        ])

        with admin_tabs[0]:
            selected_week = st.date_input(tr("week_containing"), value=today, key="overview_week")
            start = monday(selected_week)
            end = start + timedelta(days=6)
            stats = stats_between(start, end)

            if stats.empty:
                st.info(tr("no_week_ratings"))
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(tr("week_overall"), f"{stats['Overall'].mean():.2f}/5")
                m2.metric(tr("avg_taste"), f"{stats['Taste'].mean():.2f}/5")
                m3.metric(tr("avg_cleanliness"), f"{stats['Cleanliness'].mean():.2f}/5")
                m4.metric(tr("responses"), int(stats["Responses"].sum()))

                st.markdown(f"#### {tr('daily_average')}")
                chart = stats.set_index("Date")[["Overall", "Taste", "Cleanliness", "Service", "Food choice"]]
                if is_ar:
                    chart = chart.rename(columns=AR_COLUMNS)
                st.line_chart(chart)

                display_stats = stats.rename(columns=AR_COLUMNS) if is_ar else stats
                st.dataframe(display_stats, use_container_width=True, hide_index=True)

        with admin_tabs[1]:
            selected_week = st.date_input(tr("week_containing"), value=today, key="detail_week")
            start = monday(selected_week)
            end = start + timedelta(days=6)
            details = individuals_between(start, end)

            if details.empty:
                st.info(tr("no_ratings"))
            else:
                day_options = [None] + sorted(details["Date"].unique().tolist(), reverse=True)
                day_filter = st.selectbox(
                    tr("filter_day"),
                    day_options,
                    format_func=lambda value: tr("all_days") if value is None else value,
                )
                shown = details if day_filter is None else details[details["Date"] == day_filter]
                export_data = shown.rename(columns=AR_COLUMNS) if is_ar else shown
                st.dataframe(export_data, use_container_width=True, hide_index=True)

                st.download_button(
                    tr("download_csv"),
                    export_data.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"ratings_{start}_{end}.csv",
                    mime="text/csv",
                )

        with admin_tabs[2]:
            menu_date = st.date_input(tr("date"), value=today, key="menu_editor_date")
            existing = menu_between(monday(menu_date), monday(menu_date) + timedelta(days=6)).get(
                menu_date.isoformat(), {}
            )

            with st.form(f"menu_editor_{menu_date.isoformat()}"):
                language_tabs = st.tabs([tr("english_fields"), tr("arabic_fields")])
                with language_tabs[0]:
                    main = st.text_input("Main dish", value=existing.get("main_dish") or "", key=f"main_en_{menu_date}")
                    side = st.text_input("Side dish", value=existing.get("side_dish") or "", key=f"side_en_{menu_date}")
                    salad = st.text_input("Salad", value=existing.get("salad") or "", key=f"salad_en_{menu_date}")
                    dessert = st.text_input("Dessert / extra", value=existing.get("dessert") or "", key=f"dessert_en_{menu_date}")
                    notes = st.text_area("Notes", value=existing.get("notes") or "", key=f"notes_en_{menu_date}")

                with language_tabs[1]:
                    main_ar = st.text_input("الطبق الرئيسي", value=existing.get("main_dish_ar") or "", key=f"main_ar_{menu_date}")
                    side_ar = st.text_input("الطبق الجانبي", value=existing.get("side_dish_ar") or "", key=f"side_ar_{menu_date}")
                    salad_ar = st.text_input("السلطة", value=existing.get("salad_ar") or "", key=f"salad_ar_{menu_date}")
                    dessert_ar = st.text_input("الحلوى / إضافة", value=existing.get("dessert_ar") or "", key=f"dessert_ar_{menu_date}")
                    notes_ar = st.text_area("ملاحظات", value=existing.get("notes_ar") or "", key=f"notes_ar_{menu_date}")

                if st.form_submit_button(tr("save_menu"), use_container_width=True):
                    if not main.strip() and not main_ar.strip():
                        st.error(tr("main_required"))
                    else:
                        save_menu(
                            menu_date.isoformat(),
                            main.strip(), side.strip(), salad.strip(), dessert.strip(), notes.strip(),
                            main_ar.strip(), side_ar.strip(), salad_ar.strip(), dessert_ar.strip(), notes_ar.strip(),
                        )
                        st.success(tr("menu_saved"))

        with admin_tabs[3]:
            current_users = users()
            name_to_id = {row["name"]: row["id"] for row in current_users}
            selected_name = st.selectbox(tr("profile"), list(name_to_id))
            selected_id = name_to_id[selected_name]
            new_name = st.text_input(
                tr("rename_profile"),
                value=selected_name,
                max_chars=100,
                key=f"profile_name_{selected_id}",
            )
            if st.button(tr("save_profile")):
                if not new_name.strip():
                    st.error(tr("empty_name"))
                else:
                    try:
                        rename_profile(selected_id, new_name)
                        if st.session_state.user_id == selected_id:
                            st.session_state.user_name = new_name.strip()
                        st.success(tr("profile_updated"))
                        st.rerun()
                    except IntegrityError:
                        st.error(tr("name_exists"))
