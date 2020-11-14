import pandas as pd
from tqdm import tqdm
import os
import sqlite3
import logging

def check_integer(val): # Checks whether a string can be converted to an integer (CRD verification)
    try:
        val = int(val.strip())
    except:
        pass
    return val

def search_crd(txt,crd):
    midx = txt.index('Organization Affiliates') # Eliminate other affliate categories by starting at Org Affiliates section, which is last Affiliates section.
    idxs = [i for i, x in enumerate(txt) if 'CRD #:' in x] # Get positions of "CRD #" string in text file.
    idxs = [item for item in idxs if item > midx] # Keep only Org Affiliates
    fin_lst = []
    for step in range(len(idxs)):
        lst, idx  = [], idxs[step]
        if isinstance(check_integer(txt[idx]),int): # Keep text only if it is an integer/CRD #
            lst += [check_integer(txt[idx])]
        idx+= 1
        next = check_integer(txt[idx]) # Check next row
        while (':' not in str(next) or lst == []) and idx < idxs[step]+10: # Repeat process until a new data field is found or 10 rows are read.
            next = check_integer(txt[idx])
            if isinstance(next, int):
                lst += [next]
            idx+= 1
            next = check_integer(txt[idx])
        if len(lst) > 0:
            fin_lst.append(max(lst))
    return fin_lst

def db_init():
    conn = sqlite3.connect('/home/anon/Documents/db/finra/affiliates.db')
    cursor = conn.cursor()
    ################
    ## To delete DB
    ################
    try:
        cursor.execute('DELETE FROM crd')
        conn.commit()
    except:
        pass
    return conn




if __name__=='__main__':
    filedir ='/home/anon/Documents/db/finra/pdf' # Enter correct directory where TXT Files are located
    files = [item for item in os.listdir(filedir) if '.txt' in item]
    logging.basicConfig(filename='affiliates.log')
    conn = db_init()
    for file in tqdm(files):
        try:
            ####################
            ## Read TXT File
            ####################
            crd = int(file.split('.')[0].replace('decr_',''))
            with open(filedir + '/' + file,'rb') as f:
                txt = f.read()
            txt = txt.decode("utf-8").split('\n')
            txt = [item for item in txt if '©' not in item and 'User Guidance' not in item and 'Report about ' not in item and 'www.finra.org/brokercheck' not in item]
            ####################
            ## Find Affiliates
            ####################
            affiliates = search_crd(txt,crd)
            frame = pd.DataFrame([[crd,sub] for sub in affiliates],columns=['crd','affiliates']).drop_duplicates()
            frame.to_sql('crd',con=conn,if_exists='append',index=False) # Upload to SQLite
            conn.commit()
        except Exception as e: # Log errors by CRD #
            logging.critical('{}|{}'.format(crd,e))
