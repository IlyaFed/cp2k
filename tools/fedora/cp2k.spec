%global dbcsr_version 2.6.0
# TODO OpenCL support: -D__ACC -D__DBCSR_ACC -D__OPENCL

# No openmpi on i668 with openmpi 5 in Fedora 40+
%if 0%{?fedora} >= 40
%ifarch %{ix86}
%bcond_with openmpi
%else
%bcond_without openmpi
%endif
%else
%bcond_without openmpi
%endif

%ifarch x86_64
%bcond_without libxsmm
%else
# See https://bugzilla.redhat.com/show_bug.cgi?id=1515404
%bcond_with libxsmm
%endif

# Disable LTO due to https://bugzilla.redhat.com/show_bug.cgi?id=2243158
%global _lto_cflags %nil

# Compile regtests and do a brief smoketest
%bcond_without check
# Run full regtest suite - takes a very long time
%bcond_with check_full

Name:          cp2k
Version:       0.0.0
Release:       %autorelease
Summary:       Ab Initio Molecular Dynamics
License:       GPLv2+
URL:           httsp://www.cp2k.org/
Source0:       https://github.com/cp2k/cp2k/releases/download/v%{version}/cp2k-%{version}.tar.bz2

BuildRequires: flexiblas-devel
# for regtests
BuildRequires: bc
BuildRequires: fftw-devel
BuildRequires: gcc-c++
BuildRequires: gcc-gfortran
BuildRequires: ninja-build
BuildRequires: glibc-langpack-en
BuildRequires: dbcsr-devel >= %{dbcsr_version}
BuildRequires: libxc-devel >= 5.1.0
%if %{with libxsmm}
BuildRequires: libxsmm-devel >= 1.8.1-3
%endif
BuildRequires: python3-fypp
BuildRequires: spglib-devel
BuildRequires: /usr/bin/hostname
BuildRequires: python3-devel

Requires: %{name}-common = %{version}-%{release}

%global _description %{expand:
CP2K is a freely available (GPL) program, written in Fortran 95, to
perform atomistic and molecular simulations of solid state, liquid,
molecular and biological systems. It provides a general framework for
different methods such as e.g. density functional theory (DFT) using a
mixed Gaussian and plane waves approach (GPW), and classical pair and
many-body potentials.

CP2K does not implement Car-Parinello Molecular Dynamics (CPMD).}

%description
%{_description}

This package contains the non-MPI single process and multi-threaded versions.

%package common
Summary: Molecular simulations software - common files

%description common
%{_description}

This package contains the documentation and the manual.

%package devel
Summary: Development files for %{name}
Requires: %{name}%{?_isa} = %{version}-%{release}

%description devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%if %{with openmpi}
%package openmpi
Summary: Molecular simulations software - openmpi version
BuildRequires:  openmpi-devel
BuildRequires:  blacs-openmpi-devel
BuildRequires:  dbcsr-openmpi-devel >= %{dbcsr_version}
BuildRequires:  scalapack-openmpi-devel
Requires: %{name}-common = %{version}-%{release}
# Libint may have API breakage
Requires: libint2(api)%{?_isa}

%description openmpi
%{cp2k_desc_base}

This package contains the parallel single- and multi-threaded versions
using OpenMPI.

%package openmpi-devel
Summary: Development files for %{name}
Requires: %{name}-openmpi%{?_isa} = %{version}-%{release}

%description openmpi-devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%endif

%package mpich
Summary: Molecular simulations software - mpich version
BuildRequires:  mpich-devel
BuildRequires:  blacs-mpich-devel
BuildRequires:  dbcsr-mpich-devel >= %{dbcsr_version}
BuildRequires:  scalapack-mpich-devel
BuildRequires: make
Requires: %{name}-common = %{version}-%{release}
# Libint may have API breakage
Requires: libint2(api)%{?_isa}

%description mpich
%{cp2k_desc_base}

This package contains the parallel single- and multi-threaded versions
using mpich.

%package mpich-devel
Summary: Development files for %{name}
Requires: %{name}-mpich%{?_isa} = %{version}-%{release}

%description mpich-devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.


%prep
%autosetup -p1
rm tools/build_utils/fypp
rm -r exts/dbcsr

%{__python3} %{_rpmconfigdir}/redhat/pathfix.py -i "%{__python3} -Es" -p $(find . -type f -name *.py)

# $MPI_SUFFIX will be evaluated in the loops below, set by mpi modules
%global _vpath_builddir %{_vendor}-%{_target_os}-build${MPI_SUFFIX:-_serial}
# We are running the module load/unload manually until there is a macro-like way to expand this
. /etc/profile.d/modules.sh


