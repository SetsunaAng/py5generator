# *****************************************************************************
#
#   Part of the py5 library
#   Copyright (C) 2020-2021 Jim Schmitz
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
import time
import os
import logging
from pathlib import Path
import functools
from typing import overload, Any, Callable, Union, Dict, List  # noqa
from nptyping import NDArray, Float  # noqa

import jpype
from jpype.types import JException, JArray, JInt  # noqa

import numpy as np  # noqa

from .methods import Py5Methods
from .base import Py5Base
from .mixins import MathMixin, DataMixin, ThreadsMixin, PixelMixin
from .mixins.threads import Py5Promise  # noqa
from .image import Py5Image, _return_py5image  # noqa
from .shape import Py5Shape, _return_py5shape, _load_py5shape  # noqa
from .surface import Py5Surface, _return_py5surface  # noqa
from .shader import Py5Shader, _return_py5shader, _load_py5shader  # noqa
from .font import Py5Font, _return_py5font, _load_py5font, _return_list_str  # noqa
from .graphics import Py5Graphics, _return_py5graphics  # noqa
from .type_decorators import _text_fix_str  # noqa
from .pmath import _get_matrix_wrapper  # noqa
from . import image_conversion
from .image_conversion import NumpyImageArray, _convertable
from . import reference

sketch_class_members_code = None  # DELETE

_Py5Applet = jpype.JClass('py5.core.Py5Applet')

try:
    __IPYTHON__  # type: ignore
    _in_ipython_session = True
except NameError:
    _in_ipython_session = False

logger = logging.getLogger(__name__)


def _auto_convert_to_py5image(f):
    @functools.wraps(f)
    def decorated(self_, *args):
        args_index = args[0]
        if isinstance(args_index, NumpyImageArray):
            args = list(args)
            args[0] = self_.create_image_from_numpy(args_index)
        elif not isinstance(args_index, Py5Image) and _convertable(args_index):
            args = list(args)
            args[0] = self_.convert_image(args_index)
        return f(self_, *tuple(args))
    return decorated


