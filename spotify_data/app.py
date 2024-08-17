import streamlit as st
import pandas as pd
import os
from dateutil import tz
import datetime
import plotly.express as px
import numpy as np


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

    # If we're in a cloud run environment, then we should use pyxet to load the data into the data frame
    spotify_data = None
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


def artist_played(df, artists):
    # group the data by the artist and year column and then sum the ms_played column
    artist_played = (
        df.groupby(["master_metadata_album_artist_name", "year", "month"])["ms_played"]
        .sum()
        .reset_index()
    )
    artist_played["played"] = (
        artist_played["year"].astype(str) + "-" + artist_played["month"].astype(str)
    )
    artist_played = artist_played[
        artist_played["master_metadata_album_artist_name"].isin(artists)
    ]
    artist_played = (
        artist_played.pivot(
            index="played",
            columns="master_metadata_album_artist_name",
            values="ms_played",
        )
        .reset_index()
        .fillna(0)
    )
    return artist_played


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


@st.cache_data
def filter_by_artist(df, artists):
    if len(artists):
        df = df[df["master_metadata_album_artist_name"].isin(artists)]
    return df


def maxes(df):
    # Group by artist, sum up the ms played, get the artist with the maximum ms played
    artist_max = (
        df.groupby("master_metadata_album_artist_name")["ms_played"].sum().reset_index()
    )
    artist_max = artist_max.sort_values(by="ms_played", ascending=False)
    artist_max = ms_to_time(artist_max)

    album_max = (
        df.groupby(
            ["master_metadata_album_album_name", "master_metadata_album_artist_name"]
        )["ms_played"]
        .sum()
        .reset_index()
    )
    album_max = album_max.sort_values(by="ms_played", ascending=False)
    album_max = ms_to_time(album_max)

    track_max = (
        df.groupby(["master_metadata_track_name", "master_metadata_album_artist_name"])[
            "ms_played"
        ]
        .sum()
        .reset_index()
    )
    track_max = track_max.sort_values(by="ms_played", ascending=False)
    track_max = ms_to_time(track_max)

    return artist_max.iloc[:5], album_max.iloc[:5], track_max.iloc[:5]


@st.cache_data
def top_skipped_songs(df):
    # count the number of times a song has been skipped
    skipped_songs = (
        df[df["skipped"] == True]
        .groupby(["master_metadata_track_name", "master_metadata_album_artist_name"])
        .size()
        .reset_index(name="tracks_skipped")
    )
    skipped_songs.sort_values(by="tracks_skipped", ascending=False, inplace=True)
    return skipped_songs.iloc[:50]


@st.cache_data
def platforms_used(df):
    platforms_df = df.groupby("platform").size().reset_index(name="tracks_played")
    platforms_df.sort_values(by="tracks_played", ascending=False, inplace=True)
    return platforms_df


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
    if "0" in hours:
        hours = hours.replace("0", "")
    if "0" in minutes:
        minutes = minutes.replace("0", "")
    if "0" in seconds:
        seconds = seconds.replace("0", "")
    if days == "0":
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"
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


########################### Page Layout ###########################

st.set_page_config(
    layout="wide", page_title="My Spotify Wrapped", page_icon="img/favicon.ico"
)
st.title("My Spotify Wrapped")

st.divider()
st.write(
    "My Spotify Wrapped is a Streamlit app gives me some tools to splice and dice my own Spotify extended streaming data. I've taken my raw Spotify data and created some visualizations and tables to help me understand my listening habits. To the left, you can select the start and end year to filter the data. You can also drill in on a specific artist that I've listened to in that year range. Below, the metrics, charts, and graphs will all update as you filter the data. Enjoy!"
)

st.divider()

spotify_data = load_data()

st.sidebar.subheader("Filter Data by Year")
st.sidebar.write(
    "Filter the data by start and end year.Selecting/updating this range will refresh the page and all selections."
)

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

# Filter data by artist
st.sidebar.subheader("Filter Data by Artist")
st.sidebar.write(
    "You can filter the data by one to many artists. This will not cause any other selections (namely the year range) to refresh."
)
artists = st.sidebar.multiselect(
    "Artists", options=spotify_data["master_metadata_album_artist_name"].unique()
)
spotify_data = filter_by_artist(spotify_data, artists)

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

st.divider()
st.header(f"Total played time (in ms) by....")
st.write(
    "Below is a chart showing my total played time over the selected range. Interestingly, there is a precipitous drop in 2018 followed by another drop in 2020. The first drop likely corresponds to when I started dating my wife. The second drop is when I began my Master's program. Updating the granularity of this chart will give you insight into day-to-day, month-to-month, or year-to-year trends."
)
granularity = st.selectbox("Select granularity", ["year", "month", "day"], index=1)

