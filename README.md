# SpotRight
Desktop search engine for Linux systems. 

Mostly based on `textreg` Python library. The library is mostly abandoned by its original author,so, I'm using <a href='https://github.com/deanmalmgren/textract.git@pyup-scheduled-update-2024-03-04'> this fork</a> with updated dependencies. Additionally `strip_markdown` from pypi is  used. Indexes most popular text file formats (including doc, docx, pptx, pdf, epub, html, and many others). For file types outside the most popular ones, SpotRight is trying to index them as text after checking that they are not binary files. The file index itself is an SQLite database with FTS-5 full-text search enabled.

This is  just a stub so far; will be updated in the coming months.

May be useful  if you are using a desktop environment without an in-build desktop search (LXQt, Xfce).

##Dependencies
Python dependencies are listed in `requirements.txt` file and can be installed from your Python virtual environment by running:

`pip3 install -r requirements.txt`

On top of that, some system packages are required. In Ubuntu 22.04, they can be installed as:

`sudo apt install python3-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils pstotext tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig`
