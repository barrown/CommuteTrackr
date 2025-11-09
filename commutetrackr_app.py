from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime, date
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/ftp/files/commutetrackr.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DATABASE_PATH = '/home/pi/ftp/files/commutetrackr.db'


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_or_create_today_record():
    """Get today's record or create one if it doesn't exist"""
    today = date.today().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Try to get today's record
        cursor.execute('SELECT * FROM commute_logs WHERE date = ?', (today,))
        record = cursor.fetchone()
        
        if record is None:
            # Create new record for today
            cursor.execute(
                'INSERT INTO commute_logs (date) VALUES (?)',
                (today,)
            )
            conn.commit()
            
            # Fetch the newly created record
            cursor.execute('SELECT * FROM commute_logs WHERE date = ?', (today,))
            record = cursor.fetchone()
            
        return dict(record)

def update_commute_activity(activity_column, timestamp):
    """Update a specific activity with timestamp if not already set"""
    today = date.today().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if activity is already logged for today
        cursor.execute(
            f'SELECT {activity_column} FROM commute_logs WHERE date = ?',
            (today,)
        )
        
        result = cursor.fetchone()
        if result and result[0] is not None:
            return False  # Already logged
        
        # Update the record (removed updated_at column)
        cursor.execute(
            f'UPDATE commute_logs SET {activity_column} = ? WHERE date = ?',
            (timestamp, today)
        )
        
        conn.commit()
        return True

@app.route('/')
def index():
    """Main page with commute tracking buttons"""
    try:
        record = get_or_create_today_record()
        return render_template('commutetrackr.html', record=record)
    except Exception as e:
        logger.error(f"Error loading main page: {e}")
        return "Error loading page", 500

@app.route('/log_activity', methods=['POST'])
def log_activity():
    """Log commute activity via AJAX"""
    try:
        data = request.get_json()
        activity = data.get('activity')
        
        if not activity:
            return jsonify({'success': False, 'error': 'Activity not specified'}), 400
        
        # Validate activity
        valid_activities = [
            'boarded_train_out', 'alighted_train_out', 'boarded_tube_out',
            'alighted_tube_out', 'arrived_at_scale_space', 'left_scale_space',
            'boarded_tube_return', 'alighted_tube_return', 'boarded_train_return',
            'alighted_train_return'
        ]
        
        if activity not in valid_activities:
            return jsonify({'success': False, 'error': 'Invalid activity'}), 400
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        success = update_commute_activity(activity, timestamp)
        
        if success:
            logger.info(f"Logged activity: {activity} at {timestamp}")
            return jsonify({'success': True, 'timestamp': timestamp})
        else:
            return jsonify({'success': False, 'error': 'Activity already logged today'})
        
    except Exception as e:
        logger.error(f"Error logging activity: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500



@app.route('/api/log_external', methods=['POST'])
def log_external_activity():
    """API endpoint for external activity logging - Robust version"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Valid external activities
        valid_external = ['left_home', 'arrived_at_station', 'left_station', 'arrived_at_home']
        
        today = date.today().isoformat()
        logged_activities = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure today's record exists using INSERT OR IGNORE
            cursor.execute('INSERT OR IGNORE INTO commute_logs (date) VALUES (?)', (today,))
            
            # Process each activity individually
            for key, value in data.items():
                if key in valid_external and value:
                    # Validate timestamp format
                    try:
                        datetime.strptime(value, '%H:%M:%S')
                    except ValueError:
                        return jsonify({
                            'success': False, 
                            'error': f'Invalid time format for {key}. Use HH:MM:SS'
                        }), 400
                    
                    # Update individual field (removed updated_at column)
                    update_query = f'UPDATE commute_logs SET {key} = ? WHERE date = ?'
                    cursor.execute(update_query, (value, today))
                    
                    rows_affected = cursor.rowcount
                    logger.debug(f"Updated {key}: {rows_affected} rows affected")
                    
                    if rows_affected > 0:
                        logged_activities.append(key)
                    else:
                        logger.error(f"Failed to update {key} - no rows affected")
            
            # Commit all changes
            conn.commit()
            
            # Verify the updates
            cursor.execute('SELECT * FROM commute_logs WHERE date = ?', (today,))
            record = cursor.fetchone()
            if record:
                logger.info(f"Final record state: {dict(record)}")
            
        if logged_activities:
            logger.info(f"Successfully logged external activities: {logged_activities}")
            return jsonify({'success': True, 'logged': logged_activities})
        else:
            return jsonify({'success': False, 'error': 'No activities were logged'})
        
    except Exception as e:
        logger.error(f"Error logging external activity: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    

@app.route('/api/today')
def get_today_data():
    """API endpoint to get today's commute data"""
    try:
        record = get_or_create_today_record()
        return jsonify(record)
    except Exception as e:
        logger.error(f"Error fetching today's data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# after changing python script you must execute: sudo systemctl reload apache2