#!/usr/bin/env python3
"""Build release notes for a tag from GitHub's own generated notes.

GitHub resolves commits to pull requests already, including inside a merge from
develop. What it cannot do is see past a mergify backport: the backport is its
own pull request, so it lands as a second entry credited to the bot. This
collapses each backport onto the pull request a human opened, and drops
anything an earlier release already announced.
"""

import argparse
import json
import re
import subprocess
import sys

SECTIONS = [
    ("breaking", "Breaking Changes"),
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("perf", "Performance"),
]
RELEASED_TYPES = {"feat", "fix", "perf"}

ENTRY_RE = re.compile(
    r"^\* (?P<title>.+) by @(?P<author>[\w.\[\]-]+) in "
    r"https://github\.com/[^/]+/[^/]+/pull/(?P<number>\d+)\s*$"
)
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*")
PR_SUFFIX_RE = re.compile(r"\s*\((?:backport\s*)?#(\d+)\)\s*$")
BACKPORT_TITLE_RE = re.compile(r"\(backport #(\d+)\)")
BACKPORT_BODY_RE = re.compile(r"automatic backport of pull request #(\d+)")
# A leading identifier keeps its case: get_list, frappe.db.x, `col`.
IDENTIFIER_RE = re.compile(r"""^[`'"]|^[a-z][\w.]*[_.]\w""")

_pr_cache: dict[int, dict] = {}


def gh_json(path: str, method: str = "GET", **fields):
    args = ["gh", "api", path]
    if method != "GET":
        args += ["-X", method]
    for key, value in fields.items():
        args += ["-f", f"{key}={value}"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return None
    return json.loads(result.stdout)


def fetch_pr(repo: str, number: int) -> dict | None:
    if number not in _pr_cache:
        data = gh_json(f"/repos/{repo}/pulls/{number}")
        if data is None:
            return None
        _pr_cache[number] = data
    return _pr_cache[number]


def generated_entries(repo: str, prev: str, tag: str) -> list[dict]:
    fields = {"tag_name": tag}
    if prev:
        fields["previous_tag_name"] = prev
    notes = gh_json(f"/repos/{repo}/releases/generate-notes", "POST", **fields)
    if not notes:
        return []
    entries = []
    for line in (notes.get("body") or "").splitlines():
        match = ENTRY_RE.match(line)
        if match:
            entries.append(
                {
                    "number": int(match.group("number")),
                    "title": match.group("title"),
                    "author": match.group("author"),
                }
            )
    return entries


def unwrap_backport(repo: str, entry: dict) -> dict:
    """A backport is credited to the bot. Follow it to the human's pull request."""
    match = BACKPORT_TITLE_RE.search(entry["title"])
    number = int(match.group(1)) if match else None
    if number is None and entry["author"].startswith("mergify"):
        pr = fetch_pr(repo, entry["number"])
        body_match = BACKPORT_BODY_RE.search((pr or {}).get("body") or "")
        number = int(body_match.group(1)) if body_match else None
    if number is None:
        return entry
    original = fetch_pr(repo, number)
    if not original:
        return entry
    return {
        "number": number,
        "title": original["title"],
        "author": original["user"]["login"],
    }


def commit_type(repo: str, number: int) -> str:
    """commitlint governs the commit subject. Some pull request titles skip it."""
    pr = fetch_pr(repo, number)
    sha = (pr or {}).get("merge_commit_sha")
    if not sha:
        return ""
    commit = gh_json(f"/repos/{repo}/commits/{sha}")
    subject = ((commit or {}).get("commit", {}).get("message") or "").split("\n")[0]
    match = CONVENTIONAL_RE.match(subject)
    return match.group("type") if match else ""


TYPE_WORDS = {
    "feat": ("feat", "feature"),
    "fix": ("fix", "fixes", "fixed"),
    "perf": ("perf",),
}


def strip_leading_type(text: str, kind: str) -> str:
    words = TYPE_WORDS.get(kind, ())
    first, _, rest = text.partition(" ")
    if rest and first.lower() in words:
        return rest[:1].upper() + rest[1:]
    return text


def clean_title(title: str) -> tuple[str, str, bool]:
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
    """Pull requests and contributors already published, for deduping."""
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
    seen, past_logins = announced_before(repo, tag) if dedupe else (set(), set())
    entries, in_release, announced, logins = [], set(), set(), []

    for raw in generated_entries(repo, prev, tag):
        entry = unwrap_backport(repo, raw)
        number = entry["number"]
        if number in in_release or number in seen:
            continue
        in_release.add(number)

        kind, text, breaking = clean_title(entry["title"])
        if not kind:
            # No prefix on the title, so the type comes from the commit. Such a
            # title often opens with the type as a word: "Fix German ...".
            kind = commit_type(repo, number)
            text = strip_leading_type(text, kind)
        if kind not in RELEASED_TYPES:
            continue

        announced.add(number)
        entries.append(
            {
                "section": "breaking" if breaking else kind,
                "text": text,
                "number": number,
                "author": entry["author"],
            }
        )
        if entry["author"] not in logins:
            logins.append(entry["author"])

    return entries, announced, logins, past_logins


def credit(login: str) -> str:
    """A link renders like a mention but does not notify. Old work stays quiet."""
    return f"[@{login}](https://github.com/{login})"


def render(repo, prev, tag, entries, numbers, logins, past_logins) -> str:
    lines = []
    for key, heading in SECTIONS:
        rows = [e for e in entries if e["section"] == key]
        if not rows:
            continue
        lines.append(f"## {heading}")
        for row in rows:
            lines.append(f"- {row['text']} (#{row['number']}) by {credit(row['author'])}")
        lines.append("")

    if not lines:
        return ""

    if logins:
        lines.append("## Contributors")
        lines.append(" ".join(credit(login) for login in logins))
        new = [login for login in logins if login not in past_logins]
        if new and past_logins:
            lines.append("")
            first = ", ".join(credit(n) for n in new)
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

    entries, numbers, logins, past_logins = collect(args.repo, args.prev, args.tag, not args.no_dedupe)
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
