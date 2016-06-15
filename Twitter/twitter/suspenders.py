#!/usr/bin/env python3
# suspenders.py - keep your pants on

import os.path
import functools
from .util import elements


PANTS_TARGETS = [
  'android_binary',
  'android_dependency',
  'android_library',
  'android_resources',
  'annotation_processor',
  'benchmark',
  'confluence',
  'contrib_plugin',
  'cpp_binary',
  'cpp_library',
  'create_datasets',
  'create_thrift_libraries',
  'credentials',
  'go_binary',
  'go_library',
  'go_remote_libraries',
  'go_remote_library',
  'go_thrift_library',
  'hadoop_binary',
  'heron_binary',
  'idl_jar_thrift_library',
  'jar_library',
  'java_agent',
  'java_antlr_library',
  'java_library',
  'java_protobuf_library',
  'java_ragel_library',
  'java_tests',
  'java_thrift_library',
  'java_thriftstore_dml_library',
  'java_wire_library',
  'jaxb_library',
  'junit_tests',
  'jvm_app',
  'jvm_binary',
  'jvm_prep_command',
  'managed_jar_dependencies',
  'netrc_credentials',
  'node_module',
  'node_packer_module',
  'node_preinstalled_module',
  'node_remote_module',
  'node_test',
  'page',
  'pants_plugin',
  'pants_plugin_requirement_library',
  'prep_command',
  'python_antlr_library',
  'python_binary',
  'python_library',
  'python_requirement_library',
  'python_tests',
  'python_thrift_library',
  'resources',
  'ruby_thrift_library'
  'ruby_thrift_library',
  'scala_js_binary',
  'scala_js_binary',
  'scala_js_library',
  'scala_library',
  'scalac_plugin',
  'spindle_thrift_library',
  'storm_binary',
  'target',
  'testbox_tests',
  'thrift_jar',
  'unpacked_jars',
]

PANTS_GLOBALS = [
  'artifact',
  'artifactory',
  'buildfile_path',
  'bundle',
  'ConfluencePublish',
  'contrib_setup_py',
  'developer',
  'DirectoryReMapper',
  'Duplicate',
  'exclude',
  'from_target',
  'get_buildroot',
  'github',
  'globs',
  'intransitive',
  'jar',
  'jar_rules',
  'license',
  'make_lib',
  'managed_jar_libraries',
  'netrc',
  'ossrh',
  'pants_library',
  'pants_requirement',
  'pants_setup_py',
  'pants_version',
  'provided',
  'public',
  'python_artifact',
  'python_requirement',
  'python_requirements',
  'repository',
  'rglobs',
  'scala_artifact',
  'scala_jar',
  'scm',
  'scoped',
  'setup_py',
  'shading_exclude',
  'shading_exclude_package',
  'shading_keep',
  'shading_keep_package',
  'shading_relocate',
  'shading_relocate_package',
  'shading_zap',
  'shading_zap_package',
  'Skip',
  'testing',
  'Wiki',
  'wiki_artifact',
  'zglobs',
]

ROOT_TARGET_KIND = '<root>'


class Any:
  """ Stub object that visually tracks simple operations """
  def __init__(self, name):
    self.n = name

  def __call__(self, *args, **kwargs):
    a = [str(a) for a in args] + ['{!r}={!r}'.format(k, v) for k, v in kwargs.items()]
    return Any('{}({})'.format(self.n, ', '.join(a)))

  def __getattr__(self, attr):
    return Any('{}.{}'.format(self.n, attr))

  def __add__(self, other):
    return Any('{} + {!r}'.format(self.n, other))

  def __sub__(self, other):
    return Any('{} - {!r}'.format(self.n, other))

  def __radd__(self, other):
    return Any('{!r} + {}'.format(other, self.n))

  def __rsub__(self, other):
    return Any('{!r} - {}'.format(other, self.n))

  def __str__(self):
    return 'Any({})'.format(self.n)

  def __iter__(self):
    yield Any('{}[]'.format(self.n))

  def __repr__(self):
    return self.n


class BuildTarget:
  """ Pants build target """
  def __init__(self, kind, tid, deps=[], sources=[]):
    self.kind = kind
    self.tid = tid
    self.dependencies = deps
    self.sources = sources

  def is_toplvl(self):
    """ A "top level" build target is one which in not in a */src/* folder. """
    return not self.tid.contains("/src/")


class BuildFile:
  """ Result of parsing a build file """
  def __init__(self, buildpath):
    self.buildpath = buildpath
    self.targets = {}


