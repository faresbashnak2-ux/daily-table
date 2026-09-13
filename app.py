
from datetime import date, timedelta
import streamlit as st

from database import (
    IntegrityError,
    delete_rating,
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

    import os
    return os.getenv(name, default)


st.set_page_config(
    page_title="Daily Table",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ADMIN_PIN = setting("ADMIN_PIN", "1234")

st.markdown("""
<style>
:root {
  --radius: 18px;
}
.block-container {
  max-width: 1120px;
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}
[data-testid="stSidebar"] {
  min-width: 280px;
}
.hero {
  padding: 1.1rem 1.2rem;
  border: 1px solid rgba(128,128,128,.18);
  border-radius: 22px;
  margin-bottom: 1rem;
}
.day-card {
  border: 1px solid rgba(128,128,128,.18);
  border-radius: var(--radius);
  padding: 16px 18px;
  margin-bottom: 12px;
}
.today-card {
  border: 2px solid rgba(46,125,50,.8);
  border-radius: var(--radius);
  padding: 16px 18px;
  margin-bottom: 12px;
}
.profile-card button {
  min-height: 64px;
  border-radius: 16px !important;
  font-weight: 650 !important;
}
.small-note {opacity: .72; font-size: .9rem;}
.pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(128,128,128,.25);
  margin-right: 6px;
  margin-top: 4px;
  font-size: .85rem;
}
div[data-testid="stMetric"] {
  border: 1px solid rgba(128,128,128,.18);
  padding: 12px;
  border-radius: 14px;
}
hr {margin-top: .75rem; margin-bottom: .75rem;}
</style>
""", unsafe_allow_html=True)

def monday(d):
    return d - timedelta(days=d.weekday())

try:
    init_db()
except Exception:
    st.error("The app could not connect to PostgreSQL.")
    st.info("Add DATABASE_URL to Streamlit Secrets, then restart the app. See README.md for the exact format.")
    st.stop()

# ---------------- State ----------------

for k, v in {"user_id": None, "user_name": None, "admin_ok": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

today = date.today()
week_start = monday(today)
week_end = week_start + timedelta(days=6)

# ---------------- Header/nav ----------------

st.markdown("""
<div class="hero">
  <h2 style="margin:0;">🍽️ Daily Table</h2>
  <div class="small-note">Weekly menu • Daily feedback • Better meals over time</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["👤 Profile", "📅 Weekly menu", "⭐ Rate today", "📊 Admin"])

# ---------------- Profile ----------------
with tabs[0]:
    st.subheader("Choose your profile")
    st.caption("Tap your name. No password or verification is required.")

    all_users = users()
    cols = st.columns(4)
    for i, row in enumerate(all_users):
        with cols[i % 4]:
            st.markdown('<div class="profile-card">', unsafe_allow_html=True)
            label = f"✓ {row['name']}" if st.session_state.user_id == row["id"] else f"👤 {row['name']}"
            if st.button(label, key=f"profile_{row['id']}", use_container_width=True):
                st.session_state.user_id = row["id"]
                st.session_state.user_name = row["name"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.user_id:
        st.success(f"Current profile: **{st.session_state.user_name}**")

# ---------------- Weekly Menu ----------------
with tabs[1]:
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("This week's menu")
        st.caption(f"{week_start.strftime('%d %B')} – {week_end.strftime('%d %B %Y')}")
    with c2:
        if st.session_state.user_name:
            st.info(f"👤 {st.session_state.user_name}")

    wm = menu_between(week_start, week_end)
    for n in range(7):
        d = week_start + timedelta(days=n)
        item = wm.get(d.isoformat())
        klass = "today-card" if d == today else "day-card"
        badge = " • TODAY" if d == today else ""
        st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
        st.markdown(f"**{d.strftime('%A, %d %B')}{badge}**")
        if item:
            st.markdown(f"### {item['main_dish']}")
            pills = []
            if item.get("side_dish"): pills.append(f"🍚 {item['side_dish']}")
            if item.get("salad"): pills.append(f"🥗 {item['salad']}")
            if item.get("dessert"): pills.append(f"🍰 {item['dessert']}")
            if pills:
                st.markdown(" &nbsp; ".join([f"<span class='pill'>{p}</span>" for p in pills]), unsafe_allow_html=True)
            if item.get("notes"):
                st.caption(item["notes"])
        else:
            st.caption("Menu not entered yet.")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Rate Today ----------------
with tabs[2]:
    st.subheader("Rate today's experience")

    if not st.session_state.user_id:
        st.warning("Choose your profile first.")
    else:
        today_menu = wm.get(today.isoformat())
        if today_menu:
            st.markdown(f"### {today_menu['main_dish']}")
            bits = [today_menu.get("side_dish"), today_menu.get("salad"), today_menu.get("dessert")]
            bits = [b for b in bits if b]
            if bits:
                st.caption(" • ".join(bits))
        else:
            st.info("Today's menu has not been entered yet.")

        old = rating_for(st.session_state.user_id, today.isoformat())
        if old:
            st.info("You already rated today. A new submission will replace your previous rating.")

        st.caption("1 star = poor • 5 stars = excellent")

        with st.form("rating_form"):
            a, b = st.columns(2)
            with a:
                st.markdown("**Food choice**")
                choice = st.feedback("stars", key="choice")
                st.markdown("**Taste**")
                taste = st.feedback("stars", key="taste")
            with b:
                st.markdown("**Cleanliness**")
                clean = st.feedback("stars", key="clean")
                st.markdown("**Service**")
                service = st.feedback("stars", key="service")

            comment = st.text_area(
                "Comment (optional)",
                value=old["comment"] if old and old.get("comment") else "",
                placeholder="What was good? What should improve?",
                max_chars=500
            )

            if st.form_submit_button("Submit today's rating", use_container_width=True):
                vals = [choice, taste, clean, service]
                if any(v is None for v in vals):
                    st.error("Please rate all four categories.")
                else:
                    save_rating(
                        st.session_state.user_id,
                        today.isoformat(),
                        [v + 1 for v in vals],
                        comment.strip()
                    )
                    st.success("Thank you — your rating was saved.")

# ---------------- Admin ----------------
with tabs[3]:
    st.subheader("Admin dashboard")

    if not st.session_state.admin_ok:
        pin = st.text_input("Admin PIN", type="password", key="admin_pin")
        if st.button("Unlock admin", use_container_width=False):
            if pin == ADMIN_PIN:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Incorrect PIN.")
        st.caption("Development default: 1234. Change ADMIN_PIN before deployment.")
    else:
        st.success("Admin access active")
        if st.button("Lock admin"):
            st.session_state.admin_ok = False
            st.rerun()

        admin_tabs = st.tabs(["Overview", "Daily details", "Menu editor", "Profiles"])

        with admin_tabs[0]:
            week_pick = st.date_input("Week containing", value=today, key="overview_week")
            s = monday(week_pick)
            e = s + timedelta(days=6)
            stats = stats_between(s, e)

            if stats.empty:
                st.info("No ratings yet for this week.")
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Week overall", f"{stats['Overall'].mean():.2f}/5")
                m2.metric("Avg taste", f"{stats['Taste'].mean():.2f}/5")
                m3.metric("Avg cleanliness", f"{stats['Cleanliness'].mean():.2f}/5")
                m4.metric("Responses", int(stats["Responses"].sum()))

                st.markdown("#### Daily average")
                chart = stats.set_index("Date")[["Overall", "Taste", "Cleanliness", "Service", "Food choice"]]
                st.line_chart(chart)

                st.dataframe(stats, use_container_width=True, hide_index=True)

        with admin_tabs[1]:
            week_pick2 = st.date_input("Week containing", value=today, key="detail_week")
            s2 = monday(week_pick2)
            e2 = s2 + timedelta(days=6)
            details = individuals_between(s2, e2)

            if details.empty:
                st.info("No ratings yet.")
            else:
                day_options = ["All days"] + sorted(details["Date"].unique().tolist(), reverse=True)
                day_filter = st.selectbox("Filter day", day_options)
                shown = details if day_filter == "All days" else details[details["Date"] == day_filter]
                st.dataframe(shown, use_container_width=True, hide_index=True)

                st.download_button(
                    "Download CSV",
                    shown.to_csv(index=False).encode("utf-8"),
                    file_name=f"ratings_{s2}_{e2}.csv",
                    mime="text/csv"
                )

        with admin_tabs[2]:
            menu_date = st.date_input("Date", value=today, key="menu_editor_date")
            existing = menu_between(monday(menu_date), monday(menu_date)+timedelta(days=6)).get(menu_date.isoformat(), {})
            with st.form("menu_editor"):
                main = st.text_input("Main dish", value=existing.get("main_dish",""))
                side = st.text_input("Side dish", value=existing.get("side_dish",""))
                salad = st.text_input("Salad", value=existing.get("salad",""))
                dessert = st.text_input("Dessert / extra", value=existing.get("dessert",""))
                notes = st.text_area("Notes", value=existing.get("notes",""))
                if st.form_submit_button("Save menu", use_container_width=True):
                    if not main.strip():
                        st.error("Main dish is required.")
                    else:
                        save_menu(menu_date.isoformat(), main.strip(), side.strip(), salad.strip(), dessert.strip(), notes.strip())
                        st.success("Menu saved.")

        with admin_tabs[3]:
            current_users = users()
            name_to_id = {r["name"]: r["id"] for r in current_users}
            selected = st.selectbox("Profile", list(name_to_id))
            new_name = st.text_input("Rename profile", value=selected, max_chars=100)
            if st.button("Save profile name"):
                if not new_name.strip():
                    st.error("Profile name cannot be empty.")
                else:
                    try:
                        rename_profile(name_to_id[selected], new_name)
                        if st.session_state.user_id == name_to_id[selected]:
                            st.session_state.user_name = new_name.strip()
                        st.success("Profile updated.")
                        st.rerun()
                    except IntegrityError:
                        st.error("That name already exists.")
