#!/usr/bin/env ts-node

/**
 * Add GitHub PR link to ClickUp task
 *
 * Usage:
 *   yarn ts-node scripts/clickup/add-pr-link.ts <clickup-task-id> <pr-number>
 *   yarn ts-node scripts/clickup/add-pr-link.ts 86ev3b0uy 760
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
const GITHUB_REPO = 'ddoachi/jts';

async function addPRLink(taskId: string, prNumber: string): Promise<void> {
  const client = axios.create({
    baseURL: 'https://api.clickup.com/api/v2',
    headers: {
      Authorization: apiKey,
      'Content-Type': 'application/json',
    },
  });

  const prUrl = `https://github.com/${GITHUB_REPO}/pull/${prNumber}`;

  try {
    await client.post(`/task/${taskId}/link`, {
      type: 'url',
      url: prUrl,
    });

    console.log(`✅ Added PR link to task ${taskId}`);
    console.log(`   Task: https://app.clickup.com/t/${taskId}`);
    console.log(`   PR: ${prUrl}`);
  } catch (error: any) {
    console.error(`❌ Failed to add PR link:`, error.response?.data || error.message);
    throw error;
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error(
      'Usage: yarn ts-node scripts/clickup/add-pr-link.ts <clickup-task-id> <pr-number>',
    );
    console.error('Example: yarn ts-node scripts/clickup/add-pr-link.ts 86ev3b0uy 760');
    process.exit(1);
  }

  const [taskId, prNumber] = args;
  await addPRLink(taskId, prNumber);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
