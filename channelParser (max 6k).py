import requests, logging, json, csv
from bs4 import BeautifulSoup as bs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('channelParser')

class Parser:
	def __init__(self, channel_url):
		self.headers = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36",
		'x-youtube-client-name': '1',
		'x-youtube-client-version': '2.20200429.03.00',
		'accept-language': 'en-US,en;q=0.9',
		}
		self.channel_url = channel_url + '/videos'

	def getContainer(self, channel_url):
		response = requests.get(channel_url, headers = {'accept-language': 'en-US,en;q=0.9'})
		soup = bs(response.text, 'lxml')
		page_container = soup.find_all('div', attrs={'class': 'yt-lockup-content'})

		return page_container

	def parseContainer(self, page_container, data, result):
		for page_content in page_container:
			videoId = page_content.a['href'].split('v=')[1]
			if videoId not in result:
				url = 'https://www.youtube.com' + page_content.a['href']
				title = page_content.a['title']
				meta = page_content.find_all('li')
				views = int(meta[0].getText().replace(',', '').strip(' views'))
				published = meta[1].getText()
				data[videoId] = {}
				data[videoId]['title'] = title
				data[videoId]['url'] = url
				data[videoId]['videoId'] = videoId
				data[videoId]['published'] = published
				data[videoId]['views'] = views
			else:
				pass
		logger.info('Parsed {}'.format(str(len(page_container))))

		return data

	def getTokens(self, channel_url):
		permTokens = {}
		r = requests.get(channel_url, headers=self.headers)
		try:
			sessionToken = r.text.split("XSRF_TOKEN\":\"")[1].split("\"")[0]
			tokenForNewData = r.text.split("\"nextContinuationData\":{\"continuation\":\"")[1].split("\"")[0]
			itct = r.text.split("\"{}\",\"clickTrackingParams\":\"".format(tokenForNewData))[1].split("\"")[0]
			permTokens['sessionToken'] = sessionToken
			permTokens['itct'] = itct
		except IndexError:
			logger.error('Tokens for start not found!!!')
			exit()

		return permTokens, tokenForNewData

	def getNewData(self, permTokens, newDataToken):
		params = {"ctoken": newDataToken, "continuation": newDataToken, "itct": permTokens['itct']}
		sessionToken = {"session_token": permTokens['sessionToken']}
		resp = requests.post("https://www.youtube.com/browse_ajax", params=params, headers=self.headers, data=sessionToken)
		jsonContainer = resp.json()[1]

		return jsonContainer

	def parseNewData(self, jsonContainer, data, status, result):
		dataResponse = jsonContainer['response']
		metaContainer = dataResponse["continuationContents"]["gridContinuation"]
		if "continuations" in metaContainer:
			tokenForNewData = metaContainer["continuations"][0]["nextContinuationData"]["continuation"]
		else:
			tokenForNewData = None
			status = False
		if "continuationContents" in dataResponse and "items" in metaContainer:
			attempts = 3
			for item in metaContainer["items"]:
				videoId = item['gridVideoRenderer']['videoId']
				if videoId not in result:
					url = 'https://www.youtube.com/watch?v=' + item['gridVideoRenderer']['videoId']
					try:
						published = item['gridVideoRenderer']['publishedTimeText']['simpleText']
					except:
						published = 'no information'
					try:
						views = item['gridVideoRenderer']['viewCountText']['simpleText'].replace(',', '').strip(' views')
					except:
						views = 'no information'
					title = item['gridVideoRenderer']['title']['simpleText']
					data[videoId] = {}
					data[videoId]['title'] = title
					data[videoId]['url'] = url
					data[videoId]['videoId'] = videoId
					data[videoId]['published'] = published
					data[videoId]['views'] = views
				elif (videoId in result) and (attempts > 0):
					attempts -= 1
				else:
					status = False
		else:
			logger.error('items not found')

		return data, tokenForNewData, status


	def start(self):
		urlToParseNewest = self.channel_url + '?sort=dd'
		urlToParseOldest = self.channel_url + '?sort=da'
		result = {}

		logger.info('Parsing from the beginning')
		dataSortedByNewest = {}
		status = True
		while len(dataSortedByNewest) == 0:
			page_container = self.getContainer(urlToParseNewest)
			dataSortedByNewest = self.parseContainer(page_container, dataSortedByNewest, result)
		permTokens, tokenForNewData = self.getTokens(urlToParseNewest)
		while status:
			jsonContainer = self.getNewData(permTokens, tokenForNewData)
			dataSortedByNewest, tokenForNewData, status = self.parseNewData(jsonContainer, dataSortedByNewest, status, result)
			logger.info('Parsed {}'.format(str(len(dataSortedByNewest))))

		result.update(dataSortedByNewest)
		if len(dataSortedByNewest) >= 2950:
			logger.info('Parsing from the end')
			dataSortedByOldest = {}
			status = True
			while len(dataSortedByOldest) == 0:
				container = self.getContainer(urlToParseOldest)
				dataSortedByOldest = self.parseContainer(container, dataSortedByOldest, result)
			permTokens, tokenForNewData = self.getTokens(urlToParseOldest)
			while status:
				jsonContainer = self.getNewData(permTokens, tokenForNewData)
				dataSortedByOldest, tokenForNewData, status = self.parseNewData(jsonContainer, dataSortedByOldest, status, result)
				logger.info('Parsed {}'.format(str(len(dataSortedByOldest))))
			dataSortedByOldestReversed = {}
			for key, value in reversed(dataSortedByOldest.items()):
				dataSortedByOldestReversed[key] = value
			
			result.update(dataSortedByOldestReversed)

		logger.info('Successfully completed. {} objects found'.format(str(len(result))))

		return result

if __name__ == '__main__':
	channel_url = input('Enter channel url: ')
	parser = Parser(channel_url)
	result = parser.start()
	with open('result.csv', 'w') as f:
		writer = csv.writer(f)
		writer.writerow(('title', 'url', 'videoId', 'views', 'published'))
		for value in result.values():
			writer.writerow((value['title'], value['url'], value['videoId'], value['views'], value['published']))