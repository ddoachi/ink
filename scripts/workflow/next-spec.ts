#!/usr/bin/env ts-node

/**
 * Next Spec Workflow Automation
 *
 * Automates the transition from completed spec to next spec:
 * 1. Cleans up merged PR worktrees
 * 2. Finds the next sequential spec
 * 3. Updates ClickUp task to "IN PROGRESS"
 * 4. Creates worktree for the next spec
 *
 * Prerequisites:
 * - CLICKUP_API_KEY in .env.local
 * - gh CLI authenticated
 *
 * Usage:
 *   yarn exec ts-node scripts/development/next-spec.ts
 *   yarn exec ts-node scripts/development/next-spec.ts --skip-cleanup
 */

import axios, { AxiosInstance } from 'axios';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';
import * as os from 'os';

// Load environment variables
const envPath = path.join(__dirname, '../../.env.local');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  envContent.split('\n').forEach((line) => {
    const match = line.match(/^([A-Z_]+)=(.*)$/);
    if (match && match[1] && match[2] && !process.env[match[1]]) {
      process.env[match[1]] = match[2];
    }
  });
}

const CLICKUP_API_KEY = process.env['CLICKUP_API_KEY'];
const CLICKUP_API_BASE = 'https://api.clickup.com/api/v2';

if (!CLICKUP_API_KEY) {
  console.error('❌ CLICKUP_API_KEY not found in .env.local');
  process.exit(1);
}

// ============================================================================
// Types
// ============================================================================

interface SpecMetadata {
  id: string;
  title: string;
  clickup_task_id?: string;
  type: 'epic' | 'feature' | 'task' | 'subtask';
  [key: string]: unknown;
}

interface SpecFile {
  path: string;
  specId: string;
  metadata: SpecMetadata;
}

// ============================================================================
// ClickUp API Client
// ============================================================================

class ClickUpClient {
  private client: AxiosInstance;
  private lastRequestTime = 0;
  private minRequestInterval = 1000;

