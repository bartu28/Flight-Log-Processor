# Flight Log Processor

---

This repository contains a simple set of Python scripts designed to automate the processing and organization of drone flight log data. It intelligently groups raw CSV flight logs into distinct "projects" based on temporal proximity and geographical location of landing points.

## Key Features

- **Automated Project Identification**: Groups individual flight CSV files into logical projects by analyzing take-off/landing times and GPS coordinates.
- **Data Extraction & Enrichment**: Extracts crucial flight details such as take-off/landing times, flight duration, aircraft type, pilot, client, and purpose.
- **Intelligent GPS Handling**: Automatically attempts to infer missing GPS landing locations for flights within a project by utilizing valid GPS data from other closely related flights or a user-defined suggested location.
- **Configurable Parameters**: Allows customization of project grouping thresholds (time and distance) and default project metadata via a configuration file.
- **Comprehensive Reporting**: Generates detailed, project-specific CSV log files, while providing a clear overview of all processed flights and projects printed on the console of the script. Additionally it uses ne_110m_admin_0_countries from naturalearthdata.com to find the country name of the specified coordinate.

## Usage

1.  Specify the basic flight configurations to the `config.txt` file.
2.  Run the `identify projects` script.
3.  Specify configuration for individual projects (e.g., `Suggested_landing_location`).
4.  Run the `process projects` script.

---

This tool is ideal for anyone needing to filter and organize their drone flight logs based on flight time, distance, location.
