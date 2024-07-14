from tests.conftest import client
from datetime import datetime, timedelta
import requests_mock

def test_landing_page(client):
    response = client.get('/')
    assert response.status_code == 200


def test_login(client):
    response = client.get('/login')
    assert response.status_code == 302


def test_callback_success(client):
    with requests_mock.Mocker() as mock:
        mock.post('https://accounts.spotify.com/api/token', json={
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 3600
        })
        response = client.get('/callback?code=test_code')
        assert response.status_code == 302
        assert response.headers['Location'] == '/playlists'
        with client.session_transaction() as session:
            assert session['access_token'] == 'test_access_token'
            assert session['refresh_token'] == 'test_refresh_token'
            assert 'expires_at' in session

def test_get_playlists(client):
    with requests_mock.Mocker() as mock:
        mock.get('https://api.spotify.com/v1/me/tracks?limit=50', json={
            'items': [
                {'track': {'id': 'track_id_1', 'name': 'Track 1'}},
                {'track': {'id': 'track_id_2', 'name': 'Track 2'}},
                {'track': {'id': 'track_id_3', 'name': 'Track 3'}},
                {'track': {'id': 'track_id_4', 'name': 'Track 4'}}
            ],
            'next': 'https://api.spotify.com/v1/me/tracks?offset=4&limit=4'
        })
        
        mock.get('https://api.spotify.com/v1/me/tracks?offset=4&limit=4', json={
            'items': [
                {'track': {'id': 'track_id_5', 'name': 'Track 5'}},
                {'track': {'id': 'track_id_6', 'name': 'Track 6'}},
                {'track': {'id': 'track_id_7', 'name': 'Track 7'}},
                {'track': {'id': 'track_id_8', 'name': 'Track 8'}}
            ],
            'next': None
        })
        
        mock.get('https://api.spotify.com/v1/audio-features?ids=track_id_1,track_id_2,track_id_3,track_id_4,track_id_5,track_id_6,track_id_7,track_id_8', json={
            'audio_features': [
                {'danceability': 0.7, 'energy': 0.8, 'instrumentalness': 0.2, 'loudness': -5.2, 'speechiness': 0.1, 'tempo': 120, 'valence': 0.6},
                {'danceability': 0.6, 'energy': 0.7, 'instrumentalness': 0.3, 'loudness': -6.5, 'speechiness': 0.2, 'tempo': 130, 'valence': 0.5},
                {'danceability': 0.8, 'energy': 0.9, 'instrumentalness': 0.1, 'loudness': -4.8, 'speechiness': 0.15, 'tempo': 115, 'valence': 0.7},
                {'danceability': 0.5, 'energy': 0.6, 'instrumentalness': 0.4, 'loudness': -7.0, 'speechiness': 0.3, 'tempo': 140, 'valence': 0.4},
                {'danceability': 0.75, 'energy': 0.85, 'instrumentalness': 0.15, 'loudness': -5.0, 'speechiness': 0.12, 'tempo': 125, 'valence': 0.65},
                {'danceability': 0.65, 'energy': 0.75, 'instrumentalness': 0.25, 'loudness': -6.0, 'speechiness': 0.25, 'tempo': 135, 'valence': 0.55},
                {'danceability': 0.72, 'energy': 0.82, 'instrumentalness': 0.18, 'loudness': -5.5, 'speechiness': 0.11, 'tempo': 122, 'valence': 0.68},
                {'danceability': 0.68, 'energy': 0.78, 'instrumentalness': 0.22, 'loudness': -5.8, 'speechiness': 0.28, 'tempo': 132, 'valence': 0.58}
            ]
        })

        response = client.get('/playlists')

        assert response.status_code == 200
        data = response.json
        assert 'playlist #1' in data
        assert 'playlist #2' in data
        assert 'playlist #3' in data
        assert 'playlist #4' in data
        assert 'playlist #5' in data
        assert 'playlist #6' in data
        assert 'playlist #7' in data
        assert 'playlist #8' in data

def test_refresh_token(client):
    with client.session_transaction() as sess:
        sess['refresh_token'] = 'test_refresh_token'
        sess['expires_at'] = 0

    with requests_mock.Mocker() as mock:
        mock.post('https://accounts.spotify.com/api/token', json={
            'access_token': 'new_test_access_token',
            'expires_in': 3600
        })
        response = client.get('/refresh-token')
        assert response.status_code == 302
        assert response.headers['Location'] == '/playlists'
        with client.session_transaction() as sess:
            assert sess['access_token'] == 'new_test_access_token'
            assert 'expires_at' in sess
