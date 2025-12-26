#!/bin/bash

set -e

SCRIPT_NAME="create-worktree.sh"
SCRIPT_VERSION="1.0.0"

# Files and directories to copy to worktrees
FILES_TO_COPY=(
    ".env.local"
    ".env"
    "docker/.env"
    ".claude/settings.json"
)

DIRS_TO_COPY=(
    ".vscode"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}    JTS Worktree Creator with Environment Setup${NC}"
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

update_clickup_status() {
    local task_id="$1"

    # Load CLICKUP_API_KEY from .env.local
    if [ -f "$MAIN_REPO_ROOT/.env.local" ]; then
        CLICKUP_API_KEY=$(grep '^CLICKUP_API_KEY=' "$MAIN_REPO_ROOT/.env.local" | cut -d '=' -f2-)
    fi

    if [ -z "$CLICKUP_API_KEY" ]; then
        print_warning "CLICKUP_API_KEY not found in .env.local, skipping status update"
        return 0
    fi

    echo -e "\n${BLUE}Updating ClickUp task status...${NC}"
    print_info "Task ID: $task_id"

    # Update task status to IN PROGRESS
    response=$(curl -s -w "\n%{http_code}" -X PUT \
        "https://api.clickup.com/api/v2/task/$task_id" \
        -H "Authorization: $CLICKUP_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"status":"IN PROGRESS"}')

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        print_success "Task status updated to IN PROGRESS"
    else
        print_warning "Failed to update task status (HTTP $http_code)"
        print_info "Response: $body"
    fi
}

show_usage() {
    echo "Usage: $SCRIPT_NAME [<worktree-path>] [<branch>]"
    echo "   or: $SCRIPT_NAME [-b <new-branch>] <worktree-path> [<commit-ish>]"
    echo ""
    echo "Creates a new git worktree and copies necessary environment files."
    echo ""
    echo "Arguments:"
    echo "  worktree-path   Path for the worktree (default: ../worktrees/<branch>)"
    echo "  branch          Branch to checkout (default: current branch)"
    echo "  commit-ish      Commit/branch to base new branch on"
    echo ""
    echo "Options:"
    echo "  -b <branch>     Create a new branch"
    echo "  -t, --task-id <id>  ClickUp Task ID (e.g., 86ev3ymu1) to cache in worktree"
    echo "  -h, --help      Show this help message"
    echo "  -f, --force     Force creation even if worktree exists"
    echo "  -n, --no-copy   Skip copying environment files"
    echo "  --no-install    Skip yarn install"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME                                    # Create worktree with current branch"
    echo "  $SCRIPT_NAME ../worktrees/feature               # Create at path with current branch"
    echo "  $SCRIPT_NAME -b new-feature ../work             # Create new branch at path"
    echo "  $SCRIPT_NAME -b fix-auth -t 86ev3ymu1 ../work   # Create branch with TaskId"
}

FORCE=false
NO_COPY=false
NO_INSTALL=false
CREATE_BRANCH=false
NEW_BRANCH=""
TASK_ID=""
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_header
            show_usage
            exit 0
            ;;
        -b)
            CREATE_BRANCH=true
            NEW_BRANCH="$2"
            shift 2
            ;;
        -t|--task-id)
            TASK_ID="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--no-copy)
            NO_COPY=true
            shift
            ;;
        --no-install)
            NO_INSTALL=true
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional parameters
set -- "${POSITIONAL_ARGS[@]}"

if [ "$CREATE_BRANCH" = true ] && [ -z "$NEW_BRANCH" ]; then
    print_error "Branch name required with -b option"
    show_usage
    exit 1
fi

if [ "$CREATE_BRANCH" = true ]; then
    BRANCH_NAME="$NEW_BRANCH"
    WORKTREE_PATH="$1"
    COMMIT_ISH="${2:-}"
    
    if [ -z "$WORKTREE_PATH" ]; then
        print_error "Worktree path is required when creating new branch with -b"
        show_usage
        exit 1
    fi
