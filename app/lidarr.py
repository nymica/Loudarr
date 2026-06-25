import requests


class LidarrClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key})

    def _url(self, endpoint):
        return f"{self.base_url}/api/v1/{endpoint}"

    def _get(self, endpoint, params=None):
        resp = self.session.get(self._url(endpoint), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint, data):
        resp = self.session.post(self._url(endpoint), json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def test_connection(self):
        try:
            self._get('system/status')
            return True, None
        except requests.exceptions.ConnectionError:
            return False, 'Could not connect — check the URL'
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, 'Unauthorized — check the API key'
            return False, f'HTTP {e.response.status_code}'
        except Exception as e:
            return False, str(e)

    def get_artists(self):
        return self._get('artist')

    def get_quality_profiles(self):
        return self._get('qualityprofile')

    def get_metadata_profiles(self):
        return self._get('metadataprofile')

    def get_root_folders(self):
        return self._get('rootfolder')

    def lookup_artist(self, term):
        return self._get('artist/lookup', {'term': term})

    def add_artist(self, payload):
        return self._post('artist', payload)

    def get_wanted(self, page=1, page_size=100):
        return self._get('wanted/missing', {'page': page, 'pageSize': page_size})

    def refresh_artist(self, artist_id):
        return self._post('command', {'name': 'RefreshArtist', 'artistId': artist_id})
