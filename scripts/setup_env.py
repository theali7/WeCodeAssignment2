"""Create assignment-only local secrets once; never overwrite existing configuration."""
from pathlib import Path
import secrets

target = Path(__file__).resolve().parents[1] / ".env"
if target.exists():
    print(".env already exists; kept unchanged.")
else:
    try:
        with target.open("x") as stream:
            target.chmod(0o600)
            stream.write("POSTGRES_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
            stream.write("AUTH_SECRET=" + secrets.token_urlsafe(48) + "\n")
        print("Created .env with new local database and authentication secrets.")
    except Exception:
        raise
