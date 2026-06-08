#!/bin/bash
# Clean up AGENT.md conflicts (both tracked modifications and untracked) then pull

echo "Discarding local changes to tracked AGENT.md files..."
git diff --name-only | grep "AGENT.md" | xargs -r git restore --
git diff --name-only --cached | grep "AGENT.md" | xargs -r git restore --staged --

echo "Removing untracked AGENT.md files..."
git ls-files --others --exclude-standard | grep "AGENT.md" | xargs -r rm -f

echo "Pulling latest changes..."
git pull

echo "Done."
