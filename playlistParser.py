import requests, logging, json


#USER CONFIG
proxies = {
	'https': '54.37.154.101:80', #you comment this line for disabling proxy
}


#logger settings
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fileFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt='[%(asctime)s][%(module)s.py][%(funcName)s][%(levelname)s] %(message)s ')
consoleFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt = '[%(asctime)s] %(message)s')
file_handler = logging.FileHandler('./searchVideoParser.logs', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(fileFMT)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(consoleFMT)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class PlaylistParser:

	def __init__(self, playlist_url, proxies={}):
		self.headers = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
		'x-youtube-client-name': '1',
		'x-youtube-client-version': '2.20200605.00.00',
		'accept-language': 'en-US,en;q=0.9',
		}
		self.playlist_url = playlist_url
		self.session = requests.Session()
		self.urls = []
		self.proxies = proxies
		self.deleted = 0

	def url_checker(self):
		self.playlist_url = self.playlist_url.strip()
		if 'https://' not in self.playlist_url and 'youtube.com' in self.playlist_url:
			logger.debug('Missing schema...')
			self.playlist_url = 'https://' + self.playlist_url

	def get_first_page(self):
		accept_language = {'accept-language': 'en-US,en;q=0.9'}
		logger.debug('Requesting to YouTube to get first page')
		page = self.session.get(self.playlist_url, headers=accept_language, proxies=self.proxies)
		if page.status_code != 200:
			page = self.get_first_page()
		if 'pl-video' in page.text:
			page = self.get_first_page()	
		return page

	def parse_first_page(self, page):
		logger.debug('Playlist scraping')
		json_fragment = page.split('window["ytInitialData"] = ')[1].split(';\n    window["ytInitialPlayerResponse"] = null;')[0]
		json_resp = json.loads(json_fragment)
		playlist_info = json_resp['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']
		contents = playlist_info['contents']

		try:
			continue_token = playlist_info['continuations'][0]['nextContinuationData']['continuation']
		except:
			continue_token = ''
			logger.debug('continue token not found!')

		for content in contents:
			videoId = content['playlistVideoRenderer']['videoId']
			url = 'https://www.youtube.com/watch?v=' + videoId
			self.urls.append(url)

		return continue_token

	def load_more(self, continue_token):
		service = 'https://www.youtube.com/browse_ajax'
		params = {
		"continuation": continue_token
		}
		logger.debug('Loading new content.')
		new_content = self.session.post(service, params=params, headers=self.headers, proxies=self.proxies)
		while new_content.status_code != 200:
			logger.debug(new_content.status_code)
			logger.debug('Failed to load new content. Trying again.')
			r = self.session.post(service, params=params, headers=self.headers, proxies=self.proxies)
		new_content = new_content.json()[1]

		new_content_response = new_content['response']
		pl_continuation = new_content_response["continuationContents"]["playlistVideoListContinuation"]
		if "continuationContents" in new_content_response and "continuations" in pl_continuation:
			continue_token = pl_continuation["continuations"][0]["nextContinuationData"]["continuation"]
			logger.debug('continue_token: ' + continue_token)
		else:
			continue_token = ''
			logger.debug("continue_token wasn't found")
		if "continuationContents" in new_content_response and "contents" in pl_continuation:
			logger.debug('contents were found')
			logger.debug('parsing contents')
			for content in pl_continuation["contents"]:
				url = 'https://www.youtube.com/watch?v=' + content['playlistVideoRenderer']['videoId']
				if 'runs' in content['playlistVideoRenderer']['title']:
					self.deleted += 1
					logger.debug(url + " was skipped. Perhaps it is private, deleted or age restriction")
				else:
					self.urls.append(url)

		logger.info('Current urls count: {}'.format(str(len(self.urls))))
		if continue_token != '':
			self.load_more(continue_token)

	def start(self):
		if self.proxies != {}:
			logger.info('Proxy: {}'.format(self.proxies['https']))
		else:
			logger.info('Proxy: no proxy')
		try:
			logger.info('Checking url')
			self.url_checker()
			logger.info('Receiving first page')
			page = self.get_first_page()
			logger.info('Parsing first page')
			continue_token = self.parse_first_page(page.text)
			logger.info('Current urls count: {}'.format(str(len(self.urls))))
			if continue_token == '':
				logger.info('All urls were received. Total/Passed/Skipped: {}/{}/{}'.format(str(len(self.urls) + self.deleted), str(len(self.urls)), str(self.deleted)))
			elif len(continue_token) == 80:
				self.load_more(continue_token)
				logger.info('All urls were received. Total/Passed/Skipped: {}/{}/{}'.format(str(len(self.urls) + self.deleted), str(len(self.urls)), str(self.deleted)))
			return self.urls
		except requests.exceptions.ProxyError:
			logger.error('Proxy Error')
			exit()
		except requests.exceptions.ConnectionError:
			logger.error('Connection Error')
			exit()


if __name__ == '__main__':
	playlist_url = input('Enter playlist_url: ')
	parser = PlaylistParser(playlist_url, proxies)
	urls = parser.start()
	with open('playlistParser.txt', 'w') as f:
		for url in urls:
			f.write(url + '\n')