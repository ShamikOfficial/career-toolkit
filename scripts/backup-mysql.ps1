$ErrorActionPreference = "Stop"

function Read-DotEnv([string]$path) {
  $vars = @{}
  if (-not (Test-Path -LiteralPath $path)) { return $vars }
  Get-Content -LiteralPath $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $m = [regex]::Match($line, '^(?<k>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<v>.*)$')
    if (-not $m.Success) { return }
    $k = $m.Groups["k"].Value
    $v = $m.Groups["v"].Value.Trim()
    if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
      $v = $v.Substring(1, $v.Length - 2)
    }
    $vars[$k] = $v
  }
  return $vars
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$dotenv = Read-DotEnv (Join-Path $repoRoot ".env")

$dbName = if ($dotenv.ContainsKey("MYSQL_DB")) { $dotenv["MYSQL_DB"] } else { "career_toolkit" }
$dbUser = if ($dotenv.ContainsKey("MYSQL_USER")) { $dotenv["MYSQL_USER"] } else { "career_user" }
$dbPass = if ($dotenv.ContainsKey("MYSQL_PASSWORD")) { $dotenv["MYSQL_PASSWORD"] } else { "career_pass" }

$container = if ($dotenv.ContainsKey("MYSQL_CONTAINER")) { $dotenv["MYSQL_CONTAINER"] } else { "career-toolkit-mysql" }

$backupDir = Join-Path $repoRoot "data\sql-backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $backupDir ("{0}_{1}.sql" -f $dbName, $ts)
$tmpFile = $outFile + ".tmp"

docker exec $container sh -lc "mysqldump -u $dbUser -p$dbPass $dbName" | Out-File -Encoding utf8 $tmpFile
Move-Item -Force -LiteralPath $tmpFile -Destination $outFile

Write-Host "Wrote backup: $outFile"

