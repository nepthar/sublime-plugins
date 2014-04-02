#!/usr/bin/env bash -e

pkg_name="CgitUrl.sublime-package"
pkg_src="./CgitUrl"

if [[ ! -d $pkg_src ]]; then
  echo "Can't find anything to bundle. Run this from the repo root"
  exit 1
fi

rm -f "$pkg_name"
cd "$pkg_src"
zip "../${pkg_name}" ./*

echo "Made $pkg_name"
