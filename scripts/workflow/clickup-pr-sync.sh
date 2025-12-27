#!/bin/bash

set -e

SCRIPT_NAME="clickup-pr-sync.sh"
SCRIPT_VERSION="1.0.0"

# Ink project configuration
SPACE_ID="90188945109"
GITHUB_REPO="ddoachi/ink"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}    Ink: ClickUp <-> GitHub PR Sync Tool${NC}"
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

print_task() {
    echo -e "${CYAN}→${NC} $1"
}

show_usage() {
    echo "Usage: $SCRIPT_NAME [OPTIONS]"
    echo ""
    echo "Syncs ClickUp tasks with GitHub PRs:"
    echo "  1. Fetches tasks with 'In Progress' status from ClickUp"
    echo "  2. Matches tasks to GitHub PRs by branch name pattern"
    echo "  3. Updates PR titles to include [CU-{taskId}]"
    echo "  4. Updates ClickUp task status to 'Complete'"
    echo ""
    echo "Options:"
    echo "  --epic <EPIC>     Filter by epic (e.g., E08, E07)"
    echo "                    Can specify multiple: --epic E08 --epic E07"
    echo "  --dry-run         Show what would be done without making changes"
    echo "  --no-status       Skip updating ClickUp task status"
    echo "  --no-pr           Skip updating PR titles"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Environment:"
    echo "  CLICKUP_API_KEY   ClickUp API key (or set in .env.local)"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME --epic E08          # Sync only E08 epic"
    echo "  $SCRIPT_NAME --epic E08 --epic E07  # Sync E08 and E07"
    echo "  $SCRIPT_NAME --dry-run           # Preview changes for all epics"
    echo "  $SCRIPT_NAME                     # Sync all epics"
}

# Epic folder IDs will be populated dynamically from ClickUp API
declare -A EPIC_FOLDER_IDS

# Fetch folder IDs from ClickUp space
fetch_folder_ids() {
    print_info "Fetching folder IDs from ClickUp space..."

    local folders_json
    folders_json=$(curl -s -H "Authorization: $CLICKUP_API_KEY" \
        "https://api.clickup.com/api/v2/space/$SPACE_ID/folder" 2>/dev/null)

    if [ -z "$folders_json" ]; then
        print_error "Failed to fetch folders from ClickUp"
        exit 1
    fi

    # Parse folder names and IDs (format: "E## - Title")
    while IFS='|' read -r folder_id folder_name; do
        if [ -n "$folder_id" ] && [ -n "$folder_name" ]; then
            # Extract epic ID from folder name (e.g., "E01 - Domain Layer Core" -> "E01")
            local epic_id
            epic_id=$(echo "$folder_name" | grep -oE '^E[0-9]+' | head -1)
            if [ -n "$epic_id" ]; then
                EPIC_FOLDER_IDS["$epic_id"]="$folder_id"
            fi
        fi
    done <<< "$(echo "$folders_json" | jq -r '.folders[]? | "\(.id)|\(.name)"' 2>/dev/null)"

    if [ ${#EPIC_FOLDER_IDS[@]} -eq 0 ]; then
        print_warning "No epic folders found in ClickUp space"
    else
        print_success "Found ${#EPIC_FOLDER_IDS[@]} epic folder(s)"
    fi
}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    print_error "Not in a git repository"
    exit 1
fi

load_api_key() {
    if [ -n "$CLICKUP_API_KEY" ]; then
        return 0
    fi

    if [ -f "$REPO_ROOT/.env.local" ]; then
        CLICKUP_API_KEY=$(grep '^CLICKUP_API_KEY=' "$REPO_ROOT/.env.local" | cut -d '=' -f2-)
    fi

    if [ -z "$CLICKUP_API_KEY" ]; then
        print_error "CLICKUP_API_KEY not found"
        print_info "Set it in .env.local or as environment variable"
        exit 1
    fi
}

get_lists_for_folder() {
    local folder_id="$1"
    curl -s -H "Authorization: $CLICKUP_API_KEY" \
        "https://api.clickup.com/api/v2/folder/$folder_id/list" | \
        jq -r '.lists[]? | .id' 2>/dev/null
}

get_in_progress_tasks() {
    local list_id="$1"
    curl -s -H "Authorization: $CLICKUP_API_KEY" \
        "https://api.clickup.com/api/v2/list/$list_id/task?statuses[]=in%20progress" 2>/dev/null | \
        jq -r '.tasks[]? | "\(.id)|\(.name)"' 2>/dev/null
}

title_to_branch_pattern() {
    local title="$1"
    echo "$title" | sed 's/[^a-zA-Z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//'
}

find_pr_for_task() {
    local task_name="$1"
    local branch_pattern
    branch_pattern=$(title_to_branch_pattern "$task_name")

    gh pr list --state all --limit 200 --json number,title,headRefName,state 2>/dev/null | \
        jq -r --arg pattern "$branch_pattern" \
        '.[] | select(.headRefName | test($pattern; "i")) | "\(.number)|\(.title)|\(.headRefName)|\(.state)"' 2>/dev/null | head -1
}

update_pr_title() {
    local pr_number="$1"
    local task_id="$2"
    local current_title="$3"

    if echo "$current_title" | grep -qE '\[CU-[a-z0-9]+\]'; then
        return 1
    fi

    local new_title="[CU-$task_id] $current_title"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would update PR #$pr_number title to: $new_title"
        return 0
    fi

    gh pr edit "$pr_number" --title "$new_title" >/dev/null 2>&1
    return $?
}

update_clickup_status() {
    local task_id="$1"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would update ClickUp task $task_id to 'complete'"
        return 0
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" -X PUT \
        "https://api.clickup.com/api/v2/task/$task_id" \
        -H "Authorization: $CLICKUP_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"status":"complete"}')

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

DRY_RUN=false
NO_STATUS=false
NO_PR=false
SELECTED_EPICS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_header
            show_usage
            exit 0
            ;;
        --epic)
            SELECTED_EPICS+=("$2")
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-status)
            NO_STATUS=true
            shift
            ;;
        --no-pr)
            NO_PR=true
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            print_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

