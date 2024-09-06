import json
import pandas as pd
from datetime import datetime, timedelta

# Load the JSON data
with open('C:\\temp\\twitter_data_20240906_140759.json', 'r') as file:
    json_data = json.load(file)

# Extract the tweet data
tweet_data = json_data['data']

# Convert to DataFrame
df = pd.DataFrame(tweet_data)

# Convert 'start' column to datetime
df['start'] = pd.to_datetime(df['start'])

# Create a function to round down to the nearest 5-minute interval
def round_down_to_5min(dt):
    return dt - timedelta(minutes=dt.minute % 5,
                          seconds=dt.second,
                          microseconds=dt.microsecond)

# Apply the rounding function to create a new column for grouping
df['group_start'] = df['start'].apply(round_down_to_5min)

# Group by the 5-minute intervals and sum the tweet counts
grouped_df = df.groupby('group_start')['tweet_count'].sum().reset_index()

# Format the 'group_start' column to string for better readability in Excel
grouped_df['group_start'] = grouped_df['group_start'].dt.strftime('%Y-%m-%d %H:%M:%S')

# Create an Excel writer object
with pd.ExcelWriter('tweet_counts_5min_grouped.xlsx') as writer:
    # Write the grouped data to the Excel file
    grouped_df.to_excel(writer, index=False, sheet_name='Tweet Counts')

    # Auto-adjust columns' width
    for column in grouped_df:
        column_length = max(grouped_df[column].astype(str).map(len).max(), len(column))
        col_idx = grouped_df.columns.get_loc(column)
        writer.sheets['Tweet Counts'].max_column(col_idx, col_idx, column_length)

print("Excel file 'tweet_counts_5min_grouped.xlsx' has been created successfully.")