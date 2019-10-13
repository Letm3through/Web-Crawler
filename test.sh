#!/bin/sh
rm urls.db 2> /dev/null
python3 initialize_db.py
python3 parallel_crawler.py 2> /dev/null | tee results.txt
