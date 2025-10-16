#! /usr/bin/env python3
from runcmd import runcmd, waitall
import os
import re
from time import sleep
from sys import exit
from os.path import exists, getsize
from multiprocessing import cpu_count
import configparser
import click
import numpy as np
import NumpyIm as npi


def get_parms(parfile, int_parms=[], float_parms=[], str_parms=[], list_parms=[]):
    config = configparser.ConfigParser()
    config.read(parfile)
    print(config.sections())
    configparms = config["parms"]
    parms = dict()
    all_parms = int_parms + float_parms + str_parms + list_parms
    assert len(all_parms) == len(set(all_parms)), (
        "there must be overlapping names in some parameter classes"
    )
    try:
        for p in int_parms:
            parms[p] = int(configparms[p])
        for p in str_parms:
            parms[p] = configparms[p]
        for p in float_parms:
            parms[p] = float(configparms[p])
        for p in list_parms:
            parms[p] = re.split(r"[, ]", configparms[p])
    except configparser.Error as e:
        print(f"Error parsing {parfile}: {e}")
        exit(1)
    if "smc_dir" in parms:
        # smc_dir must end with a /
        parms["smc_dir"] += "" if parms["smc_dir"].endswith("/") else "/"
    isd_files = get_files(config, "isd_files", parms["radionuclides"], ".isd")
    return parms, isd_files


def get_files(config, section, rns, ext):
    if section not in config:
        raise ValueError(f"Section {section} was not found in the configuration file")
    if not ext.startswith("."):
        ext = "." + ext
    configparms = config[section]
    files = dict()
    for rn in rns:
        fn = configparms[rn] if rn in configparms else f"{rn}"
        if not fn.endswith(ext):
            fn = fn + ext
        files[rn] = fn
    return files


def get_object_sums(objs):
    sums = {}
    maxsum = 0.0
    errs = False
    first = True
    for o in objs:
        if o in sums:
            errs = True
            print(f"object {o} is duplicated")
        try:
            pix = npi.ArrayFromIm(f"{o}.im")
        except npi.error as e:
            print(f"error reading source image for :{o}: {e}")
            errs = True
            continue
        if pix.min() < 0.0:
            print("min pixel for {o} is < 0")
            errs = True
        sums[o] = pix.sum()
        maxsum = max(maxsum, sums[o])
        if first:
            first = False
            objshape = pix.shape
            if len(objshape) != 3:
                print(f"{o} is not a 3d image")
                errs = 1
                continue
        else:
            if objshape != pix.shape:
                print(
                    f"{o} has a different size than previous objects: {pix.shape} vs {objshape}"
                )
                errs = True
                continue
        if not exists(f"{o}.smi"):
            pix.astype(np.uint16).tofile(f"{o}.smi")
        if getsize(f"{o}.smi") != 2 * pix.flatten().shape[0]:
            print("{o}.smi has unexpected size")
    if errs:
        print("errors reading objects: exiting")
        exit(1)
    return sums, maxsum, objshape


