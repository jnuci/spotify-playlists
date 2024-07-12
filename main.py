import requests
import urllib.parse
import base64
import pandas as pd
import os

from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from collections import defaultdict
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session
from dotenv import load_dotenv


app = Flask(__name__)

load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SPOTIFY_CLIENT_ID'] = os.getenv('SPOTIFY_CLIENT_ID')
app.config['SPOTIFY_CLIENT_SECRET'] = os.getenv('SPOTIFY_CLIENT_SECRET')

# REDIRECT_URI = 'http://localhost:5000/callback'
REDIRECT_URI = 'https://spotify-playlists.onrender.com/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'


@app.route('/')
def index():
    return "Welcome to my Spotify App <a href='/login'>Log in with Spotify</a>"


@app.route('/login')
def login():
    scope = "user-read-private user-library-read user-read-email"

    params = {
        'client_id': app.config['SPOTIFY_CLIENT_ID'],
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)


@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
        }

        credentials = f"{app.config['SPOTIFY_CLIENT_ID']}:{app.config['SPOTIFY_CLIENT_SECRET']}"
        encoded_credentials = base64.b64encode(
            credentials.encode('utf-8')).decode('utf-8')

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_credentials}'
        }

        response = requests.post(TOKEN_URL, data=req_body, headers=headers)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + \
            token_info['expires_in']

        return redirect('/playlists')


@app.route('/playlists')
def get_playlists():
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    track_names = []
    track_ids = []
    not_included = []

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(
        API_BASE_URL + 'me/tracks?limit=50', headers=headers)
    playlist = response.json()
    batch = []
    for song in playlist['items']:
        track_names.append(song['track']['name'])
        batch.append(song['track']['id'])
    while playlist['next']:
        response = requests.get(playlist['next'], headers=headers)
        playlist = response.json()
        for song in playlist['items']:
            track_names.append(song['track']['name'])
            batch.append(song['track']['id'])
            if len(batch) == 100:
                track_ids.append(batch)
                batch = []
    if batch:
        track_ids.append(batch)

    features = []
    count = 0
    for batch in track_ids:
        response = requests.get(
            API_BASE_URL + 'audio-features' + f'?ids={",".join(batch)}', headers=headers)
        playlist = response.json()

        for song in playlist['audio_features']:
            if not song:
                not_included.append(track_names[count])
                count += 1
                continue
            count += 1
            temp = {feature: value for feature, value in song.items() if feature in [
                "danceability", "energy", "instrumentalness", "loudness", "speechiness", "tempo", "valence"]}
            features.append(temp)

    df = pd.DataFrame(features)

    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(df)

    kmeans = KMeans(n_clusters=8, random_state=42)
    kmeans.fit(scaled_features)

    playlists = defaultdict(list)

    for name, label in zip(track_names, kmeans.labels_):
        playlists[f'playlist #{label + 1}'].append(name+'\n')

    if not_included:
        playlists['Not included:'] = not_included

    return jsonify(playlists)


@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh-token': session['refresh_token'],
            'client-id': app.config['SPOTIFY_CLIENT_ID'],
            'secret-id': app.config['SPOTIFY_CLIENT_SECRET']
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + \
            new_token_info['expires_in']

    return redirect('/playlists')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
