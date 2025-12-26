#!/usr/bin/env ts-node

/**
 * Migrate Existing ClickUp Tasks to Bidirectional Mapping
 *
 * This script establishes bidirectional mapping between ClickUp tasks and spec files:
 * - ClickUp → Spec: Task titles already contain spec IDs (e.g., "E03-F03-T01: ...")
 * - Spec → ClickUp: Spec files get "clickup_task_id" field in frontmatter
 *
 * Prerequisites:
 * - CLICKUP_API_KEY must be set in .env.local
 * - All tasks must already exist in ClickUp with spec IDs in titles
 *
 * Usage:
 *   yarn exec ts-node scripts/clickup/migrate-bidirectional-mapping.ts
 *   yarn exec ts-node scripts/clickup/migrate-bidirectional-mapping.ts --dry-run
 */

import axios, { AxiosInstance } from 'axios';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';

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

interface ClickUpTask {
  id: string;
  name: string;
  list: {
    id: string;
  };
}

interface ClickUpList {
  id: string;
  name: string;
}

interface ClickUpFolder {
  id: string;
  name: string;
}

interface MigrationResult {
  totalTasks: number;
  matchedTasks: number;
  skippedTasks: number;
  updatedSpecs: number;
  errors: string[];
}

// ============================================================================
// ClickUp API Client
// ============================================================================

class ClickUpClient {
  private client: AxiosInstance;
  private lastRequestTime = 0;
  private minRequestInterval = 1000; // Increased to 1000ms (1 req/sec) to avoid rate limits

  constructor(apiKey: string) {
    this.client = axios.create({
      baseURL: CLICKUP_API_BASE,
      headers: {
        Authorization: apiKey,
        'Content-Type': 'application/json',
      },
    });

    // Rate limiting interceptor
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

    // Retry interceptor for 429 errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const config = error.config;

        // Retry on 429 (rate limit) errors
        if (error.response?.status === 429 && !config._retry) {
          config._retry = true;
          const retryAfter = parseInt(error.response.headers['retry-after'] || '60', 10);
          const waitTime = retryAfter * 1000;

          console.log(`    ⏳ Rate limit hit, waiting ${retryAfter}s before retry...`);
          await new Promise((resolve) => globalThis.setTimeout(resolve, waitTime));

          return this.client(config);
        }

        return Promise.reject(error);
      },
    );
  }

  async getTeams() {
    const response = await this.client.get('/team');
    return response.data.teams;
  }

  async getSpaces(teamId: string) {
    const response = await this.client.get(`/team/${teamId}/space`);
    return response.data.spaces;
  }

  async getFolders(spaceId: string) {
    const response = await this.client.get(`/space/${spaceId}/folder`);
    return response.data.folders;
  }

  async getLists(folderId: string) {
    const response = await this.client.get(`/folder/${folderId}/list`);
    return response.data.lists;
  }

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
}

// ============================================================================
// Helper Functions
// ============================================================================

function extractSpecIdFromTitle(title: string): string | null {
  const match = title.match(/^(E\d+(?:-F\d+)?(?:-T\d+)?(?:-S\d+)?)/);
  return match ? (match[1] ?? null) : null;
}

function findSpecFile(specId: string, specsDir: string): string | null {
  // Parse spec ID to determine file path
  const match = specId.match(/^(E\d+)(?:-(F\d+))?(?:-(T\d+))?(?:-(S\d+))?$/);
  if (!match) return null;

  const [, epic, feature, task, subtask] = match;

  let specPath: string;
  if (subtask && task && feature) {
    // Subtask: specs/E##/F##/T##/S##/E##-F##-T##-S##.spec.md
    specPath = path.join(specsDir, epic, feature, task, subtask, `${specId}.spec.md`);
  } else if (task && feature) {
    // Task: specs/E##/F##/T##/E##-F##-T##.spec.md
    specPath = path.join(specsDir, epic, feature, task, `${specId}.spec.md`);
  } else if (feature) {
    // Feature: specs/E##/F##/E##-F##.spec.md
    specPath = path.join(specsDir, epic, feature, `${specId}.spec.md`);
  } else {
    // Epic: specs/E##/E##.spec.md
    specPath = path.join(specsDir, epic, `${specId}.spec.md`);
  }

  return fs.existsSync(specPath) ? specPath : null;
}

function updateSpecFileWithTaskId(specFilePath: string, taskId: string, dryRun: boolean): boolean {
  try {
    const content = fs.readFileSync(specFilePath, 'utf-8');

    // Check if clickup_task_id already exists
    if (content.includes('clickup_task_id:')) {
      console.log(`    ⚠️  Spec file already has clickup_task_id, skipping update`);
      return false;
    }

    // Extract frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!frontmatterMatch || !frontmatterMatch[1]) {
      console.error(`    ❌ No frontmatter found in ${specFilePath}`);
      return false;
    }

    const frontmatter = frontmatterMatch[1];
    const restOfContent = content.substring(frontmatterMatch[0].length);

    // Add clickup_task_id after the id field
    const updatedFrontmatter = frontmatter.replace(
      /^(id:\s+.+)$/m,
      `$1\nclickup_task_id: '${taskId}'`,
    );

    const updatedContent = `---\n${updatedFrontmatter}\n---${restOfContent}`;

    if (!dryRun) {
      fs.writeFileSync(specFilePath, updatedContent, 'utf-8');
    }

    return true;
  } catch (error) {
    console.error(`    ❌ Error updating spec file ${specFilePath}:`, error);
    return false;
  }
}

