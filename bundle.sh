#!/usr/bin/env bash -e

case "$(uname)" in
  Darwin)
    subl_prefix="~/Library/Application Support/Sublime Text 3"
    ;;
  *)
    subl_prefix="~/.config/sublime-text-3"
    ;;
esac

subl_installed_pkgs="${subl_prefix}/Installed Packages"
subl_pkgs="${subl_prefix}/Package"


err() { echo "$@" &2; }

check-subl() {
  if [[ ! -d "$subl_prefix" ]]; then
    err "Can't find ST pacakges root. Expected $subl_prefix"
    return 1
  fi
}

mk-pkg() {

  pkg_src="$1"
  pkg_file="$2"

  if [[ ! -d "$pkg_src" ]]; then
    err "No such folder: $pkg_src"
    return 1
  fi

  rm -f "$pkg_file"
  cd "$pkg_src"
  zip "../${pkg_file}" ./*
  cd -
}

install-pkg()
{
  pkg="$1"

  if [[ ! -f "$pkg" ]] && [[ "$pkg" != *".sublime-package" ]]; then
    err "$pkg doesn't seem to be a sublime-package file"
    return 1
  fi

  cp "$pkg" "${subl_installed_pkgs}/"
  echo "Installed $pkg"
}

dev-link-pkg()
{
  pkg_dir="$1"

  if [[ ! -d "$pkg_dir" ]]; then
    err "$pkg_dir should be a folder"
    return 1
  fi

  ln -s "$pkg_dir" "${subl_pkgs}/${pkg_dir}"
}

for pkg in ./*; do
  if [[ -d "$pkg" ]]; then
    echo "-> $pkg"
  fi
done
