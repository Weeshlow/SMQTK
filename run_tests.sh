#!/usr/bin/env sh
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"
if [ -f ".coverage" ]
then
  echo "Removing previous coverage cache file"
  rm ".coverage"
fi
nosetests --with-doctest --with-coverage --cover-package=smqtk --exclude-dir-file=nose_exclude_dirs.txt python/smqtk "$@"
