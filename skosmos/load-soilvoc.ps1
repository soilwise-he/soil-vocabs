param(
    [string]$FusekiDataUrl = "http://localhost:9030/skosmos/data",
    [string]$GraphUri = "https://w3id.org/eusoilvoc",
    [string]$TurtlePath = (Join-Path $PSScriptRoot "SoilVoc_skosmos.ttl")
)

$ErrorActionPreference = "Stop"

$resolvedTurtlePath = Resolve-Path -LiteralPath $TurtlePath
$encodedGraphUri = [System.Uri]::EscapeDataString($GraphUri)
$targetUri = "${FusekiDataUrl}?graph=${encodedGraphUri}"

Write-Host "Loading $resolvedTurtlePath into $GraphUri"
Invoke-WebRequest `
    -Method Put `
    -ContentType "text/turtle" `
    -InFile $resolvedTurtlePath `
    -Uri $targetUri `
    -UseBasicParsing | Out-Null

Write-Host "Load request completed."
