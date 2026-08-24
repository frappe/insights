#!/usr/bin/env python3
"""Build release notes for a tag, one entry per landed change.

The unit is the pull request, not the commit. Walking the first parent gives
exactly one commit per change whatever the merge strategy, and descending
through integration merges reaches the branch that carries the real work.
"""

import argparse
import json
import re
import subprocess
import sys

# A merge from one of these is an integration merge: descend into it. Any other
# merge is a pull request merged without a squash, and stands as one entry.
INTEGRATION_BRANCHES = {"develop", "main", "version-3", "version-3-hotfix"}

SECTIONS = [
    ("breaking", "Breaking Changes"),
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("perf", "Performance"),
]
RELEASED_TYPES = {"feat", "fix", "perf"}
KNOWN_TYPES = RELEASED_TYPES | {
    "build",
    "chore",
    "ci",
    "docs",
    "refactor",
    "revert",
    "style",
    "test",
    "patch",
    "deprecate",
}

CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*")
PR_SUFFIX_RE = re.compile(r"\s*\((?:backport\s*)?#(\d+)\)\s*$")
MERGE_PR_RE = re.compile(r"^Merge pull request #(\d+) from [^/\s]+/(?P<branch>\S+)")
MERGE_BRANCH_RE = re.compile(r"^Merge (?:remote-tracking )?branch '(?:[^/']*/)?(?P<branch>[^']+)'")
CHORE_MERGE_RE = re.compile(r"^chore: merge ['\"`]?(?P<branch>[\w.-]+)")
BACKPORT_RE = re.compile(r"automatic backport of pull request #(\d+)")
# A leading identifier keeps its case: get_list, frappe.db.x, `col`.
IDENTIFIER_RE = re.compile(r"""^[`'"]|^[a-z][\w.]*[_.]\w""")

_pr_cache: dict[int, dict] = {}


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def gh_json(path: str):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def is_integration_merge(subject: str) -> bool:
    for pattern in (MERGE_PR_RE, MERGE_BRANCH_RE, CHORE_MERGE_RE):
        match = pattern.match(subject)
        if match and match.group("branch").strip("/") in INTEGRATION_BRANCHES:
            return True
    return False


def walk(start: str, end: str, depth: int = 0):
    """Yield (sha, subject) for each landed change between two refs."""
    if depth > 4:
        return
    for sha in git("rev-list", "--first-parent", f"{start}..{end}"):
        parents = git("rev-list", "--parents", "-n", "1", sha)[0].split()[1:]
        subject = git("log", "-1", "--pretty=%s", sha)[0]
        if len(parents) == 2 and is_integration_merge(subject):
            yield from walk(parents[0], parents[1], depth + 1)
        else:
            yield sha, subject


def landing_pr(subject: str) -> int | None:
    match = MERGE_PR_RE.match(subject)
    if match:
        return int(match.group(1))
    match = PR_SUFFIX_RE.search(subject)
    return int(match.group(1)) if match else None


def fetch_pr(repo: str, number: int) -> dict | None:
    if number not in _pr_cache:
        data = gh_json(f"/repos/{repo}/pulls/{number}")
        if data is None:
            return None
        _pr_cache[number] = data
    return _pr_cache[number]


def unwrap_backport(repo: str, number: int) -> int:
    """A mergify backport credits the bot. Follow it to the PR a human opened."""
    seen = set()
    while number not in seen:
        seen.add(number)
        pr = fetch_pr(repo, number)
        if not pr:
            break
        match = BACKPORT_RE.search(pr.get("body") or "")
        if not match:
            break
        number = int(match.group(1))
    return number


def clean_title(title: str) -> tuple[str, str, bool]:
    """Return (type, display title, is_breaking)."""
    match = CONVENTIONAL_RE.match(title)
    kind = match.group("type") if match else ""
    breaking = bool(match and match.group("bang"))
    text = title[match.end() :] if match else title
    while PR_SUFFIX_RE.search(text):
        text = PR_SUFFIX_RE.sub("", text)
    text = text.strip().rstrip(":")
    if text and not IDENTIFIER_RE.match(text):
        text = text[:1].upper() + text[1:]
    return kind, text, breaking


