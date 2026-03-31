#!/bin/bash
# Cleanup old subagent sessions

# Delete sessions older than 1 hour that are done/killed
find /home/openclaw/.openclaw/agents/agonarena/sessions -name "*.jsonl" -mmin +60 -exec rm -f {} \;

echo "Old sessions cleaned up"
