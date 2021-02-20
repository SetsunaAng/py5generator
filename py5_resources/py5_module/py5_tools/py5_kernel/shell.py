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
from ipykernel.zmqshell import ZMQInteractiveShell
from IPython.core.interactiveshell import InteractiveShellABC
from traitlets import Unicode, List

from ..parsing import TransformDynamicVariablesToCalls


class Py5Shell(ZMQInteractiveShell):

    ast_transformers = List([TransformDynamicVariablesToCalls()]).tag(config=True)

    banner2 = Unicode("Activating py5 imported mode").tag(config=True)


InteractiveShellABC.register(Py5Shell)
