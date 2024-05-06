import streamlit as st
import pandas as pd
import os
from dateutil import tz
import datetime
import plotly.express as px
import numpy as np
import pyxet


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

    spotify_data = None
    if "GCR" in os.environ:
        pyxet.login(
            os.environ["XET_UN"], os.environ["XET_PAT"], os.environ["XET_EMAIL"]
        )
        spotify_data = pd.read_csv("xet://jsulz/spotify-data/spotify_data/raw.csv")
    else:
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

    spotify_data["device"] = spotify_data["platform"].apply(
        lambda x: "Mobile" if "Android" in x else "Desktop/Laptop"
    )

    return spotify_data


@st.cache_data
def reason_table(df, column):
    # group the data frame by reason_start column and include counts of that colum
    reason_counts = df.groupby(column).size().reset_index(name="count")

    return reason_counts


@st.cache_data
def played_time(df, granularity):
    if granularity == "year":
        # group the data by the year column and then sum the ms_played column
        played_time = df.groupby("year")["ms_played"].sum().reset_index()
        played_time["date"] = played_time["year"].astype(str)

    if granularity == "month":
        # group the data by the year and month column and then sum the ms_played column
        played_time = df.groupby(["year", "month"])["ms_played"].sum().reset_index()
        played_time["date"] = (
            played_time["year"].astype(str) + "-" + played_time["month"].astype(str)
        )

    if granularity == "day":
        # group the data by the year, month, and day column and then sum the ms_played column
        played_time = (
            df.groupby(["year", "month", "day"])["ms_played"].sum().reset_index()
        )
        played_time["date"] = (
            played_time["year"].astype(str)
            + "-"
            + played_time["month"].astype(str)
            + "-"
            + played_time["day"].astype(str)
        )

    return played_time


@st.cache_data
def filter_by_year(df, start, end):
    pst = tz.gettz("America/Los_Angeles")
    startdate = datetime.datetime(year=start, month=1, day=1, tzinfo=pst)
    enddate = datetime.datetime(year=end, month=12, day=31, tzinfo=pst)
    if start == end:
        enddate = datetime.datetime(year=end + 1, month=12, day=30, tzinfo=pst)

    df = df[df["ts"] >= startdate]
    df = df[df["ts"] <= enddate]
    return df


def maxes(df):
    # Group by artist, sum up the ms played, get the artist with the maximum ms played
    artist_max = (
        df.groupby("master_metadata_album_artist_name")["ms_played"].sum().reset_index()
    )
    artist_max = artist_max.sort_values(by="ms_played", ascending=False)
    artist_max = ms_to_time(artist_max)

    album_max = (
        df.groupby("master_metadata_album_album_name")["ms_played"].sum().reset_index()
    )
    album_max = album_max.sort_values(by="ms_played", ascending=False)
    album_max = ms_to_time(album_max)

    track_max = (
        df.groupby("master_metadata_track_name")["ms_played"].sum().reset_index()
    )
    track_max = track_max.sort_values(by="ms_played", ascending=False)
    track_max = ms_to_time(track_max)

    return artist_max.iloc[:5], album_max.iloc[:5], track_max.iloc[:5]


def ms_to_time(df):
    # take in ms and convert it to an hour:min:sec format
    df["time_played"] = (
        df["ms_played"].round().apply(pd.to_timedelta, unit="ms").astype(str)
    )
    return df


def convert_delta_to_readable(time_string):
    # take in a string in the format of N days HH:MM:SS and convert it
    # to N days, HH hours, MM minutes, SS seconds
    days, time = time_string.split(" days ")
    hours, minutes, seconds = time.split(":")
    return f"{days} days, {hours} hours, {minutes}, minutes, {seconds}, seconds"


