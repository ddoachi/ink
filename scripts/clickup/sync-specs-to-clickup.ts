#!/usr/bin/env ts-node

/**
 * Sync Spec Files to ClickUp (Generalized)
 *
 * Syncs any epic, feature, task, or subtask from spec files to ClickUp.
 * Automatically detects spec type from ID structure.
 * Creates hierarchical structure: Epic → Folder, Feature → List, Task → Task, Subtask → Subtask
 *
 * Prerequisites:
 * - CLICKUP_API_KEY must be set in .env.local
 *
 * Usage:
 *   yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02
 *   yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02-F01
 *   yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02-F01-T01
 *   yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02 --dry-run
 */

import axios, { AxiosInstance } from 'axios';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';

// Load environment variables from .env.local if not already loaded
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

// Default space name for this project (can be overridden with --space or CLICKUP_SPACE_NAME env)
const DEFAULT_SPACE_NAME = 'Ink';
const CLICKUP_SPACE_NAME = process.env['CLICKUP_SPACE_NAME'] || DEFAULT_SPACE_NAME;

if (!CLICKUP_API_KEY) {
  console.error('❌ CLICKUP_API_KEY not found in .env.local');
  process.exit(1);
}

// ============================================================================
// Types
// ============================================================================

interface SpecMetadata {
  id: string;
  clickup_task_id?: string;
  title: string;
  type: 'epic' | 'feature' | 'task' | 'subtask' | 'extension';
  parent: string;
  children: string[];
  epic: string;
  domain: string;
  status: string;
  priority: string;
  created: string;
  updated: string;
  due_date?: string;
  estimated_hours: number;
  actual_hours: number;
  tags: string[];
  effort?: string;
  risk?: string;
}

interface ClickUpList {
  id: string;
  name: string;
  folder?: {
    id: string;
  };
}

interface ClickUpTask {
  id: string;
  name: string;
  description?: string;
  status: {
    status: string;
  };
  priority: {
    priority: string;
  };
  custom_fields: Array<{
    id: string;
    name: string;
    value: unknown;
  }>;
  list?: {
    id: string;
  };
}

interface ClickUpFolder {
  id: string;
  name: string;
}

interface SpecIdParts {
  epic: string;
  feature?: string;
  task?: string;
  subtask?: string;
  extension?: string;
  level: 'epic' | 'feature' | 'task' | 'subtask' | 'extension';
}

// ============================================================================
// Spec ID Parsing
// ============================================================================

function parseSpecId(specId: string): SpecIdParts | null {
  // Pattern: E##-F##-T##-S##-X## (extension is optional)
  const match = specId.match(/^(E\d+)(?:-(F\d+))?(?:-(T\d+))?(?:-(S\d+))?(?:-(X\d+))?$/);

  if (!match) {
    return null;
  }

  const [, epic, feature, task, subtask, extension] = match;

  if (!epic) {
    return null;
  }

  let level: 'epic' | 'feature' | 'task' | 'subtask' | 'extension';
  if (extension) {
    level = 'extension';
  } else if (subtask) {
    level = 'subtask';
  } else if (task) {
    level = 'task';
  } else if (feature) {
    level = 'feature';
  } else {
    level = 'epic';
  }

  return {
    epic,
    feature: feature || undefined,
    task: task || undefined,
    subtask: subtask || undefined,
    extension: extension || undefined,
    level,
  };
}

// ============================================================================
// ClickUp API Client
// ============================================================================

class ClickUpClient {
  private client: AxiosInstance;
  private lastRequestTime = 0;
  private minRequestInterval = 200; // 200ms between requests (5 req/sec max)

