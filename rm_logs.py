#! /usr/bin/env python3
from os.path import exists
from glob import glob
for f in glob('*.log'):
    rf=f.replace('.log','.res')
    if not exists(rf):
        print(f'unlink {f}')
    else:
        print(f'keep {rf}')


