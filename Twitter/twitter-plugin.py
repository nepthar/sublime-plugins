import logging
import os
import sublime
import sublime_plugin

from .twitter.interact import *
from .twitter.project import *
from .twitter.repo import SourceRepo
from .twitter.util import group_by

# If you're going to share global state, it's best to do so with a single-letter
# variable.
T = None


def reload_plugin(new_data):
  global T
  T = TwPlugin(new_data)


def plugin_loaded():
  reload_plugin(sublime.active_window().project_data())


class ProjectChangeListener(sublime_plugin.EventListener):
  """ ¯\_(ツ)_/¯ """
  def on_post_save(self, view):
    fname = view.file_name()
    if fname is not None and fname == view.window().project_file_name():
      # Allow 50 ms for the possible change to propagate
      sublime.set_timeout(lambda: self.on_activated(view), 50)

  def on_activated(self, view):
    global T
    window = view.window()
    if window:
      pd = window.project_data()
      if pd != T.project:
        reload_plugin(pd)
      if T.source:
        view.set_status('twitter', "🐦")
      else:
        view.erase_status('twitter')


class TwPlugin:
  project = None
  source = None
  settings = None

  def __init__(self, proj_data):
    self.project = proj_data
    if self.project is not None:
      self.settings = proj_data.get('settings', {}).get('twitter', {})
      if 'source' in self.settings:
        print('Twitter source extensions enabled')
        self.source = SourceRepo(os.path.abspath(os.path.expanduser(self.settings['source'])))

  def folders(self):
    if self.project:
      return ProjectFolders(self.project.get('folders', []))

  def update_project(self):
    sublime.active_window().set_project_data(self.project)
    sublime.set_timeout(lambda: reload_plugin(self.project), 50)


class TwCommand:
  cmd = None
  def name(self):
    return 'twitter_' + self.cmd if self.cmd else ''

  def description(self, *args):
    return self.__doc__.strip()


# Commands
# --------
class DisableCommand(TwCommand, sublime_plugin.WindowCommand):
  cmd = "always_disable"
  def is_enabled(self):
    return False


class OrganizeFolders(TwCommand, sublime_plugin.WindowCommand):
  """ Sort folders in the project alphabetically """
  cmd = "organize_folders"
  def is_enabled(self):
    return T.project is not None

  def run(self):
    f = T.folders()
    f.organize()
    T.project['folders'] = f.data()
    T.update_project()


class SelectAndRemoveFolder(TwCommand, MenuSelect):
  """ Remove a folder from the current project """
  cmd = "remove_folder"
  def is_enabled(self):
    return T.project is not None

  def get_selections(self):
    self.f = T.folders()
    return self.f.folders

  def select(self, i):
    self.f.pop_folder(i)
    T.project['folders'] = self.f.data()
    T.update_project()


class AddSourceFolder(TwCommand, MenuSelect):
  """ Add a top-level folder from the Source repo to the current project """
  cmd = "add_folder"

  def init(self):
    self.f = T.folders()
    blacklist = T.settings.get('project_blacklist', [])
    ignore = [T.source.abspath(i) for i in blacklist]
    ignore.extend(f.path for f in self.f.folders)
    self.ignore = set(ignore)

  def get_selections(self):
    candidates = [T.source.abspath(f) for f in T.source.projects()]
    return [Folder(f) for f in candidates if f not in self.ignore]

  def select(self, i):
    self.f.add_folder(self.get(i))
    T.project['folders'] = self.f.data()
    T.update_project()

  def is_enabled(self):
    return T.source is not None


class CopyLinkCommand(TwCommand, sublime_plugin.TextCommand):
  repo = 'source'
  branch = 'master'
  def is_enabled(self):
    # Enable only if the source setting is present and right-clicking on a file
    # within the source repo
    if T.source:
      self.filename = self.view.file_name()
      self.relpath = T.source.relpath(self.filename)
      return not self.relpath.startswith('..')
    return False

  def run(self, edit):
    row, _ = self.view.rowcol(self.view.sel()[0].begin())
    url = self.template.format(
      repo=self.repo,
      relpath=self.relpath,
      branch=self.branch,
      lineno=row + 1
    )
    sublime.set_clipboard(url)


class CopyCgitLink(CopyLinkCommand):
  """ Copy a cgit URL to the clipboard """
  cmd = "copy_cgit_link"
  template = "https://cgit.twitter.biz/{repo}/tree/{relpath}?h={branch}#n{lineno}"


class CopySourcegraphLink(CopyLinkCommand):
  """ Copy a sourcegraph URL to the clipboard """
  cmd = "copy_sourcegraph_link"
  template = "https://code.twitter.biz/twitter/{repo}@{branch}/.tree/{relpath}#startline={lineno}&endline={lineno}"


class CopyGithubLink(CopyLinkCommand):
  """ Some twitter stuff is also on github. Copy that if in a whitelisted project """
  cmd = "copy_github_link"
  template = "https://github.com/twitter/{repo}/blob/{branch}/{relpath}#L{lineno}"
  projects = {
    'finagle',
    'finatra',
    'scrooge',
    'twitter-server'
    'util',
  }

  def is_enabled(self):
    if super().is_enabled():
      self.repo, _, self.relpath = self.relpath.partition('/')
      return self.repo in self.projects
    return False


# class NewPantsProject(TwCommand, MenuSelect):
#   """ Set the current project to the selection plus dependencies """
#   cmd = "new_pants_project"
#   def is_enabled(self):
#     return False #self.source_enabled()


# class AddPantsDependencies(TwCommand, MenuSelect):
#   """ Add dependencies of a folder to the current project """
#   cmd = "add_pants_dependencies"
#   def is_enabled(self):
#     return self.source_enabled()

#   def init(self):
#     # TODO: Put this somewhere better
#     self.f = self.get_folders()
#     self.st = self.get_settings()
#     self.s = self.get_source()

#     ignore = [self.s.abspath(i) for i in self.st.get('project_blacklist', [])]
#     ignore.extend(f.path for f in self.f.folders)
#     self.ignore = set(ignore)

#   def get_selections(self):
#     return [self.s.relpath(f.path) for f in self.f.folders if self.s.is_project(f.path)]

#   def select(self, i):

#     buildpaths = self.s.find_buildpaths(self.get(i), depth=3)
#     toplvl_deps = set(d.split('/')[0] for d in self.s.dependencies(buildpaths))
#     paths = [self.s.abspath(t) for t in toplvl_deps if self.s.is_project(t)]

#     [self.f.add_path(p) for p in paths if p not in self.ignore]
#     self.f.write()


class ListDependencies(TwCommand, MenuSelect):
  cmd = "list_pants_dependencies"
  def is_enabled(self):
    return T.source is not None

  def init(self):
    # TODO: Put this somewhere better
    self.f = T.folders()

    ignore = [T.source.abspath(i) for i in T.settings.get('project_blacklist', [])]
    ignore.extend(f.path for f in self.f.folders)
    self.ignore = set(ignore)

  def display(self, items):
    return items

  def get_selections(self):
    return [T.source.relpath(f.path) for f in self.f.folders if T.source.is_project(f.path)]

  def select(self, i):
    buildpaths = T.source.find_buildpaths(self.get(i), depth=3)
    deps = T.source.dependencies(buildpaths)
    grouped = group_by(deps, lambda i: i.split('/')[0])

    for k, v in grouped.items():
      print(k)
      for i in sorted(v):
        print(' - {}'.format(i))

    self.window.show_quick_panel(sorted(grouped.keys()), lambda x: False)
