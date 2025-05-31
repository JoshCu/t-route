from setuptools import setup, Extension, Command
import numpy as np
import os
import subprocess
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize

class BuildFortran(Command):
    description = 'build Fortran reservoir kernels'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        fc = os.environ.get('FC') or os.environ.get('F90') or subprocess.run(['which', 'fc'], capture_output=True).stdout.decode('UTF-8').strip()
        fc = "gfortran"
        os.environ["F90"] = fc
        os.environ["NETCDFINC"] = "/usr/lib64/gfortran/modules/"
        # Build kernels
        print("Building Fortran muskingum kernel...")
        subprocess.check_call(['make', '-C', 'src/troute/kernel/muskingum'])
        print("Building Fortran diffusive kernel...")
        subprocess.check_call(['make', '-C', 'src/troute/kernel/diffusive'])
        print("Building Fortran reservoir kernel...")
        subprocess.check_call(['make', '-C', 'src/troute/kernel/reservoir'])

def get_fortran_config():
    fcompopt = {
        'intel': [],
        'gnu95': ['-g']
    }
    flinkopt = {
        'intel': [],
        'gnu95': []
    }
    flibs = {
        'intel': ['mpifort', 'mpi', 'ifcoremt', 'ifport', 'imf', 'svml', 'intlc'],
        'gnu95': ['gfortran']
    }

    fc = os.environ.get('FC') or os.environ.get('F90') or subprocess.run(['which', 'fc'], capture_output=True).stdout.decode('UTF-8').strip()
    fc = "gfortran"
    result = subprocess.run([fc, '--version'], stdout=subprocess.PIPE).stdout.decode('utf-8')

    if "GNU" in result:
        fcompiler_type = 'gnu95'
    elif "Intel" in result:
        fcompiler_type = 'intel'
    else:
        raise Exception("Could not identify fortran compiler!")

    print(f"Using Fortran compiler type: {fcompiler_type}")
    return fcompiler_type, fcompopt, flinkopt, flibs

class CustomBuildExt(build_ext):
    def run(self):
            # Build Fortran first
            self.run_command('build_fortran')

            # Then proceed with normal build_ext
            super().run()

    def build_extensions(self):
        fcompiler_type, fcompopt, flinkopt, flibs = get_fortran_config()
        for e in self.extensions:
            if fcompiler_type in fcompopt:
                e.extra_compile_args.extend(fcompopt[fcompiler_type])
            if fcompiler_type in flinkopt:
                e.extra_link_args.extend(flinkopt[fcompiler_type])
            if fcompiler_type in flibs:
                e.libraries.extend(flibs[fcompiler_type])
        build_ext.build_extensions(self)

def get_extensions():
    # setuptools automatically detects cython files, so long as cython is installed
    # Building like this and including pyx and c files in the package allows for the use of both by the user
    ext = "pyx"
    # All extensions from your network and routing modules
    extensions = [
        # Network extensions
        Extension(
            "troute.network.reach",
            sources=[f"src/troute/network/reach.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.network.musking.mc_reach",
            sources=[f"src/troute/network/musking/mc_reach.{ext}"],
            include_dirs=[np.get_include(), "src/troute/network/"],
        ),
        Extension(
            "troute.network.reservoirs.levelpool.levelpool",
            sources=[f"src/troute/network/reservoirs/levelpool/levelpool.{ext}"],
            include_dirs=[np.get_include(), "src/troute/network/"],
            extra_objects=["src/troute/kernel/reservoir/binding_lp.a"],
            libraries=["netcdff", "netcdf"],
        ),
        Extension(
            "troute.network.reservoirs.rfc.rfc",
            sources=[f"src/troute/network/reservoirs/rfc/rfc.{ext}"],
            include_dirs=[np.get_include(), "src/troute/network/"],
            extra_objects=["src/troute/kernel/reservoir/bind_rfc.a"],
            libraries=["netcdff", "netcdf"],
        ),
        # Routing extensions
        # Why does the routing mc reach need to source the network mc reach?
        # Why are there two of them?
        Extension(
            "troute.routing.fast_reach.mc_reach",
            sources=[f"src/troute/routing/fast_reach/mc_reach.{ext}"],
            # Not wildcarding this for now to try an keep track of what's being used and what's just duplicated
            include_dirs=[np.get_include(),
                "src/troute/network/",
                "src/troute/network/musking/",
                "src/troute/network/reservoirs/levelpool/",
                "src/troute/network/reservoirs/rfc"
            ],
        ),
        Extension(
            "troute.routing.fast_reach.simple_da",
            sources=[f"src/troute/routing/fast_reach/simple_da.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.diffusive",
            sources=[f"src/troute/routing/fast_reach/diffusive.{ext}"],
            extra_objects=["src/troute/kernel/diffusive/diffusive.o","src/troute/kernel/diffusive/pydiffusive.o"],
            include_dirs=[np.get_include(), "src/troute/routing/fast_reach/"],
        ),
        Extension(
            "troute.routing.fast_reach.chxsec_lookuptable",
            sources=[f"src/troute/routing/fast_reach/chxsec_lookuptable.{ext}"],
            extra_objects=[
                    "src/troute/kernel/diffusive/chxsec_lookuptable.o",
                    "src/troute/kernel/diffusive/pychxsec_lookuptable.o",
                ],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.reach",
            sources=[f"src/troute/routing/fast_reach/reach.{ext}"],
            extra_objects=[
                "src/troute/kernel/muskingum/mc_single_seg.o",
                "src/troute/kernel/muskingum/pymc_single_seg.o",
            ],
            include_dirs=[np.get_include()],
        ),
        # Additional routing extensions
        Extension(
            "troute.routing.fast_reach.diffusive_cnx",
            sources=[f"src/troute/routing/fast_reach/diffusive_cnx.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.diffusive_cnt",
            sources=[f"src/troute/routing/fast_reach/diffusive_cnt.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.utils",
            sources=[f"src/troute/routing/fast_reach/utils.{ext}"],
            include_dirs=[np.get_include()],
        ),
    ]

    extensions = cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "embedsignature": True,
        }
    )

    return extensions

if __name__ == "__main__":
    setup(
        ext_modules=get_extensions(),
        cmdclass={'build_ext': CustomBuildExt,
                  'build_fortran': BuildFortran},
    )
