#!/bin/bash
set -euo pipefail

MODEL="${MODEL:-vllm/qwen3.6}"
PROMPT=$(cat << 'EOF'
  There is 10X genomics scRNA-seq/TCR-seq data in @data/raw/GSE1459111_RAW.tar
  Create jupyter notebook that loads them in test/notebooks/.
  The last cell of the notebook should output two numbers separated with whitespace:
  total number of samples and how much of them have TCR data.
  This output should also be saved in a file test/results/01-data-loading-noskill.txt
  Perform all the needed data manipulations inside the data/ directory.
  All the necessary python modules are already installed in "pytcr" env.
  Upon failure or permission issue, continue and try other approaches.
EOF
)

LOG_DIR="test/logs/01-data-loading"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/bench_01_${TIMESTAMP}.jsonl"
PRETTY_FILE="$LOG_DIR/bench_01_${TIMESTAMP}.txt"
mkdir -p "$LOG_DIR"

echo "=== Model: $MODEL ===" | tee "$PRETTY_FILE"
echo "=== Prompt: $PROMPT ===" | tee -a "$PRETTY_FILE"
echo "" | tee -a "$PRETTY_FILE"

opencode run \
  --model "$MODEL" \
  --format json \
  --thinking \
  "$PROMPT" \
  | tee "$LOG_FILE" \
  | jq -r --unbuffered '
    if .type == "reasoning" then
      "🧠 THINKING: \(.part.text)"
    elif .type == "tool_use" then
      "🔧 TOOL: \(.part.tool)\n   IN:  \(.part.state.input | tostring | .[0:200])\n   OUT: \(.part.state.output | .[0:300])"
    elif .type == "text" then
      "💬 OUTPUT:\n\(.part.text)"
    elif .type == "step_finish" then
      "📊 STEP TOKENS: input=\(.part.tokens.input) output=\(.part.tokens.output) reasoning=\(.part.tokens.reasoning) total=\(.part.tokens.total)"
    else empty
    end
  ' | tee -a "$PRETTY_FILE"

echo "" | tee -a "$PRETTY_FILE"

TOTALS=$(jq -n \
  --slurpfile events "$LOG_FILE" '
  $events[]
  | select(.type == "step_finish")
  | .part.tokens
  | {input, output, reasoning, total}
' | jq -n '
  reduce inputs as $t (
    {input: 0, output: 0, reasoning: 0, total: 0};
    .input     += ($t.input     // 0) |
    .output    += ($t.output    // 0) |
    .reasoning += ($t.reasoning // 0) |
    .total     += ($t.total     // 0)
  )
')

SUMMARY=$(echo "$TOTALS" | jq -r '"=== TOTAL TOKENS ===\ninput=\(.input) output=\(.output) reasoning=\(.reasoning) total=\(.total)"')
echo "$SUMMARY" | tee -a "$PRETTY_FILE"

echo "" | tee -a "$PRETTY_FILE"
echo "=== Logs: $LOG_FILE ===" | tee -a "$PRETTY_FILE"
echo "=== Pretty: $PRETTY_FILE ===" | tee -a "$PRETTY_FILE"
