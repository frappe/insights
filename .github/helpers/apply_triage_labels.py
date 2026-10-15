"""Turn an issue-triage result into labels and a job summary."""

import json
import os
import subprocess
import sys

TYPE = {
    "bug": "bug",
    "feature": "feature request",
    "ux": "ui/ux",
    "question": "question",
    "docs": "documentation",
}
AREA = {
    "alerts",
    "charts",
    "dashboard",
    "data-source",
    "data-store",
    "desk",
    "permissions",
    "query",
    "settings",
    "shared",
    "tooling",
    "upgrade",
    "workbook",
}
STATUS = {"needs-info": "needs info", "discussion": "needs discussion"}
SUGGESTIONS = {"fix", "backlog", "needs-info", "discussion", "close"}


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def labels(result, current):
    want = set()
    # `support` has no label, and leaves the type labels alone
    managed = set(STATUS.values())
    if result["type"] in TYPE:
        want.add(TYPE[result["type"]])
        managed |= set(TYPE.values())
    if result["area"] in AREA:
        want.add("area: " + result["area"])
    if result["suggestion"] in STATUS:
        want.add(STATUS[result["suggestion"]])
    stale = {l for l in current if l in managed or l.startswith("area: ")} - want
    return sorted(want - current), sorted(stale)


def main():
    number, path = sys.argv[1], sys.argv[2]
    repo = os.environ["GITHUB_REPOSITORY"]
    result = json.load(open(path))
    if result["type"] not in TYPE.keys() | {"support"}:
        sys.exit(f"unknown type: {result['type']}")
    if result["area"] not in AREA | {"other"}:
        sys.exit(f"unknown area: {result['area']}")
    if result["suggestion"] not in SUGGESTIONS:
        sys.exit(f"unknown suggestion: {result['suggestion']}")

    current = {
        l["name"] for l in json.loads(gh("issue", "view", number, "-R", repo, "--json", "labels"))["labels"]
    }
    add, remove = labels(result, current)
    if add or remove:
        args = ["issue", "edit", number, "-R", repo]
        if add:
            args += ["--add-label", ",".join(add)]
        if remove:
            args += ["--remove-label", ",".join(remove)]
        gh(*args)

    duplicate = result.get("duplicate_of")
    related = ", ".join(f"#{n}" for n in result.get("related") or []) or "none"
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(
            f"## Triage of #{number}\n\n"
            f"{result['summary']}\n\n"
            f"**Suggestion:** {result['suggestion']}"
            + (f", duplicate of #{duplicate}" if duplicate else "")
            + f"\n\n{result['reason']}\n\n"
            f"**Related:** {related}\n\n"
            f"**Labels:** added {', '.join(add) or 'none'}, removed {', '.join(remove) or 'none'}\n"
        )


main()
