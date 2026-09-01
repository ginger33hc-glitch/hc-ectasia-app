"""Generate a 32-byte base64 CER-AI research pseudonym secret."""

import base64
import os


if __name__ == "__main__":
    print(base64.b64encode(os.urandom(32)).decode("ascii"))