@click.command()
@click.option(
    "--maxproc",
    required=False,
    type=int,
    default=None,
    help="maximum number of processes to run (default is number of CPUs on the system)",
)
@click.argument("configfile", type=click.Path(exists=True), required=True)
@click.argument("startseed", type=int, required=True)
@click.argument("endseed", type=int, required=True)
def runspectsims(configfile, startseed, endseed, maxproc):
    ncpus = cpu_count()
    if maxproc is None:
        maxproc = ncpus
    else:
        maxproc = min(maxproc, ncpus)
    print(f"run up to {maxproc} jobs at a time")

    # these are the parameters that are expected to be in the 'parms' section
    # of the configfile
    int_parms = ["NN", "score41_val", "nang"]
    str_parms = [
        "simind",
        "smc_file",
        "ewin_file",
        "smc_dir",
        "collimator",
        "densmap",
        "prefix",
    ]
    float_parms = [
        "pixsize",
        "photon_energy",
        "e_low",
        "e_high",
    ]
    list_parms = [
        "objects",
        "radionuclides",
    ]
    parms, isd_files = get_parms(
        configfile,
        int_parms=int_parms,
        float_parms=float_parms,
        str_parms=str_parms,
        list_parms=list_parms,
    )
    densmap = parms["densmap"]
    ewin_file = parms["ewin_file"]
    if not exists(densmap + ".im"):
        print(f"density map {densmap}.im does not exist")
        exit(1)
    if not exists(ewin_file + ".win"):
        print(f"energy window file {ewin_file + '.win'} does not exist")
        exit(1)
    dens = npi.ArrayFromIm(f"{densmap}.im")
    print(dens.min(), dens.max())
    if dens.min() < 0 or dens.max() > 5000:
        print("density map voxels must be >= 0 and <= 5")
        exit(1)
    if not exists(f"{densmap}.dmi"):
        dens.astype(np.uint16).tofile(f"{densmap}.dmi")
    if getsize(f"{densmap}.dmi") != dens.flatten().shape[0] * 2:
        print(f"{densmap}.dmi has unexpected size")
        exit(1)
    os.environ["SMC_DIR"] = parms["smc_dir"]
    simind = parms["simind"]
    print(os.environ["SMC_DIR"])
    print(f"running {simind} using SMC_DIR={parms['smc_dir']}")
    objs = parms["objects"]
    objsums, maxsum, objshape = get_object_sums(objs)
    if objshape != dens.shape:
        print(f"{densmap}.im and objects must be the same shape")
        exit(1)
    print(objsums)
    print(maxsum)
    # simulation flags
    # FA:1: no screen output
    # FA:8: don't use random seed
    # options
    # FD: density map name
    # FS: source map name
    # PX: pixel size of source map
    # SD: seed
    # FI: isotope file
    # RR: skip random numbers
    # NN: scale factor for photons in voxelized phantoms.
    # Index values
    # 01: energy: negative means to use the isotope file
    # 02: source half-length
    # 05: phantom half-length
    # 20:  Upper energy threshold
    # 21:  lower energy threshold
    # 28: voxel size in output image
    # 31: voxel size in density map
    # 84: score routine: 41-muliplewin
    # 76: matrix size image I
    # 77: matrix size image J
    # 78: matrix size density map I
    # 79: matrix size source map I
    # 81: matrix size density map J
    # 82: matrix size source map J

    pixsize = parms["pixsize"]
    zdim, ydim, xdim = objshape
    z_halflen = pixsize * zdim / 2.0
    prefix = parms["prefix"]
    NN = parms["NN"]
    for seed in range(startseed, endseed):
        for obj in objs:
            for rn in parms["radionuclides"]:
                isd_file = isd_files[rn]
                print(f"running {prefix} {rn} {obj} {seed} nn={NN}")
                opts = (
                    f"/FA:1/FA:8/FD:{densmap}/FS:{obj}/PX:{pixsize}/RR:{seed}"
                    f"/SD:{seed}/FI:{isd_file}/01:{parms['photon_energy']}"
                    f"/02:{z_halflen}/05:{z_halflen}/28:{pixsize}/31:{pixsize}"
                    f"/20:{parms['e_high']}/21:{parms['e_low']}/NN:{NN}/TR:5"
                    f"/31:{pixsize}/29:{parms['nang']}/84:41/CA:{parms['score41_val']}/34:{zdim}"
                    f"/76:{xdim}/77:{zdim}/78:{xdim}/79:{xdim}/81:{ydim}/82:{ydim}/83:-10"
                )
                # this saves an aligned attenuation map only for the start seed
                opts += "/FA:15" if seed != startseed else "/TR:15"
                opts += f"/84:41/fw:{ewin_file}"
                base = f"{prefix}_{rn}_{obj}_{seed}"
                cmd = f"{simind} voxphan{opts}/CC:{parms['collimator']} {base} >& {base}.log"
                if not exists(f"{base}.log") and not exists(f"{base}.res"):
                    print(cmd)
                    with open(f"{base}.log", "w") as fp:
                        fp.write("\n")
                    runcmd(cmd, maxruns=maxproc)
                    sleep(1)
                else:
                    print("skipping", prefix, obj, seed)

    waitall()


if __name__ == "__main__":
    runspectsims()
