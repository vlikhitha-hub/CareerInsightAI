from pathlib import Path
import sys
import os

# This launcher is for local HTTP development (including LAN IP access).
# Secure cookies are enabled by default for production HTTPS, but would be
# rejected by browsers over plain HTTP, preventing CSRF/session cookies from working.
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[str(root / "backend")])
