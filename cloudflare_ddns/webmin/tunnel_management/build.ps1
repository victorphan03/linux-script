# Cloudflare Tunnel Manager aaPanel Plugin Packaging Script (PowerShell for Windows)

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Get-Location }

$zipFile = Join-Path $scriptDir "cf_tunnel_manager.zip"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Packaging Cloudflare Tunnel Manager Plugin" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Remove existing zip if present
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
    Write-Host "Removed previous package: cf_tunnel_manager.zip" -ForegroundColor Yellow
}

# List of files required for aaPanel plugin package
$filesToPack = @(
    (Join-Path $scriptDir "info.json"),
    (Join-Path $scriptDir "cf_tunnel_manager_main.py"),
    (Join-Path $scriptDir "index.html"),
    (Join-Path $scriptDir "install.sh"),
    (Join-Path $scriptDir "icon.png"),
    (Join-Path $scriptDir "ico-cf_tunnel_manager.png"),
    (Join-Path $scriptDir "ico.jpg"),
    (Join-Path $scriptDir "Readme.md")
)

# Verify all files exist
$missingFiles = $filesToPack | Where-Object { -not (Test-Path $_) }
if ($missingFiles) {
    Write-Host "Error: The following required files are missing:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

# Create clean ZIP package with essential plugin files
try {
    Compress-Archive -Path $filesToPack -DestinationPath $zipFile -Force
    Write-Host "`nSuccessfully created plugin package!" -ForegroundColor Green
    Write-Host "File: $zipFile" -ForegroundColor Green
    Write-Host "`nContents of cf_tunnel_manager.zip:" -ForegroundColor Cyan
    
    # Display archive contents
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipFile)
    $zip.Entries | ForEach-Object { Write-Host " - $($_.FullName)" -ForegroundColor Gray }
    $zip.Dispose()
    
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Ready to upload to aaPanel via Third-party Plugin / Import!" -ForegroundColor Green
} catch {
    Write-Host "Error creating ZIP package: $_" -ForegroundColor Red
    exit 1
}