  constructor(apiKey: string) {
    this.client = axios.create({
      baseURL: CLICKUP_API_BASE,
      headers: {
        Authorization: apiKey,
        'Content-Type': 'application/json',
      },
    });

    // Add rate limiting interceptor
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

  // Get all teams (workspaces)
  async getTeams() {
    const response = await this.client.get('/team');
    return response.data.teams;
  }

  // Get all spaces in a team
  async getSpaces(teamId: string) {
    const response = await this.client.get(`/team/${teamId}/space`);
    return response.data.spaces;
  }

  // Get all folders in a space
  async getFolders(spaceId: string) {
    const response = await this.client.get(`/space/${spaceId}/folder`);
    return response.data.folders;
  }

  // Find folder by name (exact match)
  async findFolder(spaceId: string, folderName: string): Promise<ClickUpFolder | null> {
    const folders = await this.getFolders(spaceId);
    return folders.find((f: ClickUpFolder) => f.name === folderName) || null;
  }

  // Create a new folder
  async createFolder(spaceId: string, name: string) {
    const response = await this.client.post(`/space/${spaceId}/folder`, { name });
    return response.data;
  }

  // Get all lists in a folder
  async getLists(folderId: string) {
    const response = await this.client.get(`/folder/${folderId}/list`);
    return response.data.lists;
  }

  // Create a new list
  async createList(folderId: string, name: string, content?: string) {
    const response = await this.client.post(`/folder/${folderId}/list`, {
      name,
      content,
    });
    return response.data;
  }

  // Find list by name in folder (exact match)
  async findList(folderId: string, listName: string): Promise<ClickUpList | null> {
    const lists = await this.getLists(folderId);
    return lists.find((l: ClickUpList) => l.name === listName) || null;
  }

  // Create a task in a list
  async createTask(
    listId: string,
    taskData: {
      name: string;
      description?: string;
      status?: string;
      priority?: number;
      start_date?: number;
      due_date?: number;
      time_estimate?: number;
      tags?: string[];
    },
  ) {
    const response = await this.client.post(`/list/${listId}/task`, taskData);
    return response.data;
  }

  // Update a task (for setting parent/subtask relationship)
  async updateTask(
    taskId: string,
    updateData: {
      name?: string;
      description?: string;
      status?: string;
      priority?: number;
      parent?: string;
      tags?: string[];
    },
  ) {
    const response = await this.client.put(`/task/${taskId}`, updateData);
    return response.data;
  }

  // Get all tasks in a list
  async getTasks(listId: string) {
    const response = await this.client.get(`/list/${listId}/task`, {
      params: {
        include_closed: true,
        archived: false,
        subtasks: true,
      },
    });
    return response.data.tasks;
  }

  // Find task by custom task ID (e.g., E02-F01-T01)
  // Uses exact prefix match with colon to avoid matching subtasks
  async findTaskByCustomId(listId: string, customId: string): Promise<ClickUpTask | null> {
    const tasks = await this.getTasks(listId);
    return tasks.find((t: ClickUpTask) => t.name.startsWith(`${customId}:`)) || null;
  }

  // Get a task by ID (for debugging)
  async getTaskById(taskId: string) {
    try {
      const response = await this.client.get(`/task/${taskId}`);
      return response.data;
    } catch (error) {
      console.error(`❌ Failed to get task ${taskId}:`, error);
      return null;
    }
  }

  // Get subtasks of a task
  async getSubtasks(taskId: string) {
    const response = await this.client.get(`/task/${taskId}`);
    return response.data.subtasks || [];
  }

  // Find subtask by custom ID in a list
  // Subtasks are regular tasks in the list with a parent relationship
  // Uses exact prefix match with colon to avoid partial matches
  async findSubtaskByCustomId(listId: string, customId: string): Promise<ClickUpTask | null> {
    const tasks = await this.getTasks(listId);
    return tasks.find((t: ClickUpTask) => t.name.startsWith(`${customId}:`)) || null;
  }

  // Get custom fields for a list
  async getListCustomFields(listId: string) {
    const response = await this.client.get(`/list/${listId}/field`);
    return response.data.fields;
  }

  // Set a custom field value for a task
  async setTaskCustomField(taskId: string, fieldId: string, value: string) {
    const response = await this.client.post(`/task/${taskId}/field/${fieldId}`, {
      value,
    });
    return response.data;
  }
}

// ============================================================================
// Spec File Parsing
// ============================================================================

interface SpecData {
  metadata: SpecMetadata;
  fullContent: string;
  markdownContent: string;
}

function parseSpecFile(filePath: string): SpecData | null {
  try {
    const fullContent = fs.readFileSync(filePath, 'utf-8');

    // Extract YAML frontmatter
    const frontmatterMatch = fullContent.match(/^---\n([\s\S]*?)\n---/);
    if (!frontmatterMatch || !frontmatterMatch[1]) {
      console.warn(`⚠️  No frontmatter found in ${filePath}`);
      return null;
    }

    const metadata = yaml.load(frontmatterMatch[1]) as SpecMetadata;

    // Extract markdown content (everything after frontmatter)
    const markdownContent = fullContent.substring(frontmatterMatch[0].length).trim();

    return {
      metadata,
      fullContent,
      markdownContent,
    };
  } catch (error) {
    console.error(`❌ Error parsing ${filePath}:`, error);
    return null;
  }
}

function getAllSpecFiles(baseDir: string): Map<string, SpecData> {
  const specs = new Map<string, SpecData>();

  function scanDirectory(dir: string): void {
    if (!fs.existsSync(dir)) return;

    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        // Skip archive directories to avoid legacy specs overwriting current ones
        if (entry.name === 'archive') {
          continue;
        }
        scanDirectory(fullPath);
      } else if (entry.name.endsWith('.spec.md')) {
        const specData = parseSpecFile(fullPath);
        if (specData) {
          // Extract spec ID from filename (including extensions like -X01)
          const specIdMatch = entry.name.match(/(E\d+(?:-F\d+)?(?:-T\d+)?(?:-S\d+)?(?:-X\d+)?)/);
          if (specIdMatch && specIdMatch[1]) {
            specs.set(specIdMatch[1], specData);
          }
        }
      }
    }
  }

  scanDirectory(baseDir);
  return specs;
}

// ============================================================================
// ClickUp Mapping Functions
// ============================================================================

function mapPriorityToClickUp(priority: string): number {
  const priorityMap: Record<string, number> = {
    urgent: 1,
    critical: 1,
    high: 2,
    normal: 3,
    medium: 3,
    low: 4,
  };
  return priorityMap[priority.toLowerCase()] || 3;
}

function mapStatusToClickUp(status: string): string {
  const statusMap: Record<string, string> = {
    draft: 'DRAFT',
    planned: 'PLANNED',
    'in-progress': 'IN PROGRESS',
    in_progress: 'IN PROGRESS',
    completed: 'COMPLETE',
    complete: 'COMPLETE',
    blocked: 'BLOCKED',
    review: 'REVIEW',
    testing: 'TESTING',
    cancelled: 'CANCELLED',
    canceled: 'CANCELLED', // US spelling
    abandoned: 'CANCELLED', // Alias for cancelled
  };
  return statusMap[status.toLowerCase()] || 'DRAFT';
}

/**
 * Get the priority order of a status (higher number = more advanced in workflow)
 * This prevents downgrading from COMPLETE to PLANNED, for example.
 */
function getStatusPriority(status: string): number {
  const statusPriority: Record<string, number> = {
    DRAFT: 1,
    PLANNED: 2,
    BLOCKED: 3,
    'IN PROGRESS': 4,
    REVIEW: 5,
    TESTING: 6,
    COMPLETE: 7,
    CANCELLED: 0, // Special case: can always transition to/from cancelled
  };
  return statusPriority[status] ?? 0;
}

/**
 * Check if changing from currentStatus to newStatus would be a downgrade.
 * A downgrade is when a task that is already COMPLETE would be changed to a lower status.
 * This prevents the sync from overwriting completed tasks with outdated spec file status.
 */
function isStatusDowngrade(currentStatus: string, newStatus: string): boolean {
  // Allow transitions to/from CANCELLED
  if (currentStatus === 'CANCELLED' || newStatus === 'CANCELLED') {
    return false;
  }

  const currentPriority = getStatusPriority(currentStatus);
  const newPriority = getStatusPriority(newStatus);

  // It's a downgrade if we're moving from a higher priority to a lower one
  return currentPriority > newPriority;
}

function parseDate(dateStr: string): number | undefined {
  if (!dateStr) return undefined;
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? undefined : date.getTime();
}

function hoursToMilliseconds(hours: number): number {
  return hours * 60 * 60 * 1000;
}

