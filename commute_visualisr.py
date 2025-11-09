import sqlite3
import pandas as pd
import requests
import tempfile
import os
import matplotlib.pyplot as plt
import seaborn as sns
import calplot

response = requests.get("http://192.168.0.101:1010/commutetrackr.db")
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
temp_file.write(response.content)
temp_file.close()
db_temp_path = temp_file.name
print(f'Database downloaded successfully.\nSize: {len(response.content)} bytes.\nLocation: {db_temp_path}\n\n')

conn = sqlite3.connect(db_temp_path)

# Get values from the database, ignoring days where there was zero activity (in which every column contains a NULL)
query = """
SELECT *
FROM commute_logs
WHERE NOT (
    left_home IS NULL AND
    boarded_train_out IS NULL AND
    alighted_train_out IS NULL AND
    boarded_tube_out IS NULL AND
    alighted_tube_out IS NULL AND
    arrived_at_scale_space IS NULL AND
    left_scale_space IS NULL AND
    boarded_tube_return IS NULL
)
"""

df = pd.read_sql_query(query, conn)
conn.close()

# Clean up temporary database file
if os.path.exists(db_temp_path):
    os.unlink(db_temp_path)

# Create a 'straight_home' column
df['straight_home'] = df['boarded_tube_return'].notnull() & df['alighted_tube_return'].notnull()

#Convert time columns to datetime objects and extract useful features
df['date'] = pd.to_datetime(df['date'])

time_columns = [
    'left_home', 'boarded_train_out', 'alighted_train_out', 'boarded_tube_out', 
    'alighted_tube_out', 'arrived_at_scale_space', 'left_scale_space', 
    'boarded_tube_return', 'alighted_tube_return', 'boarded_train_return', 
    'alighted_train_return', 'arrived_at_station', 'left_station', 'arrived_at_home'
]

for col in time_columns:
    df[f'{col}_dt'] = df.apply(lambda row: 
        pd.to_datetime(f'{row['date'].date()} {row[col]}') 
        if pd.notna(row[col]) and row[col] != '' else pd.NaT, axis=1)


# Calculate durations for different segments of the journey

# cycle_there: 'left_home' > 'arrived_at_station'
# transferring_to_train_out: 'arrived_at_station' > 'boarded_train_out'
# train_out: 'boarded_train_out' > 'alighted_train_out'
# transferring_to_tube_out: 'alighted_train_out' > 'boarded_tube_out'
# tube_out: 'boarded_tube_out' > 'alighted_tube_out'
# walking_to_scalespace: 'alighted_tube_out' > 'arrived_at_scale_space'
# door_to_door_out: 'left_home' > 'arrived_at_scale_space'

if 'left_home_dt' in df.columns and 'arrived_at_station_dt' in df.columns:
    df['cycle_there'] = (df['arrived_at_station_dt'] - df['left_home_dt']).dt.total_seconds() / 60

if 'boarded_train_out_dt' in df.columns and 'arrived_at_station_dt' in df.columns:
    df['transferring_to_train_out'] = (df['boarded_train_out_dt'] - df['arrived_at_station_dt']).dt.total_seconds() / 60

if 'alighted_train_out_dt' in df.columns and 'boarded_train_out_dt' in df.columns:
    df['train_out'] = (df['alighted_train_out_dt'] - df['boarded_train_out_dt']).dt.total_seconds() / 60

if 'boarded_tube_out_dt' in df.columns and 'alighted_train_out_dt' in df.columns:
    df['transferring_to_tube_out'] = (df['boarded_tube_out_dt'] - df['alighted_train_out_dt']).dt.total_seconds() / 60

if 'alighted_tube_out_dt' in df.columns and 'boarded_tube_out_dt' in df.columns:
    df['tube_out'] = (df['alighted_tube_out_dt'] - df['boarded_tube_out_dt']).dt.total_seconds() / 60

if 'arrived_at_scale_space_dt' in df.columns and 'alighted_tube_out_dt' in df.columns:
    df['walking_to_scalespace'] = (df['arrived_at_scale_space_dt'] - df['alighted_tube_out_dt']).dt.total_seconds() / 60