def announced_before(repo: str, tag: str) -> tuple[set[int], set[str]]:
    """PR numbers and contributor logins already published, for deduping."""
    releases = gh_json(f"/repos/{repo}/releases?per_page=100") or []
    cutoff = next((r.get("created_at") for r in releases if r.get("tag_name") == tag), None)
    numbers, logins = set(), set()
    for release in releases:
        if release.get("tag_name") == tag:
            continue
        # Only what shipped before this tag. A later release is not history.
        if cutoff and (release.get("created_at") or "") >= cutoff:
            continue
        body = release.get("body") or ""
        numbers.update(int(n) for n in re.findall(r"#(\d+)", body))
        logins.update(re.findall(r"@([\w-]+(?:\[bot\])?)", body))
    return numbers, logins


def collect(repo: str, prev: str, tag: str, dedupe: bool):
    seen_prs, past_logins = announced_before(repo, tag) if dedupe else (set(), set())
    entries, in_release, announced, logins = [], set(), set(), []

    for sha, subject in walk(prev, tag):
        number = landing_pr(subject)
        if number is None:
            print(f"note: no pull request for {sha[:8]} {subject}", file=sys.stderr)
            title, author = subject, None
        else:
            number = unwrap_backport(repo, number)
            if number in in_release or number in seen_prs:
                continue
            in_release.add(number)
            pr = fetch_pr(repo, number)
            title = pr["title"] if pr else subject
            author = pr["user"]["login"] if pr else None

        kind, text, breaking = clean_title(title)
        subject_kind, _, subject_breaking = clean_title(subject)
        if kind not in KNOWN_TYPES:
            kind = subject_kind
        breaking = breaking or subject_breaking
        if kind not in RELEASED_TYPES:
            continue
        if number:
            announced.add(number)

        entries.append(
            {
                "section": "breaking" if breaking else kind,
                "text": text,
                "ref": f"#{number}" if number else sha[:8],
                "author": author,
            }
        )
        if author and author not in logins:
            logins.append(author)

    return entries, announced, logins, past_logins


def render(repo, prev, tag, entries, numbers, logins, past_logins) -> str:
    lines = []
    for key, heading in SECTIONS:
        rows = [e for e in entries if e["section"] == key]
        if not rows:
            continue
        lines.append(f"## {heading}")
        for row in rows:
            credit = f" by @{row['author']}" if row["author"] else ""
            lines.append(f"- {row['text']} ({row['ref']}){credit}")
        lines.append("")

    if not lines:
        return ""

    if logins:
        lines.append("## Contributors")
        lines.append(" ".join(f"@{login}" for login in logins))
        new = [login for login in logins if login not in past_logins]
        if new and past_logins:
            lines.append("")
            first = ", ".join(f"@{login}" for login in new)
            lines.append(f"First release for {first}. Thank you.")
        lines.append("")

    if prev:
        lines.append(f"**Full Changelog**: https://github.com/{repo}/compare/{prev}...{tag}")
    lines.append("")
    lines.append(f"<!-- prs: {','.join(str(n) for n in sorted(numbers))} -->")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--prev", default="")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--no-dedupe", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    prev = args.prev or git("rev-list", "--max-parents=0", args.tag)[-1]
    entries, numbers, logins, past_logins = collect(args.repo, prev, args.tag, not args.no_dedupe)
    body = render(args.repo, args.prev, args.tag, entries, numbers, logins, past_logins)
    if not body:
        print("note: nothing to announce", file=sys.stderr)
        return 0

    if args.publish:
        subprocess.run(
            ["gh", "release", "edit", args.tag, "--notes-file", "-"],
            input=body,
            text=True,
            check=True,
        )
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