function sanitizeTitle(title: string): string {
  return title.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function getGitUsername(): string {
  try {
    return execSync('git config user.name', { encoding: 'utf-8' }).trim();
  } catch {
    return 'unknown';
  }
}

function extractSpecIdFromTitle(title: string): string | null {
  const match = title.match(/^(E\d+(?:-F\d+)?(?:-T\d+)?(?:-S\d+)?)/);
  return match ? (match[1] ?? null) : null;
}

function updateSpecFileWithTaskId(specId: string, clickupTaskId: string): boolean {
  try {
    const parts = parseSpecId(specId);
    if (!parts) {
      console.error(`    ⚠️  Invalid spec ID: ${specId}`);
      return false;
    }

    // Construct file path
    const pathParts = [parts.epic];
    if (parts.feature) pathParts.push(parts.feature);
    if (parts.task) pathParts.push(parts.task);
    if (parts.subtask) pathParts.push(parts.subtask);
    if (parts.extension) pathParts.push(parts.extension);

    const specFilePath = path.join(__dirname, '../../specs', ...pathParts, `${specId}.spec.md`);

    if (!fs.existsSync(specFilePath)) {
      console.error(`    ⚠️  Spec file not found: ${specFilePath}`);
      return false;
    }

    // Read current file
    const content = fs.readFileSync(specFilePath, 'utf-8');

    // Check if clickup_task_id already has a non-empty value
    const existingIdMatch = content.match(/clickup_task_id:\s*'([^']+)'/);
    if (existingIdMatch && existingIdMatch[1] && existingIdMatch[1].trim() !== '') {
      console.log(
        `    ℹ️  clickup_task_id already set to '${existingIdMatch[1]}' in ${specId}, skipping`,
      );
      return false;
    }

    // Find where to insert or update clickup_task_id
    const lines = content.split('\n');
    let updated = false;

    // First, try to find and update existing clickup_task_id line
    for (let i = 0; i < lines.length; i++) {
      if (lines[i]?.match(/^clickup_task_id:/)) {
        lines[i] = `clickup_task_id: '${clickupTaskId}'`;
        updated = true;
        break;
      }
    }

    // If not found, insert after id: line
    if (!updated) {
      let insertIndex = -1;
      for (let i = 0; i < lines.length; i++) {
        if (lines[i]?.match(/^id:\s+/)) {
          insertIndex = i + 1;
          break;
        }
      }

      if (insertIndex === -1) {
        console.error(`    ⚠️  Could not find 'id:' line in ${specId}`);
        return false;
      }

      // Insert clickup_task_id after id
      lines.splice(insertIndex, 0, `clickup_task_id: '${clickupTaskId}'`);
    }

    // Write back to file
    fs.writeFileSync(specFilePath, lines.join('\n'), 'utf-8');

    const action = updated ? 'Updated' : 'Added';
    console.log(`    ✅ ${action} clickup_task_id '${clickupTaskId}' to ${specId}`);
    return true;
  } catch (error) {
    console.error(`    ⚠️  Failed to update spec file for ${specId}:`, error);
    return false;
  }
}

async function createWorktreeFromTaskId(client: ClickUpClient, taskId: string): Promise<void> {
  console.log(`\n📂 Creating worktree for task: ${taskId}`);

  try {
    const task = await client.getTaskById(taskId);
    if (!task) {
      console.error(`❌ Task not found: ${taskId}`);
      return;
    }

    const sanitizedTitle = sanitizeTitle(task.name);
    const branchName = sanitizedTitle;
    const worktreePath = path.join(__dirname, '../../worktrees', branchName);
    const scriptPath = path.join(__dirname, '../development/create-worktree.sh');

    console.log(`📋 Title: ${task.name}`);
    console.log(`📋 Branch name: ${branchName}`);
    console.log(`📋 Task ID: ${taskId}`);

    execSync(`${scriptPath} -b ${branchName} -t ${taskId} ${worktreePath}`, {
      stdio: 'inherit',
      cwd: path.join(__dirname, '../..'),
    });

    console.log(`✅ Worktree created at: ${worktreePath}`);

    console.log(`\n🔄 Updating task status to IN PROGRESS...`);
    await client.updateTask(taskId, {
      status: 'IN PROGRESS',
    });

    console.log(`✅ Task status updated to IN PROGRESS`);
  } catch (error) {
    console.error(`❌ Failed to create worktree:`, error);
  }
}

async function markTaskCompleteWithPR(
  client: ClickUpClient,
  taskId: string,
  prNumber: number,
): Promise<void> {
  console.log(`\n🔄 Marking task ${taskId} as complete with PR #${prNumber}`);

  try {
    const task = await client.getTaskById(taskId);
    if (!task) {
      console.error(`❌ Task not found: ${taskId}`);
      return;
    }

    const prUrl = `https://github.com/ddoachi/jts/pull/${prNumber}`;
    console.log(`📋 Task: ${task.name}`);
    console.log(`🔗 PR URL: ${prUrl}`);

    if (!task.list || !task.list.id) {
      console.error(`❌ Cannot determine list ID for task: ${taskId}`);
      return;
    }

    const listId = task.list.id;
    const customFields = await client.getListCustomFields(listId);
    const prField = customFields.find((field: { name: string }) => field.name === 'Pull Request');

    if (!prField) {
      console.error(`❌ Custom field 'Pull Request' not found in list`);
      console.error(
        `   Available fields: ${customFields.map((f: { name: string }) => f.name).join(', ')}`,
      );
      return;
    }

    console.log(`📌 Setting Pull Request field: ${prField.name} (${prField.id})`);
    await client.setTaskCustomField(taskId, prField.id, prUrl);

    await client.updateTask(taskId, {
      status: 'COMPLETE',
    });

    console.log(`✅ Task marked as complete with PR link in GitHub field`);
  } catch (error) {
    console.error(`❌ Failed to mark task complete:`, error);
  }
}

// ============================================================================
// Sync Functions
// ============================================================================

async function syncEpic(
  client: ClickUpClient,
  spaceId: string,
  epicId: string,
  allSpecs: Map<string, SpecData>,
  dryRun: boolean,
): Promise<void> {
  const epicData = allSpecs.get(epicId);

  if (!epicData) {
    console.error(`❌ Epic spec not found: ${epicId}`);
    return;
  }

  const epicSpec = epicData.metadata;

  console.log(`\n${'='.repeat(70)}`);
  console.log(`📁 EPIC: ${epicId} - ${epicSpec.title}`);
  console.log(`${'='.repeat(70)}`);

  // Find or create folder for epic
  const folderName = `${epicId} - ${epicSpec.title}`;
  let folder = await client.findFolder(spaceId, folderName);

  if (folder) {
    console.log(`✅ Folder exists: ${folderName}`);
  } else {
    if (dryRun) {
      console.log(`🔍 [DRY RUN] Would create folder: ${folderName}`);
    } else {
      console.log(`📝 Creating folder: ${folderName}`);
      folder = await client.createFolder(spaceId, folderName);
      if (folder) {
        console.log(`✅ Created folder: ${folder.id}`);
      }
    }
  }

  if (!folder) {
    console.log(`⚠️  Skipping epic sync (folder doesn't exist in non-dry-run mode)`);
    return;
  }

  // Find all feature folders in the epic directory
  const epicDir = path.join(__dirname, '../../specs', epicId);
  const featureDirs = fs
    .readdirSync(epicDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.match(/^F\d+$/))
    .map((entry) => `${epicId}-${entry.name}`)
    .sort();

  console.log(`\n📋 Found ${featureDirs.length} features to sync`);

  for (const featureId of featureDirs) {
    await syncFeature(client, folder.id, featureId, allSpecs, dryRun);
  }
}

