from flask import Flask, jsonify, request
import pandas as pd
import numpy as np
from scipy import stats
import mongomock
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Global variables to store data and database connection
client = mongomock.MongoClient()
db = client.water_quality_data
collection = db.asv_1
cleaned_df = None
original_count = 0
removed_count = 0

def load_and_clean_data():
    """Load CSV data, clean using z-score, and store in database"""
    global cleaned_df, original_count, removed_count
    
    # Load raw data - supports any CSV filename via DATA_FILE env var
    import os
    data_file = os.getenv('DATA_FILE', 'raw.csv')  # default to raw.csv if not set
    print(f"Loading raw data from ../data/{data_file}...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(current_dir), "data", data_file)
    df = pd.read_csv(data_path)
    original_count = len(df)
    print(f"Original data loaded: {original_count} rows")
    
    # Normalize column names and select required columns
    column_mapping = {
        'Latitude': 'latitude',
        'Longitude': 'longitude', 
        'Temperature (c)': 'temperature',
        'Salinity (ppt)': 'salinity',
        'ODO mg/L': 'odo',
        'Date m/d/y   ': 'date',
        'Time hh:mm:ss': 'time'
    }
    
    # Rename columns if they exist
    df = df.rename(columns=column_mapping)
    
    # Create timestamp from date and time if available
    if 'date' in df.columns and 'time' in df.columns:
        df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce')
    else:
        # Create artificial timestamps if not available
        df['timestamp'] = pd.date_range(start='2022-10-07', periods=len(df), freq='1S')
    
    # Select only required columns
    required_columns = ['timestamp', 'latitude', 'longitude', 'temperature', 'salinity', 'odo']
    available_columns = [col for col in required_columns if col in df.columns]
    df = df[available_columns]
    
    # Remove rows with missing values in numeric columns
    numeric_columns = ['temperature', 'salinity', 'odo']
    numeric_available = [col for col in numeric_columns if col in df.columns]
    df = df.dropna(subset=numeric_available)
    
    print(f"After removing missing values: {len(df)} rows")
    
    # Clean using z-score method
    print("Applying z-score cleaning...")
    z_scores = np.abs(stats.zscore(df[numeric_available], nan_policy='omit'))
    mask = (z_scores < 3.0).all(axis=1)
    cleaned_df = df[mask].copy()
    
    removed_count = original_count - len(cleaned_df)
    
    print(f"Data cleaning complete:")
    print(f"  Original rows: {original_count}")
    print(f"  Rows removed as outliers: {removed_count}")
    print(f"  Rows remaining: {len(cleaned_df)}")
    
    # Insert cleaned data into database
    print("Storing cleaned data in database...")
    collection.drop()  # Clear existing data
    
    # Convert DataFrame to dict for MongoDB insertion
    records = cleaned_df.to_dict('records')
    for record in records:
        # Convert timestamp to string for JSON serialization
        if pd.notna(record.get('timestamp')):
            record['timestamp'] = record['timestamp'].isoformat()
    
    if records:
        collection.insert_many(records)
        print(f"Inserted {len(records)} records into database")
    
    return cleaned_df

@app.route("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route("/api/observations")
def observations():
    """Get observations with optional filters"""
    try:
        # Get query parameters
        start = request.args.get('start')
        end = request.args.get('end')
        min_temp = request.args.get('min_temp', type=float)
        max_temp = request.args.get('max_temp', type=float)
        min_sal = request.args.get('min_sal', type=float)
        max_sal = request.args.get('max_sal', type=float)
        min_odo = request.args.get('min_odo', type=float)
        max_odo = request.args.get('max_odo', type=float)
        limit = min(request.args.get('limit', default=100, type=int), 1000)
        skip = request.args.get('skip', default=0, type=int)
        
        # Build MongoDB query
        query = {}
        
        # Date range filter
        if start or end:
            date_filter = {}
            if start:
                date_filter['$gte'] = start
            if end:
                date_filter['$lte'] = end
            query['timestamp'] = date_filter
        
        # Temperature filter
        if min_temp is not None or max_temp is not None:
            temp_filter = {}
            if min_temp is not None:
                temp_filter['$gte'] = min_temp
            if max_temp is not None:
                temp_filter['$lte'] = max_temp
            query['temperature'] = temp_filter
        
        # Salinity filter
        if min_sal is not None or max_sal is not None:
            sal_filter = {}
            if min_sal is not None:
                sal_filter['$gte'] = min_sal
            if max_sal is not None:
                sal_filter['$lte'] = max_sal
            query['salinity'] = sal_filter
        
        # ODO filter
        if min_odo is not None or max_odo is not None:
            odo_filter = {}
            if min_odo is not None:
                odo_filter['$gte'] = min_odo
            if max_odo is not None:
                odo_filter['$lte'] = max_odo
            query['odo'] = odo_filter
        
        # Execute query
        cursor = collection.find(query, {'_id': 0}).skip(skip).limit(limit)
        items = list(cursor)
        
        # Get total count
        total_count = collection.count_documents(query)
        
        return jsonify({
            "count": total_count,
            "returned": len(items),
            "items": items
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def stats_endpoint():
    """Get summary statistics for numeric fields"""
    try:
        if cleaned_df is None:
            return jsonify({"error": "Data not loaded"}), 500
        
        numeric_columns = ['temperature', 'salinity', 'odo']
        available_columns = [col for col in numeric_columns if col in cleaned_df.columns]
        
        if not available_columns:
            return jsonify({"error": "No numeric columns available"}), 500
        
        # Calculate statistics
        desc = cleaned_df[available_columns].describe(percentiles=[.25, .5, .75])
        
        # Convert to JSON-serializable format
        stats_dict = {}
        for col in available_columns:
            stats_dict[col] = {
                'count': int(desc.loc['count', col]),
                'mean': float(desc.loc['mean', col]),
                'std': float(desc.loc['std', col]),
                'min': float(desc.loc['min', col]),
                '25%': float(desc.loc['25%', col]),
                '50%': float(desc.loc['50%', col]),
                '75%': float(desc.loc['75%', col]),
                'max': float(desc.loc['max', col])
            }
        
        return jsonify(stats_dict)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/outliers")
def outliers():
    """Get outliers using specified method"""
    try:
        field = request.args.get('field', 'temperature')
        method = request.args.get('method', 'iqr')
        k = request.args.get('k', default=1.5, type=float)
        
        if cleaned_df is None:
            return jsonify({"error": "Data not loaded"}), 500
        
        if field not in cleaned_df.columns:
            return jsonify({"error": f"Field '{field}' not found"}), 400
        
        data = cleaned_df[field].dropna()
        outlier_indices = []
        
        if method == 'iqr':
            # IQR method
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - k * IQR
            upper_bound = Q3 + k * IQR
            outlier_mask = (data < lower_bound) | (data > upper_bound)
            outlier_indices = data[outlier_mask].index.tolist()
            
        elif method == 'zscore':
            # Z-score method
            z_scores = np.abs(stats.zscore(data))
            outlier_mask = z_scores > k
            outlier_indices = data[outlier_mask].index.tolist()
        
        else:
            return jsonify({"error": "Method must be 'iqr' or 'zscore'"}), 400
        
        # Get outlier records
        outliers_df = cleaned_df.iloc[outlier_indices]
        outliers_list = outliers_df.to_dict('records')
        
        # Convert timestamps to string
        for record in outliers_list:
            if 'timestamp' in record and pd.notna(record['timestamp']):
                record['timestamp'] = record['timestamp'].isoformat()
        
        return jsonify({
            "method": method,
            "field": field,
            "k": k,
            "outlier_count": len(outliers_list),
            "outliers": outliers_list
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/summary")
def summary():
    """Get data summary including cleaning results"""
    return jsonify({
        "original_rows": original_count,
        "rows_removed": removed_count,
        "rows_remaining": len(cleaned_df) if cleaned_df is not None else 0,
        "cleaning_method": "z-score with threshold 3.0"
    })

if __name__ == "__main__":
    print("Starting Flask API...")
    print("Loading and cleaning data...")
    load_and_clean_data()
    print("API ready!")
    app.run(debug=True, host='0.0.0.0', port=5000)
