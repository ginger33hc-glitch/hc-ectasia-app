import os
import uvicorn

# Single supported production composition point.
import canonical_engine  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("canonical_engine:app", host="0.0.0.0", port=port, server_header=False)
