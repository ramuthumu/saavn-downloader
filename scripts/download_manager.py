from mutagen.mp4 import MP4, MP4Cover
import urllib.request
import html
import json
import base64
import os

from concurrent.futures import ThreadPoolExecutor


from pySmartDL import SmartDL

from .pyDes import *
from .helper import argManager

REQUEST_TIMEOUT = 60

class Manager():
    def __init__(self):
        self.unicode = str
        self.args = argManager()
        self.des_cipher = self.setDecipher()
    
    def setDecipher(self):
        return des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
    
    def get_dec_url(self, enc_url):
        enc_url = base64.b64decode(enc_url.strip())
        dec_url = self.des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
        dec_url = dec_url.replace('_96.mp4', '_320.mp4')
        return dec_url
    
    def format_filename(self, filename):
        # unescape HTML specific characters
        filename = html.unescape(filename)

        # append '.m4a' to the filename
        filename += '.m4a'

        # replacing invalid filename characters
        invalid_chars = ['\"', ':', '/', '<', '>', '?', '*', '|']
        for char in invalid_chars:
            filename = filename.replace(char, '-')

        return filename


    def get_download_location(self, *args):
        if self.args.outFolder is None:
            location = os.getcwd()
        else:
            location = self.args.outFolder
        for folder in args:
            location = os.path.join(location, folder)
        return location

    def start_download(self, filename, location, dec_url, retry_count=3):
        if os.path.isfile(location) and os.path.getsize(location) > 0:
            print("Already downloaded {0}".format(filename))
            return False
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
                        print(f"File {filename} downloaded but file size is zero. Retrying...")
                        retry_count -= 1
                except Exception as e:
                    print(f'Error downloading file {filename}: {e}. Retries left: {retry_count}')
                    retry_count -= 1
            return False


    def downloadSongs(self, songs_json, album_name='songs', artist_name='Non-Artist'):
        with ThreadPoolExecutor(max_workers=5) as executor:  # you can adjust max_workers based on your system's capacity
            futures = []
            total_tracks = len(songs_json['songs'])
            for i, song in enumerate(songs_json['songs']):
                try:
                    dec_url = self.get_dec_url(song['encrypted_media_url'])
                    filename = self.format_filename(song['song'])
                    location = self.get_download_location(artist_name, album_name, filename)
                    track_number = i + 1  # Assuming tracks are listed in order
                    future = executor.submit(self.start_download, filename, location, dec_url)
                    futures.append((future, song, location, track_number, total_tracks))  # store future along with related information
                except Exception as e:
                    print('Error scheduling download for {0}: {1}'.format(song, e))

            for future, song, location, track_number, total_tracks in futures:
                try:
                    has_downloaded = future.result()  # get result from future
                    if has_downloaded:
                        try:
                            name = songs_json['name'] if 'name' in songs_json else songs_json['listname']
                        except:
                            name = ''
                        try:
                            self.addtags(location, song, name, track_number, total_tracks)
                        except Exception as e:
                            print("============== Error Adding Meta Data ==============")
                            print("Error : {0}".format(e))
                        print('\n')
                except Exception as e:
                    print('Error during download process for {0}: {1}'.format(song, e))


    def addtags(self, filename, json_data, playlist_name, track_number, total_tracks):
        audio = MP4(filename)
        audio['\xa9nam'] = html.unescape(self.unicode(json_data['song']))

        # Check the language of the song
        if json_data['language'].lower() == 'telugu':
            audio['\xa9ART'] = html.unescape(self.unicode(json_data['singers']))  # artist is now 'singers
            audio['aART'] = html.unescape(self.unicode(json_data['music']))  # album artist is now 'music'
        else:
            main_artist = html.unescape(self.unicode(json_data['singers']))
            if 'featured_artists' in json_data and json_data['featured_artists']:
                main_artist += ',' + html.unescape(self.unicode(json_data['featured_artists']))
            audio['\xa9ART'] = main_artist  # artist is now 'singers,music'
            audio['aART'] = html.unescape(self.unicode(json_data['primary_artists'].split(', ')[0]))  # album artist is 'singers'

        audio['\xa9alb'] = html.unescape(self.unicode(json_data['album']))
        audio['\xa9wrt'] = html.unescape(self.unicode(json_data['music']))
        audio['desc'] = html.unescape(self.unicode(json_data['starring']))
        audio['\xa9gen'] = html.unescape(self.unicode(playlist_name))
        audio['\xa9day'] = html.unescape(self.unicode(json_data['year']))
        audio['cprt'] = html.unescape(self.unicode(json_data['label']))
        audio['trkn'] = [(track_number, total_tracks)]

        cover_url = json_data['image'][:-11] + '500x500.jpg'
        fd = urllib.request.urlopen(cover_url)
        cover = MP4Cover(fd.read(), getattr(MP4Cover, 'FORMAT_PNG' if cover_url.endswith('png') else 'FORMAT_JPEG'))
        fd.close()
        audio['covr'] = [cover]
        audio.save()


