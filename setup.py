from setuptools import setup, Extension
import sys
import numpy as np
import os
import subprocess
from setuptools.command.build_ext import build_ext

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
    USE_CYTHON = "--use-cython" in sys.argv
    print(sys.argv)
    if not "egg_info" in sys.argv:
        raise Exception("Stop here")
    USE_CYTHON = True #TODO fix for uv build
    if USE_CYTHON:
        #sys.argv.remove("--use-cython")
        from Cython.Build import cythonize

    ext = "pyx" #if USE_CYTHON else "c"

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
            extra_objects=["./libs/binding_lp.a"],
            libraries=["netcdff", "netcdf"],
        ),
        Extension(
            "troute.network.reservoirs.rfc.rfc",
            sources=[f"src/troute/network/reservoirs/rfc/rfc.{ext}"],
            include_dirs=[np.get_include(), "src/troute/network/"],
            extra_objects=["./libs/bind_rfc.a"],
            libraries=["netcdff", "netcdf"],
        ),
        # Routing extensions
        Extension(
            "troute.routing.fast_reach.mc_reach",
            sources=[f"src/troute/routing/fast_reach/mc_reach.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.simple_da",
            sources=[f"src/troute/routing/fast_reach/simple_da.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.diffusive",
            sources=[f"src/troute/routing/fast_reach/diffusive.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.chxsec_lookuptable",
            sources=[f"src/troute/routing/fast_reach/chxsec_lookuptable.{ext}"],
            include_dirs=[np.get_include()],
        ),
        Extension(
            "troute.routing.fast_reach.reach",
            sources=[f"src/troute/routing/fast_reach/reach.{ext}"],
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

    if USE_CYTHON:
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
        cmdclass={'build_ext': CustomBuildExt},
    )
