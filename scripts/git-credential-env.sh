#!/bin/sh
# Git credential helper for the headless (scheduled, non-interactive) context.
#
# Supplies a GitHub fine-grained PAT from the GITHUB_TOKEN environment variable
# (loaded from the gitignored .env by the routine wrappers). The token is NEVER
# written to .git/config — only this script's path is. .git/config is not
# committed; this script is, and it contains no secret.
#
# Stays SILENT (exit 0, no output) for store/erase and when GITHUB_TOKEN is
# unset, so git falls through to the next configured helper ('manager') for
# ordinary interactive use. Only acts on `get`, and only when a token exists.
[ "$1" = "get" ] || exit 0
[ -n "$GITHUB_TOKEN" ] || exit 0
echo "username=x-access-token"
echo "password=$GITHUB_TOKEN"
