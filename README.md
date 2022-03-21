This directory has scripts and parameter files needed to do spect
simulations of digitized source and attenuation maps. There are 7
input object, liver, lungs, and tumors1-5. These are specified in the
config.par file. Each object must have an input integer source map,
object.im. The values in the pixels are the number of photons to emit from
that voxel. There must be one density image with pixel values equal to the
density in g/cc times 1000 (water density=1000, e.g.,). If the density
is above some threshold the material is assumed to be bone. Otherwise,
the mater is assumed to be water. In both cases, the density is that
specified for the voxel. The source and densit images should have the same
size in each dimension. The x and y dimensions should be the same. The
projections will have have nang images that are zdim*ydim in size.

The program runspectsims.py runs 1 or more simulation for each object. The
number of simulations is determined by the range of the seeds specified
on the command line. After running the simulation you will get at least 1
file for each object and each seed. The base names of the output files are
of the form {prefix}_{object}_{sd}.wNN where prefix is a string specified
in the config file (See below), object is the base name of the object,
and {sd} is an integer 'seed'. (They are not actually seeds to the random
number generator, but the number of independent sequences of numbers. So,
seed=1 is guaranteed to produce a different sequence of random numbers
than seed=2). NN is an integer window number and is the line number
in the energy window specification file (see config.par). If there is
only 1 window, then I believe wNN is not included in the basename. The
basename is followed by either a .im for the projection that contains
all photons or by a string describing one of the 16 categories of
photons: {,bkg}{pri,sca}{geo,pen,sca,xra}. In this, the first group is
whether the photon backscattered in the region behind the crystal and
was subsequently detected, the second {pri,sca} indicates whether the
photon scattered in the object or not, and the third indicatess whether
the photno passed thorugh the collimator holes, penetrated the septa,
scattered in the septa, or is the result of a collimator xray.

-runspectsims.py: script to run all the simulations. The parameters
are the name of the config file (See below) and the start and end seed
numbers. Normally you run a number of simulations for each object
and average them. This lets you do that. The noise in the resulting
projections

-config.par: parameter file

-tc99m_ewins.win: file with high and low limits for energy windows used
for projections. One window is in each file.

-voxphan.smc: simind paramter file for the simulation. Can be use to
chane pameters that are not set by runspectsims.py (from config.par). This
incldues things like the energy resolution, etc. Don't change it unless
you really know what you are doing. This is changed using the simind
program change.

-avg_done_bis.py: averages spectrum files created by the simulation
(end in .bis).

-avg_done_sims.py: averages images created by the various runs in the
simuilation

-rm_logs.py : script that removes all .log files that don't have a
matching .res file. Can be useful for cleaning up before restarting a
simulation that was interrupted.

-runcmd.py : python command for running commands in the background.

-dens.im: sample ncat input density image. Size of density and source
images should be the same.

-liver.im: sample input source image for one object.

-lungs.im

-tumor1.im

-tumor2.im

-tumor3.im

-tumor4.im

-tumor5.im
