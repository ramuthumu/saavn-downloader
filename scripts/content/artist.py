import requests
import json

from .album import Album
from ..download_manager import Manager

import urllib3

urllib3.disable_warnings()


class Artist:
    def __init__(self, proxies, headers, args, url=None):
        self.session = requests.Session()
        self.session.proxies = proxies
        self.session.headers = headers
        self.args = args
        self.artist_id = None
        self.artist_name = None
        self.artist_json = []
        self.album_ids_artist = []
        self.url = url

    def get_artist_id(self, url=None):
        if url:
            self.url = url
        token = self.url.split("/")[-1]
        self.url = ("https://www.jiosaavn.com/api.php?__call=webapi.get&token={"
                    "0}&type=artist&p=&n_song=10&n_album=14&sub_type=&category=&sort_order=&includeMetaTags=0&ctx"
                    "=web6dot0&api_version=4&_format=json&_marker=0").format(
            token)
        response = self.session.get(self.url)
        self.artist_id = response.json()["artistId"]
        return self.artist_id

    def set_artist_id(self, artist_id):
        self.artist_id = artist_id

    def get_artist_albums_ids(self):
        self.artist_json = self.get_artist_json()
        try:
            self.artist_name = self.artist_json['name']
            total_albums = self.artist_json['topAlbums']['total']
            print('Total Albums of the Artist: {0}'.format(total_albums))
            if total_albums % 10 != 0:
                total_requests = (total_albums // 10) + 1
            else:
                total_requests = total_albums // 10
            print('Total requests: {}'.format(total_requests))

            for n_album_page in range(total_requests):
                print('Getting Album page: {0}'.format(n_album_page))
                url = ('https://www.saavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails'
                       '&artistId={0}&n_album=10&page={1}').format(
                    self.artist_id, n_album_page)
                try:
                    response = self.session.get(url)
                    self.artist_json = response.json()
                    self.artist_json = json.loads(self.artist_json)
                    n_albums_in_page = len(self.artist_json['topAlbums']['albums'])
                    for i in range(n_albums_in_page):
                        albumId = self.artist_json['topAlbums']['albums'][i]['albumid']
                        self.album_ids_artist.append(albumId)
                except Exception as e:
                    print(str(e))
                    print('No albums found for the artist : {0}'.format(self.artist_name))
                    exit()
        except Exception as e:
            print(str(e))
            print('No albums found for the artist : {0}'.format(self.artist_name))
            exit()

        print('Total Number of Albums found: {0}'.format(len(self.album_ids_artist)))
        return self.album_ids_artist, self.artist_name

    def get_artist(self):
        try:
            self.get_artist_id()
            self.artist_json = self.get_artist_json()
        except Exception as e:
            print(str(e))
            print('Please check that the entered URL is for an Artist')
            exit()
        if self.args.song:
            print('Downloading all Artist songs')
            self.download_artist_all_songs()
        else:
            print('Downloading all albums for the Artist')
            self.get_artist_albums_ids()
            self.download_artist_all_albums()

    def get_artist_json(self):
        url = 'https://www.jiosaavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails&artistId={0}'.format(
            self.artist_id)
        response = self.session.get(url)
        artist_json = response.json()
        return artist_json

    def download_artist_all_albums(self):
        if self.album_ids_artist:
            for albumId in self.album_ids_artist:
                try:
                    self.download_album(albumId)
                except Exception as e:
                    print(f'Error getting album: {e}')

    def download_album(self, album_id):
        try:
            album = Album(self.session.proxies, self.session.headers)
            album.set_album_id(album_id)
            album.download_album(self.artist_name)
        except Exception as e:
            print('Error getting album with ID: {}'.format(album_id))
            raise e

    def download_artist_all_songs(self):
        try:
            artist_name = self.artist_json['name']
            total_songs = self.artist_json['topSongs']['total']
            print('Total Songs of the Artist: {0}'.format(total_songs))
            if total_songs % 10 != 0:
                total_requests = (total_songs // 10) + 1
            else:
                total_requests = total_songs // 10
            print('Total requests: {}'.format(total_requests))
            for n_song_page in range(total_requests):
                print('Getting Song page: {0}'.format(n_song_page))
                url = ('https://www.saavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails'
                       '&artistId={0}&n_song=10&page={1}').format(
                    self.artist_id, n_song_page)
                response = self.session.get(url)  # Change made here
                self.artist_json = response.json()
                self.artist_json = json.loads(self.artist_json)
                songs_json = self.artist_json['topSongs']  # A dict with key songs having at most 10 songs
                manager = Manager()
                manager.download_songs(songs_json, artist_name=artist_name)
        except Exception as e:
            print(str(e))
            print('No songs found for the artist')

    def start_download(self):
        self.get_artist()
