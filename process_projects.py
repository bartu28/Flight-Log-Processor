import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import csv
import configparser
import shutil

def append_to_csv(target_csv_file, source_csv_file):
    # Read the source CSV file
    with open(source_csv_file, newline='', encoding='utf-8') as source_file:
        reader = csv.reader(source_file)
        source_data = list(reader)
    # Skip the headers (first row) in the source file
    source_data = source_data[1:]
    # Append the data to the target CSV file
    with open(target_csv_file, mode='a', newline='', encoding='utf-8') as target_file:
        writer = csv.writer(target_file)
        writer.writerows(source_data)
    print(f"Appended data from '{source_csv_file}' to '{target_csv_file}'.")

# Directory containing project property files
properties_dir = "project_properties/"
output_dir = "project_outputs/"
output_path = Path(output_dir)
# Delete the existing directory if it exists
if output_path.exists():
    shutil.rmtree(output_path)
Path(output_dir).mkdir(exist_ok=True)

# Log file headers
summary_headers = [
    'Date',
    'Take_Off_UTC',
    'Landing_UTC',
    'Flight_Time',
    'Client',
    'Landing_Location',
    'Purpose',
    'Aircraft',
    'Pilot',
]
# function to calculate time difference
def calculate_time_difference(prev_time, curr_time, fmt='%Y-%m-%d %H:%M:%S.%f'):
    return abs((datetime.strptime(curr_time, fmt) - datetime.strptime(prev_time, fmt)).total_seconds())
def calculate_time_difference2(prev_time, curr_time, fmt='%Y-%m-%d %H:%M:%S.%f'):
    return (datetime.strptime(curr_time, fmt) - datetime.strptime(prev_time, fmt))

def process_project(properties_file):
    # Read project properties
    with open(properties_file, 'r') as f:
        # Read configuration
        config = configparser.ConfigParser()
        config.read(properties_file)

        project_id = config.get("DEFAULT", "ProjectID", fallback="Unknown Project Id")
        files = config.get("DEFAULT", "Files", fallback="").split(',')
        pilot = config.get("DEFAULT", "Pilot", fallback="")
        purpose = config.get("DEFAULT", "Purpose", fallback="")
        client = config.get("DEFAULT", "Client", fallback="")
        Suggested_landing_location = config.get("DEFAULT", "Suggested_landing_location", fallback="")
        if Suggested_landing_location == "None":
            Suggested_landing_location = None
        else:
            Suggested_landing_location = Suggested_landing_location.replace(',', '')
            Suggested_landing_location = Suggested_landing_location.replace('"', '')
    # Create a log file for the project
    log_filename = f"{output_dir}{project_id}_log.csv"
    with open(log_filename, 'w', newline='') as log_file:
        writer = csv.writer(log_file)
        writer.writerow(summary_headers)
        has_valid_gps = True
        for f in files:
            df = pd.read_csv(f)
            date = pd.to_datetime(df['Date'].iloc[0]).strftime('%Y-%m-%d')
            to = df['Time'].iloc[0]
            la = df['Time'].iloc[-1]

            landing_locations = []
            # Get current landing location
            landing_location = None
            try:
                landing_location = df['GPS'].iloc[-1]
                # Check if landing_location is NaN, None, or invalid
                if pd.isna(landing_location) or landing_location in ['None', 'nan', 'Nan', 'NAN', 'NONE', 'none', '']:
                    landing_location = 'None'
            except:
                landing_location = 'None'
            # If the current landing location is 'None', search CSV files in the same project
            if landing_location == 'None' and has_valid_gps:
                if not Suggested_landing_location:
                    print(f"Info: Searching for the nearest gps location in time for the gps missing file: {f}.")
                    for file in files:
                        other_df = pd.read_csv(file)
                        other_landing_location = None
                        try:
                            other_landing_location = other_df['GPS'].iloc[-1]
                            # Check if landing_location is NaN, None, or invalid
                            if pd.isna(other_landing_location) or other_landing_location in ['None', 'nan', 'Nan', 'NAN', '']:
                                other_landing_location = 'None'
                        except:
                            other_landing_location = 'None'
                        if other_landing_location != 'None':
                            timeDiff = calculate_time_difference(other_df['Date'].iloc[0] + " " +other_df['Time'].iloc[0], df['Date'].iloc[0] + " " + df['Time'].iloc[0], fmt='%Y-%m-%d %H:%M:%S.%f')
                            landing_locations.append({
                                'timeDiff': abs(timeDiff),
                                'location': other_landing_location
                            })
                    if len(landing_locations) > 0:
                        landing_locationn = min(landing_locations, key=lambda x: x['timeDiff'])
                        landing_location = landing_locationn['location']
                        print(f"Info: Found a gps location for {f} new location: {landing_location}")
                else:
                    print(f"Info: Using suggested landing location for the gps missing file: {f}. Loc:{Suggested_landing_location}")
                    landing_location = Suggested_landing_location

            # If still no landing location found
            if landing_location == 'None':
                print(f"Warning: No valid GPS data for file {f}.")
                has_valid_gps = False

            # advanced_to = df['Date'].iloc[0] + ' ' + df['Time'].iloc[0]
            # advanced_la = df['Date'].iloc[-1] + ' ' + df['Time'].iloc[-1]
            # Calculate flight time
            # #calculate_time_difference2(advanced_la, advanced_to, fmt='%Y-%m-%d %H:%M:%S.%f')
            Formattt = '%H:%M:%S.%f'
            flight_time = datetime.strptime(la,Formattt) - datetime.strptime(to,Formattt)
            aircraft = os.path.basename(f).split('-')[0]
            # Write flight details to the log file
            writer.writerow([
                date, to, la, flight_time, client, landing_location, purpose, aircraft, pilot
            ])
            
    print(f"Processed project {project_id} and generated {log_filename}.")
    # if new_data.csv doesnt exist, create it
    if not os.path.exists("new_data.csv"):
        with open("new_data.csv", 'w', newline='') as new_file:
            writer = csv.writer(new_file)
    append_to_csv("new_data.csv", log_filename)

# Process all project property files
if __name__ == "__main__":
    property_files = [i for i in Path(properties_dir).glob("*.txt")]
    if os.path.exists("new_data.csv"):
        os.remove("new_data.csv")
    for prop_file in property_files:
        process_project(prop_file)
    

    #csv_path_dir = "CSV LOGS/"
    #csv_path = Path(csv_path_dir)
    # Delete the existing directory if it exists
    #if csv_path.exists():
        #shutil.rmtree(csv_path)
    #Path(csv_path).mkdir(exist_ok=True)