# *****************************************************************************
#
#   Part of the py5 library
#   Copyright (C) 2020-2022 Jim Schmitz
#
#   This library is free software: you can redistribute it and/or modify it
#   under the terms of the GNU Lesser General Public License as published by
#   the Free Software Foundation, either version 2.1 of the License, or (at
#   your option) any later version.
#
#   This library is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
#   General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#   along with this library. If not, see <https://www.gnu.org/licenses/>.
#
# *****************************************************************************
# *** FORMAT PARAMS ***
from __future__ import annotations

import time
import os
import sys
import platform
import warnings
from io import BytesIO
from pathlib import Path
import functools
from typing import overload, Any, Callable, Union  # noqa

import jpype
from jpype.types import JException, JArray, JInt  # noqa

import numpy as np
import numpy.typing as npt

import py5_tools.environ as _environ
from py5_tools.printstreams import _DefaultPrintlnStream, _DisplayPubPrintlnStream
from .methods import Py5Methods
from .base import Py5Base
from .mixins import MathMixin, DataMixin, ThreadsMixin, PixelMixin, PrintlnStream
from .mixins.threads import Py5Promise  # noqa
from .image import Py5Image, _return_py5image  # noqa
from .shape import Py5Shape, _return_py5shape, _load_py5shape  # noqa
from .surface import Py5Surface, _return_py5surface  # noqa
from .shader import Py5Shader, _return_py5shader, _load_py5shader  # noqa
from .font import Py5Font, _return_py5font, _load_py5font, _return_list_str  # noqa
from .graphics import Py5Graphics, _return_py5graphics  # noqa
from .decorators import _text_fix_str, _convert_hex_color, _context_wrapper  # noqa
from .pmath import _get_matrix_wrapper  # noqa
from . import image_conversion
from .image_conversion import NumpyImageArray, _convertable
from . import reference

sketch_class_members_code = None  # DELETE

_Sketch = jpype.JClass('py5.core.Sketch')


try:
    # be aware that __IPYTHON__ and get_ipython() are inserted into the user namespace late in the kernel startup process
    __IPYTHON__  # type: ignore
    if sys.platform == 'darwin' and get_ipython().active_eventloop != 'osx':  # type: ignore
        print("Importing py5 on OSX but the necessary Jupyter OSX event loop not been activated. I'll activate it for you, but next time, execute `%gui osx` before importing this library.")
        _ipython_shell.run_line_magic('gui', 'osx')
except Exception:
    pass


_PY5_LAST_WINDOW_X = None
_PY5_LAST_WINDOW_Y = None


def _auto_convert_to_py5image(f):
    @functools.wraps(f)
    def decorated(self_, *args):
        args_index = args[0]
        if isinstance(args_index, NumpyImageArray):
            args = self_.create_image_from_numpy(args_index.array, args_index.bands), *args[1:]
        elif not isinstance(args_index, (Py5Image, Py5Graphics)) and _convertable(args_index):
            args = self_.convert_image(args_index), *args[1:]
        return f(self_, *args)
    return decorated


