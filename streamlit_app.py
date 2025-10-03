import streamlit as st
import folium
import json
import pandas as pd
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import googlemaps
from dotenv import load_dotenv
import os


# Initialize Google Maps API
def initialize_google_maps():
    load_dotenv()
    """Initialize Google Maps API client"""
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    try:
        gmaps = googlemaps.Client(key=api_key)
        return gmaps
    except Exception as e:
        st.error(f"Failed to initialize Google Maps API: {str(e)}")
        return None

def calculate_distance(gmaps, origin_lat, origin_lon, destination_address):
    """Calculate distance from origin coordinates to destination address"""
    if not gmaps or not destination_address:
        return None
    
    try:
        # Geocode the destination address
        geocode_result = gmaps.geocode(destination_address)
        if not geocode_result:
            return None
        
        dest_lat = geocode_result[0]['geometry']['location']['lat']
        dest_lon = geocode_result[0]['geometry']['location']['lng']
        
        # Calculate distance using distance matrix API
        result = gmaps.distance_matrix(
            origins=[(origin_lat, origin_lon)],
            destinations=[(dest_lat, dest_lon)],
            mode="driving",
            units="metric"
        )
        
        if result['rows'][0]['elements'][0]['status'] == 'OK':
            distance = result['rows'][0]['elements'][0]['distance']['text']
            duration = result['rows'][0]['elements'][0]['duration']['text']
            distance_value = result['rows'][0]['elements'][0]['distance']['value']  # Distance in meters
            return {
                'distance': distance,
                'duration': duration,
                'distance_value': distance_value,
                'destination_coords': (dest_lat, dest_lon)
            }
        return None
    except Exception as e:
        st.error(f"Error calculating distance: {str(e)}")
        return None

def load_data():
    """Load the site statistics data"""
    try:
        with open('site_statistics.json', 'r') as f:
            data = json.load(f)
        return data['statistics']
    except FileNotFoundError:
        st.error("site_statistics.json not found. Please run extract_site_statistics.py first.")
        return []

def load_hydrogen_stations():
    """Load hydrogen refueling stations data"""
    try:
        df = pd.read_csv('hydrogen_refuelling_stations.csv')
        return df
    except FileNotFoundError:
        st.warning("hydrogen_refuelling_stations.csv not found.")
        return pd.DataFrame()

def load_railway_data():
    """Load railway route data from GeoJSON file"""
    try:
        with open('key_freight_route_rail.geojson', 'r') as f:
            railway_data = json.load(f)
        return railway_data
    except FileNotFoundError:
        st.warning("key_freight_route_rail.geojson not found.")
        return None

def load_road_data():
    """Load key freight road route data from GeoJSON file"""
    try:
        with open('key_freight_route_road.geojson', 'r') as f:
            road_data = json.load(f)
        return road_data
    except FileNotFoundError:
        st.warning("key_freight_route_road.geojson not found.")
        return None

def load_secondary_route_data():
    """Load secondary route data from GeoJSON file"""
    try:
        with open('secondary_route.geojson', 'r') as f:
            secondary_data = json.load(f)
        return secondary_data
    except FileNotFoundError:
        st.warning("secondary_route.geojson not found.")
        return None



