from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def connect_to_mongodb(connection_string="mongodb://mads-broker.local:27017/", database_name="your_database"):
    """Connect to MongoDB and return database object"""
    client = MongoClient(connection_string)
    if not client:
        raise ConnectionError("Failed to connect to MongoDB")
    db = client[database_name]
    return db

def get_user_input():
    """Get filtering criteria from user"""
    user = 'Léandre'
    operation = 'Turning Power (AX200)'
    trial_number = '4'
    #user = input("Enter user name: ")
    #operation = input("Enter operation: ")
    #trial_number = input("Enter trial number: ")
    return user, operation, trial_number

def find_test_intervals(db, user, operation, trial_number):
    """Find test intervals based on marker in/out events"""
    metadata_collection = db['metadata']

    # Query for marker events with specified criteria
    query_in = {
        'message.info.user': user,
        'message.info.operation': operation,
        'message.info.trial_number': trial_number,
        'message.event': 'marker in'
    }
    query_out = {
        'message.info.user': user,
        'message.info.operation': operation,
        'message.info.trial_number': str(int(trial_number)+1),
        'message.event': 'marker out'
    }
    print(f"[DEBUG] {metadata_collection.find(query_in)}")
    print(f"[DEBUG] {metadata_collection.find(query_out)}")

    markers = list(metadata_collection.find(query_in).sort('timestamp', 1))
    markers += list(metadata_collection.find(query_out).sort('timestamp', 1))
    if len(markers) == 2:
        print(f"[DEBUG] Test number {query_in.get('message.info.trial_number')} found in the Data Base!")
    else:
        print(f"[ERROR] Information of test number {query_in.get('message.info.trial_number')} not found in the Data Base.")
    # If no results, try broader queries for debugging
    if not markers:
        print("[DEBUG] Trying broader queries...")

        # Try just user filter
        user_docs = list(metadata_collection.find({'message.info.user': user}).limit(5))
        print(f"[DEBUG] Documents with user '{user}': {len(user_docs)}")

        # Try just event filter
        event_docs = list(metadata_collection.find({'message.event': {'$in': ['marker in', 'marker out']}}).limit(5))
        print(f"[DEBUG] Documents with marker events: {len(event_docs)}")

        # Show structure of any marker events found
        if event_docs:
            print(f"[DEBUG] Example marker event: {event_docs[0]}")

    intervals = []
    start_time = None

    for marker in markers:
        event = marker['message']['event']
        timestamp = marker['timestamp']
        if event == 'marker in':
            start_time = timestamp
        elif event == 'marker out' and start_time is not None:
            intervals.append((start_time, timestamp))
            start_time = None

    return intervals

def get_arduino_data(db, intervals):
    """Get arduino data for specified time intervals"""
    arduino_collection = db['arduino_01']
    all_data = []

    for start_time, end_time in intervals:
        query = {
            'timestamp': {
                '$gte': start_time,
                '$lte': end_time
            }
        }

        data = list(arduino_collection.find(query).sort('timestamp', 1))
        all_data.extend(data)

    return all_data

def process_data_for_plotting(arduino_data, intervals):
    """Process arduino data and create relative time for plotting"""
    processed_data = []

    for start_time, end_time in intervals:
        interval_data = [
            doc for doc in arduino_data
            if start_time <= doc['timestamp'] <= end_time
        ]

        if interval_data:
            # Create relative time from start of test
            for doc in interval_data:
                relative_time = (doc['timestamp'] - start_time).total_seconds()
                processed_data.append({
                    'relative_time': relative_time,
                    'Current_1': doc['message']['data']['Current_1'],
                    'Current_2': doc['message']['data']['Current_2'],
                    'timestamp': doc['timestamp']
                })

    return processed_data

def plot_current_data(processed_data):
    """Plot Current_1 and Current_2 vs time"""
    if not processed_data:
        print("No data found for the specified criteria.")
        return

    df = pd.DataFrame(processed_data)

    plt.figure(figsize=(12, 8))

    plt.subplot(2, 1, 1)
    plt.plot(df['relative_time'], df['Current_1'], 'b-', linewidth=1, label='Current_1')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Current_1 (A)')
    plt.title('Current_1 vs Time')
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(df['relative_time'], df['Current_2'], 'r-', linewidth=1, label='Current_2')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Current_2 (A)')
    plt.title('Current_2 vs Time')
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.show()

    # Also plot both currents together
    plt.figure(figsize=(10, 6))
    plt.plot(df['relative_time'], df['Current_1'], 'b-', linewidth=1, label='Current_1')
    plt.plot(df['relative_time'], df['Current_2'], 'r-', linewidth=1, label='Current_2')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Current (A)')
    plt.title('Current_1 and Current_2 vs Time')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

def main():
    """Main function to execute the workflow"""
    try:
        # Connect to MongoDB (adjust connection parameters as needed)
        print("[DEBUG] Connecting to MongoDB...")
        db = connect_to_mongodb("mongodb://mads-broker.local:27017/", "mads_test")

        # Get user input
        user, operation, trial_number = get_user_input()

        print(f"[DEBUG] Searching for tests with:")
        print(f"\tUser: {user}")
        print(f"\tOperation: {operation}")
        print(f"\tTrial Number: {trial_number}")

        # Find test intervals
        intervals = find_test_intervals(db, user, operation, trial_number)

        if not intervals:
            print("[ERROR] No test intervals found for the specified criteria.")
            return

        print(f"[DEBUG] Found {len(intervals)} test interval(s):")
        for i, (start, end) in enumerate(intervals, 1):
            print(f"\tInterval {i}: {start} to {end}")

        # Get arduino data
        print("[DEBUG] Retrieving arduino data...")
        arduino_data = get_arduino_data(db, intervals)

        if not arduino_data:
            print("[ERROR] No arduino data found for the specified intervals.")
            return

        print(f"[DEBUG] Retrieved {len(arduino_data)} data points.")

        # Process data for plotting
        processed_data = process_data_for_plotting(arduino_data, intervals)

        # Plot the data
        plot_current_data(processed_data)

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

# This script is designed to connect to a MongoDB database, retrieve arduino data based on user-defined criteria,
# and plot the current data over time. It includes detailed debug statements to trace the computation values
if __name__ == "__main__":
    main()