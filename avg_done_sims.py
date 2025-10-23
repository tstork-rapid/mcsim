#! /usr/bin/env python3
from sys import exit
from glob import glob
import re
import numpy as np
import NumpyIm as npi
from os.path import exists, splitext
from subprocess import call
from runcmd import runcmd

"""
averages mulitple runs of simulations. Simulation names are assumed to be of the form a_[b_...]SD.ext.im
SD is the integer seed, and simulations are averaged over that.
"""

files = {}
for res in glob("*.res"):
    parts = res.replace(".res", "").split("_")
    sd = parts[-1]
    start = "_".join(parts[0:-1])
    num_summed = 0
    for im in glob(f"{start}_{sd}.*im"):
        b, ext = splitext(im)
        b = b.lstrip(f"{start}_{sd}")
        fstart = f"{start}{b}"
        if fstart in files:
            files[fstart].append(im)
        else:
            files[fstart] = [im]

for f, ims in files.items():
    print(f"{f}:{len(ims)} {ims[0]}")
    outf = f"{f}.avg.im"
    if exists(outf):
        print(f"skipping {outf}")
        continue
    num_summed = 0
    for im in ims:
        try:
            pix = npi.ArrayFromIm(im)
        except npi.error as e:
            print(f"error reading {im}")
            print("   skipping")
            continue
        if num_summed == 0:
            sum = pix.astype(np.float64)
        else:
            sum += pix.astype(np.float64)
        num_summed += 1
    if num_summed <= 1:
        print(" summed 1 or fewer images for {outf}: no output generated")
    else:
        print(f"saving {outf}. summed {num_summed}")
        try:
            npi.ArrayToIm(sum.astype(np.float32) / num_summed, outf)

            # Copy the header from a simulation output to the averaged file
            cmd = f"imgcpinfo {ims[0]} {outf}" # overwrites previous output
            print("Running: " + cmd)
            runcmd(cmd,1,2)

        except npi.error as e:
            print("error generating {outf}: {e}")
            exit(1)

exit(0)
