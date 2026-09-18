import os
import sys


def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else "pytest_output.txt"
    try:
        with open(log_file) as f:
            text = f.read()
    except Exception as e:
        print(f"::error::Failed to read {log_file}: {e}")
        return

    lines = text.splitlines()
    failures = [l for l in lines if l.startswith("FAILED ") or l.startswith("ERROR ")]
    for l in failures:
        print(f"::error::{l}")
        print(f"::error file=.github/workflows/ci.yml,line=1::{l}")

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
            print(f"::warning::{l}")
            print(f"::warning file=.github/workflows/ci.yml,line=1::{l}")

    if not failures and not tb_lines:
        for l in lines[-30:]:
            if l.strip():
                print(f"::error::{l}")
                print(f"::error file=.github/workflows/ci.yml,line=1::{l}")

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        try:
            with open(summary_file, "a") as f:
                f.write("### Pytest Failure Details\n\n```\n")
                if failures:
                    f.write("\n".join(failures) + "\n\n")
                if tb_lines:
                    f.write("\n".join(tb_lines) + "\n")
                if not failures and not tb_lines:
                    f.write("\n".join(lines[-30:]) + "\n")
                f.write("```\n")
        except Exception:
            pass


if __name__ == "__main__":
    main()
