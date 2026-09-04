import os

import uvicorn

if __name__ == "__main__":
    # Render (and most PaaS) inject $PORT. Fall back to 8000 for local dev.
    port = int(os.environ.get("PORT", 8000))
    # Only auto-reload in local dev. APP_ENV=production disables it in prod.
    reload = os.environ.get("APP_ENV", "local") == "local"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)
