"""
Plotting stages.
"""
    
import types

from dagpype.plot import _filt
from dagpype.plot import _snk
try:
    for fn in _filt._fns:
        exec('from ._filt import %s' % fn)
    for fn in _snk._fns:
        exec('from ._snk import %s' % fn)
except ValueError:
    for fn in _filt._fns:
        exec('from _filt import %s' % fn)
    for fn in _snk._fns:
        exec('from _snk import %s' % fn)


__all__ = []
for m in [_filt, _snk]:
    for s in dir(m):
        if s[0] == '_':
            continue
        try:
            if eval('not isinstance(m.%s, types.ModuleType)' % s):
                __all__.append(s)
        except NameError as e:
            pass
        
