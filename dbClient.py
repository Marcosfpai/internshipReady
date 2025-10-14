from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv()

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_CLUSTER_URL = os.environ.get("MONGO_CLUSTER_URL")

# The following URL is obtained from MONGODB Atlas Cloud under Connect -> Drivers
#  Your appName might be different than Cluster0, check under drivers
url=(f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_CLUSTER_URL}/?"
     f"retryWrites=true&w=majority&appName=Cluster0")

client = MongoClient(url)
print(client)

db = client["water_quality_data"]
robot1 = db["asv_1"]

print(f"Using database: '{db}' and collection: '{robot1}'")

"""Example 1"""
obs1 = {"temperature (C)": 87.2, "salinity (ppt)": 60.2, "odo (mg/L)": 6.7}

result1=robot1.insert_one(obs1)
print("Inserted IDs in Example 1", result1.inserted_id)


"""Example 2"""
observations = [
    {"temperature (C)": 27.2, "salinity (ppt)": 35.1, "odo (mg/L)": 6.7},
    {"temperature (C)": 28.0, "salinity (ppt)": 34.8, "odo (mg/L)": 7.1},
    {"temperature (C)": 29.5, "salinity (ppt)": 36.2, "odo (mg/L)": 5.9},
    {"temperature (C)": 26.4, "salinity (ppt)": 33.9, "odo (mg/L)": 8.3},
    {"temperature (C)": 30.1, "salinity (ppt)": 37.0, "odo (mg/L)": 4.8},
]

result2 = robot1.insert_many(observations)
print("Inserted IDs in Example 2", result2.inserted_ids)

""" Example 3 """
doc = robot1.find_one()
print("First document:", doc)

""" Example 4 """
for obs in robot1.find({"temperature (C)": {"$gt": 28}}):
    print("Hot water:", obs)

""" Example 5 """
print("Total docs:", robot1.count_documents({}))
print("High salinity (>36 ppt):", robot1.count_documents({"salinity (ppt)": {"$gt": 36}}))

""" Example 6"""
print("Original doc:", robot1.find_one({"temperature (C)": 30.1}))
robot1.update_one(
    {"temperature (C)": 30.1},
    {"$set": {"odo (mg/L)": 5.2}}  # simulate corrected sensor reading
)
print("Updated doc:", robot1.find_one({"temperature (C)": 30.1}))