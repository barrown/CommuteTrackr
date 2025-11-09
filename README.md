# CommuteTrackr
Frontend, Backend, Strava connection, and Visualiser for tracking my commute to Scale Space.

The main [CommuteTrackr app](commutetrackr_app.py) uses a SQLite database to store the time of various checkpoints on my commute. Each day the app is loaded a blank row is created for that date. The database was initialised with:

```
CREATE TABLE IF NOT EXISTS commute_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    left_home TEXT,
    boarded_train_out TEXT,
    alighted_train_out TEXT,
    boarded_tube_out TEXT,
    alighted_tube_out TEXT,
    arrived_at_scale_space TEXT,
    left_scale_space TEXT,
    boarded_tube_return TEXT,
    alighted_tube_return TEXT,
    boarded_train_return TEXT,
    alighted_train_return TEXT,
    arrived_at_station TEXT,
    left_station TEXT,
    arrived_at_home TEXT;
```
Flask is used to serve the [HTML+JS+CSS](templates/commutetrackr.html) frontend. The root URL shows buttons that can be pressed at the checkpoints, or if they have already been pressed, the button with the time of that activity:
![Screenshot of app](example%20figures/frontend_fresh.jpg)

When a button is pressed Javascript posts the JSON activity name to a `/log_activity` endpoint. The Python app then logs the datetime against that activity in the database. The button states are then refreshed (so no need to reload the whole page) to show the time of the activity.

To get the start & end times of my cycles, rather than pressing buttons my phone, I run a separate Python script when I get home called [strava_commute_inserter.py](strava_commute_inserter.py). This gets the last two cycle rides, calculates the end time from the duration, and posts the JSON payload (containing activities and times) to `/api/log_external`, which updates the relevant records. There is also logging and some error handling.

A final endpoint `/api/today` can be used to return a JSON of the current records for today.

The Flask app is hosted by Apache2 (on a Raspberry Pi 4) and a version of my "/etc/apache2/conf-available/[000-default.conf)](etc%20-%20apache2%20-%20conf-available%20-%20000-default.conf)" file is available, along with the [WSGI](commutetrackr_app.wsgi) file.

# CommuteVisualisr
This is designed to be run on a separate computer to the backend app. Because SQLite is just a file rather than a served database infrastructure, we first copy the database across locally, and then load it into a Pandas dataframe. Some tedious cleaning then happens to turn the text values into dates, datetimes and durations. Then a second dataframe is created with Date/Duration/Activity/Direction columns so we can make violin plots to show the distributions of the different activities and differentiate between going to work (out) and coming home (return). We also make a bar plot showing total duration of each activity:
![Bar chart](example%20figures/total_duration_by_activity.png)

Example of one of the violin plots:
![Violin plot](example%20figures/door2door_duration_distribution.png)

To see the data temporally I used ![calplot](https://calplot.readthedocs.io/en/latest/) which works nicely with any dataframe with a datetime index like we have here:

![Calplot](example%20figures/calplot_out.png)

Fridays are usually pretty fast for getting in!
