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
    # `support` and `other` have no label, and leave the type or area labels alone
    managed = set(STATUS.values())
    if result["type"] in TYPE:
        want.add(TYPE[result["type"]])
        managed |= set(TYPE.values())
    if result["area"] in AREA:
        want.add("area: " + result["area"])
        managed |= {"area: " + a for a in AREA}
    if result["suggestion"] in STATUS:
        want.add(STATUS[result["suggestion"]])
    return sorted(want - current), sorted((current & managed) - want)


def validate(result):
    if not isinstance(result, dict):
        sys.exit("result is not an object")
    if result.get("type") not in TYPE.keys() | {"support"}:
        sys.exit(f"unknown type: {result.get('type')}")
    if result.get("area") not in AREA | {"other"}:
        sys.exit(f"unknown area: {result.get('area')}")
    if result.get("suggestion") not in SUGGESTIONS:
        sys.exit(f"unknown suggestion: {result.get('suggestion')}")
    if not (result.get("duplicate_of") is None or type(result["duplicate_of"]) is int):
        sys.exit("duplicate_of is not an issue number")
    related = result.get("related") or []
    if not (isinstance(related, list) and all(type(n) is int for n in related)):
        sys.exit("related is not a list of issue numbers")
    for key in ("summary", "reason"):
        if not isinstance(result.get(key), str):
            sys.exit(f"{key} is not text")


def one_line(text, limit=600):
    return " ".join(text.split())[:limit]


def main():
    number, path = sys.argv[1], sys.argv[2]
    repo = os.environ["GITHUB_REPOSITORY"]
    result = json.load(open(path))
    validate(result)

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
            f"{one_line(result['summary'])}\n\n"
            f"**Suggestion:** {result['suggestion']}"
            + (f", duplicate of #{duplicate}" if duplicate else "")
            + f"\n\n{one_line(result['reason'])}\n\n"
            f"**Related:** {related}\n\n"
            f"**Labels:** added {', '.join(add) or 'none'}, removed {', '.join(remove) or 'none'}\n"
        )


main()