async function syncFeature(
  client: ClickUpClient,
  folderId: string,
  featureId: string,
  allSpecs: Map<string, SpecData>,
  dryRun: boolean,
): Promise<void> {
  const featureData = allSpecs.get(featureId);

  if (!featureData) {
    console.warn(`⚠️  Feature spec not found: ${featureId}`);
    return;
  }

  const featureSpec = featureData.metadata;

  console.log(`\n${'─'.repeat(60)}`);
  console.log(`📦 FEATURE: ${featureId} - ${featureSpec.title}`);
  console.log(`${'─'.repeat(60)}`);

  // Find or create list for feature
  // Use full feature ID (E##-F##) instead of just F##
  const listName = `${featureId}: ${featureSpec.title}`;
  let list = await client.findList(folderId, listName);

  if (list) {
    console.log(`✅ List exists: ${listName}`);
  } else {
    if (dryRun) {
      console.log(`🔍 [DRY RUN] Would create list: ${listName}`);
    } else {
      console.log(`📝 Creating list: ${listName}`);
      list = await client.createList(folderId, listName);
      if (list) {
        console.log(`✅ Created list: ${list.id}`);
      }
    }
  }

  if (!list) {
    console.log(`⚠️  Skipping feature sync (list doesn't exist in non-dry-run mode)`);
    return;
  }

  // Find all task folders in the feature directory
  const parts = parseSpecId(featureId);
  if (!parts || !parts.feature) {
    console.error(`❌ Invalid feature ID: ${featureId}`);
    return;
  }

  const featureDir = path.join(__dirname, '../../specs', parts.epic, parts.feature);
  const taskDirs = fs.existsSync(featureDir)
    ? fs
        .readdirSync(featureDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && entry.name.match(/^T\d+$/))
        .map((entry) => `${featureId}-${entry.name}`)
        .sort()
    : [];

  if (taskDirs.length === 0) {
    console.log(`ℹ️  No tasks found in ${featureId}`);
    return;
  }

  console.log(`\n📋 Found ${taskDirs.length} tasks to sync`);

  for (const taskId of taskDirs) {
    await syncTask(client, list.id, taskId, allSpecs, dryRun);
  }
}

async function syncTask(
  client: ClickUpClient,
  listId: string,
  taskId: string,
  allSpecs: Map<string, SpecData>,
  dryRun: boolean,
): Promise<void> {
  const taskData = allSpecs.get(taskId);

  if (!taskData) {
    console.warn(`  ⚠️  Task spec not found: ${taskId}`);
    return;
  }

  const taskSpec = taskData.metadata;

  // Check if task already exists
  const existingTask = await client.findTaskByCustomId(listId, taskId);

  if (existingTask) {
    console.log(`  ✅ Task exists: ${taskId} - ${taskSpec.title}`);

    // Check if task name needs to be updated
    const expectedName = `${taskId}: ${taskSpec.title}`;
    if (existingTask.name !== expectedName) {
      if (dryRun) {
        console.log(`    🔍 [DRY RUN] Would update name: "${existingTask.name}" → "${expectedName}"`);
      } else {
        console.log(`    🔄 Updating task name: "${existingTask.name}" → "${expectedName}"`);
        await client.updateTask(existingTask.id, { name: expectedName });
        console.log(`    ✅ Task name updated`);
      }
    }

    // Find all subtask folders in the task directory
    const parts = parseSpecId(taskId);
    let subtaskDirs: string[] = [];

    if (parts && parts.task) {
      const taskDir = path.join(
        __dirname,
        '../../specs',
        parts.epic,
        parts.feature || '',
        parts.task,
      );
      subtaskDirs = fs.existsSync(taskDir)
        ? fs
            .readdirSync(taskDir, { withFileTypes: true })
            .filter((entry) => entry.isDirectory() && entry.name.match(/^S\d+$/))
            .map((entry) => `${taskId}-${entry.name}`)
            .sort()
        : [];

      // Sync subtasks first
      if (subtaskDirs.length > 0) {
        for (const subtaskId of subtaskDirs) {
          await syncSubtask(client, listId, existingTask.id, subtaskId, allSpecs, dryRun);
        }
      }
    }

    // Determine the target status for the task
    const currentStatus = existingTask.status?.status;
    let newStatus = mapStatusToClickUp(taskSpec.status);

    // Auto-promote to COMPLETE if all children (subtasks) are COMPLETE
    if (subtaskDirs.length > 0) {
      const allChildrenComplete = subtaskDirs.every((subtaskId) => {
        const subtaskData = allSpecs.get(subtaskId);
        if (!subtaskData) return false;
        return mapStatusToClickUp(subtaskData.metadata.status) === 'COMPLETE';
      });

      if (allChildrenComplete && newStatus !== 'COMPLETE') {
        console.log(
          `    📈 All ${subtaskDirs.length} subtasks are COMPLETE, promoting parent to COMPLETE`,
        );
        newStatus = 'COMPLETE';
      }
    }

    // Update task status if it has changed (but don't downgrade)
    if (currentStatus !== newStatus) {
      // Check if this would be a downgrade (e.g., COMPLETE → PLANNED)
      if (isStatusDowngrade(currentStatus, newStatus)) {
        console.log(
          `    ⏭️  Skipping status downgrade: ${currentStatus} → ${newStatus} (keeping ${currentStatus})`,
        );
      } else if (dryRun) {
        console.log(`    🔍 [DRY RUN] Would update status: ${currentStatus} → ${newStatus}`);
      } else {
        console.log(`    🔄 Updating status: ${currentStatus} → ${newStatus}`);
        await client.updateTask(existingTask.id, {
          status: newStatus,
        });
        console.log(`    ✅ Status updated to ${newStatus}`);
      }
    }
  } else {
    if (dryRun) {
      console.log(`  🔍 [DRY RUN] Would create task: ${taskId} - ${taskSpec.title}`);
    } else {
      console.log(`  📝 Creating task: ${taskId} - ${taskSpec.title}`);

      const task = await client.createTask(listId, {
        name: `${taskId}: ${taskSpec.title}`,
        description: taskData.markdownContent,
        status: mapStatusToClickUp(taskSpec.status),
        priority: mapPriorityToClickUp(taskSpec.priority),
        start_date: parseDate(taskSpec.created),
        time_estimate: hoursToMilliseconds(taskSpec.estimated_hours),
        tags: taskSpec.tags || [],
      });

      console.log(`    📌 Time Estimate: ${taskSpec.estimated_hours}h, Start: ${taskSpec.created}`);

      console.log(`  ✅ Created task: ${task.id}`);

      // Write clickup_task_id back to spec file
      updateSpecFileWithTaskId(taskId, task.id);

      // Find all subtask folders in the task directory
      const parts = parseSpecId(taskId);
      if (parts && parts.task) {
        const taskDir = path.join(
          __dirname,
          '../../specs',
          parts.epic,
          parts.feature || '',
          parts.task,
        );
        const subtaskDirs = fs.existsSync(taskDir)
          ? fs
              .readdirSync(taskDir, { withFileTypes: true })
              .filter((entry) => entry.isDirectory() && entry.name.match(/^S\d+$/))
              .map((entry) => `${taskId}-${entry.name}`)
              .sort()
          : [];

        if (subtaskDirs.length > 0) {
          console.log(`    📎 Found ${subtaskDirs.length} subtasks`);

          for (const subtaskId of subtaskDirs) {
            await syncSubtask(client, listId, task.id, subtaskId, allSpecs, dryRun);
          }
        }
      }
    }
  }
}

