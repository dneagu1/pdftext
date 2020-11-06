import pandas as pd
import tqdm

def check_integer(val):
    try:
        val = int(val)
    except:
        pass
    return val

def search_crd(txt):
    idxs = [int(txt.index(item)+1) for item in txt if 'CRD #:' in item]
    fin_lst = []
    for idx in idxs:
        lst = check_integer(txt[idx])
        try:
            idx+= 1
            next = check_integer(txt[idx])
            while ':' not in next:
                lst += [next]
                idx+= 1
                next = check_integer(txt[idx])
        except Exception as e:
            print(e)
        if len(lst) > 0:
            fin_lst.append(max(lst))
    return lst




if __name__=='__main__':
    filedir ='/home/anon/Documents/db/finra/pdf'
    files = [item for item in os.listdir(filedir) if '.txt' in item]
    for file in tqdm(files[:2]):
        crd = int(file.split('.')[0].replace('decr_',''))
        with open(filedir + '/' + file,'rb') as f:
            txt = f.read()
        txt = txt.decode("utf-8").split('\n')
        txt = [item for item in txt if '©' not in item and 'User Guidance' not in item and 'Report about ' not in item and 'www.finra.org/brokercheck' not in item]
        print([crd,search_crd(txt)])
