#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}    Create Worktrees from ClickUp Ready Tasks${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Fetch tasks marked as 'Ready To Implement' from ClickUp and create worktrees for them."
    echo ""
    echo "Options:"
    echo "  --dry-run           Show what would be created without actually creating worktrees"
    echo "  --no-install        Skip yarn install in worktrees"
    echo "  --worktree-dir DIR  Base directory for worktrees (default: ../worktrees)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                         # Create worktrees for all ready tasks"
    echo "  $0 --dry-run              # Preview what would be created"
    echo "  $0 --no-install           # Create without running yarn install"
}

# Default options
DRY_RUN=false
NO_INSTALL_FLAG=""
WORKTREE_BASE_DIR="../worktrees"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_header
            show_usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-install)
            NO_INSTALL_FLAG="--no-install"
            shift
            ;;
        --worktree-dir)
            WORKTREE_BASE_DIR="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

print_header

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Fetch ready tasks from ClickUp
print_info "Fetching tasks marked as 'Ready To Implement'..."
READY_TASKS=$(cd "$REPO_ROOT" && yarn --silent ts-node scripts/clickup/get-ready-tasks.ts --json 2>/dev/null)

if [ $? -ne 0 ]; then
    print_error "Failed to fetch tasks from ClickUp"
    exit 1
fi

# Check if any tasks found
TASK_COUNT=$(echo "$READY_TASKS" | jq '. | length')

if [ "$TASK_COUNT" -eq 0 ]; then
    print_info "No tasks found with status 'Ready To Implement'"
    exit 0
fi

echo ""
print_success "Found $TASK_COUNT task(s) ready to implement"
echo ""

# Process each task
echo "$READY_TASKS" | jq -c '.[]' | while IFS= read -r task; do
    TASK_ID=$(echo "$task" | jq -r '.taskId')
    CLICKUP_ID=$(echo "$task" | jq -r '.clickupId')
    TASK_NAME=$(echo "$task" | jq -r '.name')

    if [ "$TASK_ID" = "unknown" ] || [ "$TASK_ID" = "null" ]; then
        print_warning "Skipping task without spec ID: $TASK_NAME"
        continue
    fi

    echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
    print_info "Task: $TASK_ID - $TASK_NAME"
    print_info "ClickUp ID: $CLICKUP_ID"

    # Include both Spec ID and ClickUp ID in path: E02-F01-T03-86ev3b0uy
    WORKTREE_PATH="$WORKTREE_BASE_DIR/$TASK_ID-$CLICKUP_ID"
    BRANCH_NAME="$TASK_ID-$CLICKUP_ID"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would create worktree:"
        print_info "  Branch: $BRANCH_NAME"
        print_info "  Path: $WORKTREE_PATH"
    else
        # Check if worktree already exists
        if git worktree list | grep -q "$WORKTREE_PATH"; then
            print_warning "Worktree already exists for $TASK_ID"
            continue
        fi

        # Create worktree using the existing script
        print_info "Creating worktree..."
        cd "$REPO_ROOT"

        if bash scripts/development/create-worktree.sh -b "$BRANCH_NAME" "$WORKTREE_PATH" $NO_INSTALL_FLAG; then
            print_success "Worktree created: $WORKTREE_PATH"
        else
            print_error "Failed to create worktree for $TASK_ID"
        fi
    fi

    echo ""
done

echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN}    Dry Run Complete!${NC}"
else
    echo -e "${GREEN}    All Worktrees Created!${NC}"
fi
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DRY_RUN" = false ] && [ "$TASK_COUNT" -gt 0 ]; then
    print_info "Next steps:"
    echo "  1. cd $WORKTREE_BASE_DIR/<task-id-clickup-id>"
    echo "  2. Make your changes and commit"
    echo "  3. Create PR - branch name contains both IDs for linking"
    echo ""
    print_info "Branch naming format: {spec-id}-{clickup-id}"
    print_info "Example: E02-F01-T03-86ev3b0uy"
    print_info "GitHub workflows can extract ClickUp ID from branch name"
fi
