#!/bin/bash
# Initialize SGLang Engine for AWQ models
export HF_HOME=${SENTIA_BASE_DIR:-/tmp}/sglang_kv_cache # Change this to your desired mount point
pkill -f sglang
sleep 2

python3 -m sglang.launch_server \
  --model-path $HF_HOME/Qwen2.5-14B-Instruct-AWQ \
  --port 30000 \
  --quantization awq \
  --attention-backend triton \
  --cuda-graph-backend-prefill disabled \
  --host 127.0.0.1
