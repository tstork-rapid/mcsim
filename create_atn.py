#! /usr/bin/env python3
from os.path import exists
from sys import exit, argv
from glob import glob
import numpy as np
import NumpyIm as npi
from runcmd import runcmd, waitall
import subprocess


# Ensure a keV was input by the user
if len(argv) < 2:
    print("Usage: create_atn.py")
    print("Uses SIMIND attenuation map to make attenuation maps (downsampled to 128x128x128 if needed)")
    print("MUST HAVE INDEX 22 IN SIMIND.INI SET TO 3")
    exit(1)

# Make a list of keVs from user input
keVs = []
for i in range(1,len(argv)):
    keVs.append(float(argv[i]))

# Check if SIMIND density map exists
atn_map_txt = "*.hct"
atn_map_files = glob(atn_map_txt)
if len(atn_map_files) < 1:
    print("No attenuation map found")
    exit(1)
elif len(atn_map_files) > 1:
    print("More than one attenuation map found, using " + atn_map_files[0])

# Convert .hct/.ict to .im
atn_map_file = atn_map_files[0]
cmd = f"imgconv -r {atn_map_file} simind_atn_map.im"
print("Running: " + cmd)
runcmd(cmd,1)
waitall()

# Load attenuation map
pix = npi.ArrayFromIm("simind_atn_map.im")

# Get bin width
pixel_size = subprocess.check_output(["imghdr", "-i", "Pixel Size", atn_map_file])
bin_width = pixel_size.decode('ascii').strip().split(" ")

# Rotate CT -90 degrees about Z axis
pix = np.rot90(pix, k=3, axes=(1, 2))

# Save attenuation map as .im
npi.ArrayToIm(pix.astype(np.float32), "temp.im")

# Reduce attenuation map to 128x128x128 if necessary
shape = pix.shape
x_factor = shape[2] / 128
y_factor = shape[1] / 128
z_factor = shape[0] / 128
new_bin_width = float(bin_width[0]) * x_factor

if shape[0] != 128 or shape[1] != 128 or shape[2] != 128:
    print("Downsampling attenuation map")
    if exists("temp_128.im"):
        print("Removing previous temp_128.im")
        cmd = "rm temp_128.im"
        print("Running: " + cmd)
        runcmd(cmd,1)

    cmd = f"collapse3d -a {x_factor} {y_factor} {z_factor} temp.im temp_128.im" # average the collapse, not sum, since it's not activity units
    print("Running: " + cmd)
    runcmd(cmd,1)
    waitall()

    atn_name = "temp_128.im"
else:
    print("No downsampling needed")
    atn_name = "temp.im"

# Convert attenuation map from linear attenuation/cm to attenuation per voxel
pix = npi.ArrayFromIm(atn_name)
pix = pix * new_bin_width / 10
npi.ArrayToIm(pix.astype(np.float32), "atn.im")

# Update pixel spacing rows and columns in header
cmd = f"imsetinfo -i \"Pixel Spacing Rows\" \"{new_bin_width}\" -i \"Pixel Spacing Cols\" \"{new_bin_width}\" -i \"Slices Spacing\" \"-{new_bin_width}\" -i \"Modality\" \"CT\" atn.im"
print("Running: " + cmd)
runcmd(cmd,1)

# Create symbolic links
if exists("atn.w1i1.im"):
    cmd = "rm atn.w1i1.im"
    print("Running: " + cmd)
    runcmd(cmd,1)
cmd = "ln -s atn.im atn.w1i1.im"
print("Running: " + cmd)
runcmd(cmd,1)

if exists("atn.w1i2.im"):
    cmd = "rm atn.w1i2.im"
    print("Running: " + cmd)
    runcmd(cmd,1)
cmd = "ln -s atn.im atn.w1i2.im"
print("Running: " + cmd)
runcmd(cmd,1)

# Remove temp .im images
cmd = "rm temp*.im"
runcmd(cmd,1)
