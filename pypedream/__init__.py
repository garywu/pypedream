"""
A framework for data processing and data preparation DAG (directed acyclic graph) pipelines. 

The examples in the documentation assume 

>>> from __future__ import print_function

if running pre Py3K, as well as

>>> from dagpype import *
"""


import types

from . import _core
from . import _src
from . import _filt
from . import _snk
from . import _subgroup_filt


try:
    from ._core import *
    from ._src import *
    from ._filt import *
    from ._snk import *
    from ._subgroup_filt import *
    from ._csv_utils import *
except ValueError:
    from _core import *
    from _src import *
    from _filt import *
    from _snk import *
    from _subgroup_filt import *
    from _csv_utils import *
from . import np
from . import plot


__all__ = []
for m in [_core, _src, _filt, _snk, _subgroup_filt]:
    for s in dir(m):
        if s[0] == '_':
            continue
        if eval('not isinstance(m.%s, types.ModuleType)' % s):
            __all__.append(s)
__all__.extend(['np', 'plot'])
__version__ = '0.1.0.3'
__author__ = 'Ami Tavory <atavory at gmail.com>'