if 'arrived_at_scale_space_dt' in df.columns and 'left_home_dt' in df.columns:
    df['door_to_door_out'] = (df['arrived_at_scale_space_dt'] - df['left_home_dt']).dt.total_seconds() / 60

# walking_to_woodlane: 'left_scale_space' > 'boarded_tube_return'
# tube_return: 'boarded_tube_return' > 'alighted_tube_return'
# transferring_to_train_return: 'alighted_tube_return' > 'boarded_train_return'
# train_return: 'boarded_train_return' > 'alighted_train_return'
# walk_to_bike: 'alighted_train_return' > 'left_station'
# cycle_home: 'left_station' > 'arrived_at_home'
# door_to_door_return: 'left_scale_space' > 'arrived_at_home'

if 'boarded_tube_return_dt' in df.columns and 'left_scale_space_dt' in df.columns:
    df['walking_to_woodlane'] = (df['boarded_tube_return_dt'] - df['left_scale_space_dt']).dt.total_seconds() / 60

if 'alighted_tube_return_dt' in df.columns and 'boarded_tube_return_dt' in df.columns:
    df['tube_return'] = (df['alighted_tube_return_dt'] - df['boarded_tube_return_dt']).dt.total_seconds() / 60

if 'boarded_train_return_dt' in df.columns and 'alighted_tube_return_dt' in df.columns:
    df['transferring_to_train_return'] = (df['boarded_train_return_dt'] - df['alighted_tube_return_dt']).dt.total_seconds() / 60

if 'alighted_train_return_dt' in df.columns and 'boarded_train_return_dt' in df.columns:
    df['train_return'] = (df['alighted_train_return_dt'] - df['boarded_train_return_dt']).dt.total_seconds() / 60

if 'left_station_dt' in df.columns and 'alighted_train_return_dt' in df.columns:
    df['walk_to_bike'] = (df['left_station_dt'] - df['alighted_train_return_dt']).dt.total_seconds() / 60

if 'arrived_at_home_dt' in df.columns and 'left_station_dt' in df.columns:
    df['cycle_home'] = (df['arrived_at_home_dt'] - df['left_station_dt']).dt.total_seconds() / 60

if 'arrived_at_home_dt' in df.columns and 'left_scale_space_dt' in df.columns:
    df['door_to_door_return'] = (df['arrived_at_home_dt'] - df['left_scale_space_dt']).dt.total_seconds() / 60

# If I've gone out in Reading after work that's not going straight home
df.loc[df['door_to_door_return'] > 180, 'straight_home'] = False


# Cycle there
valid_rows = df[df['cycle_there'].notnull()]
cycle_there_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['cycle_there'],
    "activity": "cycling",
    "direction": "out"
})

# Train out
valid_rows = df[df['train_out'].notnull()]
train_out_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['train_out'],
    "activity": "train",
    "direction": "out"
})

# Tube out
valid_rows = df[df['tube_out'].notnull()]
tube_out_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['tube_out'],
    "activity": "tube",
    "direction": "out"
})

# Transferring out (sum of transferring_to_train_out and transferring_to_tube_out)
valid_rows = df[(df['transferring_to_train_out'].notnull()) & (df['transferring_to_tube_out'].notnull())]
transferring_out_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['transferring_to_train_out'] + valid_rows['transferring_to_tube_out'],
    "activity": "transferring",
    "direction": "out"
})

# Walking to Scale Space
valid_rows = df[df['walking_to_scalespace'].notnull()]
walking_to_scalespace_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['walking_to_scalespace'],
    "activity": "walking",
    "direction": "out"
})

# Door to door out
valid_rows = df[df['door_to_door_out'].notnull()]
door_to_door_out_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['door_to_door_out'],
    "activity": "door2door",
    "direction": "out"
})

# Walking to Wood Lane
valid_rows = df[df['walking_to_woodlane'].notnull()]
walking_to_woodlane_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['walking_to_woodlane'],
    "activity": "walking",
    "direction": "return"
})

# Tube return
valid_rows = df[df['tube_return'].notnull()]
tube_return_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['tube_return'],
    "activity": "tube",
    "direction": "return"
})

# Train return
valid_rows = df[df['train_return'].notnull()]
train_return_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['train_return'],
    "activity": "train",
    "direction": "return"
})

