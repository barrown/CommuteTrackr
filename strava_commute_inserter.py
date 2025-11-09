#! python3

import requests
from datetime import datetime, date, timedelta
from dateutil import parser as date_parser
import urllib3
urllib3.disable_warnings()

payload = {
'client_id': 'ID',
'client_secret': 'SECRET',
'refresh_token': 'TOKEN',
'grant_type': "refresh_token",
'f': 'json'
}

res = requests.post('https://www.strava.com/oauth/token', data=payload, verify=False)
access_token = res.json()['access_token']
headers = {'Authorization': f'Authorization: Bearer {access_token}'}
activities = requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=5', headers=headers, verify=False).json()

list_of_times = []

for activity in activities:
    start_time = date_parser.parse(activity['start_date_local'])
    activity_date = start_time.date()
    
    if (activity_date == date.today() and activity.get('type', '') == "Ride"):
        duration_seconds = activity.get('elapsed_time', 0)
        end_time = start_time + timedelta(seconds=duration_seconds)
        
        list_of_times.append(start_time)
        list_of_times.append(end_time)
        
list_of_times.sort()

if len(list_of_times) == 0:
    print("⚠️ No rides found for today")
    exit

commute_data = {'left_home': list_of_times[0].strftime('%H:%M:%S'),
                'arrived_at_station': list_of_times[1].strftime('%H:%M:%S'),
                'left_station': list_of_times[2].strftime('%H:%M:%S'),
                'arrived_at_home': list_of_times[3].strftime('%H:%M:%S')}

print("\n🗺️  Mapped commute data:")
for key, value in commute_data.items():
    print(f"   {key}: {value}")

response = requests.post("http://192.168.0.101:1010/commutetrackr/api/log_external",
    json=commute_data,
    headers={'Content-Type': 'application/json'})

result = response.json()

if result.get('success'):
    print("\n✅ Successfully updated CommuteTrackr")
