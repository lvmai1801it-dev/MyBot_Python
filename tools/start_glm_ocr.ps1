# Start a local GLM-OCR server for the resource readout.
#
# Requirements:
#   - llama.cpp Windows build (CPU or Vulkan) extracted somewhere
#   - internet access on the first run (the model is downloaded once)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\start_glm_ocr.ps1
#   powershell -ExecutionPolicy Bypass -File tools\start_glm_ocr.ps1 -LlamaDir "D:\llama.cpp"

param(
    [string]$LlamaDir = "$env:LOCALAPPDATA\llama.cpp",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080,
    [int]$Context = 256,
    [int]$Parallel = 2,
    [int]$GpuLayers = 0
)

$exe = Join-Path $LlamaDir "llama-server.exe"
if (-not (Test-Path $exe)) {
    Write-Host "llama-server.exe not found in $LlamaDir"
    Write-Host "Download a Windows build from https://github.com/ggml-org/llama.cpp/releases"
    exit 1
}

# --no-mmap was replaced by --load-mode in newer builds.
& $exe `
    -hf ggml-org/GLM-OCR-GGUF `
    -c $Context `
    -np $Parallel `
    -ngl $GpuLayers `
    -lm none `
    --host $HostAddress `
    --port $Port