async function syncSubtask(
  client: ClickUpClient,
  listId: string,
  parentTaskId: string,
  subtaskId: string,
  allSpecs: Map<string, SpecData>,
  dryRun: boolean,
): Promise<void> {
  const subtaskData = allSpecs.get(subtaskId);

  if (!subtaskData) {
    console.warn(`    ⚠️  Subtask spec not found: ${subtaskId}`);
    return;
  }

  const subtaskSpec = subtaskData.metadata;

  // Check if subtask already exists
  const existingSubtask = await client.findSubtaskByCustomId(listId, subtaskId);

  if (existingSubtask) {
    console.log(`    ✅ Subtask exists: ${subtaskId} - ${subtaskSpec.title}`);

    // Check if subtask name needs to be updated
    const expectedName = `${subtaskId}: ${subtaskSpec.title}`;
    if (existingSubtask.name !== expectedName) {
      if (dryRun) {
        console.log(`      🔍 [DRY RUN] Would update name: "${existingSubtask.name}" → "${expectedName}"`);
      } else {
        console.log(`      🔄 Updating subtask name: "${existingSubtask.name}" → "${expectedName}"`);
        await client.updateTask(existingSubtask.id, { name: expectedName });
        console.log(`      ✅ Subtask name updated`);
      }
    }

    // Update subtask status if it has changed (but don't downgrade)
    const currentStatus = existingSubtask.status?.status;
    const newStatus = mapStatusToClickUp(subtaskSpec.status);

    if (currentStatus !== newStatus) {
      // Check if this would be a downgrade (e.g., COMPLETE → PLANNED)
      if (isStatusDowngrade(currentStatus, newStatus)) {
        console.log(
          `      ⏭️  Skipping status downgrade: ${currentStatus} → ${newStatus} (keeping ${currentStatus})`,
        );
      } else if (dryRun) {
        console.log(`      🔍 [DRY RUN] Would update status: ${currentStatus} → ${newStatus}`);
      } else {
        console.log(`      🔄 Updating status: ${currentStatus} → ${newStatus}`);
        await client.updateTask(existingSubtask.id, {
          status: newStatus,
        });
        console.log(`      ✅ Status updated to ${newStatus}`);
      }
    }
  } else {
    if (dryRun) {
      console.log(`    🔍 [DRY RUN] Would create subtask: ${subtaskId} - ${subtaskSpec.title}`);
    } else {
      console.log(`    📝 Creating subtask: ${subtaskId} - ${subtaskSpec.title}`);

      // Create subtask as a regular task in the same list
      const subtask = await client.createTask(listId, {
        name: `${subtaskId}: ${subtaskSpec.title}`,
        description: subtaskData.markdownContent,
        status: mapStatusToClickUp(subtaskSpec.status),
        priority: mapPriorityToClickUp(subtaskSpec.priority),
        start_date: parseDate(subtaskSpec.created),
        time_estimate: hoursToMilliseconds(subtaskSpec.estimated_hours),
        tags: subtaskSpec.tags || [],
      });

      console.log(
        `      📌 Time Estimate: ${subtaskSpec.estimated_hours}h, Start: ${subtaskSpec.created}`,
      );

      // Set parent to make it a subtask
      await client.updateTask(subtask.id, {
        parent: parentTaskId,
      });

      console.log(`    ✅ Created subtask: ${subtask.id}`);

      // Write clickup_task_id back to spec file
      updateSpecFileWithTaskId(subtaskId, subtask.id);
    }
  }
}

