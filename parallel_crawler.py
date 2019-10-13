import requests
from requests.exceptions import Timeout # for request timeout
import re # for url extraction
import sqlite3 # sqlite3 for database
from time import sleep # for request delay
from multiprocessing import cpu_count, Pool, TimeoutError # for parallel processing

# maximum depth to crawl
max_depth = 3
# number of processes for multiprocessing (using the number of CPUs in the system)
no_processes = cpu_count()
# regex to be used to retrieve <a href=""> relevant
HTML_TAG_REGEX = re.compile(r'<a[^<>]+?href=([\'\"])(.*?)\1', re.IGNORECASE)

# function to remove visited urls from urls_queue
def filter_visited(visited_urls, urls_to_crawl):
	urls_queue = list(urls_to_crawl - set(visited_urls))
	
	return urls_queue

# function to store url and response time to database
def db_store_url(db_cursor, url_link, response_time):
	db_cursor.execute("INSERT OR REPLACE INTO urls VALUES (?, ?)", (url_link, response_time))

# function to process incomplete url links
def process_url(base_url, url_list):
	if base_url[-1] == '/':
		base_url = base_url[:-1]

	# remove all occurences of "javascript:void(0)"
	url_list = list(filter(("javascript:void(0)").__ne__, url_list))
	# remove all occurences of empty url
	url_list = list(filter(("").__ne__, url_list))
	url_list = list(filter(("http://").__ne__, url_list))
	url_list = list(filter(("https://").__ne__, url_list))

	for index in range(len(url_list)):
		# check for special cases, assume no '#' in initial database
		if url_list[index][:2] == "//":
			url_list[index] = "https:" + url_list[index]
		elif url_list[index][0] == "/":
			# find the index of start of base url
			protocol_header_end = base_url.find("://") + 3
			# find the index of occurence of first slash
			first_slash = base_url.find("/", protocol_header_end)
			# find the index of occurence of first hash
			first_hash = base_url.find("#", protocol_header_end)
			# find the index of occurence of first question mark
			first_question = base_url.find("?", protocol_header_end)
			# find the index of end of base url + 1
			base_url_end = min(first_slash, first_hash, first_question)
			# check if no occurence of slash, hash and question mark
			if base_url_end == -1:
				url_list[index] = base_url
			else:
				# construct base url
				base_url = base_url[protocol_header_end:base_url_end]

				# construct absolute url
				if url_list[index] == "/":
					url_list[index] = base_url + "/"
				else:
					url_list[index] = base_url + "/" +url_list[index]
			
		#elif url_list[index][0] == "#":
		#	url_list[index] = base_url + url_list[index]
		elif url_list[index][:2] == "..":
			url_list[index] = base_url + "/" + url_list[index]
		elif url_list[index][:4] != "http":
			url_list[index] = base_url + "/" + url_list[index]

	return url_list

'''
function to vist and process url
returns status, url_link, urls_to_crawl
status 0 on success
status -1 on exception
'''
def crawl_url(url_link, visited_urls, urls_to_crawl, urls_queue):
	try: 
		# do not follow redirect in case url is already visited
		response = requests.get(url_link, allow_redirects=False, timeout=(4, 7), verify=False)

	except Exception:
		print('The request time out or invalid url: ' + url_link)
		return -1, url_link, urls_to_crawl

	# check for redirect and add redirect url to the queue
	if response.status_code == 302 or response.status_code == 301:
		redirect_url = response.headers['Location']
		# Check if url is already visited
		if redirect_url not in visited_urls:
			urls_to_crawl.add(redirect_url)
	else:
		# url extraction
		if response.content:
			url_list = [url for quote, url in HTML_TAG_REGEX.findall(response.content.decode('latin-1'))]
			# process url_list
			processed_url_list = process_url(url_link, url_list)
			
			# only append urls that are not visited
			for processed_url in processed_url_list:
				if processed_url not in visited_urls and "#" not in processed_url:
					urls_to_crawl.add(processed_url)

	# print("info: " + response.url + " : " + url_link)
	# get response time
	response_time = response.elapsed.total_seconds()

	# store url and response time
	db_store_url(db_cursor, url_link, response_time)
	
	# save to database
	db.commit()

	# double sleep if need to in case of dos
	#sleep(1)

	return 0, url_link, urls_to_crawl

# urls.db to store visited urls
database = 'urls.db'

db = sqlite3.connect(database, uri=True)

# create cursor object to execute SQL commands
db_cursor = db.cursor()

# retrieve url(s) from database
db_cursor.execute('''SELECT url FROM urls''')

# store unqiue urls as a list
urls_queue = list(set(url[0] for url in db_cursor.fetchall()))

# store visited urls
visited_urls = list()

# store extracted urls
urls_to_crawl = set()

depth = 0

while urls_queue:
	# store all the urls to be visited
	urls_to_crawl = set()
	# remove all occurences of empty url
	urls_queue = list(filter(("").__ne__, urls_queue))
	
	multiple_responses = []

	with Pool(processes=no_processes) as pool:
		for url_link in urls_queue:
			#crawl_url(url_link)
			multiple_responses.append(pool.apply_async(crawl_url, (url_link, visited_urls, urls_to_crawl, urls_queue)))

			# add visited url link
			visited_urls.append(url_link)

			# sleep in case of dos
			sleep(1)

		for res in multiple_responses:
			try:
				status, url_link, extracted_urls = res.get(timeout=11)
				if status == -1:
					continue
				# add extracted urls to urls_to_crawl
				urls_to_crawl = urls_to_crawl|extracted_urls
			except TimeoutError:
				print("Timeout: " + url_link)

	# filter visited urls
	urls_queue = filter_visited(visited_urls, urls_to_crawl)

	# check if there is any more urls to crawl
	if not urls_queue:
		print("No more url to be crawled!")
		exit(0)

	#print("Visited urls: " + str(visited_urls))
	#print("To be crawled: " + str(urls_queue))

	# count number of iterate
	depth = depth + 1

	if depth >= max_depth:
		print("Reached Depth:" + str(depth))
		exit(0)

# close cursor
db_cursor.close()