class PantsEnv:
  """ Fake, fast BUILD file parsing environment. Not threadsafe. A small effort
      was made to avoid unnecessary function calls during parse.

      TODO: Handle modules. Some BUILD files import extra things. Ugh.
  """

  GLOB_FMT = "|{kind}|{pattern}"

  @staticmethod
  def split_target(target):
    """ Split a target in to (path, target) """
    path, _, target = target.partition(':')
    return (path, target)

  @staticmethod
  def root(path):
    """ Find the pants root of a path, if any """
    abspath = os.path.abspath(path)
    path_pieces = abspath.split('/')
    while path_pieces:
      potential_root = os.path.join('/', *path_pieces)
      if os.path.isfile(os.path.join(potential_root, 'pants.ini')):
        return potential_root
      path_pieces.pop()
    return None

  @classmethod
  def from_path(cls, path):
    root = PantsEnv.root(path)
    if not root:
      raise ValueError("No pants root found in {}".format(path))
    return cls(root)

  def __init__(self, root):
    self.root = root
    self.env = self.make_env(PANTS_TARGETS, PANTS_GLOBALS)
    self.cache = {}
    self._bf = None # Parsing state

  def _glob(self, kind, args, kwargs):
    globs = [self.GLOB_FMT.format(kind=kind, pattern=p) for p in args]
    excludes = [e + '-' for e in elements(kwargs.get('exclude', []))]
    return globs + excludes

  def _new_target(self, kind, *args, **kwargs):
    """ Generate a new target, assign a name and resolve relative dependency paths """
    name_keys = ('name', 'basename')

    # Extract name
    name = None
    for n in name_keys:
      if n in kwargs:
        name = kwargs[n]
        break
    if not name:
      name = 'NO-NAME-{}'.format(len(self._bf.targets))

    # Generate ID
    tid = '{}:{}'.format(self._bf.buildpath, name)

    # Resolve relative dependencies & sources
    deps = [self._bf.buildpath + d if d.startswith(':') else d for d in kwargs.get('dependencies', [])]

    for d in deps:
      if not d:
        print('empty dep in ' + self._bf.buildpath)

    srcs = [os.path.join(self._bf.buildpath, s) for s in kwargs.get('sources', [])]

    self._bf.targets[tid] = BuildTarget(kind, tid, deps, srcs)

  def _parse(self, buildpath):
    try:
      self._bf = BuildFile(buildpath)
      file = os.path.join(self.root, buildpath, 'BUILD')

      with open(file, 'r') as f:
        compiled = compile(f.read(), file, 'exec')

      exec(compiled, self.env.copy())

      # Make a root target that depends on all found targets in this file
      self._bf.targets[buildpath] = BuildTarget(
        kind=ROOT_TARGET_KIND,
        tid=buildpath,
        deps=list(self._bf.targets.keys())
      )

      return self._bf

    finally:
      self._bf = None

  def make_env(self, targets, stubs):
    env = {}
    env.update({t: functools.partial(self._new_target, t) for t in targets})
    env.update({s: Any(s) for s in stubs})
    env.update({
      'globs': lambda *a, **kw: self._glob('g', a, kw),
      'rglobs': lambda *a, **kw: self._glob('r', a, kw),
      'zglobs': lambda *a, **kw: self._glob('z', a, kw),
      'pants_version': lambda: 20,
      'buildfile_path': lambda: self._bf.file,
      'get_buildroot': lambda: self.root,
    })
    return env

  def parse(self, buildpath):
    if buildpath not in self.cache:
      self.cache[buildpath] = self._parse(buildpath)
    return self.cache.get(buildpath, None)

  def graph(self, buildpaths, depth=2, _graph=None):
    """ Generate a mapping of targetId -> target, containing dependencies of at least
        `depth`, for the given list of buildpaths
    """
    graph = _graph if _graph else {}
    to_parse = set()

    for b in (self.parse(bp) for bp in buildpaths):
      new_targets = b.targets
      graph.update(new_targets)

      deps = (PantsEnv.split_target(d)[0] for d in elements(t.dependencies for t in new_targets.values()))
      [to_parse.add(d) for d in deps if d not in graph]

    return graph if depth <= 0 else self.graph(to_parse, depth - 1, graph)

  def resolve_glob(self, globstr):
    raise NotImplementedError

  def flush_cache(self):
    self.cache.clear()


if __name__ == '__main__':
  import sys
  import os

  def test(args):
    import subprocess
    import time
    pants = PantsEnv.from_path(os.getcwd())

    print('Generating list of all buildfiles... (~30 seconds)')

    clk = time.time()
    cmd = ["/usr/bin/find", ".", "-not", "-path", "*/\.*", "-name", "BUILD"]
    results = subprocess.check_output(cmd, universal_newlines=True, cwd=pants.root)
    results = [r.replace('/BUILD', '') for r in results.strip().split('\n')]

    print('Found {} buildfiles in {:.1f} seconds. Now parsing'.format(len(results), time.time() - clk))

    clk = time.time()
    failed = []
    ok = []
    for bp in results:
      try:
        ok.append(pants.parse(bp))
      except Exception as e:
        failed.append((bp, e))

    print('Done parsing {} in {:.1f} seconds'.format(len(results), time.time() - clk))
    print('Failures')
    for f in failed:
      print('{}: {}'.format(f[0], f[1]))

    print('Successfully parsed {}'.format(len(ok)))

  def targets(args):
    pants = PantsEnv.from_path(os.getcwd())
    for buildpath in args:
      for target in sorted(pants.parse(buildpath).targets.keys()):
        print(target)

  def dependencies(args):
    pants = PantsEnv.from_path(os.getcwd())
    tid = args[0]
    bp, target = PantsEnv.split_target(tid)
    depth = int(args[1]) if len(args) > 1 else 2

    graph = pants.graph([bp], depth=depth)
    deps = elements(target.dependencies for target in graph.values())
    deps = set(PantsEnv.split_target(d)[0] for d in deps)
    print('\n'.join(deps))

  def print_help(args):
    print("""
      suspenders.py - keep your pants on
      commands are test, targets, dependencies
    """)
    sys.exit(1)

  commands = {
    'test': test,
    'targets': targets,
    'deps': dependencies
  }

  cmd = sys.argv[1]
  commands.get(cmd, print_help)(sys.argv[2:])
