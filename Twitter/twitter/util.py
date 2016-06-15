# Util.py
# -------

def flatten(seq):
  return (item for subseq in seq for item in subseq)


def flatmap(f, seq):
  return (result for arg in seq for result in f(arg))


def elements(seq):
  """ A generator that extracts all elements of an object/list. This does not
      work for mapping types

      >>> list(elements([a, [b], [c, d]]))
      [a, b, c, d]
      >>> list(elements(a))
      [a]
  """
  if isinstance(seq, str) or not hasattr(seq, '__iter__'):
    yield seq
  else:
    for i in seq:
      yield from elements(i)


def group_by(seq, f):
  """ A proper groupby that doesn't require sorted input. Output is a dict,
      rather than an interator
      >>> group_by([1,2,3,4,5], mod_two)
      {0: [2, 4], 1: [1, 3, 4]}
  """
  ret = {}
  [ret.setdefault(f(i), []).append(i) for i in seq]
  return ret