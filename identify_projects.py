#!/usr/bin/env python3
import pandas as pd
import glob
import os
from geopy.distance import geodesic
from datetime import datetime
from pathlib import Path
import configparser
import re
import geopandas as gpd
from shapely.geometry import Point
import shutil

# Load the country boundaries shapefile or GeoJSON
world = gpd.read_file("ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")

# Read configuration
config = configparser.ConfigParser()
config.read("config.txt")

pilot_name = config.get("DEFAULT", "Pilot", fallback="Unknown Pilot")
purpose = config.get("DEFAULT", "Purpose", fallback="Unknown Purpose")
client = config.get("DEFAULT", "Client", fallback="Unknown Client")
time_threshold_hours = float(config.get("DEFAULT", "TimeThreshold", fallback=24))
coordinate_threshold_meters = float(config.get("DEFAULT", "CoordinateThreshold", fallback=1000))
valid_time_threshold = float(config.get("DEFAULT", "ValidTimeThreshold", fallback=50))

output_properties_dir = "project_properties/"
output_properties_path = Path(output_properties_dir)
# Delete the existing directory if it exists
if output_properties_path.exists():
    shutil.rmtree(output_properties_path) # use rmtree to delete directory and its contents
Path(output_properties_dir).mkdir(exist_ok=True)

def get_distance_display(meters):
    return f"{meters:.1f} meters" if meters < 1000 else f"{meters / 1000:.1f} kilometers"

def get_time_display(hours):
    time_display = "None"
    if hours < 1/60:
        time_display = f"{hours * 3600:.0f} seconds"
    elif hours < 1:
        time_display = f"{hours * 60:.0f} minutes"
    elif hours < 24:
        time_display = f"{hours:.1f} hours"
    else:
        time_display = f"{hours / 24:.1f} days"
    return time_display
    
def is_valid_coordinate(coord):
    if not coord or pd.isna(coord):
        return False
    try:
        latitude, longitude = map(float, coord.split())
        return latitude != 0 and longitude != 0
    except ValueError:
        return False

def format_coordinates(coord):
    return coord.replace(' ', ',') if is_valid_coordinate(coord) else None

def calculate_time_difference(prev_time, curr_time, fmt='%Y-%m-%d %H:%M:%S.%f'):
    return abs((datetime.strptime(curr_time, fmt) - datetime.strptime(prev_time, fmt)).total_seconds() / 3600)

def extract_datetime_from_filename(filename):
    match = re.search(r'\d{4}-\d{2}-\d{2}-\d{6}', filename)
    return datetime.strptime(match.group(), '%Y-%m-%d-%H%M%S') if match else None


def get_count_of_missing_gps(csv_files):
    count_of_missing_gps = 0
    for csvfile in csv_files:
        csv_df = pd.read_csv(csvfile)
        if not ('GPS' in csv_df.columns):
            count_of_missing_gps += 1
        elif not is_valid_coordinate(csv_df['GPS'].iloc[-1]):
            count_of_missing_gps += 1
    return count_of_missing_gps

def identify_projects():
    all_filenames = sorted(glob.glob('CSV LOGS/*.csv', recursive=True), key=extract_datetime_from_filename)
    projects = []

    for f in all_filenames:
        df = pd.read_csv(f)
        if 'Time' not in df.columns or 'Date' not in df.columns:
            print(f"Warning: Skipping {f}: Missing 'Time' or 'Date' column.")
            continue

        df['Datetime'] = df['Date'] + ' ' + df['Time']
        takeoff_time, landing_time = df['Datetime'].iloc[0], df['Datetime'].iloc[-1]
        flight_duration = calculate_time_difference(takeoff_time, landing_time) * 3600

        if flight_duration < valid_time_threshold:
            print(f"Info: Skipping {f}: Flight duration too short ({flight_duration:.0f} seconds).")
            continue

        landing_location = format_coordinates(df['GPS'].iloc[-1]) if 'GPS' in df.columns else None
        assigned = False
        time_diff, distance_from_previous = float('inf'), float('inf')
        if projects:
            last_project = projects[-1]
            time_diff = calculate_time_difference(last_project['last_landing_time'], takeoff_time)
            distance_from_previous = geodesic(
                tuple(map(float, last_project['last_landing_location'].split(','))) if last_project['last_landing_location'] else (float('inf'), float('inf')),
                tuple(map(float, landing_location.split(','))) if landing_location else (float('inf'), float('inf'))
            ).meters if last_project['last_landing_location'] and landing_location else float('inf')

            if time_diff <= time_threshold_hours and (distance_from_previous <= coordinate_threshold_meters or distance_from_previous == float('inf')):
                last_project['files'].append(f)
                last_project['last_landing_time'] = landing_time
                last_project['last_landing_location'] = landing_location

                if not last_project['suggested_landing_location'] and landing_location:
                    last_project['suggested_landing_location'] = landing_location
                    print(f"Info: Found a suggestable landing location for \"Project {last_project['id']}\": {landing_location}")

                distance_display = get_distance_display(distance_from_previous)
                time_display = get_time_display(time_diff)
 
                print(f"Info: Assigned {os.path.basename(f)} to {last_project['id']} (TimeDiff: {time_display}, Distance: {distance_display})")
                assigned = True

        if not assigned:
            project_date = takeoff_time.split(' ')[0].replace('/', '-')
            project_id = f"Project_{project_date}"
            if any(p['id'].startswith(project_id) for p in projects):
                project_id = f"{project_id}_{sum(1 for p in projects if project_id in p['id']) + 1}"

            country_name = "Country not found."
            if landing_location:
                latitude, longitude = map(float, landing_location.split(','))
                point = Point(longitude, latitude)
                country = world[world.contains(point)]
                if not country.empty:
                    country_name = f"Country: {country.iloc[0]['NAME']}"

            distance_display = get_distance_display(distance_from_previous)
            time_display = get_time_display(time_diff)

            print("-" * 60)
            print(f"{country_name}".center(60, '-'))
            print(f"Creating new project for {os.path.basename(f)}. TimeDiff:{time_display} Dist:{distance_display}")

            projects.append({
                'id': project_id,
                'files': [f],
                'last_landing_time': landing_time,
                'last_landing_location': landing_location,
                'suggested_landing_location': None
            })

    for project in projects:
        count_of_missing_gps = get_count_of_missing_gps(project['files'])
        with open(f"{output_properties_dir}{project['id']}.txt", 'w') as file:
            file.write("[DEFAULT]\n")
            file.write("# Project Properties\n")
            file.write(f"ProjectID={project['id']}\n")
            if count_of_missing_gps == 0:
                file.write(f"# None of the files miss GPS\n")
                file.write(f"Suggested_landing_location={None}\n")
            else:
                file.write(f"# (Missing GPS / num of files): ({count_of_missing_gps}/{len(project['files'])})\n")
                file.write(f"Suggested_landing_location={project['suggested_landing_location']}\n")
            file.write(f"Files={','.join(project['files'])}\n")
            file.write(f"Pilot={pilot_name}\n")
            file.write(f"# Purpose(Training, Testing, or Commercial)\n")
            file.write(f"Purpose={purpose}\n")
            file.write(f"Client={client}\n")

    print(f"Info: Generated {len(projects)} project property files in {output_properties_dir}.")

if __name__ == "__main__":
    identify_projects()