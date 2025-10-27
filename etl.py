import pandas as pd
from scipy.stats import zscore
import mongomock  # use MongoDB if installed

# Load CSV
df = pd.read_csv("data/raw.csv")  # change filename if needed

# Clean with z-score
z = df[["temperature", "salinity", "odo"]].apply(zscore)
cleaned_df = df[(z.abs() <= 3).all(axis=1)]

# Report
print("Original rows:", len(df))
print("Removed outliers:", len(df) - len(cleaned_df))
print("Remaining rows:", len(cleaned_df))

# Insert into mongomock
client = mongomock.MongoClient()
db = client["water_quality_data"]
collection = db["asv_1"]
collection.insert_many(cleaned_df.to_dict("records"))
