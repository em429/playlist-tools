import os
import sqlite3
from flask import g
import random

DATABASE = os.getenv("PLAYLIST_DB_PATH")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             date TEXT,
             artist TEXT,
             title TEXT,
             url TEXT,
             play_count INTEGER DEFAULT 0)
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             title TEXT UNIQUE)
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks
            (playlist_id INTEGER,
             track_id INTEGER,
             FOREIGN KEY(playlist_id) REFERENCES playlists(id),
             FOREIGN KEY(track_id) REFERENCES tracks(id),
             PRIMARY KEY(playlist_id, track_id))
        ''')
        db.commit()

def get_playlists():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title FROM playlists")
    return [row['title'] for row in cursor.fetchall()]

def read_playlist(playlist_name, search_query=None, sort_by=None, sort_direction='ASC'):
    db = get_db()
    cursor = db.cursor()
    query = '''
        SELECT t.id, t.date, t.artist, t.title, t.url, t.play_count
        FROM tracks t
        JOIN playlist_tracks pt ON t.id = pt.track_id
        JOIN playlists p ON p.id = pt.playlist_id
        WHERE p.title = ?
    '''
    params = [playlist_name]
    
    if search_query:
        query += ' AND (t.artist LIKE ? OR t.title LIKE ?)'
        params.extend(['%' + search_query + '%'] * 2)
    
    if sort_by:
        if sort_by == 'random':
            query += ' ORDER BY RANDOM()'
        elif sort_by == 'play_count':
            query += f' ORDER BY t.play_count {sort_direction}'
        else:
            query += f' ORDER BY t.{sort_by} {sort_direction}'
    
    cursor.execute(query, params)
    return cursor.fetchall()

def get_random_track():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT date, artist, title, url, play_count FROM tracks ORDER BY RANDOM() LIMIT 1")
    return cursor.fetchone()

def remove_track_from_playlist(track_id, playlist_name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        DELETE FROM playlist_tracks
        WHERE track_id = ? AND playlist_id = (SELECT id FROM playlists WHERE title = ?)
    ''', (track_id, playlist_name))
    db.commit()

def create_playlist(playlist_name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM playlists WHERE title = ?", (playlist_name,))
    existing_playlist = cursor.fetchone()
    if existing_playlist:
        return False
    cursor.execute("INSERT INTO playlists (title) VALUES (?)", (playlist_name,))
    db.commit()
    return True

def remove_playlist(playlist_name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = (SELECT id FROM playlists WHERE title = ?)", (playlist_name,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("DELETE FROM playlists WHERE title = ?", (playlist_name,))
        db.commit()
        return True
    return False

def add_track_to_playlist(playlist_name, date, artist, title, url):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM tracks WHERE artist = ? AND title = ?", (artist, title))
    existing_track = cursor.fetchone()

    if existing_track:
        track_id = existing_track['id']
    else:
        cursor.execute("INSERT INTO tracks (date, artist, title, url, play_count) VALUES (?, ?, ?, ?, 0)",
                       (date, artist, title, url))
        track_id = cursor.lastrowid

    cursor.execute('''
        SELECT 1 FROM playlist_tracks
        WHERE playlist_id = (SELECT id FROM playlists WHERE title = ?)
        AND track_id = ?
    ''', (playlist_name, track_id))
    
    if cursor.fetchone():
        return False
    else:
        cursor.execute('''
            INSERT INTO playlist_tracks (playlist_id, track_id)
            VALUES ((SELECT id FROM playlists WHERE title = ?), ?)
        ''', (playlist_name, track_id))
        db.commit()
        return True

def move_track_between_playlists(track_id, from_playlist, to_playlist):
    db = get_db()
    cursor = db.cursor()
    
    # Check if the track is already in the destination playlist
    cursor.execute('''
        SELECT 1 FROM playlist_tracks
        WHERE track_id = ? AND playlist_id = (SELECT id FROM playlists WHERE title = ?)
    ''', (track_id, to_playlist))
    
    if cursor.fetchone():
        return False  # Track already exists in the destination playlist
    
    # Remove the track from the source playlist
    cursor.execute('''
        DELETE FROM playlist_tracks
        WHERE track_id = ? AND playlist_id = (SELECT id FROM playlists WHERE title = ?)
    ''', (track_id, from_playlist))
    
    # Add the track to the destination playlist
    cursor.execute('''
        INSERT INTO playlist_tracks (playlist_id, track_id)
        VALUES ((SELECT id FROM playlists WHERE title = ?), ?)
    ''', (to_playlist, track_id))
    
    db.commit()
    return True

def increment_play_count(track_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tracks SET play_count = play_count + 1 WHERE id = ?", (track_id,))
    db.commit()
