#!/bin/bash

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 [--force] <worktree-path>"
    echo "Remove worktree and delete its associated branch"
    exit 1
fi

# Parse arguments
FORCE_FLAG=""
WORKTREE_PATH=""

if [ "$1" = "--force" ]; then
    FORCE_FLAG="--force"
    WORKTREE_PATH="$2"
    if [ -z "$WORKTREE_PATH" ]; then
        echo "Error: worktree path required after --force"
        exit 1
    fi
else
    WORKTREE_PATH="$1"
    if [ "$2" = "--force" ]; then
        FORCE_FLAG="--force"
    fi
fi

# Get the absolute path of the worktree
WORKTREE_ABS_PATH=$(realpath "$WORKTREE_PATH" 2>/dev/null || readlink -f "$WORKTREE_PATH" 2>/dev/null || echo "$WORKTREE_PATH")

# Get the branch name associated with the worktree
BRANCH_NAME=$(git worktree list --porcelain | awk -v path="$WORKTREE_ABS_PATH" '
    /^worktree / { wt = $2 }
    /^branch / { if (wt == path) { sub(/^refs\/heads\//, "", $2); print $2; exit } }
' || echo "")

# Remove the worktree
if [ "$FORCE_FLAG" = "--force" ]; then
    git worktree remove "$WORKTREE_PATH" --force
else
    git worktree remove "$WORKTREE_PATH"
fi

# Delete the branch if it exists and is not the current branch
if [ -n "$BRANCH_NAME" ] && [ "$BRANCH_NAME" != "$(git branch --show-current)" ]; then
    echo "Deleting branch: $BRANCH_NAME"
    git branch -D "$BRANCH_NAME"
else
    echo "No branch to delete or branch is currently checked out"
fi

echo "Worktree $WORKTREE_PATH removed successfully"