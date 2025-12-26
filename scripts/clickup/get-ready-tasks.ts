#!/usr/bin/env ts-node

/**
 * Get tasks marked as "Ready To Implement" from ClickUp
 *
 * Usage:
 *   yarn ts-node scripts/clickup/get-ready-tasks.ts
 *   yarn ts-node scripts/clickup/get-ready-tasks.ts --json
 */

import axios from 'axios';
import * as fs from 'fs';
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

const apiKey = process.env['CLICKUP_API_KEY'];
const SPACE_ID = '90187278086';

interface ClickUpTask {
  id: string;
  name: string;
  status: { status: string };
  list: { id: string; name: string };
  folder: { id: string; name: string };
  url: string;
}

interface ReadyTask {
  taskId: string;
  clickupId: string;
  name: string;
  listName: string;
  folderName: string;
  url: string;
}

async function getReadyTasks(): Promise<ReadyTask[]> {
  const client = axios.create({
    baseURL: 'https://api.clickup.com/api/v2',
    headers: {
      Authorization: apiKey,
      'Content-Type': 'application/json',
    },
  });

  const readyTasks: ReadyTask[] = [];
  let lastRequestTime = 0;
  const minRequestInterval = 1000; // Increased to 1 second to avoid rate limits

  // Add rate limiting
  const rateLimit = async (): Promise<void> => {
    const now = Date.now();
    const timeSinceLastRequest = now - lastRequestTime;
    if (timeSinceLastRequest < minRequestInterval) {
      await new Promise((resolve) =>
        globalThis.setTimeout(resolve, minRequestInterval - timeSinceLastRequest),
      );
    }
    lastRequestTime = Date.now();
  };

  try {
    // Get all folders in space
    await rateLimit();
    const foldersRes = await client.get(`/space/${SPACE_ID}/folder`);
    const folders = foldersRes.data.folders;

    for (const folder of folders) {
      // Get all lists in folder
      await rateLimit();
      const listsRes = await client.get(`/folder/${folder.id}/list`);
      const lists = listsRes.data.lists;

      for (const list of lists) {
        // Get all tasks in list
        await rateLimit();
        const tasksRes = await client.get(`/list/${list.id}/task`, {
          params: {
            include_closed: false,
            subtasks: false,
          },
        });
        const tasks = tasksRes.data.tasks || [];

        // Filter tasks with "Ready To Implement" status
        for (const task of tasks) {
          if (
            task.status?.status === 'READY TO IMPLEMENT' ||
            task.status?.status === 'ready to implement'
          ) {
            // Extract task ID from name (format: "E##-F##-T##: Title")
            const taskIdMatch = task.name.match(/^(E\d+-F\d+-T\d+)/);
            const taskId = taskIdMatch ? taskIdMatch[1] : null;

            readyTasks.push({
              taskId: taskId || 'unknown',
              clickupId: task.id,
              name: task.name,
              listName: list.name,
              folderName: folder.name,
              url: task.url || `https://app.clickup.com/t/${task.id}`,
            });
          }
        }
      }
    }

    return readyTasks;
  } catch (error: unknown) {
    if (error instanceof Error) {
      console.error('Error fetching tasks:', error.message);
    }
    throw error;
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const jsonOutput = args.includes('--json');

  console.error('🔍 Fetching tasks marked as "Ready To Implement"...\n');

  const readyTasks = await getReadyTasks();

  if (readyTasks.length === 0) {
    console.error('✅ No tasks found with status "Ready To Implement"');
    return;
  }

  if (jsonOutput) {
    console.log(JSON.stringify(readyTasks, null, 2));
  } else {
    console.log(`Found ${readyTasks.length} task(s) ready to implement:\n`);
    for (const task of readyTasks) {
      console.log(`📋 ${task.taskId}: ${task.name}`);
      console.log(`   List: ${task.listName}`);
      console.log(`   URL: ${task.url}`);
      console.log();
    }
  }
}

main().catch(console.error);
