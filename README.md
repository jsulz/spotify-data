# My Spotify Wrapped

## Description

This project is a simple data analysis of my own personal Spotify listening data from 2013 to the spring of 2024. The data, found in `spotify_data/raw.csv`, was [downloaded from Spotify](https://support.spotify.com/us/article/data-rights-and-privacy-settings/) and contains information about the songs I've listened to, including the artist, album, track name, and the date and time I listened to the song.

The main goal of this project is to analyze my listening habits and preferences over the years. To that end, the data is loaded into a Pandas dataframe, cleaned, and transformed in `spotify_data/app.py` where the final dataframe is used in a Streamlit application to generate visualizations.

If you're looking at this repository on GitHub, you might notice that the `spotify_data/raw.csv` looks a little... odd. That's because the GitHub repository is a mirror of the original repository hosted on XetHub. XetHub, among many other things, is a platform that allows you to store large files that GitHub doesn't support. While `spotify_data/raw.csv` is only 20MB and could be hosted by GitHub, I've chosen to host the main repository through XetHub where it can better manage the data as the file grows along with my Spotify listens. None of the data is particularly sensitive, and the [XetHub repo is public](https://xethub.com/jsulz/spotify-data) if you want to check it out.

If you dig deeply enough, you might see how many times I've listened to Adele (a lot!) and Taylor Swift (not that much). I'm not _that_ ashamed.

The GitHub mirror is helpful in that I'm leveraging GitHub actions to deploy the Streamlit app to Google Cloud Run (some of the deployment instructions required some sensitive keys, and XetHub currently doesn't support secure secrets in XetHub actions). I began by developing locally and then using XetHub's [Capsules](https://xethub.com/assets/docs/deploying-apps) for Streamlit development, but by hosting things on Google Cloud Run, I can more easily share my historically bad taste in music with the world.

Streamlit isn't exactly a lightweight install; even though I'm running on a slim Docker image, it's still a bit heavy for a Cloud Run environment with only 512MB of memory. After seeing a few crashes in the logs, I've upped that to 1GB.

The only downside is that because I'm using GitHub Actions as my CI/CD pipeline, that's also where I build the Docker image and can't bundle the data at the same time. To get around that, I'm using [PyXet](https://github.com/xetdata/pyxet) to access the data from XetHub when Streamlit loads.

The Streamlit app can be found [here](https://myspotifywrapped.jsulz.com). It make take a second for it to run since I'm spinning down the Cloud Run instance after 15 minutes of inactivity. Enjoy!
