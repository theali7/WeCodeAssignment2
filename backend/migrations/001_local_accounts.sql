CREATE SCHEMA IF NOT EXISTS wecode_private;
CREATE TABLE wecode_private.users (
 id uuid PRIMARY KEY, email text NOT NULL UNIQUE,
 password_hash text NOT NULL, display_name text NOT NULL DEFAULT '',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wecode_private.sessions (
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES wecode_private.users(id) ON DELETE CASCADE,
 refresh_hash text NOT NULL UNIQUE, expires_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_user_id_idx ON wecode_private.sessions(user_id);
CREATE TABLE profiles (
 id uuid PRIMARY KEY REFERENCES wecode_private.users(id) ON DELETE CASCADE,
 display_name text NOT NULL DEFAULT '' CHECK(length(display_name)<=80),
 path_id text CHECK(path_id IN ('front','back','java','python','sql')),
 level smallint NOT NULL DEFAULT 0 CHECK(level BETWEEN 0 AND 2)
);
CREATE TABLE lessons (
 id uuid PRIMARY KEY, path_id text NOT NULL, slug text NOT NULL UNIQUE,
 title_en text NOT NULL, content_en text NOT NULL DEFAULT '',
 title_ru text NOT NULL DEFAULT '', content_ru text NOT NULL DEFAULT '',
 position integer NOT NULL CHECK(position>=0), published boolean NOT NULL DEFAULT false
);
CREATE TABLE lesson_progress (
 user_id uuid NOT NULL REFERENCES wecode_private.users(id) ON DELETE CASCADE,
 lesson_id uuid NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 completed boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id,lesson_id)
);
CREATE TABLE learning_way_progress (
 user_id uuid NOT NULL REFERENCES wecode_private.users(id) ON DELETE CASCADE,
 item_id text NOT NULL CHECK(length(item_id) BETWEEN 1 AND 200),
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(user_id,item_id)
);
REVOKE ALL ON SCHEMA wecode_private FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
