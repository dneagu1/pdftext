import pandas as pd
from tqdm import tqdm
import os
import sqlite3
import logging

def check_integer(val):
    try:
        val = int(val.strip())
    except:
        pass
    return val

def search_crd(txt,crd):
    midx = txt.index('Organization Affiliates')
    idxs = [i for i, x in enumerate(txt) if 'CRD #:' in x]
    idxs = [item for item in idxs if item > midx]
    # idxs = [int(txt.index(item)+1) for item in txt if 'CRD #:' in item]
    fin_lst = []
    for step in range(len(idxs)):
        lst, idx  = [], idxs[step]

        if isinstance(check_integer(txt[idx]),int):
            lst += [check_integer(txt[idx])]
        # try:
        idx+= 1
        next = check_integer(txt[idx])
        while (':' not in str(next) or lst == []) and idx < idxs[step]+10:
            next = check_integer(txt[idx])
            if isinstance(next, int):
                lst += [next]
            idx+= 1
            next = check_integer(txt[idx])
        if lst == []:
            print(next)
            print('crd:{}'.format(crd))
        # except Exception as e:
        #     print(e)
        if len(lst) > 0:
            # print(lst)
            fin_lst.append(max(lst))
    return fin_lst

def db_init():
    conn = sqlite3.connect('/home/anon/Documents/db/finra/subsidiaries.db')
    cursor = conn.cursor()
    ################
    ## To delete DB
    ################
    try:
        cursor.execute('DELETE FROM subs')
        conn.commit()
    except:
        pass
    return conn




if __name__=='__main__':
    filedir ='/home/anon/Documents/db/finra/pdf'
    files = [item for item in os.listdir(filedir) if '.txt' in item]
    logging.basicConfig(filename='subsidiaries.log')
    conn = db_init()
    for file in tqdm(files):
        try:
            crd = int(file.split('.')[0].replace('decr_',''))
            with open(filedir + '/' + file,'rb') as f:
                txt = f.read()
            txt = txt.decode("utf-8").split('\n')
            txt = [item for item in txt if '©' not in item and 'User Guidance' not in item and 'Report about ' not in item and 'www.finra.org/brokercheck' not in item]
            subsidiaries = search_crd(txt,crd)
            frame = pd.DataFrame([[crd,sub] for sub in subsidiaries],columns=['crd','subsidiaries']).drop_duplicates()
            frame.to_sql('subs',con=conn,if_exists='append',index=False)
            # .drop_duplicates(reset_index=True)
            conn.commit()
        except Exception as e:
            logging.critical('{}|{}'.format(crd,e))