  constructor(apiKey: string) {
    this.client = axios.create({
      baseURL: CLICKUP_API_BASE,
      headers: {
        Authorization: apiKey,
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use(async (config) => {
      const now = Date.now();
      const timeSinceLastRequest = now - this.lastRequestTime;

      if (timeSinceLastRequest < this.minRequestInterval) {
        const waitTime = this.minRequestInterval - timeSinceLastRequest;
        await new Promise((resolve) => globalThis.setTimeout(resolve, waitTime));
      }

      this.lastRequestTime = Date.now();
      return config;
    });
  }

  async updateTaskStatus(taskId: string, status: string): Promise<void> {
    await this.client.put(`/task/${taskId}`, { status });
  }

  async getTask(taskId: string) {
    const response = await this.client.get(`/task/${taskId}`);
    return response.data;
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Detect if running in WSL environment
 */
function isWSL(): boolean {
  try {
    const osRelease = fs.readFileSync('/proc/version', 'utf-8').toLowerCase();
    return osRelease.includes('microsoft') || osRelease.includes('wsl');
  } catch {
    return false;
  }
}

/**
 * Convert WSL path to Windows path for VS Code
 * Example: /mnt/c/Users/... -> C:/Users/...
 */
function wslPathToWindows(wslPath: string): string {
  if (!isWSL()) {
    return wslPath;
  }

  try {
    // Use wslpath command to convert
    const windowsPath = execSync(`wslpath -w "${wslPath}"`, { encoding: 'utf-8' }).trim();
    // Normalize to forward slashes for consistency
    return windowsPath.replace(/\\/g, '/');
  } catch {
    // Fallback: manual conversion for /mnt/c/... paths
    const match = wslPath.match(/^\/mnt\/([a-z])(\/.*)?$/);
    if (match && match[1]) {
      const drive = match[1].toUpperCase();
      const restPath = match[2] || '';
      return `${drive}:${restPath}`;
    }
    return wslPath;
  }
}

/**
 * Get the appropriate shell command for the platform
 */
function getShellCommand(scriptPath: string, args: string[]): string {
  const isWindowsWSL = isWSL();

  if (isWindowsWSL) {
    // In WSL, use bash to run .sh scripts
    return `bash "${scriptPath}" ${args.join(' ')}`;
  } else if (os.platform() === 'win32') {
    // On native Windows, might need Git Bash or WSL
    return `bash "${scriptPath}" ${args.join(' ')}`;
  } else {
    // Linux/Mac - direct execution
    return `"${scriptPath}" ${args.join(' ')}`;
  }
}

function parseSpecFile(filePath: string): SpecMetadata | null {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    // Handle both LF (\n) and CRLF (\r\n) line endings
    const frontmatterMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);

    if (!frontmatterMatch || !frontmatterMatch[1]) {
      return null;
    }

    return yaml.load(frontmatterMatch[1]) as SpecMetadata;
  } catch (error) {
    console.error(`⚠️  Error parsing ${filePath}:`, error);
    return null;
  }
}

function extractSpecIdFromPath(filePath: string): string | null {
  const match = filePath.match(/(E\d+(?:-F\d+)?(?:-T\d+)?(?:-S\d+)?)\.spec\.md$/);
  return match ? (match[1] ?? null) : null;
}

function getAllSpecFiles(specsDir: string): SpecFile[] {
  const specs: SpecFile[] = [];

  function scanDirectory(dir: string): void {
    if (!fs.existsSync(dir)) return;

    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        scanDirectory(fullPath);
      } else if (entry.name.endsWith('.spec.md')) {
        const specId = extractSpecIdFromPath(fullPath);
        const metadata = parseSpecFile(fullPath);

        if (specId && metadata) {
          // Only include tasks and subtasks (skip epics and features)
          if (metadata.type === 'task' || metadata.type === 'subtask') {
            specs.push({ path: fullPath, specId, metadata });
          }
        }
      }
    }
  }

  scanDirectory(specsDir);
  return specs.sort((a, b) => a.specId.localeCompare(b.specId));
}

function findNextSpec(currentSpecId: string, allSpecs: SpecFile[]): SpecFile | null {
  const currentIndex = allSpecs.findIndex((spec) => spec.specId === currentSpecId);

  if (currentIndex === -1) {
    console.error(`❌ Current spec not found: ${currentSpecId}`);
    return null;
  }

  if (currentIndex === allSpecs.length - 1) {
    console.log('✨ No next spec - this is the last spec!');
    return null;
  }

  let nextSpec = allSpecs[currentIndex + 1] ?? null;

  if (!nextSpec) {
    return null;
  }

  // Bug fix: If the next spec is a task with subtasks, skip to the first subtask
  const children = nextSpec.metadata['children'];
  if (children && Array.isArray(children) && children.length > 0) {
    // Find the first subtask (first child)
    const firstSubtaskId = children[0];
    const firstSubtask = allSpecs.find((spec) => spec.specId === firstSubtaskId);
    if (firstSubtask) {
      return firstSubtask;
    }
  }

  return nextSpec;
}

interface Worktree {
  path: string;
  branch: string;
}

interface WorktreeCleanupPlan {
  worktreesToRemove: Array<{ path: string; branch: string; prNumber?: number }>;
  totalMergedPRs: number;
}

function getAllWorktrees(): Worktree[] {
  try {
    const worktreesOutput = execSync('git worktree list --porcelain', { encoding: 'utf-8' });

    const worktrees = worktreesOutput
      .split('\n\n')
      .filter((entry) => entry.trim())
      .map((entry) => {
        const lines = entry.split('\n');
        const worktreeLine = lines.find((l) => l.startsWith('worktree '));
        const branchLine = lines.find((l) => l.startsWith('branch '));

        return {
          path: worktreeLine?.replace('worktree ', '').trim() || '',
          branch: branchLine?.replace('branch refs/heads/', '').trim() || '',
        };
      })
      .filter((w) => w.path && !w.path.includes('/jts')); // Exclude main repo

    return worktrees;
  } catch (error) {
    console.error('⚠️  Error getting worktrees:', error);
    return [];
  }
}

interface WorktreeWithStatus extends Worktree {
  prStatus: 'open' | 'merged' | 'no-pr';
  prNumber?: number;
  hasUnpushedCommits: boolean;
  hasUnpushedBranch: boolean;
  hasUntrackedImportantFiles: boolean;
  untrackedImportantFiles?: string[];
}

function checkRemoteStatus(
  worktreePath: string,
  branch: string,
): {
  hasUnpushedCommits: boolean;
  hasUnpushedBranch: boolean;
} {
  try {
    // Check if remote branch exists
    const remoteBranch = execSync(
      `git -C "${worktreePath}" rev-parse --verify origin/${branch} 2>/dev/null || echo "no-remote"`,
      {
        encoding: 'utf-8',
      },
    ).trim();

    if (remoteBranch === 'no-remote') {
      return { hasUnpushedCommits: false, hasUnpushedBranch: true };
    }

    // Check for unpushed commits (commits ahead of remote)
    const unpushedCommits = execSync(
      `git -C "${worktreePath}" rev-list --count origin/${branch}..${branch}`,
      { encoding: 'utf-8' },
    ).trim();

    return {
      hasUnpushedCommits: parseInt(unpushedCommits, 10) > 0,
      hasUnpushedBranch: false,
    };
  } catch {
    return { hasUnpushedCommits: false, hasUnpushedBranch: false };
  }
}

function checkUntrackedImportantFiles(worktreePath: string): {
  hasUntrackedImportantFiles: boolean;
  untrackedImportantFiles: string[];
} {
  try {
    // Get path to main repo (parent of worktrees directory)
    const mainRepoPath = path.join(__dirname, '../..');

    // Get all untracked files (including gitignored files)
    // Use large maxBuffer to handle repositories with many untracked files
    const allFiles = execSync(`git -C "${worktreePath}" ls-files --others`, {
      encoding: 'utf-8',
      maxBuffer: 50 * 1024 * 1024, // 50MB buffer
    })
      .trim()
      .split('\n')
      .filter(Boolean);

    if (allFiles.length === 0) {
      return { hasUntrackedImportantFiles: false, untrackedImportantFiles: [] };
    }

    // Filter out common directories and expected workflow files
    const EXCLUDE_PATTERNS = [
      'node_modules/',
      '.yarn/',
      '.nx/',
      'dist/',
      'docker/dist/',
      'build/',
      '.next/',
      'coverage/',
      '.cache/',
      'tmp/',
      'temp/',
    ];

    // Files created by the workflow that should be ignored
    const IGNORE_FILES = [
      '.claude/settings.local.json',
      '.vscode/tasks.json',
      '.vscode/.vscode/grove-git-worktrees.json.backup.1756047625003',
      '.vscode/.vscode/launch.json',
      '.vscode/.vscode/settings.json',
      '.yarn-install.log',
    ];

    const filteredFiles = allFiles.filter(
      (file) =>
        !EXCLUDE_PATTERNS.some((pattern) => file.startsWith(pattern)) &&
        !IGNORE_FILES.includes(file),
    );

    if (filteredFiles.length === 0) {
      return { hasUntrackedImportantFiles: false, untrackedImportantFiles: [] };
    }

    // Check which untracked files are different from main repo
    const modifiedUntrackedFiles: string[] = [];

    for (const file of filteredFiles) {
      const worktreeFilePath = path.join(worktreePath, file);
      const mainRepoFilePath = path.join(mainRepoPath, file);

      // Check if file exists in main repo
      if (!fs.existsSync(mainRepoFilePath)) {
        // File doesn't exist in main repo - it's new
        modifiedUntrackedFiles.push(file);
        continue;
      }

      try {
        // Compare file contents
        const worktreeContent = fs.readFileSync(worktreeFilePath, 'utf-8');
        const mainRepoContent = fs.readFileSync(mainRepoFilePath, 'utf-8');

        if (worktreeContent !== mainRepoContent) {
          // File content is different
          modifiedUntrackedFiles.push(file);
        }
      } catch {
        // Error reading file - treat as modified
        modifiedUntrackedFiles.push(file);
      }
    }

    return {
      hasUntrackedImportantFiles: modifiedUntrackedFiles.length > 0,
      untrackedImportantFiles: modifiedUntrackedFiles,
    };
  } catch {
    // Silently fail - worktree might be inaccessible or corrupted
    return { hasUntrackedImportantFiles: false, untrackedImportantFiles: [] };
  }
}

function getWorktreesWithPRStatus(): WorktreeWithStatus[] {
  const allWorktrees = getAllWorktrees();

  return allWorktrees.map((worktree) => {
    // Check remote status
    const remoteStatus = checkRemoteStatus(worktree.path, worktree.branch);

    // Check for untracked important files
    const untrackedStatus = checkUntrackedImportantFiles(worktree.path);

    try {
      // Check for open PRs first
      let prInfo = execSync(
        `gh pr list --head "${worktree.branch}" --json number,state --limit 1`,
        {
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'ignore'], // Suppress stderr
        },
      ).trim();

      // If no open PR found, check merged PRs
      if (!prInfo || prInfo === '[]') {
        prInfo = execSync(
          `gh pr list --state merged --head "${worktree.branch}" --json number,state --limit 1`,
          {
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'ignore'],
          },
        ).trim();
      }

      if (!prInfo || prInfo === '[]') {
        return {
          ...worktree,
          prStatus: 'no-pr' as const,
          ...remoteStatus,
          ...untrackedStatus,
        };
      }

      const prs = JSON.parse(prInfo) as Array<{ number: number; state: string }>;
      const pr = prs[0];

      if (!pr) {
        return {
          ...worktree,
          prStatus: 'no-pr' as const,
          ...remoteStatus,
          ...untrackedStatus,
        };
      }

      return {
        ...worktree,
        prStatus: pr.state === 'MERGED' ? ('merged' as const) : ('open' as const),
        prNumber: pr.number,
        ...remoteStatus,
        ...untrackedStatus,
      };
    } catch {
      // If gh command fails, assume no PR
      return {
        ...worktree,
        prStatus: 'no-pr' as const,
        ...remoteStatus,
        ...untrackedStatus,
      };
    }
  });
}

