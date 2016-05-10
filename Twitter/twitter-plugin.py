import sublime
import sublime_plugin
import os
import logging

from .twitter.repo import SourceRepo
from .twitter.interact import *
from .twitter.project import *


class TwPlugin:
  cmd = None

  def __init__(self, *args, **kwargs):
    self.window = None
    self.view = None
    super().__init__(*args, **kwargs)

  def name(self):
    return 'twitter_' + self.cmd if self.cmd else ''

  def description(self, *args):
    return self.__doc__.strip()

  def get_settings(self):
    return self.get_project().get('settings', {}).get('twitter', {})

  def get_window(self):
    if self.window:
      return self.window
    if self.view:
      return self.view.window()
    return sublime.active_window()

  def get_project(self):
    data = self.get_window().project_data()
    return data if data else {}

  def get_source(self):
    settings = self.get_settings()
    if 'source' in settings:
      return SourceRepo(os.path.abspath(os.path.expanduser(settings['source'])))

  def get_folders(self):
    return ProjectFolders(self.get_window())

  def source_enabled(self):
    return 'source' in self.get_settings()

class DisableCommand(TwPlugin, sublime_plugin.WindowCommand):
  cmd = "always_disable"
  def is_enabled(self):
    return False


class OrganizeFolders(TwPlugin, sublime_plugin.WindowCommand):
  """ Sort folders in the project alphabetically """
  cmd = "organize_folders"
  def run(self):
    f = self.get_folders()
    f.organize()
    f.write()


class SelectAndRemoveFolder(TwPlugin, MenuSelect):
  """ Remove a folder from the current project """
  cmd = "remove_folder"
  def get_selections(self):
    self.f = self.get_folders()
    return self.f.folders

  def select(self, i):
    self.f.pop_folder(i)
    self.f.write()


class AddSourceFolder(TwPlugin, MenuSelect):
  """ Add a top-level folder from the Source repo to the current project """
  cmd = "add_folder"

  def init(self):
    self.f = self.get_folders()
    self.st = self.get_settings()
    self.s = self.get_source()

    ignore = [self.s.abspath(i) for i in self.st.get('project_blacklist', [])]
    ignore.extend(f.path for f in self.f.folders)
    self.ignore = set(ignore)

  def get_selections(self):
    candidates = [self.s.abspath(f) for f in self.s.projects()]
    return [Folder(f) for f in candidates if f not in self.ignore]

  def select(self, i):
    self.f.add_folder(self.get(i))
    self.f.write()

  def is_enabled(self):
    return self.source_enabled()


class CodeLinkCopy(TwPlugin, sublime_plugin.TextCommand):
  def is_enabled(self):
    # Enable only if the source setting is present and right-clicking on a file
    # within the source repo
    self.s = self.get_source()
    if self.s:
      self.filename = self.view.file_name()
      self.relpath = self.s.relpath(self.filename)
      return not self.relpath.startswith('..')
    return False

  def run(self, edit):
    row, _ = self.view.rowcol(self.view.sel()[0].begin())
    url = self.template.format(
      repo='source',
      relpath=self.relpath,
      branch='master',
      lineno=row + 1
    )
    sublime.set_clipboard(url)


class CopyCgitLink(CodeLinkCopy):
  """ Copy a cgit URL to the clipboard """
  cmd = "copy_cgit_link"
  template = "https://cgit.twitter.biz/{repo}/tree/{relpath}?h={branch}#n{lineno}"


class CopySourcegraphLink(CodeLinkCopy):
  """ Copy a sourcegraph URL to the clipboard """
  cmd = "copy_sourcegraph_link"
  template = "https://code.twitter.biz/twitter/{repo}@{branch}/.tree/{relpath}#startline={lineno}&endline={lineno}"


class NewPantsProject(TwPlugin, MenuSelect):
  """ Set the current project to the selection plus dependencies """
  cmd = "new_pants_project"
  def is_enabled(self):
    return False #self.source_enabled()

class AddPantsDependencies(TwPlugin, MenuSelect):
  """ Add dependencies of a folder to the current project """
  cmd = "add_pants_dependencies"
  def is_enabled(self):
    return self.source_enabled()

  def init(self):
    # TODO: Put this somewhere better
    self.f = self.get_folders()
    self.st = self.get_settings()
    self.s = self.get_source()

    ignore = [self.s.abspath(i) for i in self.st.get('project_blacklist', [])]
    ignore.extend(f.path for f in self.f.folders)
    self.ignore = set(ignore)

  def get_selections(self):
    return [self.s.relpath(f.path) for f in self.f.folders if self.s.is_project(f.path)]

  def select(self, i):

    buildpaths = self.s.find_buildpaths(self.get(i), depth=3)
    toplvl_deps = set(d.split('/')[0] for d in self.s.dependencies(buildpaths))
    paths = [self.s.abspath(t) for t in toplvl_deps if self.s.is_project(t)]

    [self.f.add_path(p) for p in paths if p not in self.ignore]
    self.f.write()


class ListDependencies(TwPlugin, MenuSelect):
  cmd = "list_pants_dependencies"
  def is_enabled(self):
    return self.source_enabled()

  def init(self):
    # TODO: Put this somewhere better
    self.f = self.get_folders()
    self.st = self.get_settings()
    self.s = self.get_source()

    ignore = [self.s.abspath(i) for i in self.st.get('project_blacklist', [])]
    ignore.extend(f.path for f in self.f.folders)
    self.ignore = set(ignore)

  def get_selections(self):
    return [self.s.relpath(f.path) for f in self.f.folders if self.s.is_project(f.path)]

  def select(self, i):
    buildpaths = self.s.find_buildpaths(self.get(i), depth=3)
    toplvl_deps = set(d.split('/')[0] for d in self.s.dependencies(buildpaths))
    display = sorted(t for t in toplvl_deps if self.s.is_project(t))
    self.window.show_quick_panel(display, lambda x: False)

