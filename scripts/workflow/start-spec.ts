#!/usr/bin/env ts-node

/**
 * Start Spec Workflow
 *
 * Creates a worktree for a specific spec by reading the spec file,
 * sanitizing the title, and setting up the development environment.
 *
 * Prerequisites:
 * - CLICKUP_API_KEY in .env.local (optional, for status updates)
 *
 * Usage:
 *   yarn exec ts-node scripts/workflow/start-spec.ts E15-F03-T02-S01
 *   yarn exec ts-node scripts/workflow/start-spec.ts --taskId=86ev4990k
 *   yarn spec:start E15-F03-T02-S01
 *   yarn spec:start --taskId=86ev4990k
 */

import { execSync, spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

import axios, { AxiosInstance } from 'axios';
import * as yaml from 'js-yaml';

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

interface SpecIdParts {
  epic: string;
  feature?: string;
  task?: string;
  subtask?: string;
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

  async getTask(taskId: string) {
    const response = await this.client.get(`/task/${taskId}`);
    return response.data;
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

function parseSpecId(specId: string): SpecIdParts | null {
  const match = specId.match(/^(E\d+)(?:-(F\d+))?(?:-(T\d+))?(?:-(S\d+))?$/);

  if (!match) {
    return null;
  }

  const [, epic, feature, task, subtask] = match;

  if (!epic) {
    return null;
  }

  return {
    epic,
    feature: feature || undefined,
    task: task || undefined,
    subtask: subtask || undefined,
  };
}

function findSpecFile(specId: string): string | null {
  const parts = parseSpecId(specId);
  if (!parts) {
    return null;
  }

  // Construct file path
  const pathParts = [parts.epic];
  if (parts.feature) pathParts.push(parts.feature);
  if (parts.task) pathParts.push(parts.task);
  if (parts.subtask) pathParts.push(parts.subtask);

  const specFilePath = path.join(__dirname, '../../specs', ...pathParts, `${specId}.spec.md`);

  if (!fs.existsSync(specFilePath)) {
    return null;
  }

  return specFilePath;
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

function sanitizeTitle(title: string): string {
  return title.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '');
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
          specs.push({ path: fullPath, specId, metadata });
        }
      }
    }
  }

  scanDirectory(specsDir);
  return specs;
}

function findSpecFileByTaskId(taskId: string): SpecFile | null {
  const specsDir = path.join(__dirname, '../../specs');
  const allSpecs = getAllSpecFiles(specsDir);

  return allSpecs.find((spec) => spec.metadata.clickup_task_id === taskId) || null;
}

// ============================================================================
// Main Logic
// ============================================================================

