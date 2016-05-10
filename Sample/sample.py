import imp
import sys

import sublime_plugin

from .colorsublime import commands
from .colorsublime import status

NO_SELECTION = -1

# Make sure all dependencies are reloaded on upgrade
reloader_path = 'Colorsublime.colorsublime.reloader'
if reloader_path in sys.modules:
    imp.reload(sys.modules[reloader_path])
from .colorsublime import reloader
reloader.reload()


class InstallThemeCommand(sublime_plugin.WindowCommand):
    def run(self):
        print('Running install command.')
        self.theme_status = {}
        self.status = status.loading('Getting Theme list')
        commands.fetch_repo(self.display_list)

    def display_list(self, themes):
        self.status.stop()
        if not themes:
            status.error('Theme list not found. Please check internet ' +
                         'connection or enable debug in settings and ' +
                         'report the stack traces.')
            return

        self.themes = themes
        self.initial_theme = commands.get_current_theme()

        quick_list = [[theme.name,
                       theme.author,
                       theme.description] for theme in self.themes.values()]
        quick_list.sort()
        self.quick_list = quick_list

        self.window.show_quick_panel(quick_list,
                                     self.on_done,
                                     on_highlight=self.on_highlighted)

    def on_highlighted(self, theme_index):
        commands.preview_theme(self._quick_list_to_theme(theme_index))

    def on_done(self, theme_index):
        if theme_index is NO_SELECTION:
            commands.revert_theme(self.initial_theme)
            status.message('Theme selection cancelled.')
            return

        theme = self._quick_list_to_theme(theme_index)
        commands.install_theme(theme)
        status.message('Theme %s installed!' % theme.name)

    def _quick_list_to_theme(self, index):
        return self.themes[self.quick_list[index][0]]


class BrowseCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('open_url', {'url': 'http://colorsublime.com'})
