"""Explicit disposable-CI database fixtures; never run against production."""
import os
import psycopg

if os.environ.get("WECODE_DISPOSABLE_E2E") != "yes":
    raise SystemExit("Set WECODE_DISPOSABLE_E2E=yes only for a disposable test database")

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    for index, language in enumerate(("java", "python", "sql"), 1):
        conn.execute(
            "INSERT INTO lessons (id,path_id,slug,title_en,content_en,position,published) "
            "VALUES (%s,%s,%s,%s,%s,%s,true) ON CONFLICT (id) DO NOTHING",
            (f"00000000-0000-4000-8000-{index:012d}", language,
             f"e2e-{language}-lesson", f"E2E {language.title()} foundations",
             "A disposable lesson for browser tests.\n\n```text\nhello WeCode\n```", index),
        )
    conn.execute(
        "INSERT INTO lessons (id,path_id,slug,title_en,content_en,position,published) "
        "VALUES ('00000000-0000-4000-8000-000000000004','python','e2e-python-practice',"
        "'E2E Python practice','Practice this example.',4,true) ON CONFLICT (id) DO NOTHING"
    )
