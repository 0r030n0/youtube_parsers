import requests
import logging
import bs4
import csv

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('GetVideoInfo')

class GetVideoInfo:
	def __init__(self, url):
		self.url = url

	def prepare_track(self, songTitle, channelTitle):
		if ' – ' in channelTitle:
			channelTitle = channelTitle.split(' – ')[0]
		elif ' - ' in channelTitle:
			channelTitle = channelTitle.split(' - ')[0]
		if '/' in songTitle:
			songTitle = songTitle.replace('/', '')
		if ' - ' in songTitle:
			trackName = songTitle
		else:
			trackName = channelTitle + ' - ' + songTitle		
		fileName = f'{trackName}.mp3'
		return fileName, trackName

	def get_opinionCount(self, soup):
		try:
			likes = soup.find("button", attrs={"class": "like-button-renderer-like-button-unclicked"})
			likes = int(likes.find('span', attrs={'class': 'yt-uix-button-content'}).getText().replace(',', ''))
		except:
			likes = 'hidden'
		try:
			dislikes = soup.find("button", attrs={"class": "like-button-renderer-dislike-button-unclicked"})
			dislikes = int(dislikes.find('span', attrs={'class': 'yt-uix-button-content'}).getText().replace(',', ''))
		except:
			dislikes = 'hidden'
		return likes, dislikes

	def getTitles(self):
		s = False
		while not s:
			try:
				r = requests.get(url=self.url, headers = {'accept-language': 'en-US,en;q=0.9'})
				soup = bs4.BeautifulSoup(r.text, 'lxml')
				songTitle = soup.find("span", attrs={"class": "watch-title"}).text.strip(' \n ')
				s = True
			except:
				pass
		channelTitle = soup.find("div", attrs={"class": "yt-user-info"}).find("a").text
		views = int(soup.find("div", attrs={"class": "watch-view-count"}).getText().replace(',', '').strip(' views'))
		return songTitle, channelTitle, views, soup

	def start(self):
		songTitle, channelTitle, views, soup = self.getTitles()
		likes, dislikes = self.get_opinionCount(soup)
		fileName, trackName = self.prepare_track(songTitle, channelTitle)
		result = {}
		result['title'] = trackName
		result['views'] = views
		result['likes'] = likes
		result['dislikes'] = dislikes
		return result

if __name__ == '__main__':
	video_url = input('Enter video url: ')
	getVideoInfo = GetVideoInfo(video_url)
	result = getVideoInfo.start()
	with open('video_analysis.csv', 'a') as f:
		writer = csv.writer(f)
		writer.writerow(('title', 'views', 'likes', 'dislikes'))
		writer.writerow((result['title'], result['views'], result['likes'], result['dislikes']))

 
