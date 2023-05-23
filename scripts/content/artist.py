import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
from concurrent.futures import ThreadPoolExecutor

from .album import Album
from ..download_manager import Manager

class Artist():
    def __init__(self, proxies, headers, args, url=None):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.session = requests.Session()
        self.session.proxies = proxies
        self.session.headers = headers
        self.args = args
        self.artistID = None
        self.artist_name = None
        self.artist_json = []
        self.album_IDs_artist = []
        self.url = url

    def getArtistID(self, url=None):
        if url:
            self.url = url
        token = self.url.split("/")[-1]
        self.url = "https://www.jiosaavn.com/api.php?__call=webapi.get&token={0}&type=artist&p=&n_song=10&n_album=14&sub_type=&category=&sort_order=&includeMetaTags=0&ctx=web6dot0&api_version=4&_format=json&_marker=0".format(token)
        response = self.session.get(self.url)
        self.artistID = response.json()["artistId"]
        return self.artistID

    def setArtistID(self, artistID):
        self.artistID = artistID

    def getArtistAlbumsIDs(self):
        self.artist_json = self.getArtistJson()
        try:
            self.artist_name = self.artist_json['name']
            total_albums = self.artist_json['topAlbums']['total']
            print('Total Albums of the Artist: {0}'.format(total_albums))
            if total_albums % 10 != 0:
                total_requests = (total_albums // 10) + 1
            else:
                total_requests = total_albums // 10
            print('Total requests: {}'.format(total_requests))

            # Create a ThreadPoolExecutor for making requests concurrently.
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Create a list to hold the future results.
                futures = []

                for n_album_page in range(total_requests):
                    print('Getting Album page: {0}'.format(n_album_page))
                    url = 'https://www.saavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails&artistId={0}&n_album=10&page={1}'.format(self.artistID, n_album_page)
                    futures.append(executor.submit(self.session.get, url))

                for future in futures:
                    try:
                        response = future.result()
                        self.artist_json = [x for x in response.text.splitlines() if x.strip().startswith('{')][0]
                        self.artist_json = json.loads(self.artist_json)
                        n_albums_in_page = len(self.artist_json['topAlbums']['albums'])
                        for i in range(n_albums_in_page):
                            albumId = self.artist_json['topAlbums']['albums'][i]['albumid']
                            self.album_IDs_artist.append(albumId)
                    except Exception as e:
                        print(str(e))
                        print('No albums found for the artist : {0}'.format(self.artist_name))
                        exit()
        except Exception as e:
            print(str(e))
            print('No albums found for the artist : {0}'.format(self.artist_name))
            exit()

        print('Total Number of Albums found: {0}'.format(len(self.album_IDs_artist)))
        return (self.album_IDs_artist, self.artist_name)


    def getArtist(self):
        try:
            self.getArtistID()
            self.artist_json = self.getArtistJson()
        except Exception as e:
            print(str(e))
            print('Please check that the entered URL is for an Artist')
            exit()
        if self.args.song:
            print('Downloading all Artist songs')
            self.downloadArtistAllSongs()
        else:
            print('Downloading all albums for the Artist')
            self.getArtistAlbumsIDs()
            self.downloadArtistAllAlbums()

    def getArtistJson(self):
        url = 'https://www.jiosaavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails&artistId={0}'.format(self.artistID)
        response = self.session.get(url)
        artist_json = [x for x in response.text.splitlines() if x.strip().startswith('{')][0]
        artist_json = json.loads(artist_json)
        return artist_json

    def downloadArtistAllAlbums(self):
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            if self.album_IDs_artist:
                for albumId in self.album_IDs_artist:
                    futures.append(executor.submit(self.downloadAlbum, albumId))
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        print(f'Error getting album: {e}')

    def downloadAlbum(self, albumId):
        try:
            album = Album(self.session.proxies, self.session.headers)
            album.setAlbumID(albumId)
            album.downloadAlbum(self.artist_name)
        except Exception as e:
            print('Error getting album with ID: {}'.format(albumId))
            raise e

    def downloadArtistAllSongs(self):
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
                url = 'https://www.saavn.com/api.php?_marker=0&_format=json&__call=artist.getArtistPageDetails&artistId={0}&n_song=10&page={1}'.format(self.artistID, n_song_page)
                response = self.session.get(url)  # Change made here
                self.artist_json = [x for x in response.text.splitlines() if x.strip().startswith('{')][0]
                self.artist_json = json.loads(self.artist_json)
                songs_json = self.artist_json['topSongs']   # A dict with key songs having at most 10 songs
                manager = Manager()
                manager.downloadSongs(songs_json, artist_name=artist_name)
        except Exception as e:
            print(str(e))
            print('No songs found for the artist')

    def start_download(self):
        self.getArtist()