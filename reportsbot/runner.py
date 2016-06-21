# -*- coding: utf-8 -*-

"""
This module contains Reports bot's task runner.
"""

from importlib.machinery import SourceFileLoader
import os.path

from .bot import Bot
from .exceptions import TaskLoaderError
from .logging import get_logger
from .task import Task

__all__ = ["find_task", "run_task"]

_logger = get_logger("runner")

def _get_module_info_for_task(name, base_dir):
    """Convert a task name and base directory into a module name and path."""
    if os.path.isabs(name):
        path = name
    else:
        path = os.path.join(os.path.abspath(base_dir), name)
    if not os.path.exists(path) and not path.endswith(".py"):
        path += ".py"
    path = os.path.normpath(path)

    modname = os.path.split(path)[1].rsplit(".", 1)[0].replace("-", "_")
    return modname, path

def _extract_task_class(objects):
    """Given a list of objects, try to return the correct Task subclass."""
    classes = []
    for obj in objects:
        if type(obj) is type and issubclass(obj, Task) and obj is not Task:
            classes.append(obj)

    if len(classes) != 1:
        classnames = [klass.__name__ for klass in classes]
        _logger.debug("No unique task class; candidates: %s", classnames)
        return None

    _logger.debug("Found unique task class: %s", classes[0].__name__)
    return classes[0]

def _get_task_class_from_module(module):
    """Extract the main Task subclass from the given module.

    There are two main ways we do this. If the module has an __all__ attribute,
    we'll check if exactly one of its elements refers to a valid subclass of
    Task. Otherwise, we'll check in the module's __dict__ for exactly one valid
    subclass of Task. If both of these checks fail, we'll return None.
    """
    if "__all__" in vars(module):
        _logger.debug("Searching within %s.__all__", module.__name__)
        objects = [getattr(module, name) for name in module.__all__
                   if hasattr(module, name)]
        task = _extract_task_class(objects)
        if task:
            return task

    _logger.debug("Searching within %s.__dict__", module.__name__)
    return _extract_task_class(vars(module).values())

def find_task(name, base_dir="."):
    """Locate and return the Task object for the given task name.

    If the name is not an absolute path, it will be treated as relative to the
    given base directory.

    Raises TaskLoaderError if the task couldn't be found.
    """
    modname, path = _get_module_info_for_task(name, base_dir)

    _logger.debug("Loading task '%s' from '%s'", modname, path)
    try:
        module = SourceFileLoader(modname, path).load_module()
    except Exception:
        msg = "Couldn't import task module: %s (%s)"
        _logger.exception(msg, name, path)
        raise TaskLoaderError(path)

    task = _get_task_class_from_module(module)
    if not task:
        msg = "Couldn't find task class within module: %s (%s)"
        _logger.exception(msg, name, path)
        raise TaskLoaderError(path)

    return task

def run_task(task, config, project=None, lang=None):
    """Execute the given Task object.

    A Config object must also be provided. If a project or language is not
    given, then we'll use the config's defaults.
    """
    if not project:
        project = config.default_project
    if not lang:
        lang = config.default_lang
    log_args = (lang, project, task.__name__)

    _logger.info("Running task (%s.%s): %s", *log_args)
    bot = Bot(config, project, lang)

    try:
        task(bot).run()
    except Exception:
        _logger.exception("Task crashed (%s.%s): %s", *log_args)
    else:
        _logger.info("Task finished (%s.%s): %s", *log_args)
