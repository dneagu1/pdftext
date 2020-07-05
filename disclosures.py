import sqlite3
import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import logging


def searchlist(lst,string):
    return [thing for thing in lst if string in thing]

def processtext(sample):
    finlst,elim = [],[]
    keylst = [':','Does the order constitute','Firm Statement','Regulator Statement'] #Start Text
    for num in range(len(sample)):
        if any([item for item in keylst if item in sample[num]]):
            ### Find Start(element) text and Stop(idx) locations for each field
            element,idx = sample[num] if ('Sought:' not in sample[num] and 'Granted:' not in sample[num]) or ('Relief Sought:' in sample[num]) else ' '.join(sample[num-1:num+1]),num+1
            if 'Sought:' not in element:
#                 and 'Granted:' not in element
                try:
                    remaining = sample[idx]
                    if 'Does the order constitute a' not in remaining:
                        char = ':'
                        while char not in remaining:
                            idx+=1
                            if 'Sanction(s)/Relief' not in remaining and 'Sanctions Ordered or Relief' not in remaining:
                                element += ' ' + remaining
                            remaining = sample[idx]
                except:
                    pass
            finlst.append(element)
    finlst = [item.split(':') for item in finlst]
    for x in range(len(finlst)):
        finlst[x] = [item.strip() for item in finlst[x] if item !='']
        ### Special Conditions:
        if 'Does the order constitute' in finlst[x][0]:
            if 'No' in finlst[x][0]:
                finlst[x] += ['No']
            elif ' Yes ' in finlst[x][0]:
                finlst[x] += ['Yes']
            finlst[x][0] = finlst[x][0].replace(' Yes ','').replace(' No ','').replace('  ','').replace('afinal','a final')
            finlst[x][0]
        if 'Sanction(s)/Relief' in finlst[x][0] and '  ' in finlst[x][0]:
            finlst[x] = [item for item in finlst[x][0].split('  ') if item!='']
            finlst[x][0] += ' Sought'
            finlst[x][1] = finlst[x][1].replace(' Sought','').strip()
        if 'Sanctions Ordered or Relief' in finlst[x][0] and '  ' in finlst[x][0]:
            finlst[x] = ' '.join(finlst[x]).split('  ')
            finlst[x] = [item for item in finlst[x] if item!='']
            finlst[x][0] += ' Granted'
            finlst[x][1] = ' '.join(finlst[x][1:]).replace(' Granted','').strip()
        if 'Firm Statement' in finlst[x][0] or 'Regulator Statement' in finlst[x][0]:
            finlst[x] = [item for item in finlst[x][0].split('  ') if item!='']
        if len(finlst[x]) > 2:
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
    firmid = int(filename.split('.')[0])
    frame = pd.DataFrame()
    locs = sorted(list(set([i for i, n in enumerate(txt) if "Disclosure" in n and " of " in n]))) # Split Disclosure Sections
    endlst = []
    for loc in locs:
        if loc != locs[-1]:
            sample = txt[loc+1:locs[locs.index(loc)+1]]
        else:
            sample = txt[loc+1:]
        sample = [item.strip() for item in sample if 'finra.org' not in item and 'All rights reserved.' not in item and item !='' and 'Report about ' not in item and '2020 FINRA' not in item]
        endlst +=processtext(sample)
    numframes = pd.DataFrame(endlst)[0].tolist().count('Reporting Source')
    numiter = 0
    while numiter < numframes:
        start = [i for i, n in enumerate(pd.DataFrame(endlst)[0].tolist()) if n == 'Reporting Source'][numiter]
        try:
            end = [i for i, n in enumerate(pd.DataFrame(endlst)[0].tolist()) if n == 'Reporting Source'][numiter+1]
        except:
            end = len(endlst)
        intframe = pd.DataFrame(endlst[start:end]).drop_duplicates(subset=0).set_index(0).T
        keep_cols = [item[1] for item in cursor.execute('PRAGMA table_info(disclosuretext);').fetchall()]
        missing=[item for item in intframe.columns if item not in keep_cols]
        ## Log Missing columns
        if missing!=[]:
            logging.warning('{}:{}:{}'.format(filename,'missing columns',str(missing)))
        intframe = intframe.drop(columns=missing).reset_index(drop=True)
        for col in [item for item in ['Date Initiated','Resolution Date','Case Initiated','Disposition Date','Date Court Action Filed'] if item in intframe.columns]:
            try:
                intframe[col] = pd.DataFrame([item.split(' ')[0] if pd.isnull(item) == False else item for item in intframe[col].tolist()])
                intframe[col]=pd.to_datetime(intframe[col],errors='coerce')
            except Exception as e:
                print(e)
        for col in ['Sanctions Ordered','Sum of All Relief Awarded','Sanctions Ordered or Relief Granted']:
            if col in intframe.columns:
                try:
                    intframe[col+' Amount'] = pd.DataFrame([float(searchlist(item.split(' '),'$')[0].replace('$','').replace(',','')) if len(searchlist(item.split(' '),'$'))>0 and pd.isnull(item) == False else 0 for item in intframe[col].tolist()])
                except Exception as e:
                    print(e)
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
        try:
            createframe(txt,file)
        except Exception as e:
            logging.critical('{}:{}:{}'.format(file,'upload error',e))
