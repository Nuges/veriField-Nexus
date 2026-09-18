import sys


def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else "pytest_output.txt"
    try:
        with open(log_file) as f:
            text = f.read()
    except Exception as e:
        print(f"::error file=backend/tests/conftest.py,line=1::Failed to read {log_file}: {e}")
        return

    lines = text.splitlines()
    failures = [l for l in lines if l.startswith("FAILED ") or l.startswith("ERROR ")]
    for l in failures:
        print(f"::error file=backend/tests/conftest.py,line=1::{l}")

    in_failure = False
    tb_lines = []
    for l in lines:
        if "=== FAILURES ===" in l or "=== ERRORS ===" in l:
            in_failure = True
            continue
        if in_failure and ("=== short test summary info ===" in l or l.startswith("=====")):
            in_failure = False
        if in_failure and len(tb_lines) < 30:
            tb_lines.append(l)

    for l in tb_lines:
        if l.strip():
            print(f"::warning file=backend/tests/conftest.py,line=1::{l}")

    if not failures and not tb_lines:
        for l in lines[-30:]:
            if l.strip():
                print(f"::error file=backend/tests/conftest.py,line=1::{l}")


if __name__ == "__main__":
    main()