/**
 * Parse user input that can contain comma-separated numbers and ranges
 * Examples: "1,3,5" -> [1,3,5], "1-5" -> [1,2,3,4,5], "1-3,7,9-11" -> [1,2,3,7,9,10,11]
 */
function parseNumbersAndRanges(input: string): number[] {
  const result: number[] = [];
  const parts = input.split(',').map((s) => s.trim());

  for (const part of parts) {
    if (part.includes('-')) {
      // Parse range like "1-5"
      const [startStr, endStr] = part.split('-').map((s) => s.trim());
      const start = parseInt(startStr ?? '', 10);
      const end = parseInt(endStr ?? '', 10);

      if (!isNaN(start) && !isNaN(end) && start <= end) {
        for (let i = start; i <= end; i++) {
          result.push(i);
        }
      }
    } else {
      // Parse single number
      const num = parseInt(part, 10);
      if (!isNaN(num)) {
        result.push(num);
      }
    }
  }

  return result;
}

async function selectWorktreesToCleanup(mergedOnly = false): Promise<WorktreeCleanupPlan> {
  let allWorktrees = getWorktreesWithPRStatus();

  // Filter to only merged PRs if requested
  if (mergedOnly) {
    allWorktrees = allWorktrees.filter((w) => w.prStatus === 'merged');
  }

  if (allWorktrees.length === 0) {
    return { worktreesToRemove: [], totalMergedPRs: 0 };
  }

  const headerText = mergedOnly ? 'Available worktrees (merged PRs only)' : 'Available worktrees';
  console.log(`\n📋 ${headerText}:\n`);

  allWorktrees.forEach((w, index) => {
    const statusEmoji = w.prStatus === 'merged' ? '✅' : w.prStatus === 'open' ? '🔄' : '❓';
    const prInfo = w.prNumber ? ` (PR #${w.prNumber})` : '';

    // Extract worktree name from path
    const worktreeName = path.basename(w.path);

    // Build compact warning indicators
    const warnings: string[] = [];
    if (w.hasUnpushedBranch) warnings.push('Not pushed');
    if (w.hasUnpushedCommits) warnings.push('Unpushed commits');
    if (w.hasUntrackedImportantFiles) {
      const fileCount = w.untrackedImportantFiles?.length || 0;
      warnings.push(`${fileCount} modified file${fileCount > 1 ? 's' : ''}`);
    }

    const warningText = warnings.length > 0 ? ` ⚠️  ${warnings.join(', ')}` : '';

    console.log(`  ${index + 1}. ${statusEmoji} ${worktreeName}${prInfo}${warningText}`);
  });

  console.log('\n  Legend: ✅ Merged  🔄 Open  ❓ No PR  |  ⚠️  = Warning');
  console.log('\n❓ Enter worktree numbers to delete (comma-separated or ranges)');
  console.log('   Examples: "1,3,5" or "1-5" or "1-3,7,9-11"');
  console.log('   Or press Enter to skip cleanup: ');

  const readline = await import('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const answer = await new Promise<string>((resolve) => {
    rl.question('', (input) => {
      rl.close();
      resolve(input.trim());
    });
  });

  if (!answer) {
    return { worktreesToRemove: [], totalMergedPRs: 0 };
  }

  // Parse numbers and ranges, convert to 0-based indices
  const selectedIndices = parseNumbersAndRanges(answer)
    .map((num) => num - 1)
    .filter((i) => i >= 0 && i < allWorktrees.length);

  const selectedWorktrees = selectedIndices
    .map((i) => allWorktrees[i])
    .filter((w): w is WorktreeWithStatus => w !== undefined);

  // Check for worktrees with warnings
  const worktreesWithWarnings = selectedWorktrees.filter(
    (w) => w.hasUnpushedBranch || w.hasUnpushedCommits || w.hasUntrackedImportantFiles,
  );

  if (worktreesWithWarnings.length > 0) {
    console.log('\n⚠️  WARNING: The following worktrees have unsaved work:\n');

    worktreesWithWarnings.forEach((w) => {
      const displayPath = isWSL() ? wslPathToWindows(w.path) : w.path;
      console.log(`  • ${displayPath}`);
      if (w.hasUnpushedBranch) console.log('    - Branch not pushed to remote');
      if (w.hasUnpushedCommits) console.log('    - Has unpushed commits');
      if (w.hasUntrackedImportantFiles) {
        console.log(`    - Important files: ${w.untrackedImportantFiles?.join(', ')}`);
      }
    });

    console.log('\n❓ Are you sure you want to delete these worktrees? (yes/no): ');

    const confirmAnswer = await new Promise<string>((resolve) => {
      const confirmRl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
      });
      confirmRl.question('', (input) => {
        confirmRl.close();
        resolve(input.trim().toLowerCase());
      });
    });

    if (confirmAnswer !== 'yes') {
      console.log('\n⊘ Cleanup cancelled - worktrees with warnings were not deleted');
      return { worktreesToRemove: [], totalMergedPRs: 0 };
    }
  }

  const worktreesToRemove = selectedWorktrees.map((w) => ({
    path: w.path,
    branch: w.branch,
  }));

  return { worktreesToRemove, totalMergedPRs: 0 };
}

