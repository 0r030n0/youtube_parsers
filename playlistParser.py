import requests, logging, json, re, csv


#USER CONFIG
proxies = {
	#'https': 'ip:port', #you comment this line for disabling proxy
}


#logger settings
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fileFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt='[%(asctime)s][%(module)s.py][%(funcName)s][%(levelname)s] %(message)s ')
consoleFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt = '[%(asctime)s] %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(consoleFMT)
logger.addHandler(stream_handler)


class PlaylistParser:

	def __init__(self, playlist_url, proxies={}):
		self.headers = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
		'x-youtube-client-name': '1',
		'x-youtube-client-version': '2.20200605.00.00',
		}
		self.playlist_url = playlist_url
		self.session = requests.Session()
		self.result = {}
		self.proxies = proxies
		self.deleted = 0
		self.playlistTitle = ''

	def url_checker(self):
		self.playlist_url = self.playlist_url.strip()
		if 'https://' not in self.playlist_url and 'youtube.com' in self.playlist_url:
			logger.debug('Missing schema...')
			self.playlist_url = 'https://' + self.playlist_url

	def get_first_page(self):
		logger.debug('Requesting to YouTube to get first page')
		page = self.session.get(self.playlist_url, proxies=self.proxies)
		if page.status_code != 200:
			logger.debug('status code: ' + str(page.status_code))
			page = self.get_first_page()
		if 'pl-video' in page.text:
			logger.debug('incorrect page format')
			page = self.get_first_page()	
		return page

	def parse_first_page(self, page):
		logger.debug('Playlist scraping')
		json_fragment = re.findall(r'\{"responseContext".+"\}{3}', page)[0]
		json_resp = json.loads(json_fragment)
		playlist_info = json_resp['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']
		contents = playlist_info['contents']
		self.playlistTitle = json_resp['metadata']['playlistMetadataRenderer']['title']
		logger.info('Playlist Title: ' + self.playlistTitle)
		try:
			continue_token = playlist_info['continuations'][0]['nextContinuationData']['continuation']
		except:
			continue_token = ''
			logger.debug('continue token not found!')
		self.parse_contents(contents)

		return continue_token

	def parse_contents(self, contents):
		for content in contents:
			videoId = content['playlistVideoRenderer']['videoId']
			url = 'https://www.youtube.com/watch?v=' + videoId
			if 'runs' in content['playlistVideoRenderer']['title'] or videoId in self.result:
				self.deleted += 1
				logger.debug(url + " was skipped. Perhaps it is private, deleted, duplicated or age restriction")
			else:
				videoTitle = content['playlistVideoRenderer']['title']['simpleText']
				videoDuration = content['playlistVideoRenderer']['lengthSeconds']
				self.result[videoId] = {}
				self.result[videoId]['title'] = videoTitle
				self.result[videoId]['url'] = url
				self.result[videoId]['duration'] = videoDuration

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
			self.parse_contents(pl_continuation['contents'])
		logger.info('Current urls count: {}'.format(str(len(self.result))))
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
			logger.info('Current urls count: {}'.format(str(len(self.result))))
			if continue_token == '':
				logger.info('All urls were received. Total/Passed/Skipped: {}/{}/{}'.format(str(len(self.result) + self.deleted), str(len(self.result)), str(self.deleted)))
			elif len(continue_token) == 80:
				self.load_more(continue_token)
				logger.info('All urls were received. Total/Passed/Skipped: {}/{}/{}'.format(str(len(self.result) + self.deleted), str(len(self.result)), str(self.deleted)))
			return self.result
		except requests.exceptions.ProxyError:
			logger.error('Proxy Error')
			exit()
		except requests.exceptions.ConnectionError:
			logger.error('Connection Error')
			exit()


if __name__ == '__main__':
	playlist_url = input('Enter playlist_url: ')

	q = input('Do you want to see log file after executing? (y/n): ').strip().lower()
	if q == 'y':
		file_handler = logging.FileHandler('./playlistParser.logs', mode='w')
		file_handler.setLevel(logging.DEBUG)
		file_handler.setFormatter(fileFMT)
		logger.addHandler(file_handler)

	parser = PlaylistParser(playlist_url, proxies)
	result = parser.start()
	with open('playlistParser.csv', 'w') as f:
		writer = csv.writer(f)
		writer.writerow(['title', 'url', 'videoId', 'videoDuration(secs)'])
		for videoId, videoData in result.items():
			writer.writerow([videoData['title'], videoData['url'], videoId, videoData['duration']])
			
	while True:
		q = input('Do you want to save urls to playlistVideos.txt? (y/n): ').strip().lower()
		if q == 'y':
			with open('playlistVideos.txt', 'w') as f:
				for videoData in result.values():
					f.write(videoData['url'] + '\n')
			exit()
		elif q == 'n':
			exit()
		else:
			pass