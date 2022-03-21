#! /usr/bin/env python3
from sys import exit
from glob import glob
import re
import numpy as np
from os.path import exists,splitext
from subprocess import call

"""
averages mulitple runs of simulations. Simulation names are assumed to be of the form a_[b_...]SD.ext.im
SD is the integer seed, and simulations are averaged over that.
"""

files={}
for res in glob("*.res"):
    parts=res.replace('.res','').split('_')
    sd=parts[-1]
    start='_'.join(parts[0:-1])
    num_summed=0
    for im in glob(f"{start}_{sd}.*bis"):
        b,ext=splitext(im)
        b=b.lstrip(f'{start}_{sd}')
        fstart=f"{start}{b}"
        if fstart in files:
            files[fstart].append(im)
        else:
            files[fstart]=[im]

for f,specs in files.items():
    outf=f'{f}.avg.bis'
    if exists(outf):
        print(f'skipping {outf}')
        continue
    num_summed=0
    for sf in specs:
        spec = np.fromfile(sf, dtype=np.float32)
        #try:
        #    spec = np.fromfile(specfile, dtype=np.float32)
        #except:
        #    print(f"error reading {sf}")
        #    continue
        if num_summed == 0:
            sum = spec.astype(np.float64)
        else:
            if len(spec.shape) != 1 or spec.shape[0] != sum.shape[0]:
                print(f'spectrum {f} has a different size than previous ones'. Skipping)
                continue
            sum += spec.astype(np.float64)
        num_summed += 1
    if num_summed <= 1:
        print(" summed 1 or fewer spectra for {outf}: no output generated")
    else:
        print(f"saving {outf}. summed {num_summed}")
        try:
            (sum/num_summed).astype(np.float32).tofile(outf)
        except:
            print("error generating {outf}")
            exit(1)

exit(0)
