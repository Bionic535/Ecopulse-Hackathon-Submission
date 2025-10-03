# WA Traffic Data Dashboard

A Streamlit web application that displays Western Australia traffic data on an interactive map using Folium.

## Features

- 🗺️ **Interactive Map**: View traffic sites on a map with color-coded markers based on traffic volume
- 📊 **Data Analysis**: Charts showing traffic distribution and heavy truck percentages
- 🔍 **Filtering**: Filter sites by traffic volume and heavy truck percentage
- 📋 **Data Table**: Detailed view of all traffic data with download capability

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## .env File
Please create a .env file in your directory with a google maps api key and write it as such
```bash
GOOGLE_MAPS_API_KEY = "YOUR_KEY"
```
## Running the App

```bash
streamlit streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

