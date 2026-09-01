"""Generate a CER-AI named-user password hash without putting the password in shell history."""

from getpass import getpass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from user_access import hash_password


def main() -> None:
    first = getpass("New CER-AI account password: ")
    second = getpass("Repeat password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    print(hash_password(first))


if __name__ == "__main__":
    main()
