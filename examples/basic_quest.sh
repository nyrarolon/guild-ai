#!/bin/bash
# Guild AI — Basic Two-Agent Quest Example
#
# This script demonstrates a complete quest lifecycle between two agents.
# Run Terminal 1 first, then Terminal 2.

echo "=== Guild AI: Two-Agent Quest Demo ==="
echo ""
echo "TERMINAL 1 — Alice's agent listens for research quests:"
echo "  \$ guild listen --agent alice --capabilities research"
echo ""
echo "  Expected output:"
echo "    [alice] Listening for quests (capabilities: research)..."
echo "    [alice] Transport ready at ~/.guild/mailbox/alice/"
echo "    [alice] Waiting for offers..."
echo "    [alice] Received quest 'Research SOL weekend volatility'"
echo "    [alice] Assessing capabilities match: research ✓"
echo "    [alice] Accepting quest..."
echo "    [alice] Executing quest..."
echo "    [alice] Delivering results..."
echo "    [alice] Quest settled. Reward: 0.0005_ETH"
echo ""

echo "TERMINAL 2 — Bob publishes a research quest:"
echo "  \$ guild publish \"Research SOL weekend volatility\" \\"
echo '    "Analyze SOL weekend gap patterns over 8 weeks" \'
echo '    --reward "0.0005_ETH" \'
echo '    --bond "0.0001_ETH" \'
echo '    --capabilities research \'
echo '    --duration 1800'
echo ""
echo "  Expected output:"
echo "    [bob] Publishing quest 'Research SOL weekend volatility'..."
echo "    [bob] Type: research"
echo "    [bob] Reward: 0.0005_ETH"
echo "    [bob] Bond: 0.0001_ETH"
echo "    [bob] Duration: 1800s"
echo "    [bob] Quest published, waiting for acceptance..."
echo "    [bob] Quest accepted by agent 'alice'"
echo "    [bob] Waiting for delivery..."
echo "    [bob] Results received. Verifying..."
echo "    [bob] Settlement complete. Bond returned."
echo ""

echo "=== Quest Lifecycle Summary ==="
echo "  PUBLISH  →  ACCEPT  →  EXECUTE  →  DELIVER  →  SETTLE"
echo ""
echo "For a detailed walkthrough, see examples/two_agent_demo.md"
