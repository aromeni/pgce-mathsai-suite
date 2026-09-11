"""Generate an APP_PASSWORD_HASH value for deployment.

Run from `mathsai/backend` with the venv active:

    python generate_password_hash.py

Paste the printed line into the hosting platform's secret manager as
APP_PASSWORD_HASH. The password itself is read via getpass, so it never
appears in shell history, in a process listing, or in this repository.
"""

import getpass
import sys

from auth import MIN_PASSWORD_LENGTH, hash_password


def main() -> int:
    try:
        password = getpass.getpass("New MathsAI password: ")
        confirmation = getpass.getpass("Confirm password: ")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 1

    if password != confirmation:
        print("Passwords do not match — nothing generated.", file=sys.stderr)
        return 1

    # This single password is the only thing standing between a public URL
    # and an API key that bills per call, so a short one is not an option.
    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            file=sys.stderr,
        )
        return 1

    print("\nSet this as APP_PASSWORD_HASH (the value after the '=' sign):\n")
    print(f"APP_PASSWORD_HASH={hash_password(password)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
