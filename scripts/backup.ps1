$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $env:LOCALAPPDATA "LedgerSplit\backups"
$retentionDays = 7

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
$fileName = "ledgersplit_$timestamp.dump"
$backupFile = Join-Path $backupDir $fileName
$containerFile = "/tmp/$fileName"

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

function Invoke-Compose {
    & docker compose --env-file .env.docker @args

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose command failed."
    }
}

Push-Location $projectRoot

try {
    Write-Host "Creating PostgreSQL backup..."

    Invoke-Compose exec -T db sh -c "umask 077; pg_dump -U ledger -d ledger -Fc -f $containerFile"

    Invoke-Compose exec -T db pg_restore -l $containerFile | Out-Null

    Invoke-Compose cp "db:$containerFile" "$backupFile"

    if ((Get-Item $backupFile).Length -le 0) {
        throw "Backup file is empty."
    }

    $hash = Get-FileHash $backupFile -Algorithm SHA256

    $hash.Hash | Set-Content "$backupFile.sha256"

    Write-Host "Backup verified: $backupFile"
    Write-Host "SHA256: $($hash.Hash)"

    $cutoff = (Get-Date).AddDays(-$retentionDays)

    Get-ChildItem $backupDir -File -Filter "ledgersplit_*.dump" |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            $checksumFile = "$($_.FullName).sha256"

            Remove-Item -LiteralPath $_.FullName

            if (Test-Path $checksumFile) {
                Remove-Item -LiteralPath $checksumFile
            }
        }

    Write-Host "Retention policy applied: $retentionDays days."
    Write-Host "Backup completed successfully."
}
finally {
    docker compose --env-file .env.docker exec -T db rm -f $containerFile
    Pop-Location
}