# Daily Table — PostgreSQL edition

A mobile-friendly Streamlit website for a small catering service. This edition
stores profiles, menus, ratings, and comments in PostgreSQL so the data survives
app restarts and deployments.

## Features

- 20 clickable user profiles with no user password
- full weekly menu, with today highlighted
- 1–5 star ratings for food choice, taste, cleanliness, and service
- optional comments (maximum 500 characters)
- one rating per user per day; re-submitting updates it safely
- PIN-protected admin dashboard
- daily and weekly averages, category breakdowns, and individual ratings
- CSV export, menu editor, and profile renaming

## 1. Create a PostgreSQL database

Use any hosted PostgreSQL provider. Create a project/database and copy its
connection string. For a deployed app, use the provider's pooled connection
string when one is available.

The connection string normally looks like:

```text
postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

If the password contains characters such as `@`, `:`, `/`, `#`, or `%`, use the
URL-encoded password supplied by your provider.

You do **not** have to create the tables manually. The app creates the schema,
index, and 20 placeholder profiles on its first successful connection.

## 2. Run locally

Create `.streamlit/secrets.toml` from the included example:

```toml
DATABASE_URL = "postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE?sslmode=require"
ADMIN_PIN = "choose-a-private-pin"
```

Do not upload the real `secrets.toml` file to GitHub. Then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows PowerShell can use environment variables instead:

```powershell
$env:DATABASE_URL="postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE?sslmode=require"
$env:ADMIN_PIN="choose-a-private-pin"
streamlit run app.py
```

## 3. Deploy on Streamlit Community Cloud

1. Put these project files in a GitHub repository.
2. In Streamlit Community Cloud, create an app from the repository and select
   `app.py` as the entry point.
3. Open **App settings → Secrets** and paste:

   ```toml
   DATABASE_URL = "postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE?sslmode=require"
   ADMIN_PIN = "choose-a-private-pin"
   ```

4. Deploy, open the app, and test one rating from a phone.
5. Open Admin and confirm that the rating appears in both the daily details and
   weekly overview.

Never put `DATABASE_URL` or the real admin PIN directly in `app.py` or commit
them to GitHub.

## Database behavior

`database.py` uses SQLAlchemy connection pooling with PostgreSQL's psycopg 3
driver. Transactions protect menu edits, profile renames, and ratings. A unique
database constraint guarantees that one user has at most one rating per day,
even when several people submit at the same time.

The application accepts connection strings starting with `postgresql://`,
`postgres://`, or `postgresql+psycopg://`.

## Files

- `app.py` — Streamlit interface
- `database.py` — PostgreSQL schema and all database operations
- `requirements.txt` — Python dependencies
- `.streamlit/config.toml` — Streamlit theme/server settings
- `.streamlit/secrets.toml.example` — safe configuration template
- `schema.sql` — optional manual schema reference

## Important note about the previous SQLite edition

This version starts with a new PostgreSQL database. Existing test data in a
local `catering.db` file is not uploaded automatically. Keep that file private
if it contains names or comments.
