#! /usr/bin/env python3
from runcmd import runcmd, waitall
import os
from time import sleep
from sys import argv, exit
from os.path import exists,getsize
from math import ceil
from multiprocessing import cpu_count
import configparser
import click
from os.path import exists
import numpy as np
import NumpyIm as npi

def get_object_sums(objs):
    sums={}
    maxsum=0.0
    errs=False
    first=True
    for o in objs:
        if o in sums: 
            errs=True
            print(f'object {o} is duplicated')
        try:
            pix=npi.ArrayFromIm(f'{o}.im')
        except npi.error as e:
            print(f'error reading source image for :{o}: {e}')
            errs=True
            continue
        if pix.min() < 0.0:
            print('min pixel for {o} is < 0')
            errs=True
        sums[o]=pix.sum()
        maxsum = max(maxsum,sums[o])
        if first:
            first=False
            objshape=pix.shape
            if len(objshape)!= 3:
                print(f'{o} is not a 3d image')
                errs=1
                continue
        else:
            if objshape != pix.shape:
                print(f'{o} has a different size than previous objects: {pix.shape} vs {objshape}')
                errs=True
                continue
        if not exists(f'{o}.smi'):
            pix.astype(np.uint16).tofile(f'{o}.smi')
        if getsize(f'{o}.smi') != 2*pix.flatten().shape[0]:
            print('{o}.smi has unexpected size')
    if errs:
        print('errors reading objects: exiting')
        exit(1)
    return sums,maxsum,objshape

@click.command()
@click.option(
    "--maxproc",
    required=False,
    type=int,
    default=None,
    help='maximum number of processes to run (default is number of CPUs on the system)',
)
@click.argument('configfile',type=click.Path(exists=True),required=True)
@click.argument('startseed',type=int,required=True)
@click.argument('endseed',type=int,required=True)
def runspectsims(configfile, startseed, endseed, maxproc):
    ncpus=cpu_count()
    print(configfile)
    with open(configfile,'r') as f:
        pars='[parms]\n' + f.read()
    config=configparser.ConfigParser()
    config.read_string(pars)
    print(config.sections())
    parms=config['parms']
    if maxproc is None:
        maxproc = ncpus
    else:
        maxproc = min(maxproc,ncpus)
    print(f'run up to {maxproc} jobs at a time')

    try:
        simind = parms['simind']
        smc_dir = parms['smc_dir']
        smc_dir = smc_dir + ('/' if smc_dir[-1] != '/' else '')
        collimator=parms['collimator']
        NN = int(parms['nn'])
        pixsize=parms['pixsize']
        photon_energy=parms['photon_energy']
        isdfile=parms['isdfile']
        densmap=parms['densmap']
        objs=parms['objects'].split()
        e_low=parms['e_low']
        e_high=parms['e_high']
        prefix=parms['prefix']
        score41_val=parms['score41_val']
        ewin_file=parms['ewin_file']
        nang=parms['nang']
    except configparser.Error as e:
        print(f'Error parsing {configfile}: {e}')
        exit(0)

    if not exists(densmap+'.im'):
        print(f'density map {densmap}.im does not exist')
        exit(0)
    dens=npi.ArrayFromIm(f'{densmap}.im')
    if dens.min() <1 | dens.max() > 5000:
        print('density map voxels must be > 0 and <= 5')
        exit(0)
    if not exists(f'{densmap}.dmi'):
        dns.astype(np.uint16).tofile(f'{densmap}.dmi')
    if getsize(f'{densmap}.dmi') != dens.flatten().shape[0]*2:
        print(f'{densmap}.dmi has unexpected size')
        exit(0)
    os.environ["SMC_DIR"] = smc_dir
    print(simind)
    print(os.environ["SMC_DIR"])
    objsums,maxsum,objshape=get_object_sums(objs)
    if objshape != dens.shape:
        print(f'{densmap}.im and objects must be the same shape')
        exit(0)
    print(objsums)
    print(maxsum)
    # simulation flags
    # 1: t screen results
    # options
    # FD: density map name
    # FS: source map name
    # PX: pixel size of source map
    # SD: seed
    # FI: isotope file
    # NN: scale factor for photons in voxelized phantoms.
    # Index values
    # 01: energy: negative means to use the isotope file
    # 05: phantom half-lengthj
    # 20:  Upper energy threshold
    # 21:  lower energy threshold
    # 84: score routine: 41-muliplewin
    zdim,ydim,xdim=objshape
    for seed in range(startseed, endseed):
        for obj in objs:
            print(f'running {prefix} {obj} {seed} nn={NN}')
            opts = (
                    f"/FA:1/FA:8/FD:{densmap}/FS:{obj}/PX:{pixsize}/RR:{seed}/SD:{seed}/FI:{isdfile}/01:{photon_energy}/"
                    f"20:300/21:100/NN:{NN}/TR:5/31:{pixsize}/29:{nang}/84:41/CA:{score41_val}/34:{zdim}"
                    f"/76:{xdim}/77:{zdim}/78:{xdim}/:79:{xdim}/81:{ydim}/82:{ydim}"
            )
            opts += '/FA:15' if seed != startseed else '/TR:15'
            opts += f"/84:41/fw:{ewin_file}"
            base=f"{prefix}_{obj}_{seed}"
            cmd = f"{simind} voxphan{opts}/CC:{collimator} {base} >& {base}.log"
            if not exists(f"{base}.log") and not exists(f"{base}.res"):
                print(cmd)
                with open(f"{base}.log",'w') as fp:
                    fp.write('\n')
                runcmd(cmd, maxruns=maxproc)
                sleep(1)
            else:
                print("skipping", prefix, obj, seed)
    waitall()

if __name__ == "__main__":
    runspectsims()
