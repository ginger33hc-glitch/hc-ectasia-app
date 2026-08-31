"""Generate a CER-AI named-user password hash without putting the password in shell history."""

from getpass import getpass

from user_access import hash_password


def main() -> None:
    first = getpass("New CER-AI account password: ")
    second = getpass("Repeat password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    print(hash_password(first))


if __name__ == "__main__":
    main()
