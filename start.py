import os
import uvicorn

# Import the complete runtime patch chain before Uvicorn resolves the app.
import pachymetry_policy  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("pachymetry_policy:app", host="0.0.0.0", port=port)
