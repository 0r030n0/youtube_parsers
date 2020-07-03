import requests, logging, json, re, csv
from urllib.parse import quote
from datetime import datetime


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

class SearchParser:
	def __init__(self, search_text, proxies={}):
		self.headers = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
		'x-youtube-client-name': '1',
		'x-youtube-client-version': '2.20200605.00.00',
		'Accept-Language': 'en-US,en;q=0.5'
		}
		self.proxies = proxies
		self.language = {'Accept-Language': 'en-US,en;q=0.5'}
		self.search_quote = quote(search_text)
		self.search_text = search_text
		self.page_template = 'https://www.youtube.com/results?search_query={}&page={}'
		self.session = requests.Session()
		self.result = {}
		self.result['videos'] = {}
		self.result['channels'] = {}
		self.result['playlists'] = {}
		self.result['movies'] = {}
		self.result['radios'] = {}

	def get_json_content(self, page_number):
		url = self.page_template.format(self.search_quote, page_number)
		while True:
			try:
				page = self.session.get(url, headers=self.language, proxies=self.proxies).text
				json_text = re.findall(r'(\{"responseContext".+\{\}\}\}|\{"responseContext".+"\]\})', page)[0]
				break
			except:
				pass
		json_content = json.loads(json_text)
		return json_content

	def parse_json_content(self, json_content):
		contents = json_content['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
		needReturn = False
		itemSection = 0
		while True:
			section = contents[itemSection]['itemSectionRenderer']['contents']
			if 'promotedSparklesTextSearchRenderer' in section[0]:
				itemSection += 1
			else:
				contents = section
				break
		for content in contents:
			if 'channelRenderer' in content:
				logger.debug('channel found')
			elif 'videoRenderer' in content:
				videoId = content['videoRenderer']['videoId']
				self.result['videos'][videoId] = {}
				video_title = content['videoRenderer']['title']['runs'][0]['text']
				video_url = 'https://www.youtube.com/watch?v=' + videoId
				if 'upcomingEventData' in content['videoRenderer']:
					time_stamp = int(content['videoRenderer']['upcomingEventData']['startTime'])
					scheduled_time = datetime.utcfromtimestamp(time_stamp).strftime('%Y/%m/%d %H:%M')
					video_published_time = 'scheduled for ' + scheduled_time
				else:
					try:
						video_published_time = content['videoRenderer']['publishedTimeText']['simpleText']
					except:
						video_published_time = 'music/live/unknown'
				try:
					video_length = content['videoRenderer']['lengthText']['simpleText']
				except:
					video_length = 'live/unknown'
				if 'upcomingEventData' in content['videoRenderer']:
					video_views = 0
				else:
					try:
						video_views = content['videoRenderer']['viewCountText']['simpleText']
						views_match = re.search(r'[0-9,]+', video_views)
						if views_match:
							video_views = int(views_match.group(0).replace(',', ''))
						elif video_views == 'No views':
							video_views = 0
					except:
						video_views = int(content['videoRenderer']['viewCountText']['runs'][0]['text'].replace(',', ''))
				video_owner = content['videoRenderer']['ownerText']['runs'][0]['text']
				self.result['videos'][videoId]['title'] = video_title
				self.result['videos'][videoId]['url'] = video_url
				self.result['videos'][videoId]['published_time'] = video_published_time
				self.result['videos'][videoId]['video_length'] = video_length
				self.result['videos'][videoId]['views'] = video_views
				self.result['videos'][videoId]['video_owner'] = video_owner
			elif 'horizontalCardListRenderer' in content:
				logger.debug('cardlist found')
			elif 'shelfRenderer' in content:
				logger.debug('shelf found')
			elif 'playlistRenderer' in content:
				playlistId = content['playlistRenderer']['playlistId']
				playlist_url = 'https://www.youtube.com/playlist?list=' + playlistId
				playlist_title = content['playlistRenderer']['title']['simpleText']
				playlist_video_count = int(content['playlistRenderer']['videoCount'])
				self.result['playlists'][playlistId] = {}
				self.result['playlists'][playlistId]['url'] = playlist_url
				self.result['playlists'][playlistId]['title'] = playlist_title
				self.result['playlists'][playlistId]['video_count'] = playlist_video_count
			elif 'movieRenderer' in content:
				logger.debug('movie found')
			elif 'radioRenderer' in content:
				logger.debug('radio found')
			elif 'showingResultsForRenderer' in content:
				logger.debug('showingResultsForRenderer')
			elif 'searchPyvRenderer' in content:
				logger.info('searchPyvRenderer found')
			elif 'messageRenderer' in content:
				if content['messageRenderer']['text']['runs'][0]['text'] == 'No more results':
					needReturn = True
			else:
				logger.info(content)
		logger.info('Current videos count: ' + str(len(self.result['videos'])))
		logger.info('Current playlists count: ' + str(len(self.result['playlists'])))
		if needReturn:
			return 'stop'
	def start(self):
		logger.info('Proxy: ' + self.proxies.get('https', 'no proxy'))
		page_number = 1
		result = None
		logger.info('Parsing...')
		while result == None:
			json_content = self.get_json_content(str(page_number))
			result = self.parse_json_content(json_content)
			page_number += 1
		logger.info('Search was parsed.')
		logger.info(' - Videos : ' + str(len(self.result['videos'])))
		logger.info(' - Playlists : ' + str(len(self.result['playlists'])))
		#logger.info(' - Channels : ' + str(len(self.result['channels'])))
		#logger.info(' - Movies : ' + str(len(self.result['movies'])))
		#logger.info(' - Radios : ' + str(len(self.result['radios'])))

if __name__ == '__main__':
	search_text = input('Enter search text: ').strip()
	searchParser = SearchParser(search_text, proxies)
	searchParser.start()