else
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    
    if [ $# -eq 0 ]; then
        WORKTREE_PATH="../worktrees/$CURRENT_BRANCH"
        BRANCH_NAME="$CURRENT_BRANCH"
    elif [ $# -eq 1 ]; then
        WORKTREE_PATH="$1"
        # Infer branch name from worktree path basename
        BRANCH_NAME="$(basename "$WORKTREE_PATH")"
    else
        WORKTREE_PATH="$1"
        BRANCH_NAME="$2"
    fi
fi

print_header

MAIN_REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ $? -ne 0 ]; then
    print_error "Not in a git repository"
    exit 1
fi

print_info "Main repository: $MAIN_REPO_ROOT"

if [ ! -d "$MAIN_REPO_ROOT" ]; then
    print_error "Could not find main repository root"
    exit 1
fi

WORKTREE_FULL_PATH=$(realpath -m "$WORKTREE_PATH" 2>/dev/null || echo "$WORKTREE_PATH")

if [ -d "$WORKTREE_FULL_PATH" ] && [ "$FORCE" = false ]; then
    print_error "Worktree already exists at: $WORKTREE_FULL_PATH"
    print_info "Use -f or --force to override"
    exit 1
fi

if [ -d "$WORKTREE_FULL_PATH" ] && [ "$FORCE" = true ]; then
    print_warning "Removing existing worktree at: $WORKTREE_FULL_PATH"
    git worktree remove --force "$WORKTREE_FULL_PATH" 2>/dev/null || true
    rm -rf "$WORKTREE_FULL_PATH"
fi

echo -e "\n${BLUE}Creating worktree...${NC}"

if [ "$CREATE_BRANCH" = true ]; then
    print_info "Creating new branch '$BRANCH_NAME'..."
    if [ -n "$COMMIT_ISH" ]; then
        git worktree add -b "$BRANCH_NAME" "$WORKTREE_FULL_PATH" "$COMMIT_ISH"
    else
        git worktree add -b "$BRANCH_NAME" "$WORKTREE_FULL_PATH"
    fi
elif git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    # Check if branch is already used by another worktree
    if git worktree list | grep -q "$BRANCH_NAME"; then
        print_error "Branch '$BRANCH_NAME' is already checked out in another worktree"
        print_info "Use 'git worktree list' to see all worktrees"
        print_info "Or use -b option to create a new branch: $SCRIPT_NAME -b new-branch-name $WORKTREE_PATH"
        exit 1
    fi
    print_info "Branch '$BRANCH_NAME' exists, checking out..."
    git worktree add "$WORKTREE_FULL_PATH" "$BRANCH_NAME"
else
    print_info "Creating new branch '$BRANCH_NAME'..."
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_FULL_PATH"
fi

if [ $? -ne 0 ]; then
    print_error "Failed to create worktree"
    exit 1
fi

print_success "Worktree created at: $WORKTREE_FULL_PATH"

# Cache ClickUp Task ID in worktree git config if provided
if [ -n "$TASK_ID" ]; then
    echo -e "\n${BLUE}Caching ClickUp Task ID...${NC}"

    # Enable worktreeConfig extension if not already enabled
    if [ "$(git config --get extensions.worktreeConfig)" != "true" ]; then
        print_info "Enabling worktreeConfig extension..."
        git config extensions.worktreeConfig true
        print_success "Enabled worktreeConfig extension"
    fi

    # Remove 'CU-' prefix if present
    CLEAN_TASK_ID=$(echo "$TASK_ID" | sed 's/^CU-//')

    git -C "$WORKTREE_FULL_PATH" config --worktree clickup.taskid "$CLEAN_TASK_ID"
    print_success "Cached TaskId in worktree: $CLEAN_TASK_ID"

    # Update ClickUp task status to IN PROGRESS
    update_clickup_status "$CLEAN_TASK_ID"
else
    # Try to extract from branch name as fallback (for backward compatibility)
    EXTRACTED_TASK_ID=$(echo "$BRANCH_NAME" | grep -oP 'CU-\K[a-z0-9]+' || true)
    if [ -n "$EXTRACTED_TASK_ID" ]; then
        echo -e "\n${BLUE}Caching ClickUp Task ID...${NC}"

        # Enable worktreeConfig extension if not already enabled
        if [ "$(git config --get extensions.worktreeConfig)" != "true" ]; then
            print_info "Enabling worktreeConfig extension..."
            git config extensions.worktreeConfig true
            print_success "Enabled worktreeConfig extension"
        fi

        git -C "$WORKTREE_FULL_PATH" config --worktree clickup.taskid "$EXTRACTED_TASK_ID"
        print_success "Cached TaskId in worktree (from branch name): $EXTRACTED_TASK_ID"

        # Update ClickUp task status to IN PROGRESS
        update_clickup_status "$EXTRACTED_TASK_ID"
    fi
fi

copied_count=0

if [ "$NO_COPY" = true ]; then
    print_info "Skipping environment file copying (--no-copy flag)"
else
    echo -e "\n${BLUE}Copying environment files...${NC}"
    
    copied_count=0
    
    # Copy files
    for file in "${FILES_TO_COPY[@]}"; do
        if [ -f "$MAIN_REPO_ROOT/$file" ]; then
            # Create directory if needed
            target_dir="$WORKTREE_FULL_PATH/$(dirname "$file")"
            if [ "$(dirname "$file")" != "." ]; then
                mkdir -p "$target_dir"
            fi
            cp "$MAIN_REPO_ROOT/$file" "$WORKTREE_FULL_PATH/$file"
            print_success "Copied $file"
            ((copied_count++)) || true
        fi
    done
    
    # Copy directories
    for dir in "${DIRS_TO_COPY[@]}"; do
        if [ -d "$MAIN_REPO_ROOT/$dir" ]; then
            cp -r "$MAIN_REPO_ROOT/$dir" "$WORKTREE_FULL_PATH/$dir"
            print_success "Copied $dir directory"
            ((copied_count++)) || true
        fi
    done
    
    if [ $copied_count -eq 0 ]; then
        print_warning "No environment files found to copy"
        print_info "You may need to create .env.local from .env.example"
    else
        print_success "Copied $copied_count items"
    fi
fi

if [ "$NO_INSTALL" = true ]; then
    print_info "Skipping dependency setup (--no-install flag)"
else
    echo -e "\n${BLUE}Setting up dependencies...${NC}"
    print_info "Changing to directory: $WORKTREE_FULL_PATH"
    cd "$WORKTREE_FULL_PATH"
    print_info "Current directory: $(pwd)"

    if [ -f "package.json" ]; then
        print_info "package.json found"

        # Check if running in WSL
        if grep -qi microsoft /proc/version 2>/dev/null; then
            print_info "Detected WSL environment"

            # Create symlink to main repo's node_modules instead of running yarn install
            # This avoids Windows symlink issues in worktrees with nodeLinker: node-modules
            if [ -d "$MAIN_REPO_ROOT/node_modules" ]; then
                print_info "Creating symlink to main repo's node_modules..."

                # Remove any existing node_modules (directory or symlink)
                if [ -e "node_modules" ] || [ -L "node_modules" ]; then
                    rm -rf node_modules
                    print_info "Removed existing node_modules"
                fi

                # Calculate relative path from worktree to main repo's node_modules
                RELATIVE_PATH=$(realpath --relative-to="$WORKTREE_FULL_PATH" "$MAIN_REPO_ROOT/node_modules")

                # Create symlink with calculated relative path
                ln -s "$RELATIVE_PATH" node_modules

                if [ -L "node_modules" ]; then
                    print_success "Created symlink to main repo's node_modules"
                    print_info "Worktree will use dependencies from: $MAIN_REPO_ROOT/node_modules"
                else
                    print_error "Failed to create symlink to node_modules"
                    exit 1
                fi
            else
                print_warning "Main repo's node_modules not found at: $MAIN_REPO_ROOT/node_modules"
                print_info "Please run 'yarn install' in the main repository first:"
                print_info "  cd $MAIN_REPO_ROOT && yarn install"
                exit 1
            fi
        else
            print_info "Non-WSL environment detected, running yarn install in background..."

            if command -v yarn &> /dev/null; then
                # Set up log file
                INSTALL_LOG="$WORKTREE_FULL_PATH/.yarn-install.log"

                echo ""
                print_info "Starting yarn install in background..."
                print_info "Building: better-sqlite3, @swc/core, esbuild, and other native packages..."
                print_info "Log file: .yarn-install.log"
                echo ""

                # Run yarn install in background with logging
                nohup bash -c '
                    echo "=== Yarn Install Started at $(date) ===" > "'"$INSTALL_LOG"'"
                    yarn install >> "'"$INSTALL_LOG"'" 2>&1
                    yarn_exit_code=$?
                    echo "" >> "'"$INSTALL_LOG"'"
                    echo "=== Yarn Install Completed at $(date) with exit code: $yarn_exit_code ===" >> "'"$INSTALL_LOG"'"

                    if [ $yarn_exit_code -eq 0 ]; then
                        echo "SUCCESS: Dependencies installed successfully" >> "'"$INSTALL_LOG"'"
                    else
                        echo "ERROR: yarn install failed with exit code: $yarn_exit_code" >> "'"$INSTALL_LOG"'"
                    fi
                ' > /dev/null 2>&1 &

                YARN_PID=$!
                print_success "yarn install running in background (PID: $YARN_PID)"
                print_info "Monitor progress with: tail -f $INSTALL_LOG"
                print_info "Check status with: ps -p $YARN_PID"
            else
                print_error "yarn not found"
                print_info "Please install Yarn: https://yarnpkg.com/getting-started/install"
                exit 1
            fi
        fi
    else
        print_info "No package.json found, skipping dependency setup"
    fi
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Worktree Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
print_success "Branch: $BRANCH_NAME"
print_success "Location: $WORKTREE_FULL_PATH"
echo ""
echo "Next steps:"
echo "  cd $WORKTREE_FULL_PATH"
if [ $copied_count -eq 0 ] && [ "$NO_COPY" = false ]; then
    echo "  cp .env.example .env.local  # Create your local environment file"
    echo "  # Edit .env.local with your actual credentials"
fi
echo "  yarn dev                  # Start development"
echo ""