// ============================================================================
// Migration Logic
// ============================================================================

async function migrateAllTasks(dryRun: boolean): Promise<MigrationResult> {
  const result: MigrationResult = {
    totalTasks: 0,
    matchedTasks: 0,
    skippedTasks: 0,
    updatedSpecs: 0,
    errors: [],
  };

  const client = new ClickUpClient(CLICKUP_API_KEY!);
  const specsDir = path.join(__dirname, '../../specs');

  console.log('🚀 Starting Migration\n');

  // Get workspace structure
  console.log('📋 Fetching ClickUp workspace structure...');
  const teams = await client.getTeams();

  if (teams.length === 0) {
    result.errors.push('No teams found in ClickUp');
    return result;
  }

  const team = teams[0];
  console.log(`✅ Using team: ${team.name}`);

  const spaces = await client.getSpaces(team.id);

  if (spaces.length === 0) {
    result.errors.push('No spaces found in team');
    return result;
  }

  const space = spaces[0];
  console.log(`✅ Using space: ${space.name}\n`);

  // Get all folders (epics)
  const folders = await client.getFolders(space.id);
  console.log(`📁 Found ${folders.length} folders (epics)`);

  for (const folder of folders) {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📁 Processing folder: ${folder.name}`);
    console.log(`${'='.repeat(70)}`);

    const lists = await client.getLists(folder.id);
    console.log(`  📋 Found ${lists.length} lists (features)`);

    for (const list of lists) {
      console.log(`\n  📦 Processing list: ${list.name}`);

      const tasks = await client.getTasks(list.id);
      console.log(`    📝 Found ${tasks.length} tasks`);

      for (const task of tasks) {
        result.totalTasks++;

        // Extract spec ID from title
        const specId = extractSpecIdFromTitle(task.name);

        if (!specId) {
          console.log(`    ⊘ Skipping task (no spec ID): ${task.name}`);
          result.skippedTasks++;
          continue;
        }

        console.log(`    ✓ Matched: ${task.name} → ${specId}`);
        result.matchedTasks++;

        // Find corresponding spec file
        const specFilePath = findSpecFile(specId, specsDir);

        if (!specFilePath) {
          console.log(`      ⚠️  Spec file not found for: ${specId}`);
          result.errors.push(`Spec file not found for: ${specId} (task: ${task.id})`);
          continue;
        }

        console.log(`      📄 Found spec: ${path.relative(specsDir, specFilePath)}`);

        // Update spec file with clickup_task_id
        const updated = updateSpecFileWithTaskId(specFilePath, task.id, dryRun);
        if (updated) {
          console.log(
            `      ✅ ${dryRun ? '[DRY RUN] Would update' : 'Updated'} spec file with clickup_task_id: ${task.id}`,
          );
          if (!dryRun) {
            result.updatedSpecs++;
          }
        }
      }
    }
  }

  return result;
}

// ============================================================================
// CLI
// ============================================================================

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: yarn exec ts-node scripts/clickup/migrate-bidirectional-mapping.ts [OPTIONS]

Options:
  --dry-run    Show what would be updated without making changes
  -h, --help   Show this help message

Description:
  This script migrates existing ClickUp tasks to establish bidirectional mapping:
  - Reads spec IDs from ClickUp task titles (e.g., "E03-F03-T01: ...")
  - Adds "clickup_task_id" to spec file frontmatter

  Tasks without spec IDs in their titles will be skipped.

Examples:
  # Dry run to preview changes
  yarn exec ts-node scripts/clickup/migrate-bidirectional-mapping.ts --dry-run

  # Perform actual migration
  yarn exec ts-node scripts/clickup/migrate-bidirectional-mapping.ts
    `);
    return;
  }

  console.log(dryRun ? '🔍 DRY RUN MODE - No changes will be made\n' : '');

  try {
    const result = await migrateAllTasks(dryRun);

    console.log(`\n${'='.repeat(70)}`);
    console.log('📊 Migration Summary');
    console.log(`${'='.repeat(70)}`);
    console.log(`Total tasks processed: ${result.totalTasks}`);
    console.log(`Tasks matched with specs: ${result.matchedTasks}`);
    console.log(`Tasks skipped (no spec ID): ${result.skippedTasks}`);

    if (!dryRun) {
      console.log(`Spec files updated: ${result.updatedSpecs}`);
    }

    if (result.errors.length > 0) {
      console.log(`\n⚠️  Errors encountered: ${result.errors.length}`);
      result.errors.forEach((error, index) => {
        console.log(`  ${index + 1}. ${error}`);
      });
    }

    console.log(`${'='.repeat(70)}\n`);

    if (dryRun) {
      console.log('✨ Dry run complete! Run without --dry-run to apply changes.\n');
    } else {
      console.log('✨ Migration complete!\n');
    }
  } catch (error) {
    console.error('❌ Migration failed:', error);
    if (axios.isAxiosError(error)) {
      console.error('Response:', error.response?.data);
    }
    process.exit(1);
  }
}

main();
