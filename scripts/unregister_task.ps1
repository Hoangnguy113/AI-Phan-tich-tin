param([string]$TaskName = "Agnet-Daemon")
$ErrorActionPreference = "Stop"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Stop-ScheduledTask  -TaskName $TaskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Da huy tac vu '$TaskName'. Agnet se khong tu chay nua." -ForegroundColor Yellow
} else {
  Write-Host "Khong co tac vu '$TaskName'."
}