async function syncExtension(
  client: ClickUpClient,
  listId: string,
  parentSubtaskId: string,
  extensionId: string,
  allSpecs: Map<string, SpecData>,
  dryRun: boolean,
): Promise<void> {
  const extensionData = allSpecs.get(extensionId);

  if (!extensionData) {
    console.warn(`      ⚠️  Extension spec not found: ${extensionId}`);
    return;
  }

  const extensionSpec = extensionData.metadata;

  // Check if extension already exists
  const existingExtension = await client.findSubtaskByCustomId(listId, extensionId);

  if (existingExtension) {
    console.log(`      ✅ Extension exists: ${extensionId} - ${extensionSpec.title}`);

    // Check if extension name needs to be updated
    const expectedName = `${extensionId}: ${extensionSpec.title}`;
    if (existingExtension.name !== expectedName) {
      if (dryRun) {
        console.log(`        🔍 [DRY RUN] Would update name: "${existingExtension.name}" → "${expectedName}"`);
      } else {
        console.log(`        🔄 Updating extension name: "${existingExtension.name}" → "${expectedName}"`);
        await client.updateTask(existingExtension.id, { name: expectedName });
        console.log(`        ✅ Extension name updated`);
      }
    }

    // Update extension status if it has changed (but don't downgrade)
    const currentStatus = existingExtension.status?.status;
    const newStatus = mapStatusToClickUp(extensionSpec.status);

    if (currentStatus !== newStatus) {
      // Check if this would be a downgrade (e.g., COMPLETE → PLANNED)
      if (isStatusDowngrade(currentStatus, newStatus)) {
        console.log(
          `        ⏭️  Skipping status downgrade: ${currentStatus} → ${newStatus} (keeping ${currentStatus})`,
        );
      } else if (dryRun) {
        console.log(`        🔍 [DRY RUN] Would update status: ${currentStatus} → ${newStatus}`);
      } else {
        console.log(`        🔄 Updating status: ${currentStatus} → ${newStatus}`);
        await client.updateTask(existingExtension.id, {
          status: newStatus,
        });
        console.log(`        ✅ Status updated to ${newStatus}`);
      }
    }
  } else {
    if (dryRun) {
      console.log(`      🔍 [DRY RUN] Would create extension: ${extensionId} - ${extensionSpec.title}`);
    } else {
      console.log(`      📝 Creating extension: ${extensionId} - ${extensionSpec.title}`);

      // Create extension as a task in the same list
      const extension = await client.createTask(listId, {
        name: `${extensionId}: ${extensionSpec.title}`,
        description: extensionData.markdownContent,
        status: mapStatusToClickUp(extensionSpec.status),
        priority: mapPriorityToClickUp(extensionSpec.priority),
        start_date: parseDate(extensionSpec.created),
        time_estimate: hoursToMilliseconds(extensionSpec.estimated_hours),
        tags: extensionSpec.tags || [],
      });

      console.log(
        `        📌 Time Estimate: ${extensionSpec.estimated_hours}h, Start: ${extensionSpec.created}`,
      );

      // Set parent to the subtask to make it a sub-subtask
      await client.updateTask(extension.id, {
        parent: parentSubtaskId,
      });

      console.log(`      ✅ Created extension: ${extension.id}`);

      // Write clickup_task_id back to spec file
      updateSpecFileWithTaskId(extensionId, extension.id);
    }
  }
}

// ============================================================================
// Main Sync Logic
// ============================================================================