class Sketch(MathMixin, DataMixin, ThreadsMixin, PixelMixin, Py5Base):
    """$classdoc_Sketch
    """

    _cls = _Py5Applet

    def __init__(self, *args, **kwargs):
        self._py5applet = _Py5Applet()
        super().__init__(instance=self._py5applet)
        self._methods_to_profile = []
        self._pre_hooks_to_add = []
        self._post_hooks_to_add = []
        # must always keep the py5_methods reference count from hitting zero.
        # otherwise, it will be garbage collected and lead to segmentation faults!
        self._py5_methods = None

        # attempt to instantiate Py5Utilities
        self.utils = None
        try:
            self.utils = jpype.JClass('py5.utils.Py5Utilities')(self._py5applet)
        except Exception:
            pass

    def run_sketch(self, block: bool = None,
                   py5_options: List = None, sketch_args: List = None) -> None:
        """$class_Sketch_run_sketch"""
        if block is None:
            block = not _in_ipython_session

        if not hasattr(self, '_instance'):
            raise RuntimeError(
                ('py5 internal problem: did you create a class with an `__init__()` '
                 'method without a call to `super().__init__()`?')
            )

        methods = dict([(e, getattr(self, e)) for e in reference.METHODS if hasattr(self, e) and callable(getattr(self, e))])
        self._run_sketch(methods, block, py5_options, sketch_args)

    def _run_sketch(self,
                    methods: Dict[str, Callable],
                    block: bool,
                    py5_options: List = None,
                    sketch_args: List = None) -> None:
        self._py5_methods = Py5Methods(self)
        self._py5_methods.set_functions(**methods)
        self._py5_methods.profile_functions(self._methods_to_profile)
        self._py5_methods.add_pre_hooks(self._pre_hooks_to_add)
        self._py5_methods.add_post_hooks(self._post_hooks_to_add)
        self._py5applet.usePy5Methods(self._py5_methods)

        if not py5_options: py5_options = []
        if not sketch_args: sketch_args = []
        if not any([a.startswith('--sketch-path') for a in py5_options]):
            py5_options.append('--sketch-path=' + os.getcwd())
        args = py5_options + [''] + sketch_args

        try:
            _Py5Applet.runSketch(args, self._py5applet)
        except Exception:
            logger.exception('exception thrown by Py5Applet.runSketch')

        if block:
            # wait for the sketch to finish
            surface = self.get_surface()
            if surface._instance is not None:
                while not surface.is_stopped():
                    time.sleep(0.25)

            # wait no more than 1 second for any shutdown tasks to complete
            time_waited = 0
            while time_waited < 1.0:
                pause = 0.01
                time_waited += pause
                time.sleep(pause)

    def _shutdown(self):
        super()._shutdown()

    def _terminate_sketch(self):
        surface = self.get_surface()
        if surface._instance is not None:
            surface.stop_thread()
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

    @property
    def is_ready(self) -> bool:
        """$class_Sketch_is_ready"""
        surface = self.get_surface()
        # if there is no surface yet, the sketch can be run.
        return surface._instance is None

    @property
    def is_running(self) -> bool:
        """$class_Sketch_is_running"""
        surface = self.get_surface()
        if surface._instance is None:
            # Sketch has not been run yet
            return False
        else:
            return not surface.is_stopped()

    @property
    def is_dead(self) -> bool:
        """$class_Sketch_is_dead"""
        surface = self.get_surface()
        if surface._instance is None:
            # Sketch has not been run yet
            return False
        return surface.is_stopped()

    @property
    def is_dead_from_error(self) -> bool:
        """$class_Sketch_is_dead_from_error"""
        return self.is_dead and not self._instance.getSuccess()

    def hot_reload_draw(self, draw: Callable) -> None:
        """$class_Sketch_hot_reload_draw"""
        self._py5_methods.set_functions(**dict(draw=draw))

    def profile_functions(self, function_names: List[str]) -> None:
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

    def save_frame(self, filename: Union[str, Path], format: str = None, drop_alpha: bool = True, use_thread: bool = True, **params) -> None:
        """$class_Sketch_save_frame"""
        self.save(self._insert_frame(str(filename)), format=format, drop_alpha=drop_alpha, use_thread=use_thread, **params)

    # *** Py5Image methods ***

    def create_image_from_numpy(self, numpy_image: NumpyImageArray, dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_create_image_from_numpy"""
        height, width = numpy_image.array.shape[:2]

        if dst:
            if width != dst.pixel_width or height != dst.pixel_height:
                raise RuntimeError("array size does not match size of dst Py5Image")
            py5_img = dst
        else:
            py5_img = self.create_image(width, height, self.ARGB)

        py5_img.set_np_pixels(numpy_image.array, numpy_image.bands)

        return py5_img

    def convert_image(self, obj: Any, dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_convert_image"""
        result = image_conversion._convert(obj)
        if isinstance(result, (Path, str)):
            return self.load_image(result, dst=dst)
        elif isinstance(result, Path):
            ret = self.load_image(result, dst=dst)
            # result.close()
            os.remove(result)
            return ret
        elif isinstance(result, NumpyImageArray):
            return self.create_image_from_numpy(result, dst=dst)

    def load_image(self, filename: Union[str, Path], dst: Py5Image = None) -> Py5Image:
        """$class_Sketch_load_image"""
        try:
            pimg = self._instance.loadImage(str(filename))
        except JException as e:
            msg = 'cannot load image file ' + str(filename)
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
                raise RuntimeError('cannot load image file ' + str(filename) + '. error message: either the file cannot be found or the file does not contain valid image data.')
        raise RuntimeError(msg)

    def request_image(self, filename: Union[str, Path]) -> Py5Promise:
        """$class_Sketch_request_image"""
        return self.launch_promise_thread(self.load_image, args=(filename,))


{sketch_class_members_code}
