import queue
import threading
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

import pystray

from work_timer import WorkTimer


class WindowRestoreTests(unittest.TestCase):
    def setUp(self):
        self.app = WorkTimer.__new__(WorkTimer)
        self.app.root = Mock()
        self.app.root.state.return_value = 'normal'
        self.app.root.focus_displayof.return_value = None
        self.app.root.winfo_children.return_value = []
        self.app.user_manager = Mock()
        self.app.user_manager.is_logged_in.return_value = True
        self.app.loading_completed = True
        self.app.topmost = False
        self.app._closing = False
        self.app._ui_queue = queue.SimpleQueue()

    def test_show_is_idempotent_and_preserves_topmost_preference(self):
        for pinned in (False, True):
            with self.subTest(pinned=pinned):
                self.app.topmost = pinned
                attributes = {'-topmost': pinned}

                def window_attributes(name, *values):
                    if values:
                        attributes[name] = values[0]
                    return attributes.get(name)

                self.app.root.attributes.side_effect = window_attributes
                self.app.show_window()
                self.app.show_window()
                self.assertEqual(attributes['-topmost'], pinned)
                self.assertEqual(self.app.topmost, pinned)
        self.assertEqual(self.app.root.deiconify.call_count, 4)
        self.assertEqual(self.app.root.lift.call_count, 4)
        self.assertEqual(self.app.root.focus_force.call_count, 4)
        self.app.root.withdraw.assert_not_called()

    def test_show_during_login_or_loading_never_reveals_main_window(self):
        dialog = Mock(spec=tk.Toplevel)
        self.app.root.winfo_children.return_value = [Mock(), dialog]
        for logged_in, loaded in [(False, True), (True, False)]:
            self.app.user_manager.is_logged_in.return_value = logged_in
            self.app.loading_completed = loaded
            self.app.show_window()
        self.assertEqual(dialog.deiconify.call_count, 2)
        self.assertEqual(dialog.lift.call_count, 2)
        self.assertEqual(dialog.focus_force.call_count, 2)
        self.app.root.winfo_children.return_value = []
        self.app.show_window()
        self.app.root.deiconify.assert_not_called()

    def test_hotkey_hides_only_the_focused_main_window(self):
        focused_widget = Mock()
        focused_widget.winfo_toplevel.return_value = self.app.root
        self.app.root.focus_displayof.return_value = focused_widget
        self.app.toggle_window()
        self.app.root.withdraw.assert_called_once_with()
        self.app.root.deiconify.assert_not_called()

    def test_hotkey_restores_covered_hidden_or_other_toplevel_window(self):
        other_window = Mock()
        other_window.winfo_toplevel.return_value = Mock()
        for state, focus in [('normal', None), ('withdrawn', None),
                             ('normal', other_window)]:
            with self.subTest(state=state, focus=focus):
                self.app.root.state.return_value = state
                self.app.root.focus_displayof.return_value = focus
                self.app.show_window = Mock()
                self.app.toggle_window()
                self.app.show_window.assert_called_once_with()
        self.app.root.withdraw.assert_not_called()

    def test_hide_preserves_the_running_timer(self):
        self.app.is_running = True
        self.app.start_time = 123.0
        self.app.minimize_window()
        self.app.root.withdraw.assert_called_once_with()
        self.assertTrue(self.app.is_running)
        self.assertEqual(self.app.start_time, 123.0)
        self.assertNotIn('window_visible', vars(self.app))

    def test_tray_default_shows_and_every_menu_action_is_queued(self):
        names = ['show_window', 'minimize_window', 'toggle_timer',
                 'show_statistics', 'show_settings', 'quit_app']
        callbacks = [Mock(name=name) for name in names]
        for name, callback in zip(names, callbacks):
            setattr(self.app, name, callback)
        with patch('work_timer.pystray.Icon') as icon_factory, \
                patch('work_timer.threading.Thread'):
            self.app.setup_tray()
        args, kwargs = icon_factory.call_args
        menu = kwargs.get('menu', args[-1] if args else None)
        self.assertIsInstance(menu, pystray.Menu)
        menu(self.app.tray_icon)
        self.assertIs(self.app._ui_queue.get_nowait(), self.app.show_window)
        items = [item for item in menu.items if item is not pystray.Menu.SEPARATOR]
        self.assertEqual(sum(bool(item.default) for item in items), 1)
        for item in items:
            item(self.app.tray_icon)
        queued = [self.app._ui_queue.get_nowait() for _ in items]
        self.assertCountEqual(queued, callbacks)
        for callback in callbacks:
            callback.assert_not_called()

    def test_hotkey_callbacks_are_queued(self):
        self.app.settings = Mock()
        self.app.settings.get.return_value = {
            'toggle_timer': 'ctrl+shift+space', 'show_hide': 'ctrl+shift+h'}
        self.app.toggle_timer = Mock()
        self.app.toggle_window = Mock()
        with patch('work_timer.keyboard.add_hotkey') as register:
            self.app._setup_hotkeys()
        self.assertEqual(register.call_count, 2)
        for call in register.call_args_list:
            call.args[1]()
        self.app.toggle_timer.assert_not_called()
        self.app.toggle_window.assert_not_called()
        self.app._process_ui_queue()
        self.app.toggle_timer.assert_called_once_with()
        self.app.toggle_window.assert_called_once_with()

    def test_worker_post_runs_only_when_the_main_thread_drains_queue(self):
        executed_on = []
        worker = threading.Thread(
            target=lambda: self.app._post_ui(
                lambda: executed_on.append(threading.get_ident())))
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(executed_on, [])
        self.app._process_ui_queue()
        self.assertEqual(executed_on, [threading.get_ident()])
        self.app.root.after.assert_called_once_with(50, self.app._process_ui_queue)

    def test_quit_stops_draining_and_ignores_subsequent_posts(self):
        later = Mock()
        self.app._post_ui(lambda: setattr(self.app, '_closing', True))
        self.app._post_ui(later)
        self.app._process_ui_queue()
        later.assert_not_called()
        self.app.root.after.assert_not_called()
        pending = self.app._ui_queue.qsize()
        self.app._post_ui(later)
        self.assertEqual(self.app._ui_queue.qsize(), pending)

    def test_callback_failure_is_reported_without_stopping_the_pump(self):
        error = ValueError('failed action')
        later = Mock()
        self.app._post_ui(Mock(side_effect=error))
        self.app._post_ui(later)
        self.app._process_ui_queue()
        later.assert_called_once_with()
        report = self.app.root.report_callback_exception
        report.assert_called_once()
        self.assertIs(report.call_args.args[0], ValueError)
        self.assertIs(report.call_args.args[1], error)
        self.assertIsNotNone(report.call_args.args[2])
        self.app.root.after.assert_called_once_with(50, self.app._process_ui_queue)


if __name__ == '__main__':
    unittest.main()