def artists_table(df):
    df_track_counts = (
        df.groupby("master_metadata_album_artist_name")["master_metadata_track_name"]
        .count()
        .reset_index()
    )
    df_track_counts.rename(
        columns={"master_metadata_track_name": "played_tracks_count"}, inplace=True
    )

    df_album_counts = (
        df.groupby("master_metadata_album_artist_name")[
            "master_metadata_album_album_name"
        ]
        .nunique()
        .reset_index()
    )
    df_album_counts.rename(
        columns={"master_metadata_album_album_name": "played_albums_count"},
        inplace=True,
    )

    df_time = (
        df.groupby("master_metadata_album_artist_name")["ms_played"].sum().reset_index()
    )

    df_album_counts.index = df_track_counts.index
    df_time.index = df_track_counts.index
    df_album_counts.drop(columns="master_metadata_album_artist_name", inplace=True)
    df_time.drop(columns="master_metadata_album_artist_name", inplace=True)
    final = pd.concat([df_track_counts, df_album_counts, df_time], axis=1)

    return final


st.set_page_config(layout="wide")
st.title("Spotify Data")

spotify_data = load_data()

years = spotify_data["year"].unique()
start_year = st.sidebar.select_slider(
    "Start Year", options=(years[:-1]), value=years[0]
)

if start_year < years[-1]:
    end_years = [year for year in years if year >= start_year]
    end_year = st.sidebar.select_slider(
        "End Year", options=(end_years), value=end_years[-1]
    )
else:
    end_year = start_year

# filter spotify data by start year and end year
spotify_data = filter_by_year(spotify_data, start_year, end_year)


# total time listened, total number of tracks, total number of artists, total number of albums, total plays
total_tracks = spotify_data["master_metadata_track_name"].nunique()
total_artists = spotify_data["master_metadata_album_artist_name"].nunique()
total_albums = spotify_data["master_metadata_album_album_name"].nunique()
total_ms = spotify_data["ms_played"].sum()
seconds = total_ms // 1000
minutes, seconds = divmod(seconds, 60)
hours, minutes = divmod(minutes, 60)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tracks", total_tracks)
col2.metric("Total Artists", total_artists)
col3.metric("Total Albums", total_albums)
col4.metric("Total Time", f"{hours}:{minutes}:{seconds}")

granularity = st.selectbox("Select granularity", ["year", "month", "day"], index=1)

st.subheader(f"Total played time (in ms) by {granularity}")
st.line_chart(
    played_time(spotify_data, granularity), x="date", y="ms_played", color="#1DB045"
)

artist_max, album_max, track_max = maxes(spotify_data)

st.subheader("Top Listens")
st.metric(
    f"Artist: {artist_max.iloc[0]['master_metadata_album_artist_name']}",
    f"{convert_delta_to_readable(artist_max.iloc[0]['time_played'][:-7])}",
)
st.metric(
    f"Album: {album_max.iloc[0]['master_metadata_album_album_name']}",
    f"{convert_delta_to_readable(album_max.iloc[0]['time_played'][:-7])}",
)
st.metric(
    f"Track: {track_max.iloc[0]['master_metadata_track_name']}",
    f"{convert_delta_to_readable(track_max.iloc[0]['time_played'][:-7])}",
)


# total time listened, total number of tracks, total number of artists, total number of albums, total plays
# Build a chart that shows artists listened to with colums for artist, total time listened to, total # of tracks
artists = st.multiselect(
    "Artists", options=spotify_data["master_metadata_album_artist_name"].unique()
)

artist_df = artists_table(spotify_data)
if len(artists):
    st.dataframe(
        data=artist_df[
            artist_df["master_metadata_album_artist_name"].isin(artists)
        ].sort_values(by="played_tracks_count", ascending=False),
        hide_index=True,
    )
else:
    st.dataframe(
        data=artist_df.sort_values(by="played_tracks_count", ascending=False),
        hide_index=True,
    )


reason_start = reason_table(spotify_data, "reason_start")
reason_end = reason_table(spotify_data, "reason_end")

st.bar_chart(reason_start, x="reason_start", y="count", color="#1DB045")
st.bar_chart(reason_end, x="reason_end", y="count", color="#1DB045")

spotify_platform = (
    spotify_data.groupby(["device"])["device"].count().reset_index(name="count")
)
fig = px.pie(spotify_platform, names="device", values="count")
st.plotly_chart(fig)