%build
cmake_common_args=(
  "-G Ninja"
  "-DCP2K_DEBUG_MODE:BOOL=OFF"
  "-DCP2K_BLAS_VENDOR:STRING=FlexiBLAS"
  "-DCP2K_USE_STATIC_BLAS:BOOL=OFF"
  "-DCP2K_ENABLE_REGTESTS:BOOL=%{?with_check:ON}%{?without_check:OFF}"
  # Dependencies already packaged
  "-DCP2K_USE_SPGLIB:BOOL=ON"
  "-DCP2K_USE_LIBXC:BOOL=ON"
  "-DCP2K_USE_FFTW3:BOOL=ON"
  # TODO: Fix Libint2 detection
  "-DCP2K_USE_LIBINT2:BOOL=OFF"
  "-DCP2K_USE_LIBXSMM:BOOL=%{?with_libxsmm:ON}%{?without_libxsmm:OFF}"
  # Missing dependencies
  "-DCP2K_USE_ELPA:BOOL=OFF"
  "-DCP2K_USE_PEXSI:BOOL=OFF"
  "-DCP2K_USE_SUPERLU:BOOL=OFF"
  "-DCP2K_USE_COSMA:BOOL=OFF"
  "-DCP2K_USE_PLUMED:BOOL=OFF"
  "-DCP2K_USE_VORI:BOOL=OFF"
  "-DCP2K_USE_PEXSI:BOOL=OFF"
  "-DCP2K_USE_QUIP:BOOL=OFF"
  "-DCP2K_USE_LIBTORCH:BOOL=OFF"
  "-DCP2K_USE_SPLA:BOOL=OFF"
  "-DCP2K_USE_METIS:BOOL=OFF"
  "-DCP2K_USE_DLAF:BOOL=OFF"
)
for mpi in '' mpich %{?with_openmpi:openmpi}; do
  if [ -n "$mpi" ]; then
    module load mpi/${mpi}-%{_arch}
    cmake_mpi_args=(
      "-DCMAKE_INSTALL_PREFIX:PATH=${MPI_HOME}"
      "-DCMAKE_INSTALL_Fortran_MODULES:PATH=${MPI_FORTRAN_MOD_DIR}/cp2k"
      "-DCMAKE_INSTALL_LIBDIR:PATH=lib"
      "-DCP2K_CMAKE_SUFFIX:STRING=${MPI_SUFFIX}"
      "-DCP2K_DATA_DIR:PATH=%{_datadir}/cp2k/data"
      "-DCP2K_USE_MPI_F08:BOOL=ON"
    )
  else
    cmake_mpi_args=(
      "-DCP2K_USE_MPI:BOOL=OFF"
      "-DCMAKE_INSTALL_Fortran_MODULES:PATH=%{_fmoddir}/cp2k"
    )
  fi

  %cmake \
    ${cmake_common_args[@]} \
    ${cmake_mpi_args[@]}
  %cmake_build

  [ -n "$mpi" ] && module unload mpi/${mpi}-%{_arch}
done

%install
for mpi in '' mpich %{?with_openmpi:openmpi}; do
  [ -n "$mpi" ] && module load mpi/${mpi}-%{_arch}
  %cmake_install
  [ -n "$mpi" ] && module unload mpi/${mpi}-%{_arch}
done

# TODO: Properly separate the installation of unit tests
rm -f %{_buildrootdir}/**/%{_bindir}/*_unittest.*
%if %{with openmpi}
rm -f %{_buildrootdir}/**/%{_libdir}/openmpi/bin/*_unittest.*
%endif
rm -f %{_buildrootdir}/**/%{_libdir}/mpich/bin/*_unittest.*


%check
# Tests are done in the tmt envrionment


%files common
%license LICENSE
%doc README.md
%{_datadir}/cp2k

%files
%{_bindir}/cp2k.ssmp
%{_bindir}/dbm_miniapp.ssmp
%{_bindir}/dumpdcd.ssmp
%{_bindir}/graph.ssmp
%{_bindir}/grid_miniapp.ssmp
%{_bindir}/xyz2dcd.ssmp
%{_libdir}/libcp2k.so.*

%files devel
%{_fmoddir}/cp2k/
%{_includedir}/cp2k/
%{_libdir}/cmake/cp2k/
%{_libdir}/libcp2k.so
%{_libdir}/pkgconfig/libcp2k.pc

%if %{with openmpi}
%files openmpi
%{_libdir}/openmpi/bin/cp2k.psmp
%{_libdir}/openmpi/bin/dumpdcd.psmp
%{_libdir}/openmpi/bin/dbm_miniapp.psmp
%{_libdir}/openmpi/bin/graph.psmp
%{_libdir}/openmpi/bin/grid_miniapp.psmp
%{_libdir}/openmpi/bin/xyz2dcd.psmp
%{_libdir}/openmpi/lib/libcp2k.so.*

%files openmpi-devel
%{_fmoddir}/openmpi/cp2k/
%{_libdir}/openmpi/include/cp2k/
%{_libdir}/openmpi/lib/cmake/cp2k/
%{_libdir}/openmpi/lib/libcp2k.so
%{_libdir}/openmpi/lib/pkgconfig/libcp2k.pc
%endif

%files mpich
%{_libdir}/mpich/bin/cp2k.psmp
%{_libdir}/mpich/bin/dbm_miniapp.psmp
%{_libdir}/mpich/bin/dumpdcd.psmp
%{_libdir}/mpich/bin/graph.psmp
%{_libdir}/mpich/bin/grid_miniapp.psmp
%{_libdir}/mpich/bin/xyz2dcd.psmp
%{_libdir}/mpich/lib/libcp2k.so.*

%files mpich-devel
%{_fmoddir}/mpich/cp2k/
%{_libdir}/mpich/include/cp2k/
%{_libdir}/mpich/lib/cmake/cp2k/
%{_libdir}/mpich/lib/libcp2k.so
%{_libdir}/mpich/lib/pkgconfig/libcp2k.pc

%changelog
%autochangelog
