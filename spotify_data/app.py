import streamlit as st
import pandas as pd
import os
from dateutil import tz


@st.cache_data
def load_data():
    # columns to drop
    drop_columns = [
        "username",
        "conn_country",
        "ip_addr_decrypted",
        "user_agent_decrypted",
        "Unnamed: 0",
        "episode_name",
        "episode_show_name",
        "spotify_episode_uri",
        "offline",
        "offline_timestamp",
        "incognito_mode",
    ]

    # Read in final.csv into a DataFrame
    spotify_data = pd.read_csv(os.path.join(os.path.dirname(__file__), "raw.csv"))

    # drop columns
    spotify_data = spotify_data.drop(columns=drop_columns)

    # convert ts column to datetime
    spotify_data["ts"] = pd.to_datetime(spotify_data["ts"], utc=True)

    # convert ts to pst timezone
    spotify_data["ts"] = spotify_data["ts"].dt.tz_convert(
        tz.gettz("America/Los_Angeles")
    )

    # Add year, month, day, and hour columns, using the ts column as the basis
    spotify_data["year"] = spotify_data["ts"].dt.year
    spotify_data["month"] = spotify_data["ts"].dt.month
    spotify_data["day"] = spotify_data["ts"].dt.day
    spotify_data["hour"] = spotify_data["ts"].dt.hour

    # convert the data frame to a st.data editor
    # format the year column to not have any commas
    st_spotify_data = st.data_editor(
        spotify_data,
        column_config={"year": st.column_config.NumberColumn(format="%.0f")},
        hide_index=True,
    )

    return st_spotify_data


@st.cache_data
def reason_table(df):
    # group the data frame by reason_start column and include counts of that colum
    reason_counts = df.groupby("reason_start").size().reset_index(name="count")
    # then transpose the data to make it easier to plot
    print(reason_counts)

    return reason_counts


st.title("Spotify Data")

spotify_data = load_data()

reasons = reason_table(spotify_data)

st.bar_chart(reasons, x="reason_start", y="count")
