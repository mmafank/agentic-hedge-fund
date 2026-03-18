#!/bin/bash
# Install the secret scanner as a git pre-commit hook.
# Run once after cloning: bash scripts/install_hooks.sh

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

if [ -z "$REPO_ROOT" ]; then
    echo "Error: Not inside a git repository."
    exit 1
fi

HOOKS_DIR="$REPO_ROOT/.git/hooks"
HOOK_FILE="$HOOKS_DIR/pre-commit"

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# Pre-commit hook: runs secret scanner on all staged files.
# Blocks commit if any secrets are detected.

python3 "$(git rev-parse --show-toplevel)/scripts/secret_scanner.py"
HOOK

chmod +x "$HOOK_FILE"
echo "Pre-commit hook installed at $HOOK_FILE"
echo "The secret scanner will run automatically before every commit."
