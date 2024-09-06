$url = "https://api.twitter.com/2/tweets/counts/recent?query=GME&start_time=2024-09-01T00:00:00.000Z&end_time=2024-09-06T00:00:00.000Z&granularity=hour&search_count.fields=end,start,tweet_count"

$Bearer_Token_Here = "AAAAAAAAAAAAAAAAAAAAANhdpAEAAAAArutnO4%2BvGFx9OL2jQAp6tHWc3Pw%3DeFmlBehZtSM8Y09PhzGgB8NUxKZrK9XESISxywgWPlxp3ViMsd"

$headers = @{
    "Authorization" = "Bearer $Bearer_Token_Here"
}

# Generate dynamic filename based on current date and time
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "C:\temp\twitter_data_$timestamp.json"

# Send the request and capture the response
$response = Invoke-WebRequest -Uri $url -Headers $headers

# Convert the content to JSON
$jsonContent = $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Save the JSON content to a file
$jsonContent | Out-File -FilePath $outputFile

Write-Host "Request completed. JSON output saved to $outputFile"