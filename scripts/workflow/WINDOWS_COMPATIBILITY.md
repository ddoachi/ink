# Windows/WSL Compatibility for next-spec.ts

## Changes Made

### 1. WSL Detection
- Added `isWSL()` function to detect if running in Windows Subsystem for Linux
- Checks `/proc/version` for Microsoft/WSL keywords

### 2. Path Conversion
- Added `wslPathToWindows()` function to convert WSL paths to Windows paths
- Uses `wslpath -w` command for accurate conversion
- Fallback manual conversion for `/mnt/c/...` style paths
- Converts paths like `/mnt/c/Users/...` to `C:/Users/...`

### 3. Shell Command Handling
- Added `getShellCommand()` to properly invoke bash scripts
- Handles differences between WSL, native Windows, and Linux/Mac
- Ensures `.sh` scripts run with bash interpreter

### 4. GitHub CLI Check
- Added explicit check for `gh` CLI availability
- Provides helpful error messages with installation instructions
- Gracefully handles missing `gh` instead of crashing

### 5. VS Code Integration
- Converts worktree paths to Windows format before opening in VS Code
- VS Code in Windows needs Windows paths (`C:/...`), not WSL paths (`/mnt/c/...`)
- Updated all VS Code `code` commands to use converted paths

### 6. Display Improvements
- All path displays now show Windows-friendly paths in WSL
- Worktree list shows `C:/Users/...` instead of `/mnt/c/Users/...`
- Summary output uses converted paths

## Installation Prerequisites (WSL)

### Install GitHub CLI
```bash
# Method 1: Using apt (Ubuntu/Debian)
sudo apt install gh -y

# Method 2: Official script
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# Authenticate
gh auth login
```

### Install Node.js & Yarn (WSL)
```bash
# Install Node.js from NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Enable Corepack for Yarn 4
sudo corepack enable

# Verify installation
node -v
yarn -v
```

## Usage

The script now works seamlessly in:
- ✅ WSL (Ubuntu, Debian, etc.)
- ✅ Git Bash on Windows
- ✅ Native Linux
- ✅ macOS

```bash
# Standard usage (works in all environments)
yarn spec:next --limit=20

# With options
yarn spec:next --skip-cleanup
yarn spec:next --yes --limit=20
```

## Testing

After installing prerequisites, test the script:

```bash
# From WSL or Git Bash
cd /mnt/c/Users/ddoac/dev/project-jts/jts  # WSL
cd /c/Users/ddoac/dev/project-jts/jts      # Git Bash

# Run with help to verify
yarn spec:next --help

# Run full workflow
yarn spec:next --limit=20
```

## Troubleshooting

### "gh: not found" error
- Install GitHub CLI using methods above
- Verify: `gh --version`
- Authenticate: `gh auth login`

### "This: command not found" when running yarn
- You have a broken Windows npm package for node
- Remove it: `npm uninstall -g node`
- Node should be installed system-wide, not via npm

### VS Code doesn't open to correct path
- The script automatically converts WSL paths to Windows paths
- Ensure VS Code is installed on Windows and `code` command is in PATH
- In WSL: `export PATH=$PATH:"/mnt/c/Program Files/Microsoft VS Code/bin"`

### Worktree creation fails
- Ensure bash is available: `which bash`
- Check Git version: `git --version` (should be 2.5+)
- Verify permissions on worktrees directory

## Technical Details

### Path Conversion Logic
```typescript
// WSL path: /mnt/c/Users/ddoac/dev/project-jts/worktrees/...
// Converts to: C:/Users/ddoac/dev/project-jts/worktrees/...

wslPathToWindows(wslPath: string): string {
  // Uses wslpath -w for accurate conversion
  // Fallback: manual regex parsing of /mnt/<drive>/...
  // Normalizes backslashes to forward slashes
}
```

### Shell Command Selection
```typescript
getShellCommand(scriptPath, args): string {
  if (isWSL()) return `bash "${scriptPath}" ${args.join(' ')}`
  if (win32) return `bash "${scriptPath}" ${args.join(' ')}`
  else return `"${scriptPath}" ${args.join(' ')}`
}
```

## Known Limitations

1. Requires bash to be available in PATH
2. VS Code must be installed on Windows host (not just WSL)
3. Git operations use WSL/Windows git, performance may vary
4. Line endings: ensure `create-worktree.sh` has LF endings

## Future Improvements

- [ ] Add PowerShell script alternative to bash script
- [ ] Better error messages for missing dependencies
- [ ] Auto-install gh CLI if missing (with prompt)
- [ ] Support for Windows Terminal integration
