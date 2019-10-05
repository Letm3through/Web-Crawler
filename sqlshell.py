import sqlite3
import readline;

print("Enter name of database file to create or connect to: ")

db = input() + ".db"
con = sqlite3.connect(db)

print("Successfully connected to " + db)

con.isolation_level = None
cur = con.cursor()

buffer = ""

print("Welcome to SQLite3 shell!")
print("Enter 'exit' to exit")

while True:
	print(db + ":>>", end=' ')
	line = input()
	if line == "exit":
		break
	buffer += line
	if sqlite3.complete_statement(buffer):
		try:
			buffer = buffer.strip()
			cur.execute(buffer)
			if buffer.lstrip().upper().startswith("SELECT"):
				print(cur.fetchall())

		except sqlite3.Error as e:
			print("An error occurred:", e.args[0])
		buffer = ""

con.close()
