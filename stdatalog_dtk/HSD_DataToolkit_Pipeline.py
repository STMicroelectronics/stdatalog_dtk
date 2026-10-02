# *****************************************************************************
#  * @file    HSD_DataToolkit_Pipeline.py
#  * @author  SRA
# ******************************************************************************
# * @attention
# *
# * Copyright (c) 2022 STMicroelectronics.
# * All rights reserved.
# *
# * This software is licensed under terms that can be found in the LICENSE file
# * in the root directory of this software component.
# * If no LICENSE file comes with this software, it is provided AS-IS.
# *
# *
# ******************************************************************************
"""HSD Data Toolkit plugin pipeline.

This module defines a lightweight plugin framework used by the Data Toolkit to
load processing and visualization plugins from a user-specified folder. It
discovers plugin modules, validates that they expose a `PluginClass`, creates
their plot widgets, and orchestrates their lifecycle (start/stop, tagging,
status updates, and data processing).

Each plugin is expected to implement the `HSD_Plugin` interface and may provide
an optional `plot_widget` with a Qt timer used for periodic UI updates.
"""

import os
import sys
import re
import importlib
from typing import Callable, Optional
from threading import Lock, Thread
from itertools import count
from abc import ABC, abstractmethod


class PluginCommandContext:
    """Command gateway exposed to each plugin.

    The context keeps plugin metadata and routes commands through the provided
    command sender callables,
    optionally on a background thread for non-blocking UI/plugin flows.
    """

    def __init__(
        self,
        plugin_id,
        plugin_name,
        send_plugin_command: Optional[Callable] = None,
        send_command: Optional[Callable] = None,
    ):
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self._send_plugin_command = send_plugin_command
        self._send_command = send_command
        self._request_counter = count(1)
        self._counter_lock = Lock()

    def _next_request_id(self):
        with self._counter_lock:
            return f"{self.plugin_id}:{next(self._request_counter)}"

    def send_command(self, json_command):
        """Send a command synchronously through the configured sender.

        Returns a tuple ``(request_id, response)``.
        """
        request_id = self._next_request_id()
        response = None

        if self._send_plugin_command is not None:
            response = self._send_plugin_command(
                self.plugin_id,
                self.plugin_name,
                request_id,
                json_command,
            )
        elif self._send_command is not None:
            response = self._send_command(json_command)

        return request_id, response

    def send_command_async(self, json_command, callback=None, error_callback=None):
        """Send a command asynchronously using a lightweight worker thread."""

        request_id = self._next_request_id()

        def _runner():
            try:
                if self._send_plugin_command is not None:
                    response = self._send_plugin_command(
                        self.plugin_id,
                        self.plugin_name,
                        request_id,
                        json_command,
                    )
                elif self._send_command is not None:
                    response = self._send_command(json_command)
                else:
                    response = None

                if callback is not None:
                    callback(request_id, response)
            except Exception as exc:
                if error_callback is not None:
                    error_callback(request_id, exc)

        worker = Thread(target=_runner, daemon=True)
        worker.start()
        return request_id

class HSD_Plugin(ABC):
    """Abstract base class for Data Toolkit plugins.

    Plugins should implement the `process` method to transform or consume data
    objects and may optionally provide a `plot_widget` for UI visualization.
    The framework calls lifecycle hooks (`start_log_cb`, `stop_log_cb`,
    `tag_cb`) when appropriate.

    Attributes:
    - components_status: dict with per-component configuration shared by the
        controller.
    """

    def __init__(self):
        self.components_status = {}
        self.plugin_context = None
        self.plugin_id = None
        self.plugin_name = self.__class__.__name__

    def attach_context(self, plugin_context):
        """Attach a plugin command context provided by the runtime pipeline."""
        self.plugin_context = plugin_context
        self.plugin_id = plugin_context.plugin_id
        self.plugin_name = plugin_context.plugin_name

    def send_command(self, json_command):
        """Send a command through the plugin context in synchronous mode.

        Returns the controller response or ``None`` if no context is attached.
        """
        if self.plugin_context is None:
            return None
        _, response = self.plugin_context.send_command(json_command)
        return response

    def send_command_async(self, json_command, callback=None, error_callback=None):
        """Send a command asynchronously through the plugin context.

        Returns the generated request id, or ``None`` if context is unavailable.
        """
        if self.plugin_context is None:
            return None
        return self.plugin_context.send_command_async(
            json_command,
            callback=callback,
            error_callback=error_callback,
        )

    def get_components_status(self):
        """Return the full components status dictionary.

        Returns:
        - dict: per-component configuration.
        """
        return self.components_status

    def get_component_status(self, comp_name):
        """Return the status for a single component.

        Parameters:
        - comp_name: str component name.

        Returns:
        - dict: component configuration/status.
        """
        return self.components_status[comp_name]

    def start_log_cb(self):
        """Lifecycle hook invoked when logging starts.

        Override in plugins that need to initialize resources.
        """

    def stop_log_cb(self):
        """Lifecycle hook invoked when logging stops.

        Override in plugins that need to clean up resources.
        """

    def tag_cb(self, status, label):
        """Handle tagging events originating from the controller.

        Parameters:
        - status: any tag status object.
        - label: str user-provided label.
        """

    @abstractmethod
    def process(self, data):
        """Process a data object.

        Parameters:
        - data: `HSD_DataToolkit_data` or plugin-specific wrapper.

        Returns:
        - any: transformed data object passed to the next plugin.
        """

