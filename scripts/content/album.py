import requests
import urllib3

urllib3.disable_warnings()
import html

from ..download_manager import Manager


class Album:
    def __init__(self, proxies, headers, url=None):
        self.list_count = None
        self.proxies = proxies
        self.headers = headers
        self.album_id = None
        self.album_name = ''
        self.songs_json = []
        self.url = url

    def get_album_id(self, url=None):
        if url:
            input_url = url
        else:
            input_url = self.url
        token = input_url.split("/")[-1]
        input_url = ("https://www.jiosaavn.com/api.php?__call=webapi.get&token={"
                     "0}&type=album&includeMetaTags=0&ctx=web6dot0&api_version=4&_format=json&_marker=0").format(
            token)
        try:
            res = requests.get(input_url, proxies=self.proxies, headers=self.headers)
        except Exception as e:
            print('Error accessing website error: {0}'.format(e))
            exit()
        try:
            content_json = res.json()
            self.album_id = content_json["id"]
            self.list_count = content_json["list_count"]
        except Exception as e:
            print("Unable to get album_id: {0}".format(e))
        return self.album_id

    def setAlbumID(self, album_id):
        self.album_id = album_id

    def get_album(self, album_id=None):
        if album_id is None:
            album_id = self.album_id
        response = requests.get(
            'https://www.jiosaavn.com/api.php?_format=json&__call=content.getAlbumDetails&albumid={0}'.format(album_id),
            verify=False, proxies=self.proxies, headers=self.headers)
        if response.status_code == 200:
            self.songs_json = response.json()
        return self.songs_json

    def download_album(self, artist_name=''):
        if self.album_id is not None:
            print("Initiating Album Download")
            manager = Manager()
            self.get_album()
            if artist_name:
                manager.download_songs(self, artist_name=artist_name)
            else:
                manager.download_songs(self)

    def start_download(self):
        self.get_album_id()
        self.download_album()
