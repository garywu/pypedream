"""
Numpy stages.

The examples in this section assume

>>> import numpy
"""
    
import types


try:
    from ._src import *
    from ._filt import *
    from ._snk import *
except ValueError:
    from _src import *
    from _filt import *
    from _snk import *


__all__ = []
for m in [_src, _filt, _snk]:
    for s in dir(m):
        if s[0] == '_':
            continue
        try:
            if eval('not isinstance(m.%s, types.ModuleType)' % s):
                __all__.append(s)
        except NameError as e:
            pass
        