class HSD_DataToolkit_data:
    """Lightweight data container forwarded through the pipeline.

    Parameters:
    - comp_name: str component name.
    - data: any payload (usually a NumPy array or raw bytes).
    - timestamp: float | None packet timestamp when available.

    Attributes mirror the parameters for convenience.
    """

    def __init__(self, comp_name, data, timestamp):
        self.comp_name = comp_name
        self.data = data
        self.timestamp = timestamp

class HSD_DataToolkit_Pipeline:
    """Runtime plugin pipeline for the Data Toolkit.

    Discovers plugins from the folder provided by the controller, validates and
    instantiates them, and manages their associated plot widgets. Provides
    lifecycle orchestration (`start`, `stop`), tagging propagation, status
    updates, and data processing across the chain.

    Parameters:
    - controller: object exposing methods like
        `get_dt_plugin_folder_path()`, `clear_all_plugin_plot_widgets()`, and
        `add_plugin_plot_widget(widget)`.
    """

    # def __init__(self, plugins = [], device_status = {}):
    def __init__(self, controller):

        self.plugin_modules_names = []
        self.plugins = []
        self.controller = controller

        self.components_status = {}
        plugins_path = self.controller.get_dt_plugin_folder_path()
        if plugins_path is not None:
            try:
                # List all .py files in the specified data toolkit plugins directory
                files = os.listdir(plugins_path)
                # Filter out directories and non-.py files, keeping only .py files
                py_files = [
                    f for f in files
                    if (
                        os.path.isfile(os.path.join(plugins_path, f))
                        and f.endswith('.py')
                        and f != "__init__.py"
                    )
                ]
                # Remove the .py extension
                self.plugin_modules_names = [os.path.splitext(f)[0] for f in py_files]
            except Exception as e:
                print(f"An error occurred: {e}")
                return None
        else:
            return None

        # Add the provided path to sys.path
        sys.path.insert(0, plugins_path)

        # Clear all existing plugin plot widgets
        self.controller.clear_all_plugin_plot_widgets()

        # Register app-level controller for plugin plot factories.
        try:
            from stdatalog_gui.Widgets.Plots.PluginPlotWidget import PluginPlotWidget
            PluginPlotWidget.set_default_controller(self.controller)
        except Exception:
            pass

        print("len(self.plugin_modules):", len(self.plugin_modules_names))

        for index, plugin_name in enumerate(self.plugin_modules_names):
            plugin_instance = self.validate_plugin(plugin_name)
            if plugin_instance is None:
                continue

            plugin_id = f"plugin:{plugin_name}:{index}"
            plugin_context = PluginCommandContext(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                send_plugin_command=getattr(self.controller, "send_plugin_command", None),
                send_command=getattr(self.controller, "send_command", None),
            )
            if hasattr(plugin_instance, "attach_context"):
                plugin_instance.attach_context(plugin_context)

            # Call the plugin's graphics method
            widget = plugin_instance.create_plot_widget()

            self.plugins.append(plugin_instance)

            # If the plugin returns a widget, add it to the main layout
            if widget is not None:
                self._bind_plot_widget_controller(widget, self.controller)
                widget.parent = self.controller.plots_layout
                self.controller.add_plugin_plot_widget(widget)

    # def add_plugin(self, plugin):
    #     self.plugins.append(plugin)

    # def remove_plugin(self, plugin):
    #     self.plugins.remove(plugin)

    @staticmethod
    def _bind_plot_widget_controller(widget, controller):
        """Bind plugin plot widgets to the shared application controller.

        This reconnects runtime plot signals so plugin plots receive the same
        logging/detecting/time-window updates as standard plots.
        """
        if widget is None or controller is None:
            return

        def _safe_connect(source, signal_name, slot):
            signal = getattr(source, signal_name, None)
            if signal is not None and slot is not None:
                try:
                    signal.connect(slot)
                except (RuntimeError, TypeError):
                    pass

        def _safe_disconnect(source, signal_name, slot):
            signal = getattr(source, signal_name, None)
            if signal is not None and slot is not None:
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass

        def _bind_one(plot_widget):
            if plot_widget is None or not hasattr(plot_widget, "controller"):
                return

            old_controller = getattr(plot_widget, "controller", None)
            if old_controller is controller:
                if hasattr(plot_widget, "app_qt"):
                    plot_widget.app_qt = getattr(controller, "qt_app", None)
                return

            if old_controller is not None:
                _safe_disconnect(
                    old_controller,
                    "sig_logging",
                    getattr(plot_widget, "s_is_logging", None),
                )
                _safe_disconnect(
                    old_controller,
                    "sig_detecting",
                    getattr(plot_widget, "s_is_detecting", None),
                )
                _safe_disconnect(
                    old_controller,
                    "sig_plot_window_time_updated",
                    getattr(plot_widget, "s_time_window_updated", None),
                )

            plot_widget.controller = controller
            if hasattr(plot_widget, "app_qt"):
                plot_widget.app_qt = getattr(controller, "qt_app", None)

            _safe_connect(
                controller,
                "sig_logging",
                getattr(plot_widget, "s_is_logging", None),
            )
            _safe_connect(
                controller,
                "sig_detecting",
                getattr(plot_widget, "s_is_detecting", None),
            )
            _safe_connect(
                controller,
                "sig_plot_window_time_updated",
                getattr(plot_widget, "s_time_window_updated", None),
            )

        _bind_one(widget)

        # Support plugin containers exposing multiple internal plot widgets.
        nested_plots = getattr(widget, "_plots", None)
        if isinstance(nested_plots, (list, tuple)):
            for plot_widget in nested_plots:
                _bind_one(plot_widget)

    @staticmethod
    def validate_plugin(plugin_name):
        """Import and validate a plugin module.

        Parameters:
        - plugin_name: str module name (without `.py`).

        Returns:
        - object | None: a `PluginClass` instance if present, otherwise `None`.
        """
        # Import the module using its name
        plugin_module = importlib.import_module(plugin_name)
        try:
            PluginClass = getattr(plugin_module, "PluginClass")
            plugin_instance = PluginClass()
            return plugin_instance
        except AttributeError as e:
            match = re.search(r"module '([^']*)'", e.args[0])
            if match:
                print(f"{match.group(1)}.py module is not a valid plugin.")
            else:
                print(f"{e}")
            return None

    def start(self):
        """Start plugins and their plot timers if available.

        Returns:
        - None
        """
        for plugin in self.plugins:
            plugin.start_log_cb()
            if hasattr(plugin, 'plot_widget') and plugin.plot_widget is not None:
                if hasattr(plugin.plot_widget, 'timer'):
                    plugin.plot_widget.timer.start(200)
                else:
                    print("Plugin Plot Widget has no timer attribute")

    def stop(self):
        """Stop plugins and their plot timers if available.

        Returns:
        - None
        """
        for plugin in self.plugins:
            plugin.stop_log_cb()
            if hasattr(plugin, 'plot_widget') and plugin.plot_widget is not None:
                if hasattr(plugin.plot_widget, 'timer'):
                    plugin.plot_widget.timer.stop()
                else:
                    print("Plugin Plot Widget has no timer attribute")

    def do_tag(self, status, label):
        """Propagate tagging events to all plugins.

        Parameters:
        - status: any tag status object.
        - label: str user-provided label.
        """
        for plugin in self.plugins:
            plugin.tag_cb(status, label)

    def update_components_status(self, components_status):
        """Update and broadcast components status.

        Parameters:
        - components_status: dict per-component configuration.
        """
        self.components_status = components_status
        for plugin in self.plugins:
            plugin.components_status = components_status

    def process_data(self, data_obj):
        """Run data through the plugin chain.

        Parameters:
        - data_obj: `HSD_DataToolkit_data` instance from the controller.

        Returns:
        - any: final data object produced by the last plugin.
        """
        data = data_obj
        for plugin in self.plugins:
            data = plugin.process(data)
        return data
