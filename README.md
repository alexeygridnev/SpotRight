# SpotRight
Desktop search engine for Linux systems. 

Mostly based on `textreg` Python library. The library is mostly abandoned by its original author,so, I'm using <a href='https://github.com/deanmalmgren/textract.git@pyup-scheduled-update-2024-03-04'> this fork</a> with updated dependencies. Additionally `strip_markdown` from pypi is  used. Indexes most popular text file formats (including doc, docx, pptx, pdf, epub, html, and many others). For file types outside the most popular ones, SpotRight is trying to index them as text after checking that they are not binary files. The file index itself is an SQLite database with FTS-5 full-text search enabled.

This is  just a stub so far; will be updated in the coming months.

May be useful  if you are using a desktop environment without an in-build desktop search (LXQt, Xfce).