async function syncToClickUp(options: {
  spec?: string;
  dryRun?: boolean;
  spaceId?: string;
  taskId?: string;
  createWorktree?: boolean;
  prNumber?: number;
}) {
  const {
    spec,
    dryRun = false,
    spaceId = null,
    taskId,
    createWorktree = false,
    prNumber,
  } = options;

  if (!CLICKUP_API_KEY) {
    console.error('❌ CLICKUP_API_KEY is required');
    return;
  }

  const client = new ClickUpClient(CLICKUP_API_KEY);

  // Handle --id with --create-worktree
  if (taskId && createWorktree) {
    await createWorktreeFromTaskId(client, taskId);
    return;
  }

  // Handle --id with --pr
  if (taskId && prNumber) {
    await markTaskCompleteWithPR(client, taskId, prNumber);
    return;
  }

  // Error if --id is used without --create-worktree or --pr
  if (taskId) {
    console.error('❌ --id must be used with either --create-worktree or --pr=<number>');
    return;
  }

  console.log('🚀 Starting Spec Sync to ClickUp\n');

  // Step 1: Get workspace/space structure
  console.log('📋 Fetching ClickUp workspace structure...');
  const teams = await client.getTeams();

  if (teams.length === 0) {
    console.error('❌ No teams found in ClickUp');
    return;
  }

  const team = teams[0];
  console.log(`✅ Using team: ${team.name} (${team.id})`);

  const spaces = await client.getSpaces(team.id);

  if (spaces.length === 0) {
    console.error('❌ No spaces found in team');
    return;
  }

  // Space selection priority:
  // 1. --space=<id-or-name> CLI argument
  // 2. CLICKUP_SPACE_NAME environment variable (default: "Ink")
  // 3. First space as fallback
  let space: { id: string; name: string } | undefined;

  if (spaceId) {
    // Try to find by ID first, then by name
    space = spaces.find((s: { id: string; name: string }) => s.id === spaceId);
    if (!space) {
      space = spaces.find((s: { id: string; name: string }) => s.name === spaceId);
    }
    if (!space) {
      console.error(`❌ Space not found: ${spaceId}`);
      console.log(`   Available spaces: ${spaces.map((s: { name: string }) => s.name).join(', ')}`);
      return;
    }
  } else {
    // Use CLICKUP_SPACE_NAME (defaults to "Ink")
    space = spaces.find((s: { id: string; name: string }) => s.name === CLICKUP_SPACE_NAME);
    if (!space) {
      console.warn(`⚠️  Space "${CLICKUP_SPACE_NAME}" not found, falling back to first space`);
      console.log(`   Available spaces: ${spaces.map((s: { name: string }) => s.name).join(', ')}`);
      space = spaces[0];
    }
  }

  if (!space) {
    console.error('❌ No space available');
    return;
  }

  console.log(`✅ Using space: ${space.name} (${space.id})`);

  // Step 2: Determine what to sync based on spec ID
  if (!spec) {
    console.error('❌ Please specify --spec with a spec ID (e.g., E02, E02-F01, E02-F01-T01)');
    return;
  }

  const parts = parseSpecId(spec);
  if (!parts) {
    console.error(`❌ Invalid spec ID: ${spec}`);
    console.log('   Expected format: E##, E##-F##, E##-F##-T##, or E##-F##-T##-S##');
    return;
  }

  console.log(`\n📌 Detected spec level: ${parts.level.toUpperCase()}`);

  // Step 3: Parse spec files (only for the relevant epic)
  console.log(`\n📖 Parsing spec files from specs/${parts.epic}/...`);
  const specsDir = path.join(__dirname, '../../specs', parts.epic);
  const allSpecs = getAllSpecFiles(specsDir);

  console.log(`✅ Found ${allSpecs.size} spec files in ${parts.epic}`);

  // Sync based on detected level
  if (parts.level === 'epic') {
    await syncEpic(client, space.id, spec, allSpecs, dryRun);
  } else if (parts.level === 'feature') {
    // Find or create epic folder
    const epicData = allSpecs.get(parts.epic);
    if (!epicData) {
      console.error(`❌ Epic spec not found: ${parts.epic}`);
      return;
    }

    const epicSpec = epicData.metadata;
    const folderName = `${parts.epic} - ${epicSpec.title}`;
    let folder = await client.findFolder(space.id, folderName);

    if (!folder) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create folder: ${folderName}`);
        console.log(`⚠️  Skipping feature sync (folder doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating folder: ${folderName}`);
        folder = await client.createFolder(space.id, folderName);
        if (folder) {
          console.log(`✅ Created folder: ${folder.id}`);
        }
      }
    }

    if (!folder) {
      console.error(`❌ Failed to create folder: ${folderName}`);
      return;
    }

    await syncFeature(client, folder.id, spec, allSpecs, dryRun);
  } else if (parts.level === 'task') {
    // Need to find the parent feature's list
    if (!parts.feature) {
      console.error(`❌ Cannot determine feature for task: ${spec}`);
      return;
    }

    const featureId = `${parts.epic}-${parts.feature}`;
    const featureData = allSpecs.get(featureId);

    if (!featureData) {
      console.error(`❌ Feature spec not found: ${featureId}`);
      return;
    }

    const featureSpec = featureData.metadata;

    // Find or create epic folder
    const epicData = allSpecs.get(parts.epic);
    if (!epicData) {
      console.error(`❌ Epic spec not found: ${parts.epic}`);
      return;
    }

    const epicSpec = epicData.metadata;
    const folderName = `${parts.epic} - ${epicSpec.title}`;
    let folder = await client.findFolder(space.id, folderName);

    if (!folder) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create folder: ${folderName}`);
        console.log(`⚠️  Skipping task sync (folder doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating folder: ${folderName}`);
        folder = await client.createFolder(space.id, folderName);
        if (folder) {
          console.log(`✅ Created folder: ${folder.id}`);
        }
      }
    }

    if (!folder) {
      console.error(`❌ Failed to create folder: ${folderName}`);
      return;
    }

    // Find or create feature list
    // Use full feature ID (E##-F##) instead of just F##
    const listName = `${featureId}: ${featureSpec.title}`;
    let list = await client.findList(folder.id, listName);

    if (!list) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create list: ${listName}`);
        console.log(`⚠️  Skipping task sync (list doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating list: ${listName}`);
        list = await client.createList(folder.id, listName);
        if (list) {
          console.log(`✅ Created list: ${list.id}`);
        }
      }
    }

    if (!list) {
      console.error(`❌ Failed to create list: ${listName}`);
      return;
    }

    await syncTask(client, list.id, spec, allSpecs, dryRun);
  } else if (parts.level === 'subtask') {
    // Need to find the parent task and feature's list
    if (!parts.feature || !parts.task) {
      console.error(`❌ Cannot determine feature/task for subtask: ${spec}`);
      return;
    }

    const featureId = `${parts.epic}-${parts.feature}`;
    const taskId = `${parts.epic}-${parts.feature}-${parts.task}`;

    const featureData = allSpecs.get(featureId);
    const taskData = allSpecs.get(taskId);

    if (!featureData) {
      console.error(`❌ Feature spec not found: ${featureId}`);
      return;
    }

    if (!taskData) {
      console.error(`❌ Task spec not found: ${taskId}`);
      return;
    }

    const featureSpec = featureData.metadata;

    // Find or create epic folder
    const epicData = allSpecs.get(parts.epic);
    if (!epicData) {
      console.error(`❌ Epic spec not found: ${parts.epic}`);
      return;
    }

    const epicSpec = epicData.metadata;
    const folderName = `${parts.epic} - ${epicSpec.title}`;
    let folder = await client.findFolder(space.id, folderName);

    if (!folder) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create folder: ${folderName}`);
        console.log(`⚠️  Skipping subtask sync (folder doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating folder: ${folderName}`);
        folder = await client.createFolder(space.id, folderName);
        if (folder) {
          console.log(`✅ Created folder: ${folder.id}`);
        }
      }
    }

    if (!folder) {
      console.error(`❌ Failed to create folder: ${folderName}`);
      return;
    }

    // Find or create feature list
    const listName = `${featureId}: ${featureSpec.title}`;
    let list = await client.findList(folder.id, listName);

    if (!list) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create list: ${listName}`);
        console.log(`⚠️  Skipping subtask sync (list doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating list: ${listName}`);
        list = await client.createList(folder.id, listName);
        if (list) {
          console.log(`✅ Created list: ${list.id}`);
        }
      }
    }

    if (!list) {
      console.error(`❌ Failed to create list: ${listName}`);
      return;
    }

    // Find parent task
    const existingTask = await client.findTaskByCustomId(list.id, taskId);

    if (!existingTask) {
      console.error(`❌ Parent task not found in ClickUp: ${taskId}`);
      console.log(`   Please sync the task first: --spec=${taskId}`);
      return;
    }

    console.log(`✅ Found parent task: ${taskId}`);

    // Sync only the specific subtask
    await syncSubtask(client, list.id, existingTask.id, spec, allSpecs, dryRun);
  } else if (parts.level === 'extension') {
    // Extensions can be children of either Task (E##-F##-T##-X##) or Subtask (E##-F##-T##-S##-X##)
    if (!parts.feature || !parts.task || !parts.extension) {
      console.error(`❌ Cannot determine feature/task for extension: ${spec}`);
      return;
    }

    const featureId = `${parts.epic}-${parts.feature}`;
    const taskId = `${parts.epic}-${parts.feature}-${parts.task}`;
    const isSubtaskExtension = !!parts.subtask;
    const subtaskId = isSubtaskExtension
      ? `${parts.epic}-${parts.feature}-${parts.task}-${parts.subtask}`
      : null;

    const featureData = allSpecs.get(featureId);
    const taskData = allSpecs.get(taskId);
    const subtaskData = subtaskId ? allSpecs.get(subtaskId) : null;

    if (!featureData) {
      console.error(`❌ Feature spec not found: ${featureId}`);
      return;
    }

    if (!taskData) {
      console.error(`❌ Task spec not found: ${taskId}`);
      return;
    }

    if (isSubtaskExtension && !subtaskData) {
      console.error(`❌ Subtask spec not found: ${subtaskId}`);
      return;
    }

    const featureSpec = featureData.metadata;
    const taskSpec = taskData.metadata;
    const subtaskSpec = subtaskData?.metadata;

    // Find or create epic folder
    const epicData = allSpecs.get(parts.epic);
    if (!epicData) {
      console.error(`❌ Epic spec not found: ${parts.epic}`);
      return;
    }

    const epicSpec = epicData.metadata;
    const folderName = `${parts.epic} - ${epicSpec.title}`;
    let folder = await client.findFolder(space.id, folderName);

    if (!folder) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create folder: ${folderName}`);
        console.log(`⚠️  Skipping extension sync (folder doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating folder: ${folderName}`);
        folder = await client.createFolder(space.id, folderName);
        if (folder) {
          console.log(`✅ Created folder: ${folder.id}`);
        }
      }
    }

    if (!folder) {
      console.error(`❌ Failed to create folder: ${folderName}`);
      return;
    }

    // Find or create feature list
    const listName = `${featureId}: ${featureSpec.title}`;
    let list = await client.findList(folder.id, listName);

    if (!list) {
      if (dryRun) {
        console.log(`🔍 [DRY RUN] Would create list: ${listName}`);
        console.log(`⚠️  Skipping extension sync (list doesn't exist in dry-run mode)`);
        return;
      } else {
        console.log(`📝 Creating list: ${listName}`);
        list = await client.createList(folder.id, listName);
        if (list) {
          console.log(`✅ Created list: ${list.id}`);
        }
      }
    }

    if (!list) {
      console.error(`❌ Failed to create list: ${listName}`);
      return;
    }

    // Find parent - either Task or Subtask depending on extension type
    let parentClickUpId: string | undefined;
    let parentLabel: string;

    if (isSubtaskExtension && subtaskSpec) {
      // Extension of Subtask (E##-F##-T##-S##-X##) - parent is Subtask
      parentLabel = subtaskId as string;
      parentClickUpId = subtaskSpec.clickup_task_id;

      if (!parentClickUpId) {
        const existingSubtask = await client.findSubtaskByCustomId(list.id, subtaskId as string);
        if (existingSubtask) {
          parentClickUpId = existingSubtask.id;
        }
      }
    } else {
      // Extension of Task (E##-F##-T##-X##) - parent is Task
      parentLabel = taskId;
      parentClickUpId = taskSpec.clickup_task_id;

      if (!parentClickUpId) {
        const existingTask = await client.findTaskByCustomId(list.id, taskId);
        if (existingTask) {
          parentClickUpId = existingTask.id;
        }
      }
    }

    if (!parentClickUpId) {
      console.error(`❌ Parent not found in ClickUp: ${parentLabel}`);
      console.log(`   Please sync the parent first: --spec=${parentLabel}`);
      return;
    }

    console.log(`✅ Found parent: ${parentLabel} (${parentClickUpId})`);

    // Sync only the specific extension
    await syncExtension(client, list.id, parentClickUpId, spec, allSpecs, dryRun);
  } else {
    console.error(`❌ Unsupported spec level: ${parts.level}`);
    console.log('   Currently supports: epic, feature, task, subtask, extension');
    return;
  }

  console.log(`\n${'='.repeat(70)}`);
  console.log('✨ Sync complete!');
  console.log(`${'='.repeat(70)}\n`);
}