function executeCleanup(plan: WorktreeCleanupPlan): void {
  console.log('\n🧹 Cleaning up worktrees...\n');

  if (plan.worktreesToRemove.length === 0) {
    console.log('  ℹ️  No worktrees to remove\n');
    return;
  }

  let removedCount = 0;
  let deletedBranches = 0;

  for (const worktree of plan.worktreesToRemove) {
    const prInfo = worktree.prNumber ? ` (PR #${worktree.prNumber})` : '';
    const displayPath = isWSL() ? wslPathToWindows(worktree.path) : worktree.path;
    console.log(`  🗑️  Removing: ${displayPath}${prInfo}`);

    try {
      // Try git worktree remove first
      try {
        execSync(`git worktree remove --force "${worktree.path}"`, { stdio: 'ignore' });
        removedCount++;
      } catch (gitError) {
        // If git worktree remove fails, manually delete and prune
        console.log(`     ℹ️  Git worktree remove failed, trying manual deletion...`);

        // Remove the directory manually
        if (os.platform() === 'win32') {
          execSync(`rd /s /q "${worktree.path.replace(/\//g, '\\')}"`, {
            stdio: 'ignore',
            shell: 'cmd.exe',
          });
        } else {
          execSync(`rm -rf "${worktree.path}"`, { stdio: 'ignore' });
        }

        // Prune git's worktree registry
        execSync('git worktree prune', { stdio: 'ignore' });
        console.log(`     ✅ Manually removed worktree`);
        removedCount++;
      }

      // Delete the associated branch
      if (worktree.branch) {
        try {
          const currentBranch = execSync('git branch --show-current', { encoding: 'utf-8' }).trim();
          if (worktree.branch !== currentBranch) {
            execSync(`git branch -D "${worktree.branch}"`, { stdio: 'ignore' });
            console.log(`     ✅ Deleted branch: ${worktree.branch}`);
            deletedBranches++;
          } else {
            console.log(
              `     ⚠️  Skipped branch deletion (currently checked out): ${worktree.branch}`,
            );
          }
        } catch (branchError) {
          console.log(`     ⚠️  Failed to delete branch: ${worktree.branch}`);
        }
      }
    } catch (error) {
      console.error(`    ⚠️  Failed to remove worktree: ${error}`);
    }
  }

  console.log(
    `\n  ✅ Removed ${removedCount} worktree(s) and deleted ${deletedBranches} branch(es)\n`,
  );
}

