# compiler
FC := ${F90}

# compile flags
F90FLAGSGFORTRAN = -g -c -O2 -fPIC -fbounds-check
F90FLAGSINTEL = -free -g -c -O2 -fPIC -I${NETCDF}/include
ifeq ($(notdir ${FC}), ifort)
FCFLAGS = $(F90FLAGSINTEL)
else ifeq ($(notdir ${FC}), mpiifort)
FCFLAGS = $(F90FLAGSINTEL)
else
FCFLAGS = $(F90FLAGSGFORTRAN)
endif

all: diffusive.o pydiffusive.o chxsec_lookuptable.o pychxsec_lookuptable.o

diffusive.o: diffusive.f90
	$(FC) $(FCFLAGS) -o $@ $<

pydiffusive.o: pydiffusive.f90
	$(FC) $(FCFLAGS) -o $@ $<

chxsec_lookuptable.o: chxsec_lookuptable.f90
	$(FC) $(FCFLAGS) -o $@ $<

pychxsec_lookuptable.o: pychxsec_lookuptable.f90
	$(FC) $(FCFLAGS) -o $@ $<


install:
	cp *.o ../../routing/fast_reach

clean:
	rm -f *.o *.mod
	rm -f ../../routing/fast_reach/diffusive.o
	rm -f ../../routing/fast_reach/pydiffusive.o
	rm -f ../../routing/fast_reach/diffusive.c
	rm -f ../../routing/fast_reach/diffusive.cpython*.so
	rm -f ../../routing/fast_reach/chxsec_lookuptable.o
	rm -f ../../routing/fast_reach/pychxsec_lookuptable.o
	rm -f ../../routing/fast_reach/chxsec_lookuptable.c
	rm -f ../../routing/fast_reach/chxsec_lookuptable.cpython*.so
