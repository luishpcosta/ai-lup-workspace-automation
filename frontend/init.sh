#!/bin/bash
set -e

echo "=== SDD Harness Initialization ==="

echo "=== echo \"No package manifest detected; replace this line with your project verification command.\" ==="
echo "No package manifest detected; replace this line with your project verification command."

echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Check docs/specs/*/spec.md (the **Phase:** line at the top) for each feature's SDD phase"
echo "2. Advance ONE feature through the flow (Specify -> Clarify -> Plan -> Tasks -> Implement -> Verify)"
echo "3. Do not start a phase before the previous gate passes"
echo "4. Re-run ./init.sh before claiming a feature done"