def create_traffic_map(data, hydrogen_stations=None, railway_data=None, road_data=None, secondary_data=None, show_traffic=True, show_hydrogen=True, show_railway=True, show_roads=True, show_secondary=True, selected_classes=None):
    """Create a Folium map with traffic data, hydrogen stations, and all route types"""
    if not data:
        return None
    
    # Calculate center point from all locations
    lats = [item['site']['location']['lat'] for item in data]
    lons = [item['site']['location']['long'] for item in data]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # Create map centered on Western Australia
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Calculate percentiles once outside the loop for efficiency
    # Define class_keys for use throughout the function
    class_keys = [f"Class{class_name.split()[-1]}" for class_name in selected_classes] if selected_classes else []
    
    if selected_classes:
        all_combined_counts = [sum(d.get(key, 0) for key in class_keys) for d in data]
        if all_combined_counts:
            top_third_threshold = np.quantile(all_combined_counts, 0.67)
            middle_third_threshold = np.quantile(all_combined_counts, 0.33)
        else:
            top_third_threshold = middle_third_threshold = 0
    else:
        all_totals = [d['Class3'] + d['Class4'] + d['Class5'] + d['Class6'] + d['Class7'] + d['Class8'] + d['Class9'] + d['Class10'] for d in data]
        if all_totals:
            top_third_threshold = np.quantile(all_totals, 0.67)
            middle_third_threshold = np.quantile(all_totals, 0.33)
        else:
            top_third_threshold = middle_third_threshold = 0
    
    # Add markers for each traffic site
    if show_traffic:
        for item in data:
                site = item['site']
                lat = site['location']['lat']
                lon = site['location']['long']
                
                
                # Create popup content based on filter
                if selected_classes:
                    # Show selected classes when filter is applied
                    combined_count = sum(item[key] for key in class_keys)
                    
                    # Create individual class lines
                    class_lines = []
                    for class_name in selected_classes:
                        class_key = f"Class{class_name.split()[-1]}"
                        class_lines.append(f"<p><strong>{class_name}:</strong> {item[class_key]:,}</p>")
                    
                    popup_content = f"""
                    <div style="width: 300px;">
                        <h4>{site['roadname']}</h4>
                        <p><strong>Site Number:</strong> {site['siteNumber']}</p>
                        <p><strong>Location:</strong> {site['locationDesc']}</p>
                        <p><strong>Direction:</strong> {site['roadDir']}</p>
                        <hr>
                        <h5>Traffic Data (2020)</h5>
                        <p><strong>Total Vehicles (Class 3+):</strong> {item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']:,}</p>
                        <p><strong>Combined ({', '.join(selected_classes)}):</strong> {combined_count:,}</p>
                        {''.join(class_lines)}
                    </div>
                    """
                else:
                    # Show all classes when no filter is applied
                    popup_content = f"""
                    <div style="width: 300px;">
                        <h4>{site['roadname']}</h4>
                        <p><strong>Site Number:</strong> {site['siteNumber']}</p>
                        <p><strong>Location:</strong> {site['locationDesc']}</p>
                        <p><strong>Direction:</strong> {site['roadDir']}</p>
                        <hr>
                        <h5>Traffic Data (2020)</h5>
                        <p><strong>Total Vehicles (Class 3+):</strong> {item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']:,}</p>
                        <p><strong>Class 3:</strong> {item['Class3']:,}</p>
                        <p><strong>Class 4:</strong> {item['Class4']:,}</p>
                        <p><strong>Class 5:</strong> {item['Class5']:,}</p>
                        <p><strong>Class 6:</strong> {item['Class6']:,}</p>
                        <p><strong>Class 7:</strong> {item['Class7']:,}</p>
                        <p><strong>Class 8:</strong> {item['Class8']:,}</p>
                        <p><strong>Class 9:</strong> {item['Class9']:,}</p>
                        <p><strong>Class 10:</strong> {item['Class10']:,}</p>
                    </div>
                    """
                
                # Determine color and tooltip based on class filter
                if selected_classes:
                    # Calculate combined count for selected classes
                    combined_count = sum(item[key] for key in class_keys)
                    
                    # Color code based on filtered class counts using filtered thresholds
                    if combined_count > top_third_threshold:
                        color = 'red'  # Most vehicles (top third)
                    elif combined_count > middle_third_threshold:
                        color = 'orange'  # Middle vehicles (middle third)
                    else:
                        color = 'green'  # Least vehicles (bottom third)
                    
                    tooltip_text = f"{site['roadname']} - Combined ({', '.join(selected_classes)}): {combined_count:,}"
                else:
                    # Calculate total truck count for color coding
                    total_traffic = item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']
                    
                    # Color code based on total truck volume thirds
                    if total_traffic > top_third_threshold:
                        color = 'red'  # Most vehicles (top third)
                    elif total_traffic > middle_third_threshold:
                        color = 'orange'  # Middle vehicles (middle third)
                    else:
                        color = 'green'  # Least vehicles (bottom third)
                    
                    tooltip_text = f"{site['roadname']} - {total_traffic:,} vehicles (Class 3+)"
                
                # Add marker
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=tooltip_text,
                    icon=folium.Icon(color=color, icon='truck', prefix='fa')
                ).add_to(m)    
    # Add hydrogen refueling stations if available
    if show_hydrogen and hydrogen_stations is not None and not hydrogen_stations.empty:
        for _, station in hydrogen_stations.iterrows():
            lat = station['Lat']
            lon = station['Long']
            name = station['name']
            city_state = station['city_state']
            operator = station['operator']
            start_year = station['Start']
            
            # Create popup content for hydrogen station
            popup_content = f"""
            <div style="width: 300px;">
                <h4>Hydrogen Station: {name}</h4>
                <p><strong>Location:</strong> {city_state}</p>
                <p><strong>Operator:</strong> {operator}</p>
                <p><strong>Started:</strong> {start_year}</p>
                <p><strong>Storage Capacity:</strong> {station.get('storage_capacity_kg', 'N/A')} kg</p>
                <p><strong>Daily Capacity:</strong> {station.get('dispensing_daily_capacity', 'N/A')} vehicles</p>
                <p><strong>Usage:</strong> {station.get('usage_case', 'N/A')[:100]}...</p>
            </div>
            """
            
            # Add hydrogen station marker with refuel icon
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"Hydrogen Station: {name} - {city_state}",
                icon=folium.Icon(color='blue', icon='gas-pump', prefix='fa')
            ).add_to(m)
    
    # Add railway routes if available
    if show_railway and railway_data:
        folium.GeoJson(
            railway_data,
            style_function=lambda feature: {
                'color': 'red',
                'weight': 3,
                'opacity': 0.7
            },
        ).add_to(m)
    
    # Add key freight road routes if available
    if show_roads and road_data:
        folium.GeoJson(
            road_data,
            style_function=lambda feature: {
                'color': 'blue',
                'weight': 4,
                'opacity': 0.8
            },
        ).add_to(m)
    
    # Add secondary routes if available
    if show_secondary and secondary_data:
        folium.GeoJson(
            secondary_data,
            style_function=lambda feature: {
                'color': 'green',
                'weight': 2,
                'opacity': 0.6
            },
        ).add_to(m)

    
    return m