st.subheader(f"....{granularity}")
st.line_chart(
    played_time(spotify_data, granularity), x="date", y="ms_played", color="#1DB045"
)
if len(artists):
    st.subheader(f"Total played time (in ms) by artist")
    st.write(
        "Congratulations! You filtered by one of the artists that I listen to. This chart breaks out the amount of time I've spent listening to each individual artist. If you select another from the dropdown to the left, you'll see a new line added to this chart that corresponds to the time I've spent listening to that artist. The granularity of this chart is in months only."
    )
    ap_df = artist_played(spotify_data, artists)
    st.line_chart(ap_df, x="played", y=artists)

st.divider()
artist_max, album_max, track_max = maxes(spotify_data)
st.subheader("Top Listens")
st.write(
    "Here, we come to my top listens. These are the artists, albums, and tracks that I've spent the most time listening to. I'm not suprised at all by the staying power of Radiohead, Bon Iver, or Beach House in my catalog. These have been my go-to artists for years. Some surprises are just how much I listened to The Districts in the past few months, and how much I love Over and Over by Hot Chip."
)
st.metric(
    f"Artist: {artist_max.iloc[0]['master_metadata_album_artist_name']}",
    f"{convert_delta_to_readable(artist_max.iloc[0]['time_played'][:-7])}",
)
st.metric(
    f"Album: {album_max.iloc[0]['master_metadata_album_album_name']}, by {album_max.iloc[0]['master_metadata_album_artist_name']}",
    f"{convert_delta_to_readable(album_max.iloc[0]['time_played'][:-7])}",
)
st.metric(
    f"Track: {track_max.iloc[0]['master_metadata_track_name']}, by {track_max.iloc[0]['master_metadata_album_artist_name']}",
    f"{convert_delta_to_readable(track_max.iloc[0]['time_played'][:-7])}",
)

st.write(
    "The table below breaks out all of the artists by total tracks and albums played."
)
artist_df = artists_table(spotify_data)
if len(artists):
    st.dataframe(
        data=artist_df[
            artist_df["master_metadata_album_artist_name"].isin(artists)
        ].sort_values(by="played_tracks_count", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.dataframe(
        data=artist_df.sort_values(by="played_tracks_count", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
st.divider()

st.header("The Weird Bits")

st.write(
    "Now we get into some more esoteric data!\n\n The next few breakdowns put the 'extended' in 'extended streaming data.' We'll look at the platforms I used to listen to Spotify, the reasons I started and ended tracks, and the songs I skipped the most. Truly trilling stuff... but still kinda fun!"
)
st.subheader("Listen time by Platform")
st.write(
    "The pie chart below shows a breakdown of whether I was listening to Spotify on a mobile device or a desktop/laptop. I might break this out into a line chart at some point, because the trends here are interesting. Early on, I was listening to Spotify mostly on my desktop/laptop. I was well behind the smartphone curve and didn't get my first Android phone until 2015. Between 2015 and 2018, I was listening to Spotify mostly on my phone, likely on my walks to and from the office in Seattle and on my runs. Since 2018, a lot of that shifted. First, I stopped going into the office (thanks Master's/COVID) and I stopped listening to music all-together on runs."
)
spotify_platform = (
    spotify_data.groupby(["device"])["device"].count().reset_index(name="count")
)
fig = px.pie(
    spotify_platform,
    names="device",
    values="count",
    color="device",
    color_discrete_map={"Mobile": "#1DB045", "Desktop/Laptop": "#b3b3b3"},
)

st.plotly_chart(fig, use_container_width=True)
st.divider()

st.subheader("Reasons for..... ")
st.write(
    'The bar graphs below show how often I chose a way to start and end listening to a song. Not surprisingly, most of the time a track ended or began because I was just done listening to the current/previous song. Interestingly, as you move the start range later and later, you should see that I started exploring Spotify more - choosing to begin a song using the "clickrow" option (meaning I clicked on the song in a playlist/album/artist page).'
)
reason_start = reason_table(spotify_data, "reason_start")
reason_end = reason_table(spotify_data, "reason_end")

st.subheader("..... starting a track")
st.bar_chart(reason_start, x="reason_start", y="count", color="#1DB045")
st.subheader("..... ending a track")
st.bar_chart(reason_end, x="reason_end", y="count", color="#1DB045")

st.divider()
st.subheader("Top Skipped Songs")
st.write(
    "Yup, just like the heading says: These are the songs I skipped the most. I've skipped a fair amount of Kanye. Not shocking. I've also skipped a lot of songs that I really enjoy. My best guess is that I get burned out by over-listening to them and invariably skip them when my favorite part of the song is done."
)
top_skipped_songs_df = top_skipped_songs(spotify_data)
st.dataframe(
    data=top_skipped_songs_df,
    hide_index=True,
    use_container_width=True,
)

st.divider()
st.subheader("Platforms/Operating Systems")
st.write(
    "These are the operating systems I've used to listen to Spotify - including the total listen time and track count. I could probably do some grouping here on Mac OS/Windows/Android/Linux, but it's nice to see the raw data like this as well. See if you can spot the Yamaha receiver in the list."
)
platforms_df = platforms_used(spotify_data)
st.dataframe(
    data=platforms_df,
    hide_index=True,
    use_container_width=True,
)
