#! /usr/bin/env python3
import re
from os.path import exists
from sys import exit, argv
from glob import glob
import numpy as np
import NumpyIm as npi
from runcmd import runcmd, waitall
import subprocess

# Ensure user inputs are present
if len(argv) != 5:
    print("Usage: quantify.py CF projection_file recon_file outfile")
    print("\nCF: conversion factor for the image in cps/MBq")
    exit(1)

# Retrieve user input
CF = float(argv[1])
proj = argv[2]
recon = argv[3]
outf = argv[4]

# Check to make sure the files exist
if not exists(proj) or not exists(recon):
    print("Infiles do not exist!")
    exit(1)

# Read in the infile (assumes units of counts)
pix = npi.ArrayFromIm(recon)

# Get the frame duration from projections
hdr = subprocess.check_output(["header", "-i", proj])
hdr = hdr.decode('ascii').strip().split("\n")
try:
    frame_duration_txt = [item for item in hdr if "Actual Frame Duration" in item]
    frame_duration = frame_duration_txt[0].split("\t")
    frame_duration = float(frame_duration[-1]) / 1000 # convert to seconds
    print(f"Found frame duration of {frame_duration} seconds in header")
except:
    print("No frame duration found in header")
    frame_duration = float(input("Enter the frame duration in seconds: "))

# Get the total number of frames
try:
    num_frames_txt = [item for item in hdr if "Number of Projections" in item]
    num_frames = num_frames_txt[0].split("\t")
    num_frames = int(num_frames[-1])
    print(f"Found {num_frames} frames in header")
except:
    print("No number of projections found in header")
    num_frames = int(input("Enter the number of projections: "))

# Convert image to cps
pix = pix / (frame_duration * num_frames)

# Get the voxel dimensions
slice_thickness = subprocess.check_output(["imghdr", "-i", "SliceThickness", recon])
slice_thickness = slice_thickness.decode('ascii')
try:
    slice_thickness = float(slice_thickness)
    print(f"Found slice thickness of {slice_thickness} cm in header")
except:
    print("No slice thickness found in header")
    slice_thickness = float(input("Enter the slice thickness in cm: "))

pixel_width = subprocess.check_output(["imghdr", "-i", "PixelWidth", recon])
pixel_width = pixel_width.decode('ascii')
try:
    pixel_width = float(pixel_width)
    print(f"Found pixel width of {pixel_width} cm in header")
except:
    print("No pixel width found in header")
    pixel_width = float(input("Enter the pixel width in cm: "))

# Convert image to cps/mL
pix = pix / (slice_thickness * pixel_width * pixel_width) # assumes square pixels in the axial direction

# Convert image to Bq/mL
pix = pix * (1 / CF) * 1e6

# Save quantified image
npi.ArrayToIm(pix.astype(np.float32), outf)