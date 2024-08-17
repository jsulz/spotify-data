# My Spotify Wrapped

## Description

This project is a simple data analysis of my own personal Spotify listening data from 2013 to the spring of 2024. The data, found in `spotify_data/raw.csv`, was [downloaded from Spotify](https://support.spotify.com/us/article/data-rights-and-privacy-settings/) and contains information about the songs I've listened to, including the artist, album, track name, and the date and time I listened to the song.

The main goal of this project is to analyze my listening habits and preferences over the years. To that end, the data is loaded into a Pandas dataframe, cleaned, and transformed in `spotify_data/app.py` where the final dataframe is used in a Streamlit application to generate visualizations.

If you dig deeply enough, you might see how many times I've listened to Adele (not that much) and Taylor Swift (a lot! Bon Iver collab doomed me). I'm not _that_ ashamed.

Streamlit isn't exactly a lightweight install; even though I'm running on a slim Docker image, it's still a bit heavy for a Cloud Run environment with only 512MB of memory. After seeing a few crashes in the logs, I've upped that to 1GB.

The Streamlit app can be found [here](https://myspotifywrapped.jsulz.com). It make take a second for it to run since I'm spinning down the Cloud Run instance after 15 minutes of inactivity. Enjoy!
