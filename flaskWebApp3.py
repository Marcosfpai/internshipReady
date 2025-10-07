from flask import Flask, jsonify
import pandas as pd

app = Flask(__name__)

df = pd.read_csv("datasets/cars.csv")
# print(df.head())
# print(df.columns)

@app.route("/")
def index():
    return jsonify({
        "routes":{
            "/cars": "First 10 rows of all cars",
            "/cars/makes": "List of all unique car makes",
            "/cars/bodies": "List of all unique car bodies",
            "/cars/prices": "First 10 rows showing car name & price"
        }
    })

@app.route("/cars")
def cars():
    return jsonify(df.head(10).to_dict(orient="records"))

@app.route("/cars/makes")
def cars_makes():
    return jsonify(df["CarName"].str.split().str[0].unique().tolist())

@app.route("/cars/bodies")
def cars_bodies():
    return jsonify(df["carbody"].unique().tolist())

@app.route("/cars/prices")
def cars_prices():
    return jsonify(df[["CarName","price"]].head(10).to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True, port=5050)