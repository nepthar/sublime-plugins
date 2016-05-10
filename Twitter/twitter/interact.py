# Interact.py
# -----------
import os
import sys
import sublime, sublime_plugin


class MenuSelect(sublime_plugin.WindowCommand):

  _list = []
  args = []

  def get_selections(self):
    """ Perform any initialization necessary and return a list of selections """
    raise NotImplementedError

  def select(self, index):
    """ Perform the selection. Return true if this selection should result in
        additional selections. Index will be in bounds of self.selections """
    raise NotImplementedError

  def init(self, *args):
    """ Called before anything else when the command is run """
    pass

  def finish(self, cancelled):
    """ Called when the selection process ends. Canceled is True if the user
        hit escape at any point, or there's an error somewhere. """
    pass

  def get(self, i):
    return self._list[i]

  def display(self, items):
    """ Convert each choice item to a string for display in the menu """
    return [str(i) for i in items]

  def _select(self, i):
    if i >= 0:
      if self.select(i):
        self._ask()
      else:
        self.finish(cancelled=False)
    else:
      self.finish(cancelled=True)

  def _ask(self):
    self._list = self.get_selections()
    display = self.display(self._list)
    if len(display) != len(self._list):
      raise ValueError('Length of display items must equal length of selections')
    self.window.show_quick_panel(display, self._select)

  def run(self, *args):
    self.init(*args)
    self._ask()
