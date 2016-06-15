# Project.py
# ----------
# Manipulate sublimetext project folders
import os.path


class Folder:
  def __init__(self, path, name=None):
    self.path = path
    self.name = name
    if name:
      self.display = name
    else:
      self.display = os.path.basename(self.path)

  def __str__(self):
    return self.display

  def __lt__(self, other):
    return self.path < other.path

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  def is_partition(self):
    return self.display.startswith('--')

  def data(self):
    data = { 'path': self.path }
    if self.name:
      data['name'] = self.name
    return data


class ProjectFolders:
  def __init__(self, folder_list):
    self.folders = [Folder(**f) for f in folder_list]

  def add_path(self, path, name=None, index=0):
    self.add_folder(Folder(path, name), index)

  def add_folder(self, folder, index=0):
    self.folders.insert(index, folder)

  def remove_path(self, path):
    self.folders = filter(lambda f: f.path != path, self.folders)

  def remove_folder(self, folder):
    self.folders.remove(folder)

  def pop_folder(self, index):
    self.folders.pop(index)

  def organize(self):
    result = []
    current = []

    for f in self.folders:
      if f.is_partition():
        result.extend(sorted(current))
        result.append(f)
        current = []
      else:
        current.append(f)

    result.extend(sorted(current))
    self.folders = result

  def data(self):
    return [f.data() for f in self.folders]