print_header

load_api_key

if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is required but not installed"
    print_info "Install it from: https://cli.github.com/"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    print_info "Install it: sudo apt install jq"
    exit 1
fi

# Fetch folder IDs from ClickUp API
fetch_folder_ids

if [ ${#SELECTED_EPICS[@]} -eq 0 ]; then
    EPICS_TO_PROCESS=("${!EPIC_FOLDER_IDS[@]}")
else
    EPICS_TO_PROCESS=("${SELECTED_EPICS[@]}")
fi

if [ "$DRY_RUN" = true ]; then
    print_warning "DRY-RUN mode: No changes will be made"
    echo ""
fi

print_info "Processing epics: ${EPICS_TO_PROCESS[*]}"
echo ""

TOTAL_TASKS=0
TOTAL_MATCHED=0
TOTAL_PR_UPDATED=0
TOTAL_STATUS_UPDATED=0

COL_TASK=50
COL_ID=12
COL_PR=6
COL_STATE=8
COL_PR_STATUS=12
COL_CU_STATUS=12

truncate_str() {
    local str="$1"
    local max_len="$2"
    if [ ${#str} -gt $max_len ]; then
        echo "${str:0:$((max_len-2))}.."
    else
        echo "$str"
    fi
}

print_table_header() {
    local epic="$1"
    echo ""
    echo -e "${CYAN}━━━ Epic: $epic ━━━${NC}"
    echo ""
    printf "${BLUE}%-${COL_TASK}s${NC} " "Task"
    printf "${BLUE}%-${COL_ID}s${NC} " "ID"
    printf "${BLUE}%-${COL_PR}s${NC} " "PR"
    printf "${BLUE}%-${COL_STATE}s${NC} " "State"
    printf "${BLUE}%-${COL_PR_STATUS}s${NC} " "PR Update"
    printf "${BLUE}%-${COL_CU_STATUS}s${NC}\n" "CU Update"
    printf "%s\n" "$(printf '─%.0s' $(seq 1 $((COL_TASK + COL_ID + COL_PR + COL_STATE + COL_PR_STATUS + COL_CU_STATUS + 5))))"
}

print_table_row() {
    local task_name="$1"
    local task_id="$2"
    local pr_number="$3"
    local pr_state="$4"
    local pr_update_status="$5"
    local cu_update_status="$6"

    local task_truncated
    task_truncated=$(truncate_str "$task_name" $COL_TASK)

    printf "%-${COL_TASK}s " "$task_truncated"
    printf "%-${COL_ID}s " "$task_id"

    if [ "$pr_number" = "-" ]; then
        printf "${YELLOW}%-${COL_PR}s${NC} " "$pr_number"
        printf "${YELLOW}%-${COL_STATE}s${NC} " "$pr_state"
    else
        printf "%-${COL_PR}s " "#$pr_number"
        if [ "$pr_state" = "MERGED" ]; then
            printf "${GREEN}%-${COL_STATE}s${NC} " "$pr_state"
        elif [ "$pr_state" = "OPEN" ]; then
            printf "${BLUE}%-${COL_STATE}s${NC} " "$pr_state"
        else
            printf "%-${COL_STATE}s " "$pr_state"
        fi
    fi

    case "$pr_update_status" in
        "updated")
            printf "${GREEN}%-${COL_PR_STATUS}s${NC} " "✓ Updated"
            ;;
        "skipped")
            printf "${YELLOW}%-${COL_PR_STATUS}s${NC} " "○ Has ID"
            ;;
        "would-update")
            printf "${CYAN}%-${COL_PR_STATUS}s${NC} " "→ Would"
            ;;
        "no-pr")
            printf "${YELLOW}%-${COL_PR_STATUS}s${NC} " "- No PR"
            ;;
        *)
            printf "%-${COL_PR_STATUS}s " "$pr_update_status"
            ;;
    esac

    case "$cu_update_status" in
        "updated")
            printf "${GREEN}%-${COL_CU_STATUS}s${NC}\n" "✓ Complete"
            ;;
        "would-update")
            printf "${CYAN}%-${COL_CU_STATUS}s${NC}\n" "→ Would"
            ;;
        "failed")
            printf "${RED}%-${COL_CU_STATUS}s${NC}\n" "✗ Failed"
            ;;
        "skipped")
            printf "${YELLOW}%-${COL_CU_STATUS}s${NC}\n" "○ Skipped"
            ;;
        *)
            printf "%-${COL_CU_STATUS}s\n" "$cu_update_status"
            ;;
    esac
}

