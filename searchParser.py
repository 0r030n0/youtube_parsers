import requests, logging, json, re, csv, os
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
		###########ANTI AD###########
		itemSection = 0
		content_types = ['channelRenderer', 'playlistRenderer', 'movieRenderer', 'videoRenderer', 'messageRenderer', 'radioRenderer', 'horizontalCardListRenderer']
		contents_found = False
		while True:
			section = contents[itemSection]
			if 'itemSectionRenderer' in section:
				itemContents = section['itemSectionRenderer']['contents']
				for content_type in content_types:
					if content_type in itemContents[0].keys():
						contents = itemContents
						contents_found = True
						break
				if contents_found:
					break
				itemSection += 1
		##############################
		for content in contents:
			if 'channelRenderer' in content:
				channel_title = content['channelRenderer']['title']['simpleText']
				channelId = content['channelRenderer']['channelId']
				channel_url = 'https://www.youtube.com/channel/' + channelId
				if 'Topic' not in channel_title:
					if 'videoCountText' in content['channelRenderer']:
						video_count = content['channelRenderer']['videoCountText']['runs'][0]['text'].replace(',', '')
						video_count = int(re.findall(r'\d+', video_count)[0])
					else:
						video_count = 0
				else:
					video_count = None

				if 'subscriberCountText' in content['channelRenderer']:
					channel_subscribers = content['channelRenderer']['subscriberCountText']['simpleText'].replace(',', '')
					if 'M' in channel_subscribers:
						channel_subscribers = int(float(re.findall(r'(\d+\.\d+|\d+)', channel_subscribers)[0]) * 1000000)
					elif 'K' in channel_subscribers:
						channel_subscribers = int(float(re.findall(r'(\d+\.\d+|\d+)', channel_subscribers)[0]) * 1000)
					else:
						channel_subscribers = int(re.findall(r'\d+', channel_subscribers)[0])
				else:
					channel_subscribers = 0

				self.result['channels'][channelId] = {}
				self.result['channels'][channelId]['title'] = channel_title
				self.result['channels'][channelId]['url'] = channel_url
				self.result['channels'][channelId]['video_count'] = video_count
				self.result['channels'][channelId]['subscribers'] = channel_subscribers

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
					if 'viewCountText' in content['videoRenderer']:
						try:
							video_views = content['videoRenderer']['viewCountText']['simpleText'].replace(',', '')
							views_match = re.search(r'[0-9]+', video_views)
							if views_match:
								video_views = int(views_match.group(0).replace(',', ''))
							elif video_views == 'No views':
								video_views = 0
						except:
							video_views = content['videoRenderer']['viewCountText']['runs'][0]['text'].replace(',', '')
							views_match = re.search(r'[0-9]+', video_views)
							if views_match:
								video_views = int(views_match.group(0))
							else:
								video_views = 0
					else:
						video_views = None
				video_owner = content['videoRenderer']['ownerText']['runs'][0]['text']
				self.result['videos'][videoId]['title'] = video_title
				self.result['videos'][videoId]['url'] = video_url
				self.result['videos'][videoId]['published_time'] = video_published_time
				self.result['videos'][videoId]['video_length'] = video_length
				self.result['videos'][videoId]['views'] = video_views
				self.result['videos'][videoId]['video_owner'] = video_owner
			elif 'playlistRenderer' in content:
				playlistId = content['playlistRenderer']['playlistId']
				playlist_url = 'https://www.youtube.com/playlist?list=' + playlistId
				playlist_title = content['playlistRenderer']['title']['simpleText']
				playlist_video_count = int(content['playlistRenderer']['videoCount'])
				self.result['playlists'][playlistId] = {}
				self.result['playlists'][playlistId]['title'] = playlist_title
				self.result['playlists'][playlistId]['url'] = playlist_url
				self.result['playlists'][playlistId]['video_count'] = playlist_video_count
			elif 'movieRenderer' in content:
				movieId = content['movieRenderer']['videoId']
				movie_url = 'https://www.youtube.com/watch?v=' + movieId
				movie_title = content['movieRenderer']['title']['runs'][0]['text']
				movie_duration = content['movieRenderer']['lengthText']['simpleText']
				metadata = ''
				try:
					for info in content['movieRenderer']['topMetadataItems']:
						metadata += info['simpleText'] + '\n'
				except KeyError:
					pass
				try:
					for info in content['movieRenderer']['bottomMetadataItems']:
						metadata += info['simpleText'] + '\n'
				except KeyError:
					pass
				self.result['movies'][movieId] = {}
				self.result['movies'][movieId]['title'] = movie_title
				self.result['movies'][movieId]['url'] = movie_url
				self.result['movies'][movieId]['duration'] = movie_duration
				self.result['movies'][movieId]['metadata'] = metadata
			elif 'radioRenderer' in content:
				radio_title = content['radioRenderer']['title']['simpleText']
				radioId = content['radioRenderer']['playlistId']
				video_count = content['radioRenderer']['videoCountText']['runs'][0]['text']
				radio_url = 'https://www.youtube.com' + content['radioRenderer']['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url']
				self.result['radios'][radioId] = {}
				self.result['radios'][radioId]['title'] = radio_title
				self.result['radios'][radioId]['url'] = radio_url
				self.result['radios'][radioId]['video_count'] = video_count
			elif 'messageRenderer' in content:
				if content['messageRenderer']['text']['runs'][0]['text'] == 'No more results':
					needReturn = True
		logger.info('*' * 50)
		logger.info('Current videos count: ' + str(len(self.result['videos'])))
		logger.info('Current playlists count: ' + str(len(self.result['playlists'])))
		logger.info('Current movies count: ' + str(len(self.result['movies'])))
		logger.info('Current channels count: ' + str(len(self.result['channels'])))
		logger.info('Current radios count: ' + str(len(self.result['radios'])))
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
		logger.info(' - Channels : ' + str(len(self.result['channels'])))
		logger.info(' - Movies : ' + str(len(self.result['movies'])))
		logger.info(' - Radios : ' + str(len(self.result['radios'])))
		return self.result

