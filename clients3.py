import streamlit as st
import requests
import pandas as pd


base_url = "http://127.0.0.1:5050"

st.title("Cars Explorer")

tab1, tab2, tab3, tab4 = st.tabs([
    "Cars",
    "Makes",
    "Bodies",
    "Prices"
])

with tab1:
    if st.button("Load Cars"):
        response = requests.get(base_url + "/cars").json()
        st.dataframe(pd.DataFrame(response))

with tab2:
    if st.button("Load Makes"):
        response = requests.get(base_url + "/cars/makes").json()
        st.write(response)

with tab3:
    if st.button("Load Bodies"):
        response = requests.get(base_url + "/cars/bodies").json()
        st.write(response)

with tab4:
    if st.button("Load Prices"):
        response = requests.get(base_url + "/cars/prices").json()
        st.dataframe(pd.DataFrame(response))