interface MergedPRSpec {
  prNumber: number;
  branch: string;
  specId: string | null;
  nextSpec: SpecFile | null;
}

function getSpecFromBranch(branchName: string, allSpecs: SpecFile[]): SpecFile | null {
  // Try to extract TaskId from branch name
  const taskIdMatch = branchName.match(/CU-([a-z0-9]+)/);

  if (taskIdMatch && taskIdMatch[1]) {
    const taskId = taskIdMatch[1];
    return allSpecs.find((spec) => spec.metadata.clickup_task_id === taskId) || null;
  }

  // Try to extract spec ID from branch name
  const specIdMatch = branchName.match(/(E\d+(?:-F\d+)?(?:-T\d+)?(?:-S\d+)?)/);

  if (specIdMatch && specIdMatch[1]) {
    return allSpecs.find((spec) => spec.specId === specIdMatch[1]) || null;
  }

  return null;
}

function getNextSpecsFromMergedPRs(allSpecs: SpecFile[], limit = 10): MergedPRSpec[] {
  try {
    // Check if gh CLI is available
    try {
      execSync('gh --version', { stdio: 'ignore' });
    } catch {
      console.error('⚠️  GitHub CLI (gh) is not installed or not in PATH');
      console.error('   Install from: https://cli.github.com/');
      if (isWSL()) {
        console.error('   WSL: Run `sudo apt install gh` or use the official install script');
      }
      return [];
    }

    const mergedPRs = execSync(
      `gh pr list --state merged --json number,headRefName --limit ${limit}`,
      {
        encoding: 'utf-8',
      },
    );

    const prs = JSON.parse(mergedPRs) as Array<{ number: number; headRefName: string }>;

    // Get all active worktrees to filter out specs already being worked on
    const activeWorktrees = getAllWorktrees();
    const activeSpecIds = new Set<string>();

    for (const worktree of activeWorktrees) {
      const spec = getSpecFromBranch(worktree.branch, allSpecs);
      if (spec) {
        activeSpecIds.add(spec.specId);
      }
    }

    // First pass: collect all completed specs from merged PRs
    const completedSpecs = new Set<string>();
    for (const pr of prs) {
      const spec = getSpecFromBranch(pr.headRefName, allSpecs);
      if (spec) {
        completedSpecs.add(spec.specId);
      }
    }

    // Second pass: collect next specs, excluding those already completed or in active worktrees
    const mergedPRSpecs: MergedPRSpec[] = [];
    const seenNextSpecs = new Set<string>();

    for (const pr of prs) {
      const spec = getSpecFromBranch(pr.headRefName, allSpecs);
      if (spec) {
        const nextSpec = findNextSpec(spec.specId, allSpecs);

        if (
          nextSpec &&
          !seenNextSpecs.has(nextSpec.specId) &&
          !completedSpecs.has(nextSpec.specId) && // Filter out already completed specs
          !activeSpecIds.has(nextSpec.specId) // Filter out specs in active worktrees
        ) {
          seenNextSpecs.add(nextSpec.specId);
          mergedPRSpecs.push({
            prNumber: pr.number,
            branch: pr.headRefName,
            specId: spec.specId,
            nextSpec,
          });
        }
      }
    }

    return mergedPRSpecs;
  } catch (error) {
    console.error('⚠️  Error getting merged PRs:', error);
    return [];
  }
}

async function selectNextSpecs(candidates: SpecFile[]): Promise<SpecFile[]> {
  if (candidates.length === 0) {
    return [];
  }

  if (candidates.length === 1) {
    return [candidates[0]].filter((s): s is SpecFile => s !== undefined);
  }

  console.log('\n📋 Multiple next specs available:\n');

  candidates.forEach((spec, index) => {
    console.log(`  ${index + 1}. ${spec.specId}: ${spec.metadata.title}`);
  });

  console.log('\n❓ Select specs to work on (comma-separated, e.g., "1,2,3" or single "1"): ');

  const readline = await import('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const answer = await new Promise<string>((resolve) => {
    rl.question('', (input) => {
      rl.close();
      resolve(input.trim());
    });
  });

  // Parse comma-separated input
  const selectedIndices = answer
    .split(',')
    .map((s) => parseInt(s.trim(), 10) - 1)
    .filter((i) => i >= 0 && i < candidates.length);

  if (selectedIndices.length > 0) {
    return selectedIndices.map((i) => candidates[i]).filter((s): s is SpecFile => s !== undefined);
  }

  console.log('\n⚠️  Invalid selection, using first option\n');
  return [candidates[0]].filter((s): s is SpecFile => s !== undefined);
}