for epic in "${EPICS_TO_PROCESS[@]}"; do
    folder_id="${EPIC_FOLDER_IDS[$epic]}"

    if [ -z "$folder_id" ]; then
        print_warning "Unknown epic: $epic (skipping)"
        continue
    fi

    lists=$(get_lists_for_folder "$folder_id")

    if [ -z "$lists" ]; then
        continue
    fi

    EPIC_HAS_TASKS=false
    EPIC_ROWS=()

    for list_id in $lists; do
        tasks=$(get_in_progress_tasks "$list_id")

        if [ -z "$tasks" ]; then
            continue
        fi

        while IFS='|' read -r task_id task_name; do
            if [ -z "$task_id" ] || [ -z "$task_name" ]; then
                continue
            fi

            EPIC_HAS_TASKS=true
            ((TOTAL_TASKS++)) || true

            # Show real-time progress
            echo -ne "\r\033[K${CYAN}→${NC} Processing: ${task_name:0:60}..."

            pr_info=$(find_pr_for_task "$task_name")

            if [ -z "$pr_info" ]; then
                EPIC_ROWS+=("$task_name|$task_id|-|-|no-pr|skipped")
                continue
            fi

            ((TOTAL_MATCHED++)) || true

            IFS='|' read -r pr_number pr_title pr_branch pr_state <<< "$pr_info"

            pr_update_status="skipped"
            cu_update_status="skipped"

            if [ "$NO_PR" = false ]; then
                if echo "$pr_title" | grep -qE '\[CU-[a-z0-9]+\]'; then
                    pr_update_status="skipped"
                else
                    if [ "$DRY_RUN" = true ]; then
                        pr_update_status="would-update"
                        ((TOTAL_PR_UPDATED++)) || true
                    else
                        if gh pr edit "$pr_number" --title "[CU-$task_id] $pr_title" >/dev/null 2>&1; then
                            pr_update_status="updated"
                            ((TOTAL_PR_UPDATED++)) || true
                        else
                            pr_update_status="failed"
                        fi
                    fi
                fi
            fi

            # Only update ClickUp status to complete when PR is merged
            if [ "$NO_STATUS" = false ] && [ "$pr_state" = "MERGED" ]; then
                if [ "$DRY_RUN" = true ]; then
                    cu_update_status="would-update"
                    ((TOTAL_STATUS_UPDATED++)) || true
                else
                    if update_clickup_status "$task_id"; then
                        cu_update_status="updated"
                        ((TOTAL_STATUS_UPDATED++)) || true
                    else
                        cu_update_status="failed"
                    fi
                fi
            fi

            EPIC_ROWS+=("$task_name|$task_id|$pr_number|$pr_state|$pr_update_status|$cu_update_status")
        done <<< "$tasks"
    done

    if [ "$EPIC_HAS_TASKS" = true ]; then
        echo -ne "\r\033[K"  # Clear progress line
        print_table_header "$epic"
        for row in "${EPIC_ROWS[@]}"; do
            IFS='|' read -r task_name task_id pr_number pr_state pr_update cu_update <<< "$row"
            print_table_row "$task_name" "$task_id" "$pr_number" "$pr_state" "$pr_update" "$cu_update"
        done
    fi
done

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Summary${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
print_info "Total 'In Progress' tasks found: $TOTAL_TASKS"
print_info "Tasks matched to PRs: $TOTAL_MATCHED"
if [ "$DRY_RUN" = true ]; then
    print_info "PR titles would be updated: $TOTAL_PR_UPDATED"
    print_info "ClickUp statuses would be updated: $TOTAL_STATUS_UPDATED"
else
    print_success "PR titles updated: $TOTAL_PR_UPDATED"
    print_success "ClickUp statuses updated: $TOTAL_STATUS_UPDATED"
fi
echo ""
