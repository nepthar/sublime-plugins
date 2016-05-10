import os.path
import subprocess

from .suspenders import PantsEnv
from .util import flatmap, flatten


class Repo:
  """ A code repository consisting of multiple projects, subprojects, build targets, etc. Pants is
      assumed to be the build system.

      target:    Repo-relative pants target          geoduck/yelp:whatever
      buildpath: Path which contains a buildfile     geoduck/yelp
      project:   Top-level non-special folder        finagle
      relpath:   Path relative to the source root    finagle/finagle-mux
      abspath:   Absolute path                       /Users/you/workspace/source/finagle/finagle-mux
  """

  def __init__(self, root_abspath):
    assert root_abspath.startswith('/')
    assert os.path.isdir(root_abspath)
    self.root = root_abspath
    self.pants = PantsEnv(self.root)


  def projects(self):
    """ List of top-level projects in the repo """
    raise NotImplementedError

  def find(self, relpath, pattern, depth):
    cmd = ('find', relpath,
      '-not', '-path', '*/\.*',
      '-name', pattern,
      '-maxdepth', str(depth)
    )

    lines = subprocess.check_output(cmd, universal_newlines=True, cwd=self.root)
    return (l.replace('./', '') for l in lines.split())

  def abspath(self, relpath):
    """ Generate an absolute path, given a relpath. This should not check for existence """
    return os.path.abspath(os.path.join(self.root, relpath))

  def relpath(self, abspath):
    """ Generate a path relative to the repo (no leading slash) from an absolute path. """
    return os.path.relpath(abspath, self.root)

  def is_project(self, name):
    """ Determine if a given name is a top level project """
    raise NotImplementedError

  def get_project(self, relpath_or_target):
    raise NotImplementedError

  def git_in_rebase(self):
    return os.path.isdir(os.path.join(self.root, '.git', 'rebase-merge'))

  def git_branch(self):
    prefix = 'REBASE ' if self.git_in_rebase() else ''
    with open(os.path.join(self.root, '.git', 'HEAD'), 'r') as f:
      refline = f.read().strip()
      if refline.startswith('ref:'):
        return "{}{}".format(prefix, refline[16:])
      else:
        return "{}sha: {}".format(prefix, refline[:8])


class SourceRepo(Repo):

  def is_project(self, path_or_project):
    if path_or_project.startswith('/'):
      relpath = self.relpath(path_or_project)
    else:
      relpath = path_or_project

    return not (
      '/' in relpath or
      relpath.startswith('.') or
      relpath == 'science'
    ) and os.path.isdir(os.path.join(self.root, relpath))

  def projects(self):
    return [f for f in os.listdir(self.root) if self.is_project(f)]

  def get_project(self, target_or_buildpath):
    return self.get_buildpath(target_or_buildpath).split('/')[0]

  def get_buildpath(self, target):
    return target.split(':')[0]

  def get_targets(self, buildpath):
    return list(self.pants.parse(buildpath).targets.keys())

  def find_buildpaths(self, relpath, depth=3):
    """ Find all buildpaths under relpath """
    return list(p.replace('/BUILD', '') for p in self.find(relpath, 'BUILD', depth))

  def find_targets(self, relpath, depth=3):
    """ Find all targets under relpath """
    return flatten(self.get_targets(p) for p in self.find_buildpaths(relpath, depth))

  # TODO: Target-level sophistication? Probably not.
  def dependencies(self, buildpaths, depth=2):
    """ List dependencies of buildpath """
    graph = self.pants.graph(buildpaths, depth)
    deps = flatten(target.dependencies for target in graph.values())
    return set(self.pants.split_target(d)[0] for d in deps)

  def project_dependencies(self, buildpaths, depth=2):
    deps = set(d.split('/')[0] for d in self.dependencies(buildpaths, depth))
    return set(d for d in deps if self.is_project(d))
