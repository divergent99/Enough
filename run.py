import os
import uvicorn

if __name__ == "__main__":
    # Reload locally so backend and cached frontend routes cannot drift apart.
    # Railway supplies PORT, which keeps production reload disabled by default.
    reload_default = "false" if os.getenv("PORT") else "true"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8770")),
        reload=os.getenv("RELOAD", reload_default).lower() == "true",
    )
