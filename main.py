#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  9 11:00:19 2024

@author: aleksei
"""

import textract
import strip_markdown
import sqlite3
import os
import codecs
import bs4
import time
import pandas as pd
import datetime
import hashlib

def is_binary_file(source_path): #https://stackoverflow.com/a/43789171
    #: BOMs to indicate that a file is a text file even if it contains zero bytes.
    _TEXT_BOMS = (
        codecs.BOM_UTF16_BE,
        codecs.BOM_UTF16_LE,
        codecs.BOM_UTF32_BE,
        codecs.BOM_UTF32_LE,
        codecs.BOM_UTF8,
    )
    
    with open(source_path, 'rb') as source_file:
        initial_bytes = source_file.read(8192)
    return not any(initial_bytes.startswith(bom) for bom in _TEXT_BOMS) and b'\0' in initial_bytes

#files we should not even attempt to index:
blocklist = ['exe', 'app', 'AppImage', #apps
             'zip', '7z', '7zip', 'gz', 'xz', #archives
             'iso', 'img', 'dmg', 'qcow', 'qcow2', #disk image files
             'flac', 'waw', 'mp3', 'ogg', 'mp4', 'mpeg4', 'avi', #audio/video
             'xls', 'xlsx', 'csv' #tables; will implement indexing text in tables later
             'tif', 'tiff', 'gif', 'bmp', 'jpg', 'jpeg'] #images

#files we should process by textract default:
list_as_textract = ['doc', 'docx', 'eml', 'epub', 'json', 'htm', 'html', 'msg', 'odt', 'pptx', 'txt' ]

#files we should treat as text:
list_as_text = ['bat', 'sh', 'py', 'h', 'c', 'cpp', 'sln', 'csproj', 'cs', 'rst', 'sql', 'java', 'jar']

def text_extraction(path, filename, blocklist, list_as_textract, list_as_text):
    
    path = path + "/"
    
    textraw = ""
    
    try:
        if not "." in filename:
            textraw = textract.process(path + filename, extension = "txt").decode('utf-8')            
        elif filename.split(".")[-1] in blocklist:
            textraw = ""
        elif filename.split(".")[-1] in list_as_textract:
            textraw = textract.process(path + filename).decode('utf-8')     
        elif filename.split(".")[-1] == "pdf": #for now, the same, maybe will add OCR later:
            textraw = textract.process(path + filename, method = 'pdftotext').decode('utf-8')     
        elif filename.split(".")[-1] in (list_as_text):
            textraw = textract.process(path + filename, extension = "txt").decode('utf-8')     
        elif filename.split(".")[-1] == "md": #markdown
            textraw = strip_markdown.strip_markdown_file(path + filename)
        elif filename.split(".")[-1] == "xml": #xml
            textraw = bs4.BeautifulSoup(open(path + filename).read(), 'xml').text

        else: #check if binary and try to process as text:
            if is_binary_file(path + filename):
                textraw = textract.process(path + filename, extension = "txt").decode('utf-8')        
        #remove extra spaces, line breaks etc:
        textlist = textraw.split()
                
        text = " ".join(textlist)
        # making sure single quotes are replaced with double quotes, to work nicely with SQL:
        
        text = text.replace("'", "''")
        
        #to facilitate search:
        text = text.lower()
        
    except Exception as e:
        text = ""
    return text

rootpath = os.path.expanduser('~')

#create SQLite database if not exists; otherwise, connect to it:

def full_indexing(rootpath):    

    conn = sqlite3.connect(rootpath + "/" +  "indexing.sql")
    cur = conn.cursor()
    
    try:
        deletion_query = "DROP TABLE IF EXISTS Indexing" #temporary
        
        table_creation_query = '''CREATE TABLE IF NOT EXISTS Indexing 
                                (PK_File INTEGER PRIMARY KEY,
                                 Path TEXT,
                                 File TEXT,
                                 Extension TEXT,
                                 Modification_date DATETIME,
                                 Content TEXT,
                                 Hash_filepath BIGINT)'''
                                
        deletion_query_timestamp = "DROP TABLE IF EXISTS Indexing_time"
        
        indexing_timestamps_query = '''
                                  CREATE TABLE IF NOT EXISTS Indexing_time
                                  (PK_Timestamp INTEGER PRIMART KEY,
                                  Timestamp DATETIME,
                                  Indexing_type BOOLEAN)
                                  '''
                                
        cur.execute(deletion_query)      
        conn.commit() 
                      
        cur.execute(table_creation_query)
        conn.commit()
        
        cur.execute(deletion_query_timestamp)
        conn.commit()

        
        cur.execute(indexing_timestamps_query)
        conn.commit()
        
        counter = 0
                
        #start with registering timestamp of full indexing:
        register_ts_query = "INSERT INTO Indexing_time (Timestamp, Indexing_type) VALUES(?, ?)"
        ts_full = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(register_ts_query, (ts_full, 1))
        conn.commit()
        
        
        for root, dirs, files in os.walk(rootpath):
            for file in files:
                #skip symlinks:
                if os.path.islink(root + "/" + file):
                    continue
                #skip files in ".cache" folders:
                elif ".cache" in root:
                    continue
                
                else:
            
                    #do not index files over 100 MB in size:
                    if os.path.getsize(root + "/" + file) > 1024 * 1024 * 100:
                        text = ""
                    #do not index files in hidden folders:
                    elif  "." in root:     
                        text = ""
                    else:
                        text = text_extraction(root, file, blocklist, list_as_textract, list_as_text)
                    
                    #hash of the file path. Will help in optimizing incremental reindexing:
                    hash_filepath = int(hashlib.sha1((root + "/" + file).encode('utf-8')).hexdigest(), 16) % 10**16
    
                    
                    mod_date = os.path.getmtime(root + "/" + file)
                    
                    mod_date_ts = datetime.datetime.fromtimestamp(mod_date).strftime('%Y-%m-%d %H:%M:%S')
                        
                    if "." in file:
                        values = (root, file, file.split(".")[-1], mod_date_ts,  text, hash_filepath)
                    else:
                        values = (root, file, "", mod_date_ts, text, hash_filepath)
                    
                    insertion_query = '''INSERT INTO Indexing (Path, File, Extension, Modification_date, Content, Hash_filepath)
                                        VALUES(?, ?, ?, ?, ?, ?)'''
            
                    cur.execute(insertion_query, values)
                    
                    counter += 1
                
                    if counter % 10 == 0:
                        print(str(counter) + " files indexed")
                        conn.commit()
                    
        table_index_query = "CREATE UNIQUE INDEX IF NOT EXISTS Hash_filepath_idx ON Indexing(Hash_filepath)"
        
        cur.execute(table_index_query)
        conn.commit()
   
    except Exception as e:
        print(e)
        raise ValueError
    finally:
        conn.close()
        
def incremental_indexing():
    conn = sqlite3.connect(rootpath + "/" +  "indexing.sql")
    cur = conn.cursor()
    
    try:
        
        deletion_query = "DROP TABLE IF EXISTS Partial_Indexing" 

        
        table_creation_query = '''CREATE TABLE IF NOT EXISTS Partial_Indexing 
                                (PK_File INTEGER PRIMARY KEY,
                                 Path TEXT,
                                 File TEXT,
                                 Extension TEXT,
                                 Modification_date DATETIME,
                                 Content TEXT,
                                 Hash_filepath BIGINT)'''
                                
        
        cur.execute(deletion_query)      
        conn.commit() 
                                            
        cur.execute(table_creation_query)
        conn.commit()
        
        
        counter = 0
        
        #start with registering timestamp of full indexing:
        get_ts_query = "SELECT MAX(Timestamp) FROM Indexing_time WHERE Indexing_type = 1"
        last_indexing_ts = cur.execute(get_ts_query).fetchall()[0][0]
        
        
        for root, dirs, files in os.walk(rootpath):
            for file in files:                 
                #skip symlinks:
                if os.path.islink(root + "/" + file):
                    continue 
                #main point of partial reindexing: if the file modification time is before the time of the last reindexing, skip
                elif os.path.getmtime(root + "/" + file) <= time.mktime(datetime.datetime.strptime(last_indexing_ts, '%Y-%m-%d %H:%M:%S').timetuple()):
                    continue
                #skip files in ".cache" folders:
                elif ".cache" in root:
                    continue
                
                else:                     
                    #do not index files over 100 MB in size:
                    if os.path.getsize(root + "/" + file) > 1024 * 1024 * 100:
                        text = ""
                    #do not index files in hidden folders:
                    elif  "." in root:     
                        text = ""
                    else:
                        text = text_extraction(root, file, blocklist, list_as_textract, list_as_text)
                    
                    #hash of the file path.
                    hash_filepath = int(hashlib.sha1((root + "/" + file).encode('utf-8')).hexdigest(), 16) % 10**16
                    
                    mod_date = os.path.getmtime(root + "/" + file)
    
                    mod_date_ts = datetime.datetime.fromtimestamp(mod_date).strftime('%Y-%m-%d %H:%M:%S')
                        
                    if "." in file:
                        values = (root, file, file.split(".")[-1], mod_date_ts,  text, hash_filepath)
                    else:
                        values = (root, file, "", mod_date_ts, text, hash_filepath)
                    
                    insertion_query = '''INSERT INTO Partial_Indexing (Path, File, Extension, Modification_date, Content, Hash_filepath)
                                        VALUES(?, ?, ?, ?, ?, ?)'''
            
                    cur.execute(insertion_query, values)
                    
                    counter += 1
                    
                    if counter % 10 == 0:
                        #print(str(counter) + " files indexed")
                        conn.commit()
                
        table_index_query = "CREATE UNIQUE INDEX IF NOT EXISTS Hash_filepath_temp_idx ON Partial_Indexing(Hash_filepath)"
        
        cur.execute(table_index_query)
        conn.commit()
        
        #update full indexing table using partial indexing
        #testing showed that delete and reinsert approach is way more performant than update
            
        delete_old_values_query = '''
                                    DELETE
                                    FROM Indexing
                                    WHERE Hash_filepath IN
                                    	(SELECT Hash_filepath FROM Partial_Indexing)
                                        '''
        add_new_values_query = '''
                                INSERT INTO Indexing
                                	(Path, File, Extension, Modification_date, Content, Hash_filepath)
                                SELECT Path, File, Extension, Modification_date, Content, Hash_filepath FROM Partial_Indexing
        '''
        
        cur.execute(delete_old_values_query)
        cur.execute(add_new_values_query)
        conn.commit()
    
                                    
    except Exception as e:
        print(e)
        raise ValueError
    finally:
        conn.close()

def search():
    conn = sqlite3.connect(rootpath + "/" +  "indexing.sql")
    cur = conn.cursor()
    
    prepare_query_0 = "DROP TABLE IF EXISTS Search"
    prepare_query_1 = "CREATE VIRTUAL TABLE IF NOT EXISTS Search USING fts5 (Path, File, Content)"
    prepare_query_2 = "INSERT INTO Search SELECT Path, File, Content FROM Indexing WHERE Content != ''"
    
    search_query_title = '''SELECT Path, File,
                      SNIPPET(Search, 1, '[', ']', '...', 16) AS Output
                      FROM Search
                      WHERE File MATCH ? ORDER BY Rank LIMIT 10'''
                      
    search_query_content = '''SELECT Path, File,
                          SNIPPET(Search, 2, '[', ']', '...', 16) AS Output
                          FROM Search
                          WHERE Content MATCH ? ORDER BY Rank LIMIT 10'''

    
    cur.execute(prepare_query_0)
    conn.commit()
    cur.execute(prepare_query_1)
    conn.commit()
    cur.execute(prepare_query_2)
    conn.commit()
    
    while True:
        try:
            print("Type your query:")
            query_text = input()
            query_text_tuple = (query_text,)
            out_1 = cur.execute(search_query_title, query_text_tuple).fetchall() #title search
            print("\n===Title search===\n")
            for el in out_1:
                print("File path: " + el[0])
                print("File name: " + el[1])
            
            out_2 = cur.execute(search_query_content, query_text_tuple).fetchall() #content search
            print("\n===Content search===\n")
            for el in out_2:
                print("File path: " + el[0])
                print("File name: " + el[1])
                print("Snippet: " + el[2])    
            
        except Exception as e:
            print(e)
            conn.close()
            break

search()