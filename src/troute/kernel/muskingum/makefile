# compiler
FC := $(F90)
# compile flags
#FCFLAGS = -c -fdefault-real-8 -fno-align-commons -fbounds-check --free-form
F90FLAGSGFORTRAN = -g -c -O2 -fPIC -lgfortran -lgcc -static-libgfortran -static-libgcc -nodefaultlibs
F90FLAGSINTEL = -free -w -c -O2 -fPIC -fconvert=big-endian -frecord-marker=4
ifeq ($(notdir ${FC}), ifort)
F90FLAGS = $(F90FLAGSINTEL)
else ifeq ($(notdir ${FC}), mpiifort)
F90FLAGS = $(F90FLAGSINTEL)
else
F90FLAGS = $(F90FLAGSGFORTRAN)
endif

.PHONY: reach all install clean

all: reach

reach: mc_single_seg.o pymc_single_seg.o

precis.mod: varPrecision.f90
	$(FC) $(F90FLAGS) $<

# This compiles the muskingcunge_module
mc_single_seg.o: MCsingleSegStime_f2py_NOLOOP.f90 precis.mod
	$(FC) $(F90FLAGS) -o $@ $<

# This depends on mc_single_seg.o to ensure muskingcunge_module.mod is created first
pymc_single_seg.o: pyMCsingleSegStime_NoLoop.f90 mc_single_seg.o
	$(FC) $(F90FLAGS) -o $@ $<

install:
	cp *.o ../../../src/troute-routing/troute/routing/fast_reach

%.o: %.F
	$(FC) $(F90FLAGS) -o $@ $<

%.o: %.f90
	$(FC) $(F90FLAGS) -o $@ $<

clean:
	rm -f *.o *.mod
