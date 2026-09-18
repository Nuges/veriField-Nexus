import os
import sys


def main():
    log_file = sys.argv[1] if len(sys.argv) > 1 else "pytest_output.txt"
    github_output = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GITHUB_OUTPUT", "")

    try:
        with open(log_file) as f:
            text = f.read()
    except Exception as e:
        print(f"::error::Failed to read {log_file}: {e}")
        if github_output:
            try:
                with open(github_output, "a") as out:
                    out.write(f"fail1=Failed to read {log_file}: {e}\n")
            except Exception:
                pass
        return

    lines = text.splitlines()
    failures = [l.strip() for l in lines if l.startswith("FAILED ") or l.startswith("ERROR ")]
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
        if in_failure and l.strip():
            tb_lines.append(l.strip())

    for l in tb_lines:
        if l.strip():
            print(f"::warning::{l}")
            print(f"::warning file=.github/workflows/ci.yml,line=1::{l}")

    def sanitize(s):
        return s.replace('"', "").replace("'", "").replace("\n", " ").replace("\r", "")[:200]

    if github_output:
        try:
            with open(github_output, "a") as out:
                for i in range(5):
                    val = sanitize(failures[i]) if i < len(failures) else "none"
                    out.write(f"fail{i+1}={val}\n")
                for i in range(5):
                    val = sanitize(tb_lines[i]) if i < len(tb_lines) else "none"
                    out.write(f"tb{i+1}={val}\n")
                summary_line = sanitize(lines[-1] if lines else "empty")
                out.write(f"summary={summary_line}\n")
        except Exception as e:
            print(f"Error writing to GITHUB_OUTPUT: {e}")

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