if __name__ == '__main__':
	search_text = input('Enter search text: ').strip()
	searchParser = SearchParser(search_text, proxies)
	result = searchParser.start()
	datetime_stmp = str(datetime.now().strftime('%Y-%m-%d %H-%M'))
	folder_name = 'search parser ' + datetime_stmp
	os.mkdir(folder_name)
	channels = result['channels']
	videos = result['videos']
	radios = result['radios']
	playlists = result['playlists']
	movies = result['movies']

	with open('./' + folder_name + '/channels.csv', 'w') as f:
		csv_writer = csv.writer(f)
		csv_writer.writerow(['channelId', 'title', 'url', 'video_count', 'subscribers'])
	for channelId, metadata in channels.items():
		with open('./' + folder_name + '/channels.csv', 'a') as f:
			csv_writer = csv.writer(f)
			csv_writer.writerow([channelId, metadata['title'], metadata['url'], metadata['video_count'], metadata['subscribers']])

	with open('./' + folder_name + '/videos.csv', 'w') as f:
		csv_writer = csv.writer(f)
		csv_writer.writerow(['videoId', 'title', 'url', 'published_time', 'video_length', 'views', 'video_owner'])
	for videoId, metadata in videos.items():
		with open('./' + folder_name + '/videos.csv', 'a') as f:
			csv_writer = csv.writer(f)
			csv_writer.writerow([videoId, metadata['title'], metadata['url'], metadata['published_time'], metadata['video_length'], metadata['views'], metadata['video_owner']])

	with open('./' + folder_name + '/radios.csv', 'w') as f:
		csv_writer = csv.writer(f)
		csv_writer.writerow(['radioId', 'title', 'url', 'video_count'])
	for radioId, metadata in radios.items():
		with open('./' + folder_name + '/radios.csv', 'a') as f:
			csv_writer = csv.writer(f)
			csv_writer.writerow([radioId, metadata['title'], metadata['url'], metadata['video_count']])

	with open('./' + folder_name + '/playlists.csv', 'w') as f:
		csv_writer = csv.writer(f)
		csv_writer.writerow(['playlistId', 'title', 'url', 'video_count'])
	for playlistId, metadata in playlists.items():
		with open('./' + folder_name + '/playlists.csv', 'a') as f:
			csv_writer = csv.writer(f)
			csv_writer.writerow([playlistId, metadata['title'], metadata['url'], metadata['video_count']])

	with open('./' + folder_name + '/movies.csv', 'w') as f:
		csv_writer = csv.writer(f)
		csv_writer.writerow(['movieId', 'title', 'url', 'duration', 'metadata'])
	for movieId, metadata in movies.items():
		with open('./' + folder_name + '/movies.csv', 'a') as f:
			csv_writer = csv.writer(f)
			csv_writer.writerow([movieId, metadata['title'], metadata['url'], metadata['duration'], metadata['metadata']])



