# Start llama-server with DeepSeek-OCR Q4_K_M for dsh-ocr1-memory.
# Usage: powershell -File scripts/start-ocr-server.ps1 -ModelDir <models>\deepseek-ocr-gguf -Server <llama.cpp>\llama-server.exe [-Port 18080] [-Embeddings]
param(
  [string]$ModelDir = $env:OCR1_MODEL_DIR,
  [string]$Server = $env:OCR1_LLAMA_SERVER,
  [int]$Port = 18080,
  [switch]$Embeddings
)

if ([string]::IsNullOrWhiteSpace($ModelDir)) { throw "ModelDir 未指定：请用 -ModelDir 或设置 OCR1_MODEL_DIR" }
if ([string]::IsNullOrWhiteSpace($Server)) { throw "Server 未指定：请用 -Server 或设置 OCR1_LLAMA_SERVER" }
$server = $Server
$model = Join-Path $ModelDir 'deepseek-ocr-Q4_K_M.gguf'
$mmproj = Join-Path $ModelDir 'mmproj-deepseek-ocr-q8_0.gguf'

if (-not (Test-Path $server)) { throw "llama-server not found: $server" }
if (-not (Test-Path $model)) { throw "model not found: $model" }
if (-not (Test-Path $mmproj)) { throw "mmproj not found: $mmproj" }

$args = @('--host', '127.0.0.1', '--port', [string]$Port, '-m', $model, '--mmproj', $mmproj, '--alias', 'deepseek-ocr', '-c', '8192', '-n', '1024')
if ($Embeddings) {
  $args += @('--embeddings', '--pooling', 'mean', '-b', '2048', '-ub', '2048')
}
Write-Host "Starting DeepSeek-OCR llama-server on port $Port ..."
& $server @args
