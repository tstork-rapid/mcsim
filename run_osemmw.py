#! /usr/bin/env python3
from os.path import exists
from multiprocessing import cpu_count
from sys import exit
from runcmd import runcmd, waitall

# Declare variables
prj_nf = "collapsed.prj.nf.w0"
prj_n = "collapsed.prj.n.w0"
atn = "atn.w1"
out_prefix = "ads"

# Ensure projections exist
if not exists(prj_nf + "1.im") or not exists(prj_nf + "2.im"):
    print("Noise free projections are missing")
    exit(1)
if not exists(prj_n + "1.im") or not exists(prj_n + "2.im"):
    print("Noisey projections are missing")
    exit(1)

# Ensure attenuation maps exist
if not exists(atn + ".im") or not exists(atn + "i1.im") or not exists(atn + "i2.im"):
    print("Attenuation maps are missing")
    exit(1)

# Ensure outputs don't exist
if exists(out_prefix + "nf.reconi1.1.im") or exists (out_prefix + "n.reconi1.1.im"):
    print("Outputs already exist, exiting to prevent overwriting")
    exit(1)

# Reconstruct noise free projections
cmd = f"~frey/bin/osemmw mwosem.2ws.par {prj_nf} {atn} {out_prefix}.nf.recon >& {out_prefix}.nf.recon.log"
runcmd(cmd,cpu_count())
waitall()

# Reconstruct noisey projections
cmd = f"~frey/bin/osemmw mwosem.2ws.par {prj_n} {atn} {out_prefix}.n.recon >& {out_prefix}.n.recon.log"
runcmd(cmd,cpu_count())