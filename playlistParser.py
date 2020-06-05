#0r030n0
import logging
from bs4 import BeautifulSoup as bs
import requests
import json
import sys, re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fileFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt='[%(asctime)s][%(module)s.py][%(funcName)s][%(levelname)s] %(message)s ')
consoleFMT = logging.Formatter(datefmt='%y-%m-%d %H:%M:%S', fmt = '[%(asctime)s] %(message)s')
file_handler = logging.FileHandler('./playlistParser.logs', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(fileFMT)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(consoleFMT)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

class Parser:
	def __init__(self, pl_url):
		self.pl_url = pl_url
		self.urls = []
		self.session = requests.Session()
		self.headers = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36",
		'x-youtube-client-name': '1',
		'x-youtube-client-version': '2.20200429.03.00',
		}
		self.deleted = 0


	def remove_signs(self, pl_title: str): #thanks to Kamil Slowikowski (slowkow)
		pl_title = pl_title.replace('\n', '').strip()
		emoji_pattern = re.compile("["
			u"\U0001F600-\U0001F64F" #emoticons
			u"\U0001F300-\U0001F5FF" #symbols & pictographs
			u"\U0001F680-\U0001F6FF" #transport & map symbols
			u"\U0001F1E0-\U0001F1FF" #flags (iOS)
			u"\U00002702-\U000027B0"
			#u"\U000024C2-\U0001F251" #japanese characters
			"]+", flags = re.UNICODE)
		pl_title = emoji_pattern.sub(r'', pl_title)
		self.pl_title = pl_title
		logger.info('Playlist title: ' + self.pl_title)


	def parse_pl_page(self, pl_page):
		try:
			logger.debug('Playlist scraping')
			soup = bs(pl_page, 'lxml')
			pl_header_details = soup.find('ul', attrs={'class': 'pl-header-details'})
			for pl_header_detail in pl_header_details:
				if 'videos' in pl_header_detail.getText():
					self.total_video = int(pl_header_detail.getText().strip(' videos').replace(',', ''))
			pl_title = soup.find('h1', attrs={'class': 'pl-header-title'}).getText()
			self.remove_signs(pl_title)
			pl_video_container = soup.select('tr.pl-video')
			for pl_video_element in pl_video_container:
				pl_video_url = 'https://www.youtube.com' + pl_video_element.a['href'].split('&list')[0]
				self.urls.append(pl_video_url)
			if len(self.urls) > 0:
				logger.info('{:.1%} of urls were parsed.'.format(len(self.urls) / self.total_video))
				return 'success'
			else:
				logger.debug('Failed to find urls. Trying again.')
				return 'restart'
		except TypeError:
			return 'restart'
		except Exception as unexpected_error:
			raise Exception(unexpected_error)


	def parse_token(self, token_page):
		try:
			continue_token = token_page.text.split('"nextContinuationData":{"continuation":"')[1].split('","')[0]
			logger.debug('continue_token was found. Length: ' + str(len(continue_token)))
		except:
			continue_token = ''
			logger.debug("continue_token wasn't found.")
		return continue_token


	def load_more(self, continue_token):
		service = 'https://www.youtube.com/browse_ajax'
		params = {
		"ctoken": continue_token,
		"continuation": continue_token
		}
		logger.debug('Getting new data.')
		new_data = self.session.post(service, params=params, headers=self.headers)
		while new_data.status_code != 200:
			logger.debug(new_data.status_code)
			logger.debug('Failed to get new data. Trying again.')
			r = requests.post(service, params=params, headers=self.headers)
		logger.debug('New data was successfully received')
		new_data = new_data.json()[1]
		return new_data


	def parse_more(self, new_data):
		logger.debug('Parsing new data')
		new_data_response = new_data['response']
		pl_continuation = new_data_response["continuationContents"]["playlistVideoListContinuation"]
		if "continuationContents" in new_data_response and "continuations" in pl_continuation:
			continue_token = pl_continuation["continuations"][0]["nextContinuationData"]["continuation"]
			logger.debug('continue_token: ' + continue_token)
		else:
			continue_token = ''
			logger.debug("continue_token wasn't found")
		if "continuationContents" in new_data_response and "contents" in pl_continuation:
			logger.debug('contents were found')
			logger.debug('parsing contents')
			for content in pl_continuation["contents"]:
				url = 'https://www.youtube.com/watch?v=' + content['playlistVideoRenderer']['videoId']
				if 'runs' in content['playlistVideoRenderer']['title']:
					self.deleted += 1
					logger.debug(url + " was skipped. Perhaps it is private, deleted or age restriction")
				else:
					self.urls.append(url)
			logger.info('{:.1%} of urls were parsed'.format(len(self.urls) / self.total_video))
		return continue_token


	def start(self):
		if 'https://' not in self.pl_url:
			self.pl_url = 'https://' + self.pl_url
		try:
			accept_language = {'accept-language': 'en-US,en;q=0.9'}
			logger.debug('Requesting to YouTube to get page')
			pl_page = self.session.get(self.pl_url, headers=accept_language)
			while pl_page.status_code != 200:
				logger.debug('Response: ' + str(pl_page.status_code))
				logger.debug('Failed to request to YouTube. Trying to fix')
				pl_page = requests.get(self.pl_url, headers=accept_language)
				if pl_page.status_code == 200:
					logger.debug('The issue was successfully resolved')

			parse_status = self.parse_pl_page(pl_page.text)
			while parse_status == 'restart':
				logger.warning('There is nothing in the playlist. Trying to fix')
				pl_page = requests.get(self.pl_url, headers=accept_language)
				parse_status = self.parse_pl_page(pl_page.text)
				if parse_status == 'success':
					logger.info('The issue was successfully resolved')
				
			logger.debug('Requesting to YouTube to get token page')
			token_page = self.session.get(self.pl_url, headers=self.headers)
			while token_page.status_code != 200:
				logger.warning('Failed to request to token page. Trying to fix.')
				token_page = requests.get(self.pl_url, headers=self.headers)
				if token_page.status_code == 200:
					logger.info('The issue was successfully resolved')

			continue_token = self.parse_token(token_page)
			if continue_token != '':
				while continue_token != '':
					new_data = self.load_more(continue_token)
					continue_token = self.parse_more(new_data)
				logger.info('All urls were successfully received')
			else:
				logger.info('All urls were successfully received')
			logger.info('{} urls were parsed.'.format(len(self.urls)))
			logger.info("{} urls were skipped. More information in playlistParser.logs".format(self.deleted))
			return self.urls, len(self.urls), self.pl_title
		except requests.exceptions.ConnectionError:
			logger.critical('ConnectionError: Internet connection lost.')
			sys.exit()
		except (requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema):
			logger.critical('Invalid url! Enter the url in format: youtube.com/******************')
			sys.exit()

if __name__ == '__main__':
	playlist_url = input('Enter playlist url: ')
	parser = Parser(playlist_url)
	urls, total, playlist_name = parser.start()
	with open('playlistParser.txt', 'a') as f:
		for url in urls:
			f.write(url + '\n')