// ============================================================================
// CLI
// ============================================================================

async function main() {
  const args = process.argv.slice(2);

  const prArg = args.find((arg) => arg.startsWith('--pr='))?.split('=')[1];

  const options: {
    spec?: string;
    dryRun?: boolean;
    spaceId?: string;
    taskId?: string;
    createWorktree?: boolean;
    prNumber?: number;
  } = {
    spec: args.find((arg) => arg.startsWith('--spec='))?.split('=')[1],
    dryRun: args.includes('--dry-run'),
    spaceId: args.find((arg) => arg.startsWith('--space='))?.split('=')[1],
    taskId: args.find((arg) => arg.startsWith('--id='))?.split('=')[1],
    createWorktree: args.includes('--create-worktree'),
    prNumber: prArg ? parseInt(prArg, 10) : undefined,
  };

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts [OPTIONS]

Options:
  --spec=<id>         Spec ID to sync (auto-detects epic/feature/task from ID structure)
                      Examples: E02 (epic), E02-F01 (feature), E02-F01-T01 (task)
  --dry-run           Show what would be created without making changes
  --space=<name|id>   Use a specific ClickUp space (by name or ID)
                      Default: "Ink" (can be overridden with CLICKUP_SPACE_NAME env)
  --id=<task-id>      ClickUp Task ID (use with --create-worktree or --pr)
  --create-worktree   Create a worktree for the task (requires --id)
  --pr=<number>       PR number to mark task complete (requires --id)
  -h, --help          Show this help message

Environment Variables:
  CLICKUP_API_KEY     Required. Your ClickUp API key
  CLICKUP_SPACE_NAME  Optional. Default space name (default: "Ink")

Spec ID Format:
  E##                   Epic (creates folder + all features + tasks + subtasks)
  E##-F##               Feature (creates list + all tasks + subtasks)
  E##-F##-T##           Task (creates task + all subtasks)
  E##-F##-T##-S##       Subtask (creates only this specific subtask)
  E##-F##-T##-X##       Extension of Task (creates as subtask of Task)
  E##-F##-T##-S##-X##   Extension of Subtask (creates as sub-subtask of Subtask)

Examples:
  # Sync entire epic E02
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02

  # Sync only feature E02-F01
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02-F01

  # Sync only task E02-F01-T01 (includes all subtasks)
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02-F01-T01

  # Sync only specific subtask E02-F01-T01-S05
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02-F01-T01-S05

  # Sync extension of subtask (sub-subtask)
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E08-F01-T10-S03-X01

  # Dry run to preview changes
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E02 --dry-run

  # Sync E03 epic
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --spec=E03

  # Create worktree for ClickUp task x1y2z3
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --id=x1y2z3 --create-worktree

  # Mark task x1y2z3 as complete with PR #780
  yarn exec ts-node scripts/clickup/sync-specs-to-clickup.ts --id=x1y2z3 --pr=780
    `);
    return;
  }

  try {
    await syncToClickUp(options);
  } catch (error) {
    console.error('❌ Error during sync:', error);
    if (axios.isAxiosError(error)) {
      console.error('Response:', error.response?.data);
    }
    process.exit(1);
  }
}

main();
