import sqlite3
import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import logging


def searchlist(lst,string):
    return [thing for thing in lst if string in thing]

def processtext(sample,keep_cols):
    finlst,elim = [],[]
    headerdict = {'Does the order constitute a':'final order based on violations of any laws or regulations that prohibit fraudulent, manipulative, or deceptive conduct?',
    'Principal Sanction(s)/Relief':'Sought',
    'Other Sanction(s)/Relief':'Sought',
    'Sanctions Ordered or Relief':'Granted',
    'Appealed To and Date Appeal':'Filed',
    'Firm Statement':'',
    'Regulator Statement':''}
    keylst = [':'] + list(headerdict.keys()) #Start Text
    for num in range(len(sample)):
        for x in range(10): # Avoid Date columns
            sample[num] = sample[num].replace(str(x)+':',str(x))
        if any([item in sample[num] for item in keylst]) ==True and sample[num].strip() not in ['Sought:','Granted:','Filed:']: # variable name either in dictionary or has ":"
         # or any([thing for thing in keep_cols if thing in sample_num]):
            ### Find Start(element) text and Stop(idx) locations for each field
            element,idx = sample[num],num+1
            # if ('Sought:' not in sample[num] and 'Granted:' not in sample[num]) or ('Relief Sought:' in sample[num]) else ' '.join(sample[num-1:num+1])
            try: # start appending to original text
                remaining = sample[idx]
                # if 'Sanction(s)' in element:
                #     print('first')
                #     print([element,remaining])
                #     print(any([ele in remaining for ele in keylst]))
                #     print(any([item==remaining.strip() for item in ['Sought:','Granted:','Filed:']]))
                if any([ele in remaining for ele in keylst])==False or any([item==remaining.strip() for item in ['Sought:','Granted:','Filed:']])==True:
                    if 'Does the order constitute' in element:
                        while 'Yes' not in element and 'No' not in element:
                            idx+=1
                            element += ' ' + remaining
                            remaining = sample[idx]
                        element = element.replace('Sanctions Ordered','')
                    else:

                        #     print(any([ele in remaining for ele in keylst]))
                        #     print(any([item==remaining.strip() for item in ['Sought:','Granted:','Filed:']]))
                        while any([ele in remaining for ele in keylst])==False or any([item==remaining.strip() for item in ['Sought:','Granted:','Filed:']])==True:
                            idx+=1
                            # if 'Sanction(s)/Relief' not in remaining and 'Sanctions Ordered or Relief' not in remaining and 'Appealed To and Date Appeal' not in remaining:
                            element += ' ' + remaining
                            remaining = sample[idx]
                        if 'Sanctions Ordered' in element:
                            element = element.replace('Yes','').replace('No','')
                        # if 'Sanction(s)' in element:
                            # print(element)
            except:
                pass
            finlst.append(element)
    finlst = [item.split(':') for item in finlst if item.strip()!='']
    for x in range(len(finlst)):
        finlst[x] = [item.strip() for item in finlst[x] if item !='']
        ### Special Conditions:
        # print(finlst[x])
        for key in list(headerdict.keys()):
            if key in finlst[x][0]:
                # if 'Sanction(s)' in finlst[x][0]:
                #     print(finlst[x])
                keystr = key + ' ' + headerdict[key] if headerdict[key] != '' else key
                txtstr = ' '.join(finlst[x]).replace(key,'').replace(headerdict[key],'').strip()
                if txtstr != '':
                    finlst[x] = [keystr,txtstr]
                else:
                    finlst[x] = [keystr]
        if 'Current Status' in finlst[x][0] and ('Final' in finlst[x][1] or 'FINAL' in finlst[x][1]):
            finlst[x][1] = 'Final'
        if len(finlst[x]) > 2: ## Combine additional arrays
            finlst[x][1] = ' '.join(finlst[x][1:]).strip()
            del finlst[x][2:]
        if finlst[x][0].isupper():
            try:
                elim.append(x)
                finlst[x-1][1] += ' '.join(finlst[x]).strip()
            except:
                pass
    rem = 0
    for num in elim:
        del finlst[num-rem]
        rem+=1
    return finlst

