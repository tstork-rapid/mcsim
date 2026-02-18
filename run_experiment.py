#! /usr/bin/env python3
import click
import os
from glob import glob
from sys import exit
import subprocess
from multiprocessing import cpu_count
from runcmd import runcmd, waitall
import numpy as np
import NumpyIm as npi

def osemmw(manufacturer, startseed, endseed, s, r, d):
    # Process inputs
    if "siemens" in manufacturer.lower():
        bin_width = 0.47952
    elif "ge" in manufacturer.lower():
        bin_width = 0.442
    else:
        print("Unknown manufacturer.")
        exit(1)

    half_bin_width = bin_width / 2
    print(f"Manufacturer, {manufacturer}, with a bin width of {bin_width}") if d else None

    # Make required folders if they don't exist
    main_dir = os.getcwd()

    if not os.path.isdir(main_dir + "/sim_inputs"):
        os.mkdir("sim_inputs")
    if not os.path.isdir(main_dir + "/sim_outputs"):
        os.mkdir("sim_outputs")
    if not os.path.isdir(main_dir + "/processed_outputs"):
        os.mkdir("processed_outputs")
    if not os.path.isdir(main_dir + "/recon"):
        os.mkdir("recon")

    # Change directory to sim_inputs
    os.chdir(main_dir + "/sim_inputs")

    # Check that .win file exists in sim_inputs
    win_files = glob("*.win")
    if len(win_files) == 0:
        print(".win file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(win_files) > 1:
        print("More than one .win file exists in the sim_inputs folder")
        exit(1)
    win_file = win_files[0].split("/")[-1]

    # Check that .par file exists in sim_inputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the sim_inputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Check that .smc file exists in sim_inputs
    smc_files = glob("*.smc")
    if len(smc_files) == 0:
        print(".smc file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(smc_files) > 1:
        print("More than one .smc file exists in the sim_inputs folder")
        exit(1)
    smc_file = smc_files[0].split("/")[-1]

    # Check if there are any .im files in sim_inputs
    if any(glob("*.im")):
        print(".im files exist in sim_inputs, skipping mkphan.py") if d else None
    else:
        # Check that .dat file exists in sim_inputs
        dat_files = glob("*.dat")
        if len(dat_files) == 0:
            print(".dat file doesn't exist in sim_inputs folder")
            exit(1)
        elif len(dat_files) > 1:
            print("More than one .dat file exists in sim_inputs folder")
            exit(1)
        dat_file = dat_files[0].split("/")[-1]
        
        # Run mkphan.py to create .im files
        voi_name = dat_file.replace(".dat", "")
        subprocess.call(["mkphan.py", str(half_bin_width), "256", "256", "256", dat_file, voi_name])

    # Get .im outputs from mkphan.py
    im_files = glob("*.im")
    
    # Copy .im, .win, .par, and .smc files to sim_outputs
    for file in im_files:
        new_file = file.split("/")[-1]

        num_periods = new_file.count(".")
        num_replacements = num_periods - 1

        if num_replacements > 0:
            new_file = new_file.replace(".", "_", num_replacements) # SIMIND doesn't like period separators, replace with underscores

        subprocess.call(["cp", file, main_dir + "/sim_outputs/" + new_file])

    subprocess.call(["cp", win_file, main_dir + "/sim_outputs/" + win_file])
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])
    subprocess.call(["cp", smc_file, main_dir + "/sim_outputs/" + smc_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    if s:
        # Run SIMIND
        subprocess.call(["nohup", "nice", "-n", "19", "runspectsims.py", par_file, str(startseed), str(endseed)])
    else:
        print("Skipping SIMIND due to flag") if d else None

    # Check that all SIMIND runs completed sucessfully
    # TODO

    # Change directory to processed_outputs
    os.chdir(main_dir + "/processed_outputs")

    # Check that .par file exists in processed_outputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in processed_outputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the processed_outputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Copy .par file from processed_outputs to sim_outputs
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    # Check if there are any prj files in sim_outputs
    if any(glob("*prj*.im")):
        print("prj files exist in sim_outputs, skipping post_process_simind.py") if d else None
    else:
        # Post process SIMIND outputs
        subprocess.call(["nice", "-n", "19", "post_process_simind.py", par_file])

    # Get .im outputs from post_process_simind.py
    processed_files = glob("*prj*.im")

    # Copy processed SIMIND outputs to processed_outputs folder
    for file in processed_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/processed_outputs/" + new_file])

    # Check if there are any atn files in sim_outputs
    if any(glob("atn*.im")):
        print("atn files exist in sim_outputs, skipping create_atn.py") if d else None
    else:
        # Create attenuation files
        subprocess.call(["create_atn.py"])

    # Get ant outputs from create_atn.py
    atn_files = glob("atn*.im")

    # Copy atn files to processed_outputs folder
    for file in atn_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/processed_outputs/" + new_file])

    # Change directory to processed_outputs
    os.chdir(main_dir + "/processed_outputs")

    # Copy processed outputs to recon folder
    prj_files = glob("collapsed*.im")
    atn_files = glob("atn*.im")

    for file in prj_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/recon/" + new_file])

    for file in atn_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/recon/" + new_file])

    # Change directory to recon
    os.chdir(main_dir + "/recon")

    # Check if any .dat files in recon
    if any(glob("*.dat")):
        print(".dat file exists in recon, skipping computeorbit") if d else None
    else:
        # Create oribt file
        subprocess.call(["computeorbit", "120", "-90", "-360", "64", "1", str(bin_width), "0.01", "2", "atn.im", "orbit.dat"])

    # Check that .par files exist in recon
    par_files = glob("*.par")
    if len(par_files) == 0:
        print("No .par files exist in recon folder")
        exit(1)
    elif len(par_files) < 4 or len(par_files) > 4:
        print("4 .par files don't exist in the recon folder")
        exit(1)

    # Check if there are any recon files in recon
    if any(glob("*.log")):
        print("Recon files exist in recon folder, skipping osemmw") if d else None
    else:
        # Run osemmw
        if r:
            par_files = glob("*osemmw*.par")
            par_file = par_files[0].split("/")[-1]
            cmd_nf = f"nohup nice -n 19 ~frey/bin/osemmw {par_file} collapsed.prj.nf.w0 atn.w1 ads.nf >& ads.nf.log &"
            cmd_n = f"nohup nice -n 19 ~frey/bin/osemmw {par_file} collapsed.prj.n.w0 atn.w1 ads.n >& ads.n.log &"
            runcmd(cmd_nf,cpu_count(), 60)
            runcmd(cmd_n,cpu_count(), 60)
            waitall()

            print("Running OSEMMW in the background")
        else:
            print("Skipping OSEMMW due to flag") if d else None

def osem(manufacturer, startseed, endseed, s, r, d):
    # Process inputs
    if "siemens" in manufacturer.lower():
        bin_width = 0.47952
    elif "ge" in manufacturer.lower():
        bin_width = 0.442
    else:
        print("Unknown manufacturer.")
        exit(1)

    half_bin_width = bin_width / 2
    print(f"Manufacturer, {manufacturer}, with a bin width of {bin_width}") if d else None

    # Make required folders if they don't exist
    main_dir = os.getcwd()

    if not os.path.isdir(main_dir + "/sim_inputs"):
        os.mkdir("sim_inputs")
    if not os.path.isdir(main_dir + "/sim_outputs"):
        os.mkdir("sim_outputs")
    if not os.path.isdir(main_dir + "/processed_outputs"):
        os.mkdir("processed_outputs")
    if not os.path.isdir(main_dir + "/recon"):
        os.mkdir("recon")

    # Change directory to sim_inputs
    os.chdir(main_dir + "/sim_inputs")

    # Check that .win file exists in sim_inputs
    win_files = glob("*.win")
    if len(win_files) == 0:
        print(".win file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(win_files) > 1:
        print("More than one .win file exists in the sim_inputs folder")
        exit(1)
    win_file = win_files[0].split("/")[-1]

    # Check that .par file exists in sim_inputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the sim_inputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Check that .smc file exists in sim_inputs
    smc_files = glob("*.smc")
    if len(smc_files) == 0:
        print(".smc file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(smc_files) > 1:
        print("More than one .smc file exists in the sim_inputs folder")
        exit(1)
    smc_file = smc_files[0].split("/")[-1]

    # Check if there are any .im files in sim_inputs
    if any(glob("*.im")):
        print(".im files exist in sim_inputs, skipping mkphan.py") if d else None
    else:
        # Check that .dat file exists in sim_inputs
        dat_files = glob("*.dat")
        if len(dat_files) == 0:
            print(".dat file doesn't exist in sim_inputs folder")
            exit(1)
        elif len(dat_files) > 1:
            print("More than one .dat file exists in sim_inputs folder")
            exit(1)
        dat_file = dat_files[0].split("/")[-1]
        
        # Run mkphan.py to create .im files
        voi_name = dat_file.replace(".dat", "")
        subprocess.call(["mkphan.py", str(half_bin_width), "256", "256", "256", dat_file, voi_name])

    # Get .im outputs from mkphan.py
    im_files = glob("*.im")
    atn_files = glob("*atn*.im")
    if len(atn_files) == 0:
        atn_files = glob("*dens*.im")

    # Copy .im, .win, .par, and .smc files to sim_outputs
    for file in im_files:
        new_file = file.split("/")[-1]

        num_periods = new_file.count(".")
        num_replacements = num_periods - 1

        new_file = new_file.replace(".", "_", num_replacements) # SIMIND doesn't like period separators, replace with underscores
        subprocess.call(["cp", file, main_dir + "/sim_outputs/" + new_file])

    subprocess.call(["cp", win_file, main_dir + "/sim_outputs/" + win_file])
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])
    subprocess.call(["cp", smc_file, main_dir + "/sim_outputs/" + smc_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    if s:
        # Run SIMIND
        subprocess.call(["nohup", "nice", "-n", "19", "runspectsims.py", par_file, str(startseed), str(endseed)])
    else:
        print("Skipping SIMIND due to flag") if d else None

    # Check that all SIMIND runs completed sucessfully
    # TODO

    # Change directory to processed_outputs
    os.chdir(main_dir + "/processed_outputs")

    # Check that .par file exists in processed_outputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in processed_outputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the processed_outputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Copy .par file from processed_outputs to sim_outputs
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    # Check if there are any prj files in sim_outputs
    if any(glob("*prj*.im")):
        print("prj files exist in sim_outputs, skipping post_process_simind.py") if d else None
    else:
        # Post process SIMIND outputs
        subprocess.call(["nice", "-n", "19", "post_process_simind.py", par_file])

    # Get .im outputs from post_process_simind.py
    processed_files = glob("*prj*.im")

    # Copy processed SIMIND outputs to processed_outputs folder
    for file in processed_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/processed_outputs/" + new_file])

    # Check if there are any atn files in sim_outputs
    if any(glob("atn*.im")):
        print("atn files exist in sim_outputs, skipping hu2atn") if d else None
    else:
        peaks_text = input("Enter in keVs of peaks (separated by ,): ")
        peaks = peaks_text.strip().split(",")
        peaks = [float(peak) for peak in peaks]
        
        # Get atn file
        atn_file = atn_files[0].split("/")[-1]
        infile = main_dir + "/sim_inputs/" + atn_file
        atn = npi.ArrayFromIm(infile)

        # Check if there is only water and air
        mask = (atn != 0) & (atn != 1000)
        has_other_values = np.any(mask)
        if has_other_values:
            print("Script doesn't handle all densities in the atn image.")
            exit(1)

        # Convert atn file from g/cc*1000 to HU
        atn[atn == 0] = -1000 # Convert air
        atn[atn == 1000] = 0 # Convert water
        npi.ArrayToIm(atn.astype(np.float32), "ct.im")

        # Reduct CT to 128
        subprocess.call(["collapse3d", "-a", "2", "2", "2", "ct.im", "ct_128.im"])

        # Convert to atn/cm
        for peak in peaks:
            subprocess.call(["hu2atn", "-s", str(bin_width), "-e", str(peak), "ct_128.im", f"atn.{peak}.im"])

    # Get atn outputs from hu2atn
    atn_files = glob("atn*.im")

    # Copy atn files to processed_outputs folder
    for file in atn_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/processed_outputs/" + new_file])

    # Change directory to processed_outputs
    os.chdir(main_dir + "/processed_outputs")

    # Copy processed outputs to recon folder
    prj_files = glob("collapsed*.im")
    atn_files = glob("atn*.im")

    for file in prj_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/recon/" + new_file])

    for file in atn_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/recon/" + new_file])

    # Change directory to recon
    os.chdir(main_dir + "/recon")

    # Check if any .dat files in recon
    if any(glob("*.dat")):
        print(".dat file exists in recon, skipping computeorbit") if d else None
    else:
        # Create oribt file
        subprocess.call(["computeorbit", "120", "-90", "-360", "64", "1", str(bin_width), "0.01", "2", atn_files[0], "orbit.dat"])

    # Check that .par files exist in recon
    par_files = glob("*.par")
    if len(par_files) == 0:
        print("No .par files exist in recon folder")
        exit(1)

    # Check if there are any recon files in recon
    if any(glob("*.log")):
        print("Recon files exist in recon folder, skipping osems") if d else None
    else:
        # Run osems
        if r:
            win_text = input("Enter window numbers to reconstruct (separated by ,): ")
            win = win_text.strip().split(",")
            win = [int(w) for w in win]

            peaks_text = input("Enter in keVs of peaks for those window numbers (separated by ,): ")
            peaks = peaks_text.strip().split(",")
            peaks = [float(peak) for peak in peaks]

            for i, w in enumerate(win):
                peak = peaks[i]
                par_files = glob(f"*osem*w{w}*.par")
                par_file = par_files[0].split("/")[-1]

                cmd_nf = f"nohup nice -n 19 osems {par_file} collapsed.prj.nf.w0{w}.im atn.{peak}.im ads.nf.w0{w} >& ads.nf.w0{w}.log &"
                cmd_n = f"nohup nice -n 19 osems {par_file} collapsed.prj.n.w0{w}.im atn.{peak}.im ads.n.w0{w} >& ads.n.w0{w}.log &"
                runcmd(cmd_nf,cpu_count(), 60)
                runcmd(cmd_n,cpu_count(), 60)

            waitall()
            print("Running OSEMS in the background")
        else:
            print("Skipping OSEMS due to flag") if d else None


def psen(manufacturer, startseed, endseed, s, d):
    # Process inputs
    if "siemens" in manufacturer.lower():
        bin_width = 0.47952
    elif "ge" in manufacturer.lower():
        bin_width = 0.442
    else:
        print("Unknown manufacturer.")
        exit(1)

    half_bin_width = bin_width / 2
    print(f"Manufacturer, {manufacturer}, with a bin width of {bin_width}") if d else None

    # Make required folders if they don't exist
    main_dir = os.getcwd()

    if not os.path.isdir(main_dir + "/sim_inputs"):
        os.mkdir("sim_inputs")
    if not os.path.isdir(main_dir + "/sim_outputs"):
        os.mkdir("sim_outputs")
    if not os.path.isdir(main_dir + "/processed_outputs"):
        os.mkdir("processed_outputs")

    # Change directory to sim_inputs
    os.chdir(main_dir + "/sim_inputs")

    # Check that .win file exists in sim_inputs
    win_files = glob("*.win")
    if len(win_files) == 0:
        print(".win file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(win_files) > 1:
        print("More than one .win file exists in the sim_inputs folder")
        exit(1)
    win_file = win_files[0].split("/")[-1]

    # Check that .par file exists in sim_inputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the sim_inputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Check that .smc file exists in sim_inputs
    smc_files = glob("*.smc")
    if len(smc_files) == 0:
        print(".smc file doesn't exist in sim_inputs folder")
        exit(1)
    elif len(smc_files) > 1:
        print("More than one .smc file exists in the sim_inputs folder")
        exit(1)
    smc_file = smc_files[0].split("/")[-1]

    # Check if there are any .im files in sim_inputs
    if any(glob("*.im")):
        print(".im files exist in sim_inputs, skipping mkphan.py") if d else None
    else:
        # Check that .dat file exists in sim_inputs
        dat_files = glob("*.dat")
        if len(dat_files) == 0:
            print(".dat file doesn't exist in sim_inputs folder")
            exit(1)
        elif len(dat_files) > 1:
            print("More than one .dat file exists in sim_inputs folder")
            exit(1)
        dat_file = dat_files[0].split("/")[-1]
        
        # Run mkphan.py to create .im files
        voi_name = dat_file.replace(".dat", "")
        subprocess.call(["mkphan.py", str(half_bin_width), "256", "256", "256", dat_file, voi_name])

    # Get .im outputs from mkphan.py
    im_files = glob("*.im")
    atn_files = glob("*atn*.im")
    if len(atn_files) == 0:
        atn_files = glob("*dens*.im")

    # Copy .im, .win, .par, and .smc files to sim_outputs
    for file in im_files:
        new_file = file.split("/")[-1]

        num_periods = new_file.count(".")
        num_replacements = num_periods - 1

        new_file = new_file.replace(".", "_", num_replacements) # SIMIND doesn't like period separators, replace with underscores
        subprocess.call(["cp", file, main_dir + "/sim_outputs/" + new_file])

    subprocess.call(["cp", win_file, main_dir + "/sim_outputs/" + win_file])
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])
    subprocess.call(["cp", smc_file, main_dir + "/sim_outputs/" + smc_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    if s:
        # Run SIMIND
        subprocess.call(["nohup", "nice", "-n", "19", "runspectsims.py", par_file, str(startseed), str(endseed)])
    else:
        print("Skipping SIMIND due to flag") if d else None

    # Check that all SIMIND runs completed sucessfully
    # TODO

    # Change directory to processed_outputs
    os.chdir(main_dir + "/processed_outputs")

    # Check that .par file exists in processed_outputs
    par_files = glob("*.par")
    if len(par_files) == 0:
        print(".par file doesn't exist in processed_outputs folder")
        exit(1)
    elif len(par_files) > 1:
        print("More than one .par file exists in the processed_outputs folder")
        exit(1)
    par_file = par_files[0].split("/")[-1]

    # Copy .par file from processed_outputs to sim_outputs
    subprocess.call(["cp", par_file, main_dir + "/sim_outputs/" + par_file])

    # Change directory to sim_outputs
    os.chdir(main_dir + "/sim_outputs")

    # Check if there are any prj files in sim_outputs
    if any(glob("*prj*.im")):
        print("prj files exist in sim_outputs, skipping post_process_simind.py") if d else None
    else:
        # Post process SIMIND outputs
        subprocess.call(["nice", "-n", "19", "post_process_simind.py", par_file])

    # Get .im outputs from post_process_simind.py
    processed_files = glob("prj.nf*.im") # Only grabbing non-collapsed noise free

    # Copy processed SIMIND outputs to processed_outputs folder
    for file in processed_files:
        new_file = file.split("/")[-1]
        subprocess.call(["cp", file, main_dir + "/processed_outputs/" + new_file])

    # Change directory to processed outputs
    os.chdir(main_dir + "/processed_outputs")

    # Calculate CFs
    processed_files.sort()
    with open("CFs.txt", "w") as cf_file:
        for file in processed_files:
            pix = npi.ArrayFromIm(file)
            Z, Y, X = pix.shape
            for frame in range(Z):
                CF = np.sum(pix[frame, :, :])
                line = f"{file} frame {frame}: {CF} cps/MBq"
                print(line)
                cf_file.write(line + "\n")

@click.command(help="""
Requires .dat file for mkphan.py to make the .im files for SIMIND, .win file for SIMIND, .par file for SIMIND, .smc file for SIMIND, etc. to exist
Flow:
1. Uses manufacturer input to determine bin width
2. Uses .dat 
""")
@click.argument("mode", required=True)
@click.argument("manufacturer", required=True)
@click.argument("startseed", required=True)
@click.argument("endseed", required=True)
@click.option(
    "-s",
    is_flag=True,
    required=False,
    default=True,
    help="Skip running SIMIND",
)
@click.option(
    "-r",
    is_flag=True,
    required=False,
    default=True,
    help="Skip running OSEMS/OSEMMW",
)
@click.option(
    "-d",
    is_flag=True,
    required=False,
    default=False,
    help="Print debug information",
)

def experiment(mode, manufacturer, startseed, endseed, s, r, d):
    if "osemmw" in mode.lower():
        osemmw(manufacturer, startseed, endseed, s, r, d)
    elif "osem" in mode.lower():
        osem(manufacturer, startseed, endseed, s, r, d)
    elif "psen" in mode.lower():
        psen(manufacturer, startseed, endseed, s, d)
    else:
        print("Mode not recognized!")
        exit(1)

if __name__ == "__main__":
    experiment()