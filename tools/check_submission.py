"""Check the form of your result files before you push.

    python tools/check_submission.py          (from the top folder of your repository)

This runs the same format and consistency checks as the autograder that runs
on every push. It does not tell you whether your numbers are right: their
accuracy is checked separately by the course staff, who report back in an
issue of your repository. Do not edit msi_checks.py or members.json; the
autograder uses its own copies.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import msi_checks as pub    # noqa: E402


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    read, listdir = pub.local_reader(root)
    checks = pub.run_checks(pub.Submission(read), listdir)
    print(pub.render(checks))
    return 0 if all(c.passed for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
