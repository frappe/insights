#!/usr/bin/env bash
set -euo pipefail

PREV_TAG="${1:-}"
REPO="${2:-}"

LATEST_TAG=$(gh release list --limit 1 --json tagName --jq '.[0].tagName // ""')

if [ -z "$LATEST_TAG" ] || [ "$PREV_TAG" = "$LATEST_TAG" ]; then
  echo "No new release created, skipping."
  exit 0
fi

if [ -z "$PREV_TAG" ]; then
  PREV_TAG=$(git rev-list --max-parents=0 HEAD | head -1)
fi

FEATURES=""
FIXES=""
FEAT_RE='^feat(\([^)]*\))?[!]?:'
FIX_RE='^fix(\([^)]*\))?[!]?:'

while IFS= read -r line; do
  SUBJECT=$(echo "$line" | jq -r '.subject')
  LOGIN=$(echo "$line" | jq -r '.login')

  if [[ "$SUBJECT" =~ $FEAT_RE ]]; then
    FEATURES="${FEATURES}- ${SUBJECT} (@${LOGIN})"$'\n'
  elif [[ "$SUBJECT" =~ $FIX_RE ]]; then
    FIXES="${FIXES}- ${SUBJECT} (@${LOGIN})"$'\n'
  fi
done < <(gh api "/repos/${REPO}/compare/${PREV_TAG}...${LATEST_TAG}" \
  | jq -c '.commits[] | {subject: (.commit.message | split("\n")[0]), login: (.author.login // .commit.author.name)}')

BODY=""
if [ -n "$FEATURES" ]; then
  BODY="## Features"$'\n'"${FEATURES}"
fi
if [ -n "$FIXES" ]; then
  [ -n "$BODY" ] && BODY="${BODY}"$'\n'
  BODY="${BODY}## Bug Fixes"$'\n'"${FIXES}"
fi

if [ -n "$BODY" ]; then
  printf '%s' "${BODY}" | gh release edit "${LATEST_TAG}" --notes-file -
else
  echo "No feat/fix commits found."
fi