def createframe(txt,filename):
    firmid = int(filename.split('.')[0].replace('decr_',''))
    keep_cols = [item[1] for item in cursor.execute('PRAGMA table_info(disclosuretext);').fetchall()] ## Columns in Database
    frame = pd.DataFrame()
    locs = sorted(list(set([i for i, n in enumerate(txt) if "Disclosure" in n and " of " in n]))) # Split Disclosure Sections
    endlst = []
    for loc in locs: # Process 1 Disclosure event at a time
        if loc != locs[-1]:
            sample = txt[loc+1:locs[locs.index(loc)+1]]
        else:
            sample = txt[loc+1:]
        sample = [item.strip() for item in sample if 'finra.org' not in item and 'All rights reserved.' not in item and item !='' and 'Report about ' not in item and '2020 FINRA' not in item]
        endlst +=processtext(sample,keep_cols) # Apply function to raw text
    numframes = pd.DataFrame(endlst)[0].tolist().count('Reporting Source')
    numiter = 0
    while numiter < numframes: # Pandas Formatting before going into SQL Database
        start = [i for i, n in enumerate(pd.DataFrame(endlst)[0].tolist()) if n == 'Reporting Source'][numiter]
        try:
            end = [i for i, n in enumerate(pd.DataFrame(endlst)[0].tolist()) if n == 'Reporting Source'][numiter+1]
        except:
            end = len(endlst)
        intframe = pd.DataFrame(endlst[start:end]).drop_duplicates(subset=0,keep='last').set_index(0).T

        missing=[item for item in intframe.columns if item not in keep_cols]
        if missing!=[]: ## Log Missing columns
            logging.warning('{}:index {}:{}:{}'.format(filename,str(numiter),'missing columns',str(missing)))
        intframe = intframe.drop(columns=missing).reset_index(drop=True)
        for col in [item for item in ['Date Initiated','Resolution Date','Case Initiated','Disposition Date','Date Court Action Filed','Date Notice/Process Served'] if item in intframe.columns]:
            try:
                intframe[col] = pd.DataFrame([item.split(' ')[0] if pd.isnull(item) == False else item for item in intframe[col].tolist()])
                intframe[col]=pd.to_datetime(intframe[col],errors='coerce')
            except Exception as e:
                logging.warning('{}:index {}:{}:{}'.format(filename,str(numiter),'datetime error',e))
        for col in ['Sanctions Ordered','Sum of All Relief Awarded','Sanctions Ordered or Relief Granted','Payout Details']:
            if col in intframe.columns:
                try:
                    intframe[col+' Amount'] = pd.DataFrame([float(searchlist(item.split(' '),'$')[0].replace('$','').replace(',','')) if len(searchlist(item.split(' '),'$'))>0 and pd.isnull(item) == False else 0 for item in intframe[col].tolist()])
                except Exception as e: # Log Dollar amount errors
                    logging.warning('{}:index {}:{}:{}'.format(filename,str(numiter),'amount to float error',e))
        for floatcol in [item for item in ['Sum of All Relief Awarded','Sum of All Relief Requested'] if item in intframe.columns]:
            intframe[floatcol]=intframe[floatcol].str.replace('$','').str.replace(',','')
            intframe[floatcol] = pd.to_numeric(intframe[floatcol],errors='ignore')
        intframe['timestamp'] = pd.Timestamp.now()
        intframe['firmId'] =  firmid
        intframe.to_sql('disclosuretext',conn,if_exists='append',index=False)
        numiter += 1
    return


if __name__=='__main__':
    logging.basicConfig(filename='disclosures.log',level=logging.DEBUG)
    conn = sqlite3.connect('/home/anon/Documents/db/finra/firms.db')
    cursor = conn.cursor()
    ################
    ## To delete DB
    ################
    cursor.execute('DELETE FROM disclosuretext')
    conn.commit()
    ################
    ################

    ################
    ### Process TXT Files
    ################
    filedir ='/home/anon/Documents/db/finra/pdf'
    files = [item for item in os.listdir(filedir) if '.txt' in item]
    for file in tqdm(files):
        with open(filedir + '/' + file,'rb') as f:
            txt = f.read()
        txt = txt.decode("utf-8").split('\n')
        txt = [item for item in txt if '©' not in item and 'User Guidance' not in item and 'Report about ' not in item and 'www.finra.org/brokercheck' not in item]
        try:
            createframe(txt,file)
        except Exception as e: # Log files that do not have disclosures
            logging.critical('{}:{}:{}'.format(file,'upload error',e))