// ============================================================================
// Main Logic
// ============================================================================

async function main() {
  const args = process.argv.slice(2);
  const skipCleanup = args.includes('--skip-cleanup');
  const cleanupOnly = args.includes('--cleanup-only');
  const autoConfirm = args.includes('--yes') || args.includes('-y');
  const limitArg = args.find((arg) => arg.startsWith('--limit='))?.split('=')[1];
  const prLimit = limitArg ? parseInt(limitArg, 10) : 10;

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: yarn spec:next [OPTIONS]

Options:
  --cleanup-only  Only cleanup merged worktrees, don't create new ones
  --skip-cleanup  Skip cleaning up merged worktrees
  --limit=<N>     Number of recent merged PRs to check (default: 10)
  -y, --yes       Auto-confirm without prompting
  -h, --help      Show this help message

Description:
  Automates the workflow of transitioning to the next spec:
  1. Cleans up worktrees for merged PRs (unless --skip-cleanup)
  2. Finds the next sequential spec file
  3. Shows execution plan and asks for confirmation (unless --yes)
  4. Updates ClickUp task status to "IN PROGRESS"
  5. Creates worktree for the next spec

Examples:
  # Interactive mode (shows plan, asks for confirmation)
  yarn spec:next

  # Auto-confirm without prompting
  yarn spec:next --yes

  # Only cleanup merged worktrees, don't create new ones
  yarn spec:next --cleanup-only

  # Cleanup merged worktrees with auto-confirm
  yarn spec:next --cleanup-only --yes

  # Skip worktree cleanup
  yarn spec:next --skip-cleanup
    `);
    return;
  }

  console.log('🚀 Next Spec Workflow Automation\n');
  console.log('='.repeat(70));

  // Handle cleanup-only mode
  if (cleanupOnly) {
    console.log('🧹 Cleanup-Only Mode\n');
    console.log('='.repeat(70));

    const cleanupPlan = await selectWorktreesToCleanup(true);

    if (cleanupPlan.worktreesToRemove.length === 0) {
      console.log('\n✨ No merged worktrees to cleanup');
      return;
    }

    // Show execution plan
    console.log('\n📝 Execution Plan:');
    console.log('='.repeat(70));
    console.log('Cleanup worktrees:');
    for (const worktree of cleanupPlan.worktreesToRemove) {
      const displayPath = isWSL() ? wslPathToWindows(worktree.path) : worktree.path;
      console.log(`   🗑️  ${displayPath}`);
    }
    console.log('='.repeat(70));

    // Ask for confirmation (unless --yes)
    if (!autoConfirm) {
      console.log('\n❓ Proceed with cleanup? (Y/n): ');

      const readline = await import('readline');
      const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
      });

      const answer = await new Promise<string>((resolve) => {
        rl.question('', (input) => {
          rl.close();
          resolve(input.trim().toLowerCase());
        });
      });

      // Default to 'y' if empty input
      if (answer && answer !== 'y' && answer !== 'yes') {
        console.log('\n⊘ Cleanup cancelled by user');
        return;
      }
    } else {
      console.log('\n✅ Auto-confirming (--yes flag)\n');
    }

    // Execute cleanup
    executeCleanup(cleanupPlan);

    console.log('\n✨ Cleanup complete!');
    return;
  }

  // Step 1: Interactive worktree cleanup selection
  let cleanupPlan: WorktreeCleanupPlan = { worktreesToRemove: [], totalMergedPRs: 0 };

  if (!skipCleanup) {
    cleanupPlan = await selectWorktreesToCleanup();
  }

  // Step 2: Get all specs
  const specsDir = path.join(__dirname, '../../specs');
  const allSpecs = getAllSpecFiles(specsDir);

  console.log(`\n📚 Total implementable specs found: ${allSpecs.length}\n`);

  // Step 3: Find next specs from merged PRs
  console.log(`🔍 Analyzing last ${prLimit} merged PRs for next specs...\n`);

  const mergedPRSpecs = getNextSpecsFromMergedPRs(allSpecs, prLimit);

  if (mergedPRSpecs.length > 0) {
    console.log(`  📋 Found ${mergedPRSpecs.length} next spec(s) from merged PRs:\n`);

    mergedPRSpecs.forEach((m) => {
      console.log(
        `     PR #${m.prNumber} (${m.specId}) → ${m.nextSpec?.specId}: ${m.nextSpec?.metadata.title}`,
      );
    });

    console.log('');
  } else {
    console.log('  ℹ️  No merged PRs with identifiable specs found\n');
  }

  // Step 4: Select next specs (can be multiple)
  let nextSpecs: SpecFile[] = [];

  const nextSpecCandidates = mergedPRSpecs
    .map((m) => m.nextSpec)
    .filter((s): s is SpecFile => s !== null);

  if (nextSpecCandidates.length > 0) {
    nextSpecs = await selectNextSpecs(nextSpecCandidates);
  } else {
    // Fallback: try to detect current spec from branch
    try {
      const currentBranch = execSync('git branch --show-current', { encoding: 'utf-8' }).trim();
      const currentSpecFile = getSpecFromBranch(currentBranch, allSpecs);

      if (currentSpecFile) {
        console.log(`  📍 Current spec: ${currentSpecFile.specId}\n`);
        const nextSpec = findNextSpec(currentSpecFile.specId, allSpecs);
        if (nextSpec) {
          nextSpecs = [nextSpec];
        }
      } else {
        console.log('  ℹ️  No current spec detected, showing first spec\n');
        const firstSpec = allSpecs[0];
        if (firstSpec) {
          nextSpecs = [firstSpec];
        }
      }
    } catch {
      console.log('  ℹ️  Using first spec\n');
      const firstSpec = allSpecs[0];
      if (firstSpec) {
        nextSpecs = [firstSpec];
      }
    }
  }

  if (nextSpecs.length === 0) {
    console.log('\n❌ No next spec found');

    // Execute cleanup even if no next spec found
    if (!skipCleanup && cleanupPlan.worktreesToRemove.length > 0) {
      console.log('\n📝 Proceeding with cleanup only...\n');
      executeCleanup(cleanupPlan);
    }

    return;
  }

  // Validate all specs have ClickUp task IDs
  const specsWithoutTaskId = nextSpecs.filter((spec) => !spec.metadata.clickup_task_id);
  if (specsWithoutTaskId.length > 0) {
    console.log('\n⚠️  Some specs are missing ClickUp Task ID:');
    specsWithoutTaskId.forEach((spec) => {
      console.log(`   - ${spec.specId}: ${spec.metadata.title}`);
    });
    console.log('   Run migration script to add clickup_task_id to specs');
    return;
  }

  // Show details for all selected specs
  console.log(`\n${'='.repeat(70)}`);
  console.log(`📋 Selected Specs (${nextSpecs.length})`);
  console.log('='.repeat(70));
  nextSpecs.forEach((spec, index) => {
    console.log(`\n${index + 1}. ${spec.specId}: ${spec.metadata.title}`);
    console.log(`   Type: ${spec.metadata.type}`);
    console.log(`   ClickUp Task ID: ${spec.metadata.clickup_task_id}`);
    console.log(`   Path: ${path.relative(process.cwd(), spec.path)}`);
  });
  console.log(`\n${'='.repeat(70)}`);

  // Prepare execution plans for all specs
  interface WorktreePlan {
    spec: SpecFile;
    branchName: string;
    worktreePath: string;
    displayPath?: string;
  }

  const worktreePlans: WorktreePlan[] = nextSpecs.map((spec) => {
    const fullTitle = `${spec.specId}: ${spec.metadata.title}`;
    const sanitizedTitle = fullTitle.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    const branchName = sanitizedTitle;

    // On native Windows, convert backslashes to forward slashes for bash compatibility
    let worktreePath = path.join(__dirname, '../../../worktrees', branchName);
    if (os.platform() === 'win32' && !isWSL()) {
      worktreePath = worktreePath.replace(/\\/g, '/');
    }

    // Convert to Windows path if in WSL for display purposes
    const displayPath = isWSL() ? wslPathToWindows(worktreePath) : worktreePath;

    return { spec, branchName, worktreePath, displayPath };
  });

  // Step 5: Show execution plan
  console.log('\n📝 Execution Plan:');
  console.log('='.repeat(70));

  if (cleanupPlan.worktreesToRemove.length > 0) {
    console.log('1. Cleanup worktrees:');
    for (const worktree of cleanupPlan.worktreesToRemove) {
      const displayPath = isWSL() ? wslPathToWindows(worktree.path) : worktree.path;
      console.log(`   🗑️  ${displayPath}`);
    }
    console.log('');
  }

  console.log(`2. Create ${worktreePlans.length} worktree(s):`);
  worktreePlans.forEach((plan, index) => {
    console.log(`\n   ${index + 1}. ${plan.spec.specId}`);
    console.log(`      Branch: ${plan.branchName}`);
    console.log(`      Path: ${plan.displayPath || plan.worktreePath}`);
    console.log(`      TaskId: ${plan.spec.metadata.clickup_task_id}`);
    console.log(`      Status: → IN PROGRESS`);
  });
  console.log(`\n${'='.repeat(70)}`);

  // Step 5: Ask for confirmation (unless --yes)
  if (!autoConfirm) {
    console.log('\n❓ Proceed with this workflow? (Y/n): ');

    const readline = await import('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    const answer = await new Promise<string>((resolve) => {
      rl.question('', (input) => {
        rl.close();
        resolve(input.trim().toLowerCase());
      });
    });

    // Default to 'y' if empty input
    if (answer && answer !== 'y' && answer !== 'yes') {
      console.log('\n⊘ Workflow cancelled by user');
      return;
    }
  } else {
    console.log('\n✅ Auto-confirming (--yes flag)\n');
  }

  const client = new ClickUpClient(CLICKUP_API_KEY!);

  // Step 6: Execute cleanup if planned
  if (!skipCleanup && cleanupPlan.worktreesToRemove.length > 0) {
    executeCleanup(cleanupPlan);
  }

  const scriptPath = path.join(__dirname, 'create-worktree.sh');

  // Step 7: Process all worktrees in parallel
  console.log(`\n${'='.repeat(70)}`);
  console.log(`🚀 Creating ${worktreePlans.length} worktree(s) in parallel...`);
  console.log('='.repeat(70));

  const results = await Promise.allSettled(
    worktreePlans.map(async (plan, index) => {
      const logPrefix = `[${index + 1}/${worktreePlans.length}] ${plan.spec.specId}`;

      try {
        // Update ClickUp task status
        console.log(`\n${logPrefix}: Updating ClickUp status...`);
        await client.updateTaskStatus(plan.spec.metadata.clickup_task_id!, 'IN PROGRESS');
        console.log(`${logPrefix}: ✅ ClickUp status updated`);

        // Create worktree
        console.log(`${logPrefix}: Creating worktree...`);

        const shellCmd = getShellCommand(scriptPath, [
          '-b',
          `"${plan.branchName}"`,
          '-t',
          `"${plan.spec.metadata.clickup_task_id!}"`,
          '--no-install',
          '--force',
          `"${plan.worktreePath}"`,
        ]);

        execSync(shellCmd, {
          encoding: 'utf-8',
          stdio: 'inherit',
          cwd: path.join(__dirname, '../..'),
        });
        console.log(`${logPrefix}: ✅ Worktree created`);

        // Create VS Code task for launching claude
        const vscodeDir = path.join(plan.worktreePath, '.vscode');
        const tasksPath = path.join(vscodeDir, 'tasks.json');

        if (!fs.existsSync(vscodeDir)) {
          fs.mkdirSync(vscodeDir, { recursive: true });
        }

        const tasksConfig = {
          version: '2.0.0',
          tasks: [
            {
              label: 'Start Claude',
              type: 'shell',
              command: 'claude',
              presentation: {
                echo: true,
                reveal: 'always',
                focus: true,
                panel: 'new',
              },
              problemMatcher: [],
              runOptions: {
                runOn: 'folderOpen',
              },
            },
          ],
        };

        fs.writeFileSync(tasksPath, JSON.stringify(tasksConfig, null, 2));
        console.log(`${logPrefix}: ✅ VS Code task created`);

        // Open VS Code in new window - use Windows path if in WSL
        const vscodePath = plan.displayPath || plan.worktreePath;
        console.log(`${logPrefix}: Opening VS Code with auto-start task...`);
        execSync(`code -n "${vscodePath}"`, { stdio: 'ignore' });
        console.log(`${logPrefix}: ✅ VS Code opened (claude will auto-start)`);
        console.log(`${logPrefix}: 💡 Task 'Start Claude' is set to run on folder open`);

        // Wait a bit for VS Code to fully load, then try to trigger the task
        await new Promise((resolve) => globalThis.setTimeout(resolve, 2000));

        try {
          execSync(
            `code -r "${vscodePath}" --command "workbench.action.tasks.runTask" --args "Start Claude"`,
            {
              stdio: 'ignore',
            },
          );
          console.log(`${logPrefix}: ✅ Claude task triggered`);
        } catch (e) {
          console.log(
            `${logPrefix}: ⚠️  Manual task trigger failed, but task will auto-run on folder open`,
          );
        }

        return { success: true, spec: plan.spec.specId, path: plan.worktreePath };
      } catch (error) {
        console.error(`${logPrefix}: ❌ Failed -`, error);
        return { success: false, spec: plan.spec.specId, error };
      }
    }),
  );

  // Collect results
  const createdWorktrees: string[] = [];
  const failedWorktrees: string[] = [];

  results.forEach((result) => {
    if (result.status === 'fulfilled') {
      if (result.value.success) {
        createdWorktrees.push((result.value as { success: true; spec: string; path: string }).path);
      } else {
        failedWorktrees.push(result.value.spec);
      }
    } else if (result.status === 'rejected') {
      failedWorktrees.push('Unknown spec');
    }
  });

  // Summary
  console.log(`\n${'='.repeat(70)}`);
  console.log('✨ Workflow Complete!');
  console.log('='.repeat(70));
  console.log(`\n📊 Summary:`);
  console.log(`  ✅ Created: ${createdWorktrees.length} worktree(s)`);
  if (failedWorktrees.length > 0) {
    console.log(`  ❌ Failed: ${failedWorktrees.length} worktree(s)`);
    console.log(`     ${failedWorktrees.join(', ')}`);
  }

  if (createdWorktrees.length > 0) {
    console.log(`\n📂 Created worktrees:`);
    createdWorktrees.forEach((wt) => {
      const displayPath = isWSL() ? wslPathToWindows(wt) : wt;
      console.log(`  - ${displayPath}`);
    });
  }

  console.log('');
}

main().catch((error) => {
  console.error('❌ Unexpected error:', error);
  process.exit(1);
});
