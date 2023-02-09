#!/bin/bash

set -e
set -o pipefail

OS=$(uname)

if [ "${OS}" == "Darwin" ];
then
  brew update && brew install coreutils
  READLINK_COMMAND="greadlink"
else
  READLINK_COMMAND="readlink"
fi

# We use David Li's personal repo branch because the ADBC driver work has not yet been merged
# Track PR: https://github.com/apache/arrow/pull/14082 for details...
ARROW_REPO=${1:-"https://github.com/lidavidm/arrow"} # https://github.com/apache/arrow.git
ARROW_VERSION=${2:-"adbc-flight-sql"} # apache-arrow-10.0.1
echo "Variable: ARROW_REPO=${ARROW_REPO}"
echo "Variable: ARROW_VERSION=${ARROW_VERSION}"

SCRIPT_DIR=$(dirname ${0})
ROOT_DIR=$(${READLINK_COMMAND} --canonicalize "${SCRIPT_DIR}/..")
echo -e "ROOT_DIR=${ROOT_DIR}"
pushd ${ROOT_DIR}

rm -rf arrow

# clone the repository
echo "Cloning Arrow."
git clone --depth 1 ${ARROW_REPO} --branch ${ARROW_VERSION}

pushd arrow
git submodule update --init
popd

pip install -r arrow/python/requirements-build.txt
export ARROW_HOME=${ROOT_DIR}/arrow_dist
rm -rf ${ARROW_HOME}
mkdir -p ${ARROW_HOME}
export LD_LIBRARY_PATH=${ARROW_HOME}/lib:$LD_LIBRARY_PATH

# Add exports to the .bashrc for future sessions
echo "export ARROW_HOME=${ARROW_HOME}" >> ~/.bashrc
echo "export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" >> ~/.bashrc

#----------------------------------------------------------------------
# Build C++ library
echo -e "Building Arrow C++ library"

pushd arrow/cpp

# Do some Mac stuff if needed...
if [ "${OS}" == "Darwin" ]; then
  echo "Running Mac-specific setup steps..."
  brew update && brew bundle --file=Brewfile
  export MACOSX_DEPLOYMENT_TARGET="12.0"
  export DYLD_FALLBACK_LIBRARY_PATH=${ARROW_HOME}/lib:$DYLD_FALLBACK_LIBRARY_PATH
  echo "export DYLD_FALLBACK_LIBRARY_PATH=${DYLD_FALLBACK_LIBRARY_PATH}" >> ~/.bashrc
fi

cmake -GNinja -DCMAKE_INSTALL_PREFIX=$ARROW_HOME \
        -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_BUILD_TYPE=Debug \
        -DARROW_BUILD_TESTS=ON \
        -DARROW_COMPUTE=ON \
        -DARROW_CSV=ON \
        -DARROW_DATASET=ON \
        -DARROW_FILESYSTEM=ON \
        -DARROW_FLIGHT=ON \
        -DARROW_FLIGHT_SQL=ON \
        -DARROW_HDFS=ON \
        -DARROW_JSON=ON \
        -DARROW_PARQUET=ON \
        -DARROW_SUBSTRAIT=ON \
        -DARROW_WITH_BROTLI=ON \
        -DARROW_WITH_BZ2=ON \
        -DARROW_WITH_LZ4=ON \
        -DARROW_WITH_SNAPPY=ON \
        -DARROW_WITH_ZLIB=ON \
        -DARROW_WITH_ZSTD=ON \
        -DPARQUET_REQUIRE_ENCRYPTION=ON \
        -DGTest_SOURCE=BUNDLED

ninja install
popd

#----------------------------------------------------------------------
# Build and test Python library
echo -e "Building PyArrow"

pushd arrow/python

rm -rf build/  # remove any pesky pre-existing build directory

export CMAKE_PREFIX_PATH=${ARROW_HOME}${CMAKE_PREFIX_PATH:+:${CMAKE_PREFIX_PATH}}
export PYARROW_WITH_PARQUET=1
export PYARROW_WITH_DATASET=1
export PYARROW_WITH_SUBSTRAIT=1
export PYARROW_PARALLEL=4
export PYARROW_BUNDLE_ARROW_CPP=1
export PYARROW_WITH_FLIGHT=1
export PYARROW_WITH_FLIGHT_SQL=1
python setup.py develop
popd

popd

echo -e "All done!"
