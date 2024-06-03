import base64
import html
import os
import threading
import time
import urllib.request

from mutagen.mp4 import MP4, MP4Cover
from pySmartDL import SmartDL

from .helper import argManager
from .pyDes import *

REQUEST_TIMEOUT = 60


def remove_duplicates(input_str):
    if not isinstance(input_str, str):
        return input_str

    elements = input_str.split(', ')
    elements = list(set(elements))  # remove duplicates
    return ', '.join(elements)  # join back together


def format_filename(filename):
    # unescape HTML specific characters
    filename = html.unescape(filename)

    # append '.m4a' to the filename
    filename += '.m4a'

    # replacing invalid filename characters
    invalid_chars = ['\"', ':', '/', '<', '>', '?', '*', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '-')

    return filename


def start_download(filename, location, dec_url, retry_count=10, backoff_time=1):
    if os.path.isfile(location) and os.path.getsize(location) > 0:
        print("Already downloaded {0}".format(filename))
        return True
    else:
        while retry_count > 0:
            try:
                print("Downloading {0}".format(filename))
                obj = SmartDL(dec_url, location, timeout=REQUEST_TIMEOUT)
                obj.start()
                # after download, check file size. If file size is 0 or too small, retry download
                if os.path.getsize(location) > 0:
                    return True
                else:
                    print(
                        f"File {filename} downloaded but file size is zero. Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    retry_count -= 1
                    backoff_time *= 2  # double the backoff time
            except Exception as e:
                print(f'Error downloading file {filename}: {e}. Retrying in {backoff_time} seconds...')
                time.sleep(backoff_time)
                retry_count -= 1
                backoff_time *= 2  # double the backoff time
        print(f"Failed to download {filename} after multiple attempts.")
        return False


class Manager:
    def __init__(self):
        self.unicode = str
        self.args = argManager()
        self.des_cipher = self.set_decipher()
        self.lock = threading.Lock()

    @staticmethod
    def set_decipher():
        return des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

    def get_dec_url(self, enc_url):
        enc_url = base64.b64decode(enc_url.strip())
        dec_url = self.des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
        dec_url = dec_url.replace('_96.mp4', '_320.mp4')
        return dec_url

    def get_download_location(self, *args):
        with self.lock:  # Acquire the lock before checking and creating directory
            if self.args.outFolder is None:
                location = os.getcwd()
            else:
                location = self.args.outFolder
            for folder in args:
                location = os.path.join(location, folder)
        return location

    def download_songs(self, album, artist_name='Non-Artist'):
        print(f"Downloading {album.list_count} songs...")
        songs_json = album.album_json
        album_name = album.album_json['name']
        songs = [song for song in songs_json['songs']]
        total_tracks = len(songs)

        for i, song in enumerate(songs):
            try:
                dec_url = self.get_dec_url(song['encrypted_media_url'])
                filename = format_filename(song['song'])
                location = self.get_download_location(artist_name, album_name, filename)
                track_number = i + 1
                has_downloaded = start_download(filename, location, dec_url)
                if has_downloaded:
                    name = songs_json.get('name', songs_json.get('listname', ''))
                    try:
                        self.addtags(location, song, name, track_number, total_tracks)
                    except Exception as e:
                        print("============== Error Adding Meta Data ==============")
                        print(f"Error : {e}")
                    print('\n')
            except Exception as e:
                print(f'Error during download process for {song["song"]}: {e}')

    def addtags(self, filename, json_data, playlist_name, track_number, total_tracks):
        audio = MP4(filename)
        audio['\xa9nam'] = html.unescape(self.unicode(remove_duplicates(json_data['song'])))

        # Handle duplicate entries in the json_data
        for key in json_data:
            json_data[key] = remove_duplicates(json_data[key])

        metadata_mapping = {
            'telugu': {
                'artist': html.unescape(self.unicode(json_data['singers'])),
                'album_artist': html.unescape(self.unicode(json_data['music']))
            },
            'default': {
                'artist': html.unescape(self.unicode(json_data['singers'])),
                'album_artist': html.unescape(self.unicode(json_data['primary_artists'].split(', ')[0]))
            }
        }

        if 'featured_artists' in json_data and json_data['featured_artists']:
            metadata_mapping['default']['artist'] += ', ' + html.unescape(self.unicode(json_data['featured_artists']))

        language = json_data['language'].lower()
        metadata = metadata_mapping.get(language, metadata_mapping['default'])

        audio['\xa9ART'] = remove_duplicates(metadata['artist'])
        audio['aART'] = remove_duplicates(metadata['album_artist'])
        audio['\xa9alb'] = html.unescape(self.unicode(json_data['album']))
        audio['\xa9wrt'] = html.unescape(self.unicode(json_data['music']))
        audio['desc'] = html.unescape(self.unicode(json_data['starring']))
        audio['\xa9gen'] = html.unescape(self.unicode(playlist_name))
        audio['\xa9day'] = html.unescape(self.unicode(json_data['year']))
        audio['cprt'] = html.unescape(self.unicode(json_data['label']))
        audio['trkn'] = [(track_number, total_tracks)]

        cover_url = json_data['image'][:-11] + '500x500.jpg'
        with urllib.request.urlopen(cover_url) as fd:
            cover = MP4Cover(fd.read(), getattr(MP4Cover, 'FORMAT_PNG' if cover_url.endswith('png') else 'FORMAT_JPEG'))

        audio['covr'] = [cover]
        audio.save()
