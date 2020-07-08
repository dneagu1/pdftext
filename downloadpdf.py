from subprocess import call
import requests
import sqlite3
import os
import time
from tqdm import tqdm

if __name__=='__main__':
    conn = sqlite3.connect('/home/anon/Documents/db/finra/firms.db')
    cursor = conn.cursor()
    firmids = [item[0] for item in cursor.execute('SELECT DISTINCT firmId FROM basicInformation').fetchall()]
    # print(firmids[:10])
    downloaddir = '/home/anon/Documents/db/finra/pdf'
    os.chdir(downloaddir)
    for firmid in tqdm(firmids):
        response = requests.get('https://files.brokercheck.finra.org/firm/firm_{}.pdf'.format(str(firmid)))
        pdfname = '{}.pdf'.format(str(firmid))
        with open(pdfname, 'wb') as f:
            f.write(response.content)
        call('qpdf --password=%s --decrypt %s %s' %('', pdfname, 'decr_'+pdfname), shell=True)
        os.remove(pdfname)
