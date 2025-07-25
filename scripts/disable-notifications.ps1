# Script to disable Azure DevOps pipeline email notifications
# Requires: AZURE_DEVOPS_EXT_PAT environment variable
# Usage: ./scripts/disable-notifications.ps1 -Organization "RussellBoley" -ProjectName "ado-mcp2"

param(
    [Parameter(Mandatory=$false)]
    [string]$Organization = "RussellBoley",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = "ado-mcp2"
)

# Get PAT from environment variable or .env file
$pat = $env:AZURE_DEVOPS_EXT_PAT
if (-not $pat -and (Test-Path ".env")) {
    Write-Host "Reading PAT from .env file..."
    $envContent = Get-Content ".env" | Where-Object { $_ -match "AZURE_DEVOPS_EXT_PAT=" }
    if ($envContent) {
        $pat = ($envContent -split "=", 2)[1].Trim('"')
    }
}

if (-not $pat) {
    Write-Error "AZURE_DEVOPS_EXT_PAT not found in environment variable or .env file"
    exit 1
}

Write-Host "🔧 Disabling pipeline notifications for organization '$Organization', project '$ProjectName'"

$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{
    "Authorization" = "Basic $base64AuthInfo"
    "Content-Type" = "application/json"
    "Accept" = "application/json"
}

$baseUrl = "https://dev.azure.com/$Organization"

# Get notification subscriptions
$subscriptionsUrl = "$baseUrl/_apis/notification/subscriptions?api-version=7.1-preview.1"

try {
    Write-Host "📡 Fetching notification subscriptions..."
    $response = Invoke-RestMethod -Uri $subscriptionsUrl -Headers $headers -Method Get
    
    # Filter for pipeline-related notifications
    $pipelineSubscriptions = $response.value | Where-Object { 
        $_.description -like "*build*" -or 
        $_.description -like "*pipeline*" -or
        $_.description -like "*release*" -or
        $_.description -like "*deployment*" -or
        $_.eventType -like "*build*" -or
        $_.eventType -like "*pipeline*" -or
        $_.eventType -like "*release*"
    }
    
    if ($pipelineSubscriptions.Count -eq 0) {
        Write-Host "✅ No pipeline-related notification subscriptions found (already disabled or not configured)"
        exit 0
    }
    
    Write-Host "📋 Found $($pipelineSubscriptions.Count) pipeline-related notification subscriptions:"
    foreach ($sub in $pipelineSubscriptions) {
        Write-Host "   - $($sub.description) (Status: $($sub.status))"
    }
    
    $disabledCount = 0
    $skippedCount = 0
    
    foreach ($subscription in $pipelineSubscriptions) {
        if ($subscription.status -eq "disabled" -or $subscription.status -eq "disabledByAdmin") {
            Write-Host "⏭️  Skipping already disabled: $($subscription.description)"
            $skippedCount++
            continue
        }
        
        Write-Host "🔧 Disabling: $($subscription.description)"
        
        # Update subscription to disable it
        $updateUrl = "$baseUrl/_apis/notification/subscriptions/$($subscription.id)?api-version=7.1-preview.1"
        $updateBody = @{
            id = $subscription.id
            status = "disabled"
        } | ConvertTo-Json
        
        try {
            Invoke-RestMethod -Uri $updateUrl -Headers $headers -Method Patch -Body $updateBody
            Write-Host "✅ Disabled: $($subscription.description)"
            $disabledCount++
        }
        catch {
            Write-Warning "❌ Failed to disable: $($subscription.description) - $($_.Exception.Message)"
        }
    }
    
    Write-Host ""
    Write-Host "🎉 Notification update complete!"
    Write-Host "   - Disabled: $disabledCount subscriptions"
    Write-Host "   - Already disabled: $skippedCount subscriptions"
    Write-Host "   - Total processed: $($pipelineSubscriptions.Count) subscriptions"
    
    if ($disabledCount -gt 0) {
        Write-Host ""
        Write-Host "📧 You should now receive fewer email notifications for pipeline builds, deployments, and releases."
        Write-Host "💡 You can re-enable notifications anytime through Azure DevOps web interface."
    }
}
catch {
    Write-Error "❌ Failed to fetch or update notifications: $($_.Exception.Message)"
    Write-Host "💡 This might be due to insufficient permissions or API changes."
    Write-Host "🔗 You can manually disable notifications at: $baseUrl/_settings/notifications"
    exit 1
}