# The create_traffic_charts function has been removed.

def main():
    st.set_page_config(
        page_title="WA Traffic Data Dashboard",
        layout="wide"
    )
    
    st.title("Truck Dashboard")
    
    # Initialize Google Maps API
    gmaps = initialize_google_maps()
    if gmaps is None:
        st.warning("Google Maps API not available. Some features may be limited.")
    
    # Load data
    data = load_data()
    hydrogen_stations = load_hydrogen_stations()
    railway_data = load_railway_data()
    road_data = load_road_data()
    secondary_data = load_secondary_route_data()
    
    if not data:
        st.stop()
    
    # Data is not filtered
    filtered_data = data
    
    # Sidebar filters
    st.sidebar.header("Map Filters")
    show_traffic = st.sidebar.checkbox("Show Traffic Sites", value=True, help="Display traffic monitoring sites with color-coded markers")
    show_hydrogen = st.sidebar.checkbox("Show Hydrogen Stations", value=True, help="Display hydrogen refueling stations")
    show_railway = st.sidebar.checkbox("Show Railway Routes", value=False, help="Display key freight railway routes")
    show_roads = st.sidebar.checkbox("Show Key Freight Roads", value=False, help="Display key freight road routes")
    show_secondary = st.sidebar.checkbox("Show Secondary Routes", value=False, help="Display secondary road routes")

    
    
    # Truck class filtering and color coding
    st.sidebar.header("Truck Class Analysis")
    selected_classes = st.sidebar.multiselect(
        "Select Truck Classes to Analyze", 
        ["Class 3", "Class 4", "Class 5", 
         "Class 6", "Class 7", "Class 8", "Class 9", "Class 10"],
        default=[],
        help="Select one or more truck classes to color-code markers based on combined counts"
    )
    
    # Determine if filtering is active
    class_filter = "None" if not selected_classes else "Multiple"
    

    


    
    # Main content

    

    st.header("Interactive Map")
    
    # Add dynamic legend
    legend_items = []
    if show_traffic:
        if selected_classes:
            legend_items.append(f"**Traffic Sites**: Color-coded by combined {', '.join(selected_classes)} count (Red=Most trucks, Orange=Middle 3rd percentile of trucks, green=Least trucks)")
        else:
            legend_items.append("**Traffic Sites**: Color-coded by Class 3+ volume (Red=Most trucks, Orange=Middle 3rd percentile of trucks, green=Least trucks)")
    if show_hydrogen:
        legend_items.append("**Hydrogen Stations**: Blue gas pump icons for refueling stations")
    if show_railway:
        legend_items.append("**Railway Routes**: Red lines showing key freight railway routes")
    if show_roads:
        legend_items.append("**Key Freight Roads**: Blue lines showing major freight road routes")
    if show_secondary:
        legend_items.append("**Secondary Routes**: Green lines showing secondary road routes")

    
    if legend_items:
        legend_text = "**Map Legend:**\n" + "\n".join([f"- {item}" for item in legend_items])
        st.markdown(legend_text)
    
    # Create and display map
    if filtered_data:
        traffic_map = create_traffic_map(
            filtered_data, 
            hydrogen_stations, 
            railway_data, 
            road_data, 
            secondary_data, 
            show_traffic, 
            show_hydrogen, 
            show_railway, 
            show_roads, 
            show_secondary, 
            selected_classes
        )
        if traffic_map:
            map_data = st_folium(traffic_map, width=700, height=500)

            # Section to display when a marker is clicked
            if map_data and map_data.get('last_object_clicked_popup'):
                st.header("📈 Truck Class Distribution")
                
                
    else:
        st.warning("No sites match the current filters")

    
    # Fuel estimation section
    st.header("Fuel Estimation")
    
    # Create columns for fuel estimation inputs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Truck class selection
        fuel_consumption = {
            "Class 4 (Medium Rigid)": 12.45859,   # Medium trucks
            "Class 5 (Heavy Rigid)": 23.22869,   # Medium trucks
            "Class 7 (Arctic 4 Axle)": 27.24712,   # Heavy trucks
            "Class 8 (Artic 5 Axle)": 30.44964,   # Heavy trucks
            "Class 9 (Artic 6 Axle)": 38.14329,   # Heavy trucks
            "Class 9 (Rigid + 5 Axle Dog)": 38.14329,
            "Class 10 (B-Double)": 41.48179   # Heavy trucks
        }
        
        truck_class = st.selectbox(
            "Select Truck Class",
            list(fuel_consumption.keys()),
            help="Select the truck class for fuel estimation"
        )
    
    with col2:
        # Traffic site selection
        site_options = []
        for item in data:
            site = item['site']
            site_options.append(f"{site['roadname']} - {site['locationDesc']}")
        
        selected_site_index = st.selectbox(
            "Select Starting Point",
            range(len(site_options)),
            format_func=lambda x: site_options[x],
            help="Select a traffic monitoring site as your starting point"
        )
    
    with col3:
        # Destination input
        destination = st.text_input(
            "Enter Destination",
            placeholder="e.g., Perth, Western Australia",
            help="Enter your destination address"
        )
    
    # Calculate button and results
    if st.button("Calculate Distance", type="primary"):
        if destination and gmaps:
            selected_site = data[selected_site_index]
            site_lat = selected_site['site']['location']['lat']
            site_lon = selected_site['site']['location']['long']
            
            # Calculate distance
            distance_result = calculate_distance(gmaps, site_lat, site_lon, destination)
            
            if distance_result:
                st.success("Distance calculated successfully!")
                
                # Display results in columns
                result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                
                with result_col1:
                    st.metric("Distance", distance_result['distance'])
                
                with result_col2:
                    st.metric("Driving Time", distance_result['duration'])
                
                with result_col3:
                    # Convert distance from meters to kilometers for fuel calculation
                    distance_km = distance_result['distance_value'] / 1000
                    
                    # Basic fuel consumption estimates by truck class (L/100km)
                    fuel_consumption = {
                        "Class 4 (Medium Rigid)": 12.45859,   # Medium trucks
                        "Class 5 (Heavy Rigid)": 23.22869,   # Medium trucks
                        "Class 7 (Arctic 4 Axle)": 27.24712,   # Heavy trucks
                        "Class 8 (Artic 5 Axle)": 30.44964,   # Heavy trucks
                        "Class 9 (Artic 6 Axle)": 38.14329,   # Heavy trucks
                        "Class 9 (Rigid + 5 Axle Dog)": 38.14329,
                        "Class 10 (B-Double)": 41.48179   # Heavy trucks
                    }
                    
                    fuel_needed = (distance_km / 100) * fuel_consumption[truck_class]
                    st.metric("Estimated Fuel", f"{fuel_needed:.1f} L")
                
                with result_col4:
                    hydrogen_use = (fuel_needed * 45)/120
                    st.metric("Hydrogen Usage", f"{hydrogen_use:.1f} Kg")
                
                # Additional information
                st.info(f"**Route Details:**\n- **From:** {site_options[selected_site_index]}\n- **To:** {destination}\n- **Truck Class:** {truck_class}")
                
            else:
                st.error("Failed to calculate distance. Please check your destination address.")
        elif not destination:
            st.warning("Please enter a destination address.")
        elif not gmaps:
            st.error("Google Maps API is not available. Please check your API key.")
    
    st.markdown("---")
    
    # The traffic analysis.
    st.header("📈 Total Truck Class Distribution")
    
    total_data = {'Class 3': [], 'Class 4': [], 'Class 5': [], 'Class 6': [], 'Class 7': [], 'Class 8': [], 'Class 9': [], 'Class 10': []}
    for item in data:
        total_data['Class 3'].append(item['Class3'])
        total_data['Class 4'].append(item['Class4'])
        total_data['Class 5'].append(item['Class5'])
        total_data['Class 6'].append(item['Class6'])
        total_data['Class 7'].append(item['Class7'])
        total_data['Class 8'].append(item['Class8'])
        total_data['Class 9'].append(item['Class9'])
        total_data['Class 10'].append(item['Class10'])

    # Calculate the total count for each truck class
    class_totals = {class_name: sum(counts) for class_name, counts in total_data.items()}

    # Create a DataFrame for the bar chart
    df_class_totals = pd.DataFrame(list(class_totals.items()), columns=['Truck Class', 'Total Count'])

    # Create the bar chart using plotly
    fig = px.bar(df_class_totals, x='Truck Class', y='Total Count', title='Amount of Trucks By Class')
    st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.header("📋 Detailed Data")
    
    if filtered_data:
        # Create a simplified DataFrame for display
        display_data = []
        for item in filtered_data:
            site = item['site']
            display_data.append({
                'Site Number': site['siteNumber'],
                'Road Name': site['roadname'],
                'Location': site['locationDesc'],
                'Total Vehicles (Class 3+)': item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10'],
                'Medium Trucks (3-5)': item['Class3'] + item['Class4'] + item['Class5'],
                'Heavy Trucks (6+)': item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10'],
                'Heavy Truck %': round((item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']) / (item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']) * 100, 2) if (item['Class3'] + item['Class4'] + item['Class5'] + item['Class6'] + item['Class7'] + item['Class8'] + item['Class9'] + item['Class10']) > 0 else 0
            })
        
        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, use_container_width=True)
        
        # Download button
        csv = df_display.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name="traffic_data.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
