import os
import uvicorn

# Import runtime UI patch before Uvicorn resolves the cached bootstrap application.
import critical_score_highlight  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("critical_score_highlight:app", host="0.0.0.0", port=port)