async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h') || args.length === 0) {
    console.log(`
Usage: yarn spec:start <spec-id>
   or: yarn spec:start <spec-id1>,<spec-id2>,...
   or: yarn spec:start --taskId=<clickup-task-id>
   or: yarn spec:start --taskId=<id1>,<id2>,...

Arguments:
  spec-id         Spec ID to start working on (e.g., E15-F03-T02-S01)
                  Multiple IDs can be comma-separated for parallel execution

Options:
  --taskId=<id>   ClickUp Task ID (e.g., 86ev4990k)
                  Multiple IDs can be comma-separated for parallel execution
  -h, --help      Show this help message

Description:
  Creates a worktree for a specific spec by:
  1. Reading the spec file from filesystem (or ClickUp API if using --taskId)
  2. Extracting title and clickup_task_id from frontmatter
  3. Sanitizing title for branch name
  4. Creating worktree with create-worktree.sh
  5. Updating ClickUp task status to "IN PROGRESS"

Examples:
  # Start work on a specific subtask by spec ID
  yarn spec:start E15-F03-T02-S01

  # Start work on a task by spec ID
  yarn spec:start E15-F03-T02

  # Start work using ClickUp Task ID
  yarn spec:start --taskId=86ev4990k

  # Start multiple specs in parallel
  yarn spec:start E09-F01-T06,E09-F01-T07

  # Start multiple tasks by ClickUp IDs in parallel
  yarn spec:start --taskId=86ev4990k,86ev4991m
    `);
    return;
  }

  const taskIdArg = args.find((arg) => arg.startsWith('--taskId='))?.split('=')[1];
  const specId = taskIdArg ? undefined : args[0];

  // Handle multiple comma-separated inputs for parallel execution
  const multipleInputs: string[] = [];
  const isTaskIdMode = !!taskIdArg;

  if (taskIdArg && taskIdArg.includes(',')) {
    multipleInputs.push(
      ...taskIdArg
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    );
  } else if (specId && specId.includes(',')) {
    multipleInputs.push(
      ...specId
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    );
  }

  if (multipleInputs.length > 1) {
    console.log('🚀 Starting Multiple Specs in Parallel\n');
    console.log('='.repeat(70));
    console.log(`📋 ${multipleInputs.length} specs to process: ${multipleInputs.join(', ')}`);
    console.log('='.repeat(70));
    console.log('');

    const scriptPath = __filename;
    const processes: Promise<{ input: string; exitCode: number }>[] = [];

    for (const input of multipleInputs) {
      const childArgs = isTaskIdMode ? [`--taskId=${input}`] : [input];

      const childProcess = spawn('ts-node', [scriptPath, ...childArgs], {
        stdio: 'inherit',
        cwd: path.join(__dirname, '../..'),
        shell: true,
      });

      const processPromise = new Promise<{ input: string; exitCode: number }>((resolve) => {
        childProcess.on('close', (code) => {
          resolve({ input, exitCode: code ?? 1 });
        });
        childProcess.on('error', (_err) => {
          resolve({ input, exitCode: 1 });
        });
      });

      processes.push(processPromise);
    }

    const results = await Promise.all(processes);
    const failed = results.filter((r) => r.exitCode !== 0);

    console.log('\n');
    console.log('='.repeat(70));
    if (failed.length === 0) {
      console.log('✨ All specs started successfully!');
    } else {
      console.log(`⚠️  ${failed.length} of ${results.length} specs failed:`);
      for (const f of failed) {
        console.log(`   - ${f.input} (exit code: ${f.exitCode})`);
      }
    }
    console.log('='.repeat(70));

    process.exit(failed.length > 0 ? 1 : 0);
  }

  if (!specId && !taskIdArg) {
    console.error('❌ Please provide a spec ID or --taskId');
    console.log('   Usage: yarn spec:start <spec-id>');
    console.log('      or: yarn spec:start --taskId=<clickup-task-id>');
    console.log('   Example: yarn spec:start E15-F03-T02-S01');
    console.log('   Example: yarn spec:start --taskId=86ev4990k');
    process.exit(1);
  }

  console.log('🚀 Starting Spec Workflow\n');
  console.log('='.repeat(70));

  let title: string;
  let clickupTaskId: string | undefined;
  let displaySpecId: string | undefined;

  // Handle --taskId workflow
  if (taskIdArg) {
    console.log(`🔗 ClickUp Task ID: ${taskIdArg}`);

    // Try to find spec file by taskId
    const specFile = findSpecFileByTaskId(taskIdArg);

    if (specFile) {
      console.log(`✅ Found spec file: ${path.relative(process.cwd(), specFile.path)}`);
      console.log(`📋 Spec ID: ${specFile.specId}`);
      console.log(`📝 Title: ${specFile.metadata.title}`);
      console.log(`📦 Type: ${specFile.metadata.type}`);

      // Include spec ID in title for branch name
      title = `${specFile.specId}: ${specFile.metadata.title}`;
      clickupTaskId = taskIdArg;
      displaySpecId = specFile.specId;
    } else {
      console.log(`⚠️  No spec file found with clickup_task_id: ${taskIdArg}`);
      console.log(`📡 Fetching task details from ClickUp API...`);

      if (!CLICKUP_API_KEY) {
        console.error('❌ CLICKUP_API_KEY not found in .env.local');
        console.log('   Cannot fetch task from ClickUp API without API key');
        process.exit(1);
      }

      try {
        const client = new ClickUpClient(CLICKUP_API_KEY);
        const task = await client.getTask(taskIdArg);

        console.log(`✅ Found task in ClickUp: ${task.name}`);
        title = task.name;
        clickupTaskId = taskIdArg;
        displaySpecId = undefined;
      } catch (error) {
        console.error(`❌ Failed to fetch task from ClickUp:`, error);
        process.exit(1);
      }
    }
  } else {
    // Handle spec ID workflow
    if (!specId) {
      console.error('❌ Spec ID is required');
      process.exit(1);
    }

    // Step 1: Parse spec ID
    const parts = parseSpecId(specId);
    if (!parts) {
      console.error(`❌ Invalid spec ID: ${specId}`);
      console.log('   Expected format: E##, E##-F##, E##-F##-T##, or E##-F##-T##-S##');
      process.exit(1);
    }

    console.log(`📋 Spec ID: ${specId}`);

    // Step 2: Find spec file
    const specFilePath = findSpecFile(specId);
    if (!specFilePath) {
      console.error(`❌ Spec file not found for: ${specId}`);
      console.log(
        `   Expected location: specs/${parts.epic}/${parts.feature || ''}/${parts.task || ''}/${parts.subtask || ''}`,
      );
      process.exit(1);
    }

    console.log(`✅ Found spec file: ${path.relative(process.cwd(), specFilePath)}`);

    // Step 3: Parse spec file
    const metadata = parseSpecFile(specFilePath);
    if (!metadata) {
      console.error(`❌ Failed to parse spec file: ${specFilePath}`);
      process.exit(1);
    }

    console.log(`📝 Title: ${metadata.title}`);
    console.log(`📦 Type: ${metadata.type}`);

    if (metadata.clickup_task_id) {
      console.log(`🔗 ClickUp Task ID: ${metadata.clickup_task_id}`);
    } else {
      console.log(`⚠️  No ClickUp Task ID found (status update will be skipped)`);
    }

    // Include spec ID in title for branch name
    title = `${specId}: ${metadata.title}`;
    clickupTaskId = metadata.clickup_task_id;
    displaySpecId = specId;
  }

  // Step 4: Sanitize title for branch name
  const sanitizedTitle = sanitizeTitle(title);
  const branchName = sanitizedTitle;
  const worktreePath = path.join(__dirname, '../../../worktrees', branchName);

  console.log(`\n${'='.repeat(70)}`);
  console.log('📂 Worktree Plan');
  console.log('='.repeat(70));
  if (displaySpecId) {
    console.log(`Spec ID: ${displaySpecId}`);
  }
  console.log(`Branch: ${branchName}`);
  console.log(`Path: ${worktreePath}`);
  if (clickupTaskId) {
    console.log(`TaskId: ${clickupTaskId}`);
  }
  console.log('='.repeat(70));

  // Step 5: Create worktree
  console.log('\n📂 Creating worktree...\n');

  const scriptPath = path.join(__dirname, 'create-worktree.sh');

  try {
    const taskIdFlag = clickupTaskId ? `-t "${clickupTaskId}"` : '';

    execSync(`"${scriptPath}" -b "${branchName}" ${taskIdFlag} "${worktreePath}"`, {
      stdio: 'pipe',
      cwd: path.join(__dirname, '../..'),
    });

    console.log('✅ Worktree created\n');

    // Create VS Code task for launching claude
    const vscodeDir = path.join(worktreePath, '.vscode');
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
    console.log('✅ Cursor task created');

    // Open Cursor in new window
    console.log('📂 Opening Cursor with auto-start task...');
    execSync(`cursor -n "${worktreePath}"`, { stdio: 'ignore' });
    console.log('✅ Cursor opened (claude will auto-start)');
    console.log('💡 Task "Start Claude" is set to run on folder open');

    // Wait a bit for Cursor to fully load, then try to trigger the task
    await new Promise((resolve) => globalThis.setTimeout(resolve, 2000));

    try {
      execSync(
        `cursor -r "${worktreePath}" --command "workbench.action.tasks.runTask" --args "Start Claude"`,
        {
          stdio: 'ignore',
        },
      );
      console.log('✅ Claude task triggered');
    } catch (e) {
      console.log('⚠️  Manual task trigger failed, but task will auto-run on folder open');
    }

    console.log('\n');
    console.log('='.repeat(70));
    console.log('✨ Worktree Created Successfully!');
    console.log('='.repeat(70));
    console.log(`\nWorktree ready at: ${worktreePath}`);
    console.log('');
  } catch (error) {
    console.error('\n❌ Failed to create worktree:', error);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('❌ Unexpected error:', error);
  process.exit(1);
});
