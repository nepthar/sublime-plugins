#!/usr/bin/env bash -e
# Source this

case "$(uname)" in
  Darwin)
    subl_prefix="${HOME}/Library/Application Support/Sublime Text 3"
    ;;
  *)
    subl_prefix="${HOME}/.config/sublime-text-3"
    ;;
esac

subl_installed_pkgs="${subl_prefix}/Installed Packages"
subl_pkgs="${subl_prefix}/Packages"


err() { echo "$@" &2; }

check-subl() {
  if [[ ! -d "$subl_prefix" ]]; then
    err "Can't find ST pacakges root. Expected $subl_prefix"
    return 1
  fi
}

subl.bundle-pkg()
{
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

subl.is-pkg()
{
  [[ -f "./${1}/package-metadata.json" ]]
}

subl.install()
{
  pkg="$1"

  if [[ ! -f "$pkg" ]] && [[ "$pkg" != *".sublime-package" ]]; then
    err "$pkg doesn't seem to be a sublime-package file"
    return 1
  fi

  cp "$pkg" "${subl_installed_pkgs}/"
  echo "Installed $pkg"
}

subl.dev-link()
{
  pkg_dir="$1"

  if [[ ! -d "$pkg_dir" ]]; then
    err "$pkg_dir should be a folder"
    return 1
  fi
  ln -s "${PWD}/$pkg_dir" "${subl_pkgs}/"
}

subl.list()
{
  echo "Found the following pacakges here: "
  for pkg in ./*; do
    if subl.is-pkg "$pkg" ; then
      echo "-> $pkg"
    fi
  done
}


subl.new()
{
  pkg_name="$1"
  pkg_metadata="${pkg_name}/package-metadata.json"

  if [[ -z $pkg_name ]]; then
    err "Specify a package name"
    return 1
  fi

  if [[ -d "$pkg_name" ]]; then
    err "A folder with that name already exists"
    return 1
  fi

  mkdir "./$pkg_name"
  echo "{\"version\":\"0.0.1\",\"description\":\"...\"}" > "$pkg_metadata"
  echo "Created $pkg_name"
}

echo "Soured sublime dev commands prefixed with subl."
echo "Pakcages root: $subl_prefix"