# Transferring return (sum of transferring_to_train_return and walk_to_bike)
valid_rows = df[(df['transferring_to_train_return'].notnull()) & (df['walk_to_bike'].notnull()) & (df['straight_home'] == True)]
transferring_return_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['transferring_to_train_return'] + valid_rows['walk_to_bike'],
    "activity": "transferring",
    "direction": "return"
})

# Cycle home
valid_rows = df[df['cycle_home'].notnull()]
cycle_home_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['cycle_home'],
    "activity": "cycling",
    "direction": "return"
})

# Door to door return
valid_rows = df[(df['door_to_door_return'].notnull()) & (df['straight_home'] == True)]
door_to_door_return_df = pd.DataFrame({
    "date": valid_rows['date'],
    "duration": valid_rows['door_to_door_return'],
    "activity": "door2door",
    "direction": "return"
})

# Combine all into one durations dataframe
durations = pd.concat([
    cycle_there_df,
    train_out_df,
    tube_out_df,
    walking_to_scalespace_df,
    door_to_door_out_df,
    transferring_out_df,
    walking_to_woodlane_df,
    tube_return_df,
    train_return_df,
    cycle_home_df,
    door_to_door_return_df,
    transferring_return_df
], ignore_index=True)



total_time_commuting = df.loc[(df['door_to_door_return'].notnull()) & (df['straight_home'] == True)].door_to_door_return.sum() + df.door_to_door_out.sum()
hours = int(total_time_commuting // 60)
minutes = int(total_time_commuting % 60)
print(f"Total time spent commuting: {hours}h {minutes}m\n(excluding days when I didn't come straight home)\n\n")


# Get list of unique activities to loop over
activities = durations['activity'].unique()

# Create separate figures for each activity
for activity in activities:
    # Filter data for current activity
    activity_data = durations[durations['activity'] == activity]
    
    # Create figure
    plt.figure(figsize=(8, 6))
    
    # Create split violin plot
    sns.violinplot(
        data=activity_data,
        x='activity',
        y='duration',
        hue='direction',
        inner="points",
        split=True,
        bw_adjust=0.8,
        palette=['lightblue', 'lightcoral']
        #,inner_kws=dict(box_width=15, whis_width=1.5, color="0.4", marker="<", markersize=8)
    )
    
    plt.title(f'{activity.capitalize()} Duration Distribution (Out vs Return)', fontsize=14, fontweight='bold')
    plt.xticks([])  # Remove x-axis tick labels
    plt.xlabel('')  # Remove x-axis label
    plt.ylabel('Duration (minutes)', fontsize=12)
    plt.legend(title='Direction', loc='upper right')
    plt.tight_layout()

    plt.savefig(f'{activity}_duration_distribution.png', dpi=300, bbox_inches='tight')



# Bar plot of total duration by activity (excluding door2door)
activity_totals = durations[durations['activity'] != 'door2door'].groupby("activity")["duration"].sum().reset_index()
plt.figure(figsize=(10, 6))
sns.barplot(data=activity_totals, x='activity', y='duration')
plt.title('Total Duration by Activity')
plt.ylabel('Total Duration (minutes)')
plt.xlabel('')
plt.tight_layout()
plt.savefig('total_duration_by_activity.png', dpi=300, bbox_inches='tight')



df.set_index("date", inplace=True)

fig, ax = calplot.calplot(df.door_to_door_out,
                          vmin=60,
                          vmax=90,
                          dropzero=True,
                          linewidth=0.2,
                          cmap="plasma",
                          yearlabel_kws={'fontname':'sans-serif'},
                          suptitle='Door-to-door time, in minutes, commuting to work');
fig.savefig("calplot_out", dpi=300, bbox_inches='tight')

fig, ax = calplot.calplot(df.loc[df['straight_home'] == True].door_to_door_return,
                          vmin=60,
                          vmax=90,
                          dropzero=True,
                          linewidth=0.2,
                          cmap="plasma",
                          yearlabel_kws={'fontname':'sans-serif'},
                          suptitle='Door-to-door time, in minutes, returning home');
fig.savefig("calplot_return", dpi=300, bbox_inches='tight')

print("Plots created.")
