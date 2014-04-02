import sublime, sublime_plugin
import os
import subprocess

PLUGIN_NAME = 'CgitUrl'


class GitRepo(object):

  CGIT_URL = "{cgit_root}/tree/{path}?h={branch}#n{lineno}"
  CONF_TR = str.maketrans({c: None for c in '[]\"'})

  @staticmethod
  def find_repo_root(git_path):
    abspath = os.path.abspath(git_path)

    path_pieces = abspath.split('/')
    # Find .../.git
    while path_pieces:
      head = os.path.join('/', *(path_pieces + ['.git']))
      if os.path.isdir(head):
        return os.path.join('/', *path_pieces)
      path_pieces.pop()

    return None

  @staticmethod
  def parse_git_config(config_file):
    section = ''
    conf = {}
    with open(config_file, 'r') as f:
      for line in f:
        line = line.partition('#')[0].strip()
        if len(line) == 0:
          continue
        if line.startswith('['):
          section = '.'.join(line.translate(GitRepo.CONF_TR).split())
        else:
          k, _, v = line.partition('=')
          key = '{}.{}'.format(section, k.strip())
          conf[key] = v.strip()

      return conf

    return None

  def __init__(self, git_path):
    self.root = GitRepo.find_repo_root(git_path)
    if not self.root:
      raise ValueError("Unable to find git repo")

    self.config_file = '{}/.git/config'.format(self.root)
    self.head_file = '{}/.git/HEAD'.format(self.root)
    self.conf = GitRepo.parse_git_config(self.config_file)
    self.origin_url = self.conf.get('remote.origin.url', None)

  def branch(self):
    with open(self.head_file, 'r') as f:
      refline = f.read().strip()
      if refline.startswith("ref:"):
        return refline.split(' ')[1].replace('refs/heads/', '')
      else:
        return refline

  def guess_name(self):
    return self.root.rpartition('/')[2]

  def repo_relpath(self, file_path):
    abspath = os.path.abspath(file_path)
    return abspath.replace('{}/'.format(self.root), '')

  def cgit_url(self, file_path, custom_branch=None, lineno=1):
    relpath = self.repo_relpath(file_path)
    branch = custom_branch if custom_branch else self.branch()
    cgit_root = self.conf['remote.origin.url'].replace('git', 'cgit')
    return GitRepo.CGIT_URL.format(cgit_root=cgit_root, path=relpath, branch=branch, lineno=lineno)


class CopyCgitLinkCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.file_name()
    row, _ = self.view.rowcol(self.view.sel()[0].begin())

    try:
      gr = GitRepo(filename)
      link = gr.cgit_url(filename, lineno=row)
      sublime.set_clipboard(link)
    except ValueError:
      sublime.error_message("Can't generate cgit link")


class OpenCgitLinkCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.file_name()
    row, _ = self.view.rowcol(self.view.sel()[0].begin())

    try:
      gr = GitRepo(filename)
      link = gr.cgit_url(filename, lineno=row)
      subprocess.call(['open', link])
    except ValueError:
      sublime.error_message("Can't generate cgit link")


class CopyCgitLinkMasterCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.file_name()
    row, _ = self.view.rowcol(self.view.sel()[0].begin())

    try:
      gr = GitRepo(filename)
      link = gr.cgit_url(filename, custom_branch='master', lineno=row)
      sublime.set_clipboard(link)
    except ValueError:
      sublime.error_message("Can't generate cgit link")


class OpenCgitLinkMasterCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.file_name()
    row, _ = self.view.rowcol(self.view.sel()[0].begin())

    try:
      gr = GitRepo(filename)
      link = gr.cgit_url(filename, custom_branch='master', lineno=row)
      subprocess.call(['open', link])
    except ValueError:
      sublime.error_message("Can't generate cgit link")
