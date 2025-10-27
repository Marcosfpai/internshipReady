import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np

# Configure page
st.set_page_config(
    page_title="Water Quality Dashboard",
    page_icon="🌊",
    layout="wide"
)

# Constants
API_BASE_URL = "http://127.0.0.1:5000/api"

def make_api_request(endpoint, params=None):
    """Make API request with error handling"""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def main():
    st.title("🌊 Water Quality Data Dashboard")
    st.markdown("Interactive dashboard for water quality observations")
    
    # Check API health
    health = make_api_request("health")
    if health and health.get("status") == "ok":
        st.success("✅ API Connection: Healthy")
    else:
        st.error("❌ API Connection: Failed")
        return
    
    # Sidebar controls
    st.sidebar.header("📊 Filter Controls")
    
    # Get stats to determine full data ranges
    stats_data = make_api_request("stats")
    if not stats_data:
        st.error("Failed to load data statistics")
        return
    
    # Get sample data for date range
    sample_data = make_api_request("observations", {"limit": 100})
    if not sample_data or not sample_data.get("items"):
        st.warning("No data available")
        return
    
    df_sample = pd.DataFrame(sample_data["items"])
    
    # Date range filter
    st.sidebar.subheader("📅 Date Range")
    if 'timestamp' in df_sample.columns:
        df_sample['timestamp'] = pd.to_datetime(df_sample['timestamp'])
        min_date = df_sample['timestamp'].min().date()
        max_date = df_sample['timestamp'].max().date()
        
        start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    else:
        start_date = end_date = None
    
    # Temperature filter - use stats for full range
    st.sidebar.subheader("🌡️ Temperature (°C)")
    if 'temperature' in stats_data:
        temp_min = float(stats_data['temperature']['min'])
        temp_max = float(stats_data['temperature']['max'])
        temp_range = st.sidebar.slider(
            "Temperature Range", 
            temp_min, temp_max, 
            (temp_min, temp_max),
            step=0.1
        )
    else:
        temp_range = None
    
    # Salinity filter - use stats for full range
    st.sidebar.subheader("🧂 Salinity (ppt)")
    if 'salinity' in stats_data:
        sal_min = float(stats_data['salinity']['min'])
        sal_max = float(stats_data['salinity']['max'])
        sal_range = st.sidebar.slider(
            "Salinity Range", 
            sal_min, sal_max, 
            (sal_min, sal_max),
            step=0.1
        )
    else:
        sal_range = None
        st.sidebar.info("Salinity data not available")
    
    # ODO filter - use stats for full range
    st.sidebar.subheader("💨 ODO (mg/L)")
    if 'odo' in stats_data:
        odo_min = float(stats_data['odo']['min'])
        odo_max = float(stats_data['odo']['max'])
        odo_range = st.sidebar.slider(
            "ODO Range", 
            odo_min, odo_max, 
            (odo_min, odo_max),
            step=0.1
        )
    else:
        odo_range = None
    
    # Pagination controls
    st.sidebar.subheader("📄 Pagination")
    limit = st.sidebar.selectbox("Records per page", [50, 100, 200, 500, 1000], index=1)
    skip = st.sidebar.number_input("Skip records", min_value=0, value=0, step=limit)
    
    # Build API parameters
    params = {"limit": limit, "skip": skip}
    
    if start_date and end_date:
        # Convert dates to datetime strings for proper API filtering
        params["start"] = f"{start_date}T00:00:00"
        params["end"] = f"{end_date}T23:59:59"
    
    if temp_range:
        params["min_temp"] = temp_range[0]
        params["max_temp"] = temp_range[1]
    
    if sal_range:
        params["min_sal"] = sal_range[0]
        params["max_sal"] = sal_range[1]
    
    if odo_range:
        params["min_odo"] = odo_range[0]
        params["max_odo"] = odo_range[1]
    
    # Debug: Show parameters being sent
    st.sidebar.write("🔍 Debug - API Parameters:")
    st.sidebar.json(params)
    
    # Get filtered data
    data = make_api_request("observations", params)
    
    if not data:
        st.error("Failed to load data")
        return
    
    st.info(f"📊 Total records matching filters: {data.get('count', 0)} | Showing: {data.get('returned', 0)}")
    
    if not data.get("items"):
        st.warning("No data matches your filters")
        return
    
    df = pd.DataFrame(data["items"])
    
    # Convert timestamp column if it exists
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Table", "📈 Visualizations", "📊 Statistics", "⚠️ Outliers"])
    
    with tab1:
        st.subheader("📋 Filtered Observations")
        st.dataframe(df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download filtered data as CSV",
            data=csv,
            file_name=f"water_quality_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.subheader("📈 Interactive Visualizations")
        
        if len(df) == 0:
            st.warning("No data to visualize")
        else:
            # Temperature over time
            if 'timestamp' in df.columns and 'temperature' in df.columns:
                st.subheader("🌡️ Temperature Over Time")
                fig_temp = px.line(
                    df, x='timestamp', y='temperature',
                    title="Temperature Trends",
                    labels={'temperature': 'Temperature (°C)', 'timestamp': 'Time'}
                )
                fig_temp.update_traces(line=dict(width=2))
                fig_temp.update_layout(
                    height=450,
                    template='plotly_white',
                    margin=dict(l=10, r=10, t=60, b=10)
                )
                st.plotly_chart(fig_temp, use_container_width=True)
                st.divider()

            # Salinity distribution
            if 'salinity' in df.columns and df['salinity'].notna().any():
                st.subheader("🧂 Salinity Distribution")
                fig_sal = px.histogram(
                    df, x='salinity', nbins=40,
                    title="Salinity Distribution",
                    labels={'salinity': 'Salinity (ppt)', 'count': 'Frequency'}
                )
                fig_sal.update_layout(
                    height=450,
                    template='plotly_white',
                    bargap=0.05,
                    margin=dict(l=10, r=10, t=60, b=10)
                )
                st.plotly_chart(fig_sal, use_container_width=True)
                st.divider()

            # Scatter plot: Temperature vs Salinity colored by ODO
            if all(col in df.columns for col in ['temperature', 'odo']):
                st.subheader("🌡️ Temperature vs ODO Relationship")
                if 'salinity' in df.columns and df['salinity'].notna().any():
                    fig_scatter = px.scatter(
                        df, x='temperature', y='salinity', color='odo',
                        title="Temperature vs Salinity (colored by ODO)",
                        labels={'temperature': 'Temperature (°C)', 'salinity': 'Salinity (ppt)', 'odo': 'ODO (mg/L)'}
                    )
                else:
                    fig_scatter = px.scatter(
                        df, x='temperature', y='odo',
                        title="Temperature vs ODO",
                        labels={'temperature': 'Temperature (°C)', 'odo': 'ODO (mg/L)'}
                    )
                fig_scatter.update_traces(marker=dict(size=8, opacity=0.85))
                fig_scatter.update_layout(
                    height=450,
                    template='plotly_white',
                    margin=dict(l=10, r=10, t=60, b=10)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                st.divider()

            # Geographic map with path and heat map
            if all(col in df.columns for col in ['latitude', 'longitude']):
                st.subheader("🗺️ Geographic Distribution & Path")

                df_sorted = df.sort_values('timestamp') if 'timestamp' in df.columns else df.copy()
                df_sorted = df_sorted.reset_index(drop=True)

                map_fields = [col for col in ['temperature', 'salinity', 'odo'] if col in df_sorted.columns]
                map_color_field = None
                if map_fields:
                    map_color_field = st.selectbox(
                        "Color measurements by:",
                        map_fields,
                        index=0,
                        key="map_color_field"
                    )

                def format_label(field_name: str) -> str:
                    if field_name == 'temperature':
                        return 'Temperature (°C)'
                    if field_name == 'salinity':
                        return 'Salinity (ppt)'
                    if field_name == 'odo':
                        return 'ODO (mg/L)'
                    return field_name.title()

                hover_fields = []
                hover_template = "<b>Water Quality Measurement</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<br>"
                for field in ['temperature', 'salinity', 'odo']:
                    if field in df_sorted.columns and field not in hover_fields:
                        idx = len(hover_fields)
                        hover_fields.append(field)
                        label = format_label(field)
                        hover_template += f"{label}: %{{customdata[{idx}]:.2f}}<br>"
                if 'timestamp' in df_sorted.columns:
                    hover_fields.append('timestamp')
                    hover_template += "Time: %{customdata[-1]}<br>"
                hover_template += "<extra></extra>"

                custom_data = None
                if hover_fields:
                    custom_df = df_sorted[hover_fields].copy()
                    if 'timestamp' in hover_fields:
                        custom_df['timestamp'] = custom_df['timestamp'].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else ""
                        )
                    custom_data = custom_df.to_numpy()

                fig_map = go.Figure()
                if 'timestamp' in df_sorted.columns and len(df_sorted) > 1:
                    fig_map.add_trace(go.Scattermapbox(
                        lat=df_sorted['latitude'],
                        lon=df_sorted['longitude'],
                        mode='lines',
                        line=dict(width=3, color='#1f77b4'),
                        name='Measurement Path',
                        hoverinfo='skip'
                    ))

                marker_config = dict(size=10, opacity=0.85)
                color_title = "Measurements"
                if map_color_field:
                    color_values = pd.to_numeric(df_sorted[map_color_field], errors='coerce')
                    if color_values.isna().all():
                        color_values = pd.Series(np.zeros(len(df_sorted)), index=df_sorted.index)
                    else:
                        color_values = color_values.fillna(color_values.mean())
                    color_title = format_label(map_color_field)
                    marker_config.update({
                        "color": color_values,
                        "colorscale": "Turbo",
                        "cmin": float(color_values.min()),
                        "cmax": float(color_values.max()),
                        "colorbar": dict(title=color_title, thickness=14, len=0.6),
                        "showscale": True
                    })
                else:
                    marker_config.update({"color": '#d62728'})

                scatter_kwargs = {}
                if custom_data is not None:
                    scatter_kwargs["customdata"] = custom_data
                    scatter_kwargs["hovertemplate"] = hover_template
                else:
                    scatter_kwargs["hovertemplate"] = "<b>Water Quality Measurement</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<extra></extra>"

                fig_map.add_trace(go.Scattermapbox(
                    lat=df_sorted['latitude'],
                    lon=df_sorted['longitude'],
                    mode='markers',
                    marker=marker_config,
                    name='Measurements',
                    showlegend=bool(map_color_field),
                    **scatter_kwargs
                ))

                lat_range = df_sorted['latitude'].max() - df_sorted['latitude'].min()
                lon_range = df_sorted['longitude'].max() - df_sorted['longitude'].min()
                coverage = max(lat_range, lon_range)
                zoom_level = 12
                if coverage < 0.005:
                    zoom_level = 15
                elif coverage < 0.015:
                    zoom_level = 14
                elif coverage < 0.03:
                    zoom_level = 13

                fig_map.update_layout(
                    height=540,
                    mapbox=dict(
                        style="carto-positron",
                        zoom=zoom_level,
                        center=dict(
                            lat=float(df_sorted['latitude'].mean()),
                            lon=float(df_sorted['longitude'].mean())
                        )
                    ),
                    margin=dict(l=0, r=0, t=60, b=0),
                    legend=dict(orientation='h', yanchor='bottom', y=0.01, xanchor='right', x=1)
                )

                st.plotly_chart(fig_map, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Points", len(df_sorted))
                with col2:
                    if len(df_sorted) > 1:
                        from math import radians, cos, sin, asin, sqrt

                        def haversine(lon1, lat1, lon2, lat2):
                            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                            dlon = lon2 - lon1
                            dlat = lat2 - lat1
                            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
                            c = 2 * asin(sqrt(a))
                            return 6371 * c

                        total_distance = 0.0
                        for i in range(1, len(df_sorted)):
                            total_distance += haversine(
                                df_sorted.iloc[i - 1]['longitude'], df_sorted.iloc[i - 1]['latitude'],
                                df_sorted.iloc[i]['longitude'], df_sorted.iloc[i]['latitude']
                            )
                        st.metric("Path Distance", f"{total_distance:.2f} km")
                    else:
                        st.metric("Path Distance", "N/A")
                with col3:
                    st.metric("Coverage Area", f"{lat_range:.4f}° × {lon_range:.4f}°")
                st.caption("Tip: Use the colour selector above the map to highlight specific measurements along the path.")
    
    with tab3:
        st.subheader("📊 Statistical Summary")
        
        # Get statistics from API
        stats_data = make_api_request("stats")
        
        if stats_data:
            col1, col2, col3 = st.columns(3)
            
            for i, (field, stats) in enumerate(stats_data.items()):
                with [col1, col2, col3][i % 3]:
                    st.metric(
                        label=f"{field.title()} Mean",
                        value=f"{stats['mean']:.2f}",
                        delta=f"σ: {stats['std']:.2f}"
                    )
                    
                    with st.expander(f"{field.title()} Details"):
                        st.json(stats)
        
        # Summary table
        if not df.empty:
            st.subheader("📋 Current Filter Summary")
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                summary_df = df[numeric_columns].describe()
                st.dataframe(summary_df, use_container_width=True)
    
    with tab4:
        st.subheader("⚠️ Outlier Detection")
        
        # Outlier detection controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            outlier_field = st.selectbox(
                "Field to analyze",
                ['temperature', 'salinity', 'odo'],
                key="outlier_field"
            )
        
        with col2:
            outlier_method = st.selectbox(
                "Detection method",
                ['iqr', 'zscore'],
                key="outlier_method"
            )
        
        with col3:
            if outlier_method == 'iqr':
                k_value = st.slider("IQR multiplier (k)", 1.0, 3.0, 1.5, 0.1)
            else:
                k_value = st.slider("Z-score threshold", 1.0, 4.0, 3.0, 0.1)
        
        # Get outliers from API
        outlier_params = {
            "field": outlier_field,
            "method": outlier_method,
            "k": k_value
        }
        
        outliers_data = make_api_request("outliers", outlier_params)
        
        if outliers_data:
            st.info(f"🔍 Found {outliers_data.get('outlier_count', 0)} outliers using {outlier_method.upper()} method")
            
            if outliers_data.get('outliers'):
                outliers_df = pd.DataFrame(outliers_data['outliers'])
                if 'timestamp' in outliers_df.columns:
                    outliers_df['timestamp'] = pd.to_datetime(outliers_df['timestamp'])
                
                st.dataframe(outliers_df, use_container_width=True)
                
                # Visualize outliers
                if len(outliers_df) > 0 and 'timestamp' in outliers_df.columns:
                    fig_outliers = px.scatter(
                        outliers_df, x='timestamp', y=outlier_field,
                        title=f"Outliers in {outlier_field.title()}",
                        color_discrete_sequence=['red']
                    )
                    fig_outliers.update_layout(height=400)
                    st.plotly_chart(fig_outliers, use_container_width=True)
            else:
                st.success("✅ No outliers detected with current parameters")

if __name__ == "__main__":
    main()