class Sketch(MathMixin, DataMixin, ThreadsMixin, PixelMixin, PrintlnStream, Py5Base):
    """$classdoc_Sketch
    """

    _cls = _Sketch

    def __init__(self, *args, **kwargs):
        super().__init__(instance=_Sketch())
        self._methods_to_profile = []
        self._pre_hooks_to_add = []
        self._post_hooks_to_add = []
        # must always keep the py5_methods reference count from hitting zero.
        # otherwise, it will be garbage collected and lead to segmentation faults!
        self._py5_methods = None
        self._environ = None
        iconPath = Path(__file__).parent.parent / 'py5_tools/kernel/resources/logo-64x64.png'
        if iconPath.exists():
            self._instance.setPy5IconPath(str(iconPath))
        elif hasattr(sys, '_MEIPASS'):
            warnings.warn("py5 logo image cannot be found. You are running this Sketch with pyinstaller and the image is missing from the packaging. I'm going to nag you until you fix it :)")
        _Sketch.setJOGLProperties(str(Path(__file__).parent))

        # attempt to instantiate Py5Utilities
        self.utils = None
        try:
            self.utils = jpype.JClass('py5.utils.Py5Utilities')(self._instance)
        except Exception:
            pass


    def run_sketch(self, block: bool = None, *,
                   py5_options: list = None, sketch_args: list = None) -> None:
        """$class_Sketch_run_sketch"""
        if not hasattr(self, '_instance'):
            raise RuntimeError(
                ('py5 internal problem: did you create a class with an `__init__()` '
                 'method without a call to `super().__init__()`?')
            )

        methods = dict([(e, getattr(self, e)) for e in reference.METHODS if hasattr(self, e) and callable(getattr(self, e))])
        self._run_sketch(methods, block, py5_options, sketch_args)

    def _run_sketch(self,
                    methods: dict[str, Callable],
                    block: bool,
                    py5_options: list[str] = None,
                    sketch_args: list[str] = None) -> None:
        self._environ = _environ.Environment()
        self.set_println_stream(_DisplayPubPrintlnStream() if self._environ.in_jupyter_zmq_shell else _DefaultPrintlnStream())
        self._init_println_stream()

        self._py5_methods = Py5Methods(self)
        self._py5_methods.set_functions(**methods)
        self._py5_methods.profile_functions(self._methods_to_profile)
        self._py5_methods.add_pre_hooks(self._pre_hooks_to_add)
        self._py5_methods.add_post_hooks(self._post_hooks_to_add)
        self._instance.usePy5Methods(self._py5_methods)

        if not py5_options: py5_options = []
        if not sketch_args: sketch_args = []
        if not any([a.startswith('--sketch-path') for a in py5_options]):
            py5_options.append('--sketch-path=' + os.getcwd())
        if not any([a.startswith('--location') for a in py5_options]) and _PY5_LAST_WINDOW_X is not None and _PY5_LAST_WINDOW_Y is not None:
            py5_options.append('--location=' + str(_PY5_LAST_WINDOW_X) + ',' + str(_PY5_LAST_WINDOW_Y))
        args = py5_options + [''] + sketch_args

        try:
            _Sketch.runSketch(args, self._instance)
        except Exception as e:
            self.println('Java exception thrown by Sketch.runSketch:\n' + str(e), stderr=True)

        if platform.system() == 'Darwin' and self._environ.in_ipython_session and block:
            if (renderer := self._instance.getRendererName()) in ['JAVA2D', 'P2D', 'P3D', 'FX2D']:
                self.println("On OSX, blocking is not allowed in Jupyter when using the", renderer, "renderer.", stderr=True)
                block = False

        if block or (block is None and not self._environ.in_ipython_session):
            # wait for the sketch to finish
            surface = self.get_surface()
            if surface._instance is not None:
                while not surface.is_stopped() and not hasattr(self, '_shutdown_initiated'):
                    time.sleep(0.25)

            # Wait no more than 1 second for any shutdown tasks to complete.
            # This will not wait for the user's `exiting` method, as it has
            # already been called. It will not wait for any threads to exit, as
            # that code calls `stop_all_threads(wait=False)` in its shutdown
            # procedure. Bottom line, this currently doesn't do very much but
            # might if a mixin had more complex shutdown steps.
            time_waited = 0
            while time_waited < 1.0 and not hasattr(self, '_shutdown_complete'):
                pause = 0.01
                time_waited += pause
                time.sleep(pause)

    def _shutdown(self):
        global _PY5_LAST_WINDOW_X
        global _PY5_LAST_WINDOW_Y
        if self._instance.lastWindowX is not None and self._instance.lastWindowY is not None:
            _PY5_LAST_WINDOW_X = int(self._instance.lastWindowX)
            _PY5_LAST_WINDOW_Y = int(self._instance.lastWindowY)
        super()._shutdown()

    def _terminate_sketch(self):
        self._instance.noLoop()
        self._shutdown_initiated = True
        self._shutdown()

    def _add_pre_hook(self, method_name, hook_name, function):
        if self._py5_methods is None:
            self._pre_hooks_to_add.append((method_name, hook_name, function))
        else:
            self._py5_methods.add_pre_hook(method_name, hook_name, function)

    def _remove_pre_hook(self, method_name, hook_name):
        if self._py5_methods is None:
            self._pre_hooks_to_add = [x for x in self._pre_hooks_to_add if x[0] != method_name and x[1] != hook_name]
        else:
            self._py5_methods.remove_pre_hook(method_name, hook_name)

    def _add_post_hook(self, method_name, hook_name, function):
        if self._py5_methods is None:
            self._post_hooks_to_add.append((method_name, hook_name, function))
        else:
            self._py5_methods.add_post_hook(method_name, hook_name, function)

    def _remove_post_hook(self, method_name, hook_name):
        if self._py5_methods is None:
            self._post_hooks_to_add = [x for x in self._post_hooks_to_add if x[0] != method_name and x[1] != hook_name]
        else:
            self._py5_methods.remove_post_hook(method_name, hook_name)

    # *** BEGIN METHODS ***

    @overload
    def sketch_path(self) -> Path:
        """$class_Sketch_sketch_path"""
        pass

    @overload
    def sketch_path(self, where: str, /) -> Path:
        """$class_Sketch_sketch_path"""
        pass

    def sketch_path(self, *args) -> Path:
        """$class_Sketch_sketch_path"""
        if len(args) <= 1:
            return Path(str(self._instance.sketchPath(*args)))
        else:
            # this exception will be replaced with a more informative one by the custom exception handler
            raise TypeError('The parameters are invalid for method sketch_path')

    def _get_is_ready(self) -> bool:  # @decorator
        """$class_Sketch_is_ready"""
        surface = self.get_surface()
        # if there is no surface yet, the sketch can be run.
        return surface._instance is None
    is_ready: bool = property(fget=_get_is_ready, doc="""$class_Sketch_is_ready""")

    def _get_is_running(self) -> bool:  # @decorator
        """$class_Sketch_is_running"""
        surface = self.get_surface()
        if surface._instance is None:
            # Sketch has not been run yet
            return False
        else:
            return not surface.is_stopped() and not hasattr(self, '_shutdown_initiated')
    is_running: bool = property(fget=_get_is_running, doc="""$class_Sketch_is_running""")

    def _get_is_dead(self) -> bool:  # @decorator
        """$class_Sketch_is_dead"""
        surface = self.get_surface()
        if surface._instance is None:
            # Sketch has not been run yet
            return False
        return surface.is_stopped() or hasattr(self, '_shutdown_initiated')
    is_dead: bool = property(fget=_get_is_dead, doc="""$class_Sketch_is_dead""")

    def _get_is_dead_from_error(self) -> bool:  # @decorator
        """$class_Sketch_is_dead_from_error"""
        return self.is_dead and not self._instance.getSuccess()
    is_dead_from_error: bool = property(fget=_get_is_dead_from_error, doc="""$class_Sketch_is_dead_from_error""")

    def _get_is_mouse_pressed(self) -> bool:  # @decorator
        """$class_Sketch_is_mouse_pressed"""
        return self._instance.isMousePressed()
    is_mouse_pressed: bool = property(fget=_get_is_mouse_pressed, doc="""$class_Sketch_is_mouse_pressed""")

    def _get_is_key_pressed(self) -> bool:  # @decorator
        """$class_Sketch_is_key_pressed"""
        return self._instance.isKeyPressed()
    is_key_pressed: bool = property(fget=_get_is_key_pressed, doc="""$class_Sketch_is_key_pressed""")

    def hot_reload_draw(self, draw: Callable) -> None:
        """$class_Sketch_hot_reload_draw"""
        self._py5_methods.set_functions(**dict(draw=draw))

    def profile_functions(self, function_names: list[str]) -> None:
        """$class_Sketch_profile_functions"""
        if self._py5_methods is None:
            self._methods_to_profile.extend(function_names)
        else:
            self._py5_methods.profile_functions(function_names)

    def profile_draw(self) -> None:
        """$class_Sketch_profile_draw"""
        self.profile_functions(['draw'])

    def print_line_profiler_stats(self) -> None:
        """$class_Sketch_print_line_profiler_stats"""
        self._py5_methods.dump_stats()

    def _insert_frame(self, what, num=None):
        """Utility function to insert a number into a filename.

        This is just like PApplet's insertFrame method except it allows you to
        override the frameCount with something else.
        """
        if num is None:
            num = self._instance.frameCount
        first = what.find('#')
        last = len(what) - what[::-1].find('#')
        if first != -1 and last - first > 1:
            count = last - first
            numstr = str(num)
            numprefix = '0' * (count - len(numstr))
            what = what[:first] + numprefix + numstr + what[last:]
        return what

    def save_frame(self, filename: Union[str, Path, BytesIO], *, format: str = None, drop_alpha: bool = True, use_thread: bool = False, **params) -> None:
        """$class_Sketch_save_frame"""
        if not isinstance(filename, BytesIO):
            filename = self._insert_frame(str(filename))
        self.save(filename, format=format, drop_alpha=drop_alpha, use_thread=use_thread, **params)

    # *** Py5Image methods ***

    def create_image_from_numpy(self, array: npt.NDArray[np.uint8], bands: str = 'ARGB', *, dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_create_image_from_numpy"""
        height, width = array.shape[:2]

        if dst:
            if width != dst.pixel_width or height != dst.pixel_height:
                raise RuntimeError("array size does not match size of dst Py5Image")
            py5_img = dst
        else:
            py5_img = self.create_image(width, height, self.ARGB)

        py5_img.set_np_pixels(array, bands)

        return py5_img

    def convert_image(self, obj: Any, *, dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_convert_image"""
        result = image_conversion._convert(obj)
        if isinstance(result, (Path, str)):
            return self.load_image(result, dst=dst)
        elif isinstance(result, NumpyImageArray):
            return self.create_image_from_numpy(result.array, result.bands, dst=dst)
        else:
            # could be Py5Image or something comparable
            return result

    def load_image(self, image_path: Union[str, Path], *, dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_load_image"""
        try:
            pimg = self._instance.loadImage(str(image_path))
        except JException as e:
            msg = 'cannot load image file ' + str(image_path)
            if e.message() == 'None':
                msg += '. error message: either the file cannot be found or the file does not contain valid image data.'
            else:
                msg += '. error message: ' + e.message()
        else:
            if pimg and pimg.width > 0:
                if dst:
                    if pimg.pixel_width != dst.pixel_width or pimg.pixel_height != dst.pixel_height:
                        raise RuntimeError("size of loaded image does not match size of dst Py5Image")
                    dst._replace_instance(pimg)
                    return dst
                else:
                    return Py5Image(pimg)
            else:
                raise RuntimeError('cannot load image file ' + str(image_path) + '. error message: either the file cannot be found or the file does not contain valid image data.')
        raise RuntimeError(msg)

    def request_image(self, image_path: Union[str, Path]) -> Py5Promise:
        """$class_Sketch_request_image"""
        return self.launch_promise_thread(self.load_image, args=(image_path,))


{sketch_class_members_code}
