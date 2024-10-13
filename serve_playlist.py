#!/usr/bin/env python3

import os
import math
import re
import random
from glob import glob

import pandas as pd
from flask import Flask, render_template_string, request

app = Flask(__name__)

PLAYLIST_FOLDER = os.environ.get('PLAYLIST_FOLDER', '.')

def get_playlist_files():
    return [os.path.basename(f) for f in glob(os.path.join(PLAYLIST_FOLDER, '*.csv'))]

def read_playlist(filename):
    return pd.read_csv(os.path.join(PLAYLIST_FOLDER, filename), header=None, names=['date', 'artist', 'title', 'url'])

def get_youtube_id(url):
    # Extract YouTube video ID from URL
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

def get_random_video():
    all_videos = []
    for playlist_file in get_playlist_files():
        playlist = read_playlist(playlist_file)
        all_videos.extend(playlist.to_dict('records'))
    return random.choice(all_videos) if all_videos else None

@app.route('/')
def index():
    playlists = [os.path.splitext(f)[0] for f in get_playlist_files()]
    random_video = get_random_video()
    return render_template_string(BASE_TEMPLATE, playlists=playlists, content=render_template_string(INDEX_TEMPLATE, random_video=random_video, get_youtube_id=get_youtube_id), get_youtube_id=get_youtube_id)

@app.route('/playlist/<playlist_name>')
def playlist(playlist_name):
    playlists = [os.path.splitext(f)[0] for f in get_playlist_files()]
    playlist = read_playlist(f"{playlist_name}.csv")
    page = request.args.get('page', 1, type=int)
    per_page = 9
    total_pages = math.ceil(len(playlist) / per_page)
    
    start = (page - 1) * per_page
    end = start + per_page
    
    playlist_page = playlist.iloc[start:end]
    
    return render_template_string(BASE_TEMPLATE, playlists=playlists, content=render_template_string(PLAYLIST_TEMPLATE, playlist_page=playlist_page, page=page, total_pages=total_pages, get_youtube_id=get_youtube_id, playlist_name=playlist_name), get_youtube_id=get_youtube_id)

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playlist Viewer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://www.youtube.com/iframe_api"></script>
</head>
<body class="bg-slate-100 min-h-screen">
    <nav class="bg-sky-800 p-4">
        <div class="container mx-auto space-x-3 flex justify-center text-white">
            <a href="/" class="hover:underline">home</a>
            {% for playlist in playlists %}
            <a href="{{ url_for('playlist', playlist_name=playlist) }}" class="hover:underline">{{ playlist }}</a>
            {% endfor %}
        </div>
    </nav>
    <div class="container mx-auto px-4 py-8">
        {{ content | safe }}
    </div>
    <script>
    let players = {};
    
    function onYouTubeIframeAPIReady() {
        // The API is ready, but we'll create players on demand
    }
    
    function playAudio(videoId, imgElement) {
        if (!players[videoId]) {
            players[videoId] = new YT.Player('player-' + videoId, {
                height: '0',
                width: '0',
                videoId: videoId,
                playerVars: {
                    'autoplay': 1,
                    'controls': 0,
                },
                events: {
                    'onReady': function(event) {
                        event.target.playVideo();
                        imgElement.style.opacity = '0.5';
                        updateProgressBar(videoId);
                    },
                    'onStateChange': function(event) {
                        if (event.data == YT.PlayerState.PLAYING) {
                            updateProgressBar(videoId);
                        } else {
                            clearInterval(players[videoId].progressInterval);
                        }
                    }
                }
            });
        } else {
            if (players[videoId].getPlayerState() === YT.PlayerState.PLAYING) {
                players[videoId].pauseVideo();
                imgElement.style.opacity = '1';
                clearInterval(players[videoId].progressInterval);
            } else {
                players[videoId].playVideo();
                imgElement.style.opacity = '0.5';
                updateProgressBar(videoId);
            }
        }
    }

    function updateProgressBar(videoId) {
        clearInterval(players[videoId].progressInterval);
        players[videoId].progressInterval = setInterval(() => {
            const player = players[videoId];
            const duration = player.getDuration();
            const currentTime = player.getCurrentTime();
            const progress = (currentTime / duration) * 100;
            const progressBar = document.getElementById('progress-' + videoId);
            if (progressBar) {
                progressBar.style.width = progress + '%';
            }
        }, 1000);
    }
    </script>
</body>
</html>
'''

INDEX_TEMPLATE = '''
<div class="text-center">
    <h2 class="text-2xl font-semibold mb-4">Random Track</h2>
    {% if random_video %}
    <div class="max-w-2xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
        <div class="aspect-w-16 aspect-h-9 relative">
            <img src="https://img.youtube.com/vi/{{ get_youtube_id(random_video.url) }}/0.jpg" 
                 alt="{{ random_video.title }}" 
                 class="w-full h-full object-cover cursor-pointer"
                 onclick="playAudio('{{ get_youtube_id(random_video.url) }}', this)">
            <div id="player-{{ get_youtube_id(random_video.url) }}" class="absolute inset-0 hidden"></div>
            <div class="absolute bottom-0 left-0 right-0 h-1 bg-slate-200">
                <div id="progress-{{ get_youtube_id(random_video.url) }}" class="h-full bg-red-500 w-0"></div>
            </div>
        </div>
        <div class="p-4">
            <h2 class="text-xl font-semibold mb-2 text-slate-800">{{ random_video.title }}</h2>
            <p class="text-slate-600 mb-2">{{ random_video.artist }}</p>
            <p class="text-sm text-slate-500">{{ random_video.date }}</p>
        </div>
    </div>
    {% else %}
    <p>No videos available.</p>
    {% endif %}
</div>
'''

PLAYLIST_TEMPLATE = '''
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
    {% for _, track in playlist_page.iterrows() %}
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
        <div class="aspect-w-16 aspect-h-9 relative">
            <img src="https://img.youtube.com/vi/{{ get_youtube_id(track.url) }}/0.jpg" 
                 alt="{{ track.title }}" 
                 class="w-full h-full object-cover cursor-pointer"
                 onclick="playAudio('{{ get_youtube_id(track.url) }}', this)">
            <div id="player-{{ get_youtube_id(track.url) }}" class="absolute inset-0 hidden"></div>
            <div class="absolute bottom-0 left-0 right-0 h-1 bg-slate-200">
                <div id="progress-{{ get_youtube_id(track.url) }}" class="h-full bg-red-500 w-0"></div>
            </div>
        </div>
        <div class="p-4">
            <h2 class="font-semibold mb-2 text-slate-800 truncate">{{ track.title }}</h2>
            <p class="text-sm text-slate-600 mb-2">{{ track.artist }}</p>
            <p class="place-item-bottom text-xs text-slate-500">{{ track.date }}</p>
        </div>
    </div>
    {% endfor %}
</div>
<div class="mt-8 flex justify-center">
    {% if page > 1 %}
        <a href="{{ url_for('playlist', playlist_name=playlist_name, page=page-1) }}" class="bg-sky-800 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-l">
            Previous
        </a>
    {% endif %}
    {% if page < total_pages %}
        <a href="{{ url_for('playlist', playlist_name=playlist_name, page=page+1) }}" class="bg-sky-800 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-r">
            Next
        </a>
    {% endif %}
</div>
'''

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
