#! /usr/bin/env python3
from os.path import exists
from sys import exit, argv
from glob import glob
import numpy as np
import NumpyIm as npi
from runcmd import runcmd

# Ensure a keV was input by the user
if len(argv) < 2:
    print("Usage: create_atn.py keV [keV 2] ... [keV n]")
    print("Uses SIMIND density map to make attenuation maps (downsampled to 128x128x128 if needed) at the desired keVs")
    exit(1)

# Make a list of keVs from user input
keVs = []
for i in range(1,len(argv)):
    keVs.append(float(argv[i]))

# Check if SIMIND density map exists
dens_map_txt = "*dens*.im"
dens_map_files = glob(dens_map_txt)
if len(dens_map_files) < 1:
    print("No density map found")
    exit(1)
elif len(dens_map_files) > 1:
    print("More than one density map found, using " + dens_map_files[0])

# Load density map
dens_map_file = dens_map_files[0]
pix = npi.ArrayFromIm(dens_map_file)

# Check if there is only water and air
mask = (pix != 0) & (pix != 1000)
has_other_values = np.any(mask)
if has_other_values:
    print("Script doesn't handle all densities in the image")
    exit(1)

# Convert density map to CT
pix[pix == 0] = -1000 # convert air
pix[pix == 1000] = 0 # convert water

# Rotate CT -90 degrees about Z axis
pix = np.rot90(pix, k=3, axes=(1, 2))

# Save CT as .im
npi.ArrayToIm(pix.astype(np.float32), "ct.im")

# Reduce CT to 128x128x128 if necessary
shape = pix.shape
x_factor = shape[2] / 128
y_factor = shape[1] / 128
z_factor = shape[0] / 128

if shape[0] != 128 or shape[1] != 128 or shape[2] != 128:
    print("Downsampling CT")
    if exists("ct_128.im"):
        print("Removing previous ct_128.im")
        cmd = "rm ct_128.im"
        print("Running: " + cmd)
        runcmd(cmd,1)

    cmd = f"collapse3d -a {x_factor} {y_factor} {z_factor} ct.im ct_128.im" # average the collapse, not sum, since it's not activity units
    print("Running: " + cmd)
    runcmd(cmd,1)

    ct_name = "ct_128.im"
else:
    print("No downsampling needed")
    ct_name = "ct.im"

# Create attenuation map from CT for each keV
i = 0
for keV in keVs:
    i += 1
    cmd = f"./hu2atn -e {keV} -s 0.48 {ct_name} atn.w{i}.im"
    print("Running: " + cmd)
    runcmd(cmd,1)

    # Update pixel spacing rows and columns in header
    cmd = f"imsetinfo -i \"Pixel Spacing Rows\" \"4.8\" -i \"Pixel Spacing Cols\" \"4.8\" -i \"Slices Spacing\" \"-4.8\" -i \"Modality\" \"CT\" atn.w{i}.im"
    print("Running: " + cmd)
    runcmd(cmd,1)

# Create symbolic links
if exists("atn.w1i1.im"):
    cmd = "rm atn.w1i1.im"
    print("Running: " + cmd)
    runcmd(cmd,1)
cmd = "ln -s atn.w1.im atn.w1i1.im"
print("Running: " + cmd)
runcmd(cmd,1)

if exists("atn.w1i2.im"):
    cmd = "rm atn.w1i2.im"
    print("Running: " + cmd)
    runcmd(cmd,1)
cmd = "ln -s atn.w1.im atn.w1i2.im"
print("Running: " + cmd)
runcmd(cmd,1)
