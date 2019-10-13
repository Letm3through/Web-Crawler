import sqlite3

db = sqlite3.connect('urls.db')
cursor = db.cursor()
cursor.execute("CREATE TABLE urls (url text primary key, response real)")
#cursor.execute("INSERT INTO urls VALUES ('https://crawler-test.com/', 0.0)")
cursor.execute("INSERT INTO urls VALUES ('http://quotes.toscrape.com/', 0.0)")
db.commit()
db.close()
