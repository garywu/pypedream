import numpy
import types
import functools
import itertools
has_matplotlib = True
try:
    from matplotlib import pyplot, figure
except ImportError:
    has_matplotlib = False

from dagpype._core import sinks


def plot(*args, **kwargs):
    """
    Convenience sink utility for pyplot's plot.

    Example:

    >>> source([1, 2, 3, 4]) | plot.hold(True) | (plot.plot() | plot.savefig('foo.png'))
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        l = []
        try:
            while True:
                l.append((yield))
        except GeneratorExit:  
            if len(l) > 0 and isinstance(l[0], tuple):
                xs = tuple([x[i] for x in l] for i in range(len(l[0])))            
                xs = tuple(itertools.chain.from_iterable(
                    itertools.izip_longest(
                        itertools.islice(xs, 0, None, 2),
                        itertools.islice(xs, 1, None, 2),
                        args)))            
                xs = [x for x in xs if x is not None]
                r = functools.partial(pyplot.plot, **kwargs)(*xs)
            else:
                r = pyplot.plot(l, *args, **kwargs)
            target.send(r)    
            target.close()

    return _dagpype_internal_fn_act


def _make_x_call(fn, name):
    def new_fn(*args, **kwargs):
        @sinks
        def _dagpype_internal_fn_act(target):
            x = []
            try:
                while True:
                    x.append((yield))
            except GeneratorExit:
                r = functools.partial(fn, *args, **kwargs)(x)
                target.send(r)    
                target.close()

        return _dagpype_internal_fn_act

    new_fn.__name__ = name
    new_fn.__doc__ = """
        Convenience sink utility for corresponding function in pyplot.

        Examples:

        >>> source([1, 2, 3, 4]) | (pyplot.pie() | plot.savefig('pie.png'))
        >>> source(range(100)) | (pyplot.acorr() | plot.savefig('acorr.png'))
        """

    return new_fn


def _make_xy_call(fn, name):
    def new_fn(*args, **kwargs):
        @sinks
        def _dagpype_internal_fn_act(target):
            x, y = [], []
            try:
                while True:
                    e = (yield)
                    assert len(e) == 2
                    x.append(e[0])
                    y.append(e[1])
            except GeneratorExit:
                r = functools.partial(fn, *args, **kwargs)(x, y)
                target.send(r)    
                target.close()

        return _dagpype_internal_fn_act

    new_fn.__name__ = name
    new_fn.__doc__ = """
        Convenience sink utility for corresponding function in pyplot.

        Examples:

        >>> source([1, 2, 3, 4]) + source([2, 3, 6, 7]) | figure(0) | (plot.scatter() | plot.savefig('foo.png'))
        >>> source([1, 2, 3, 4]) + source([2, 3, 6, 7]) | figure(1) | (plot.hexbin() | plot.savefig('bar.png'))
        """

    return new_fn


def _make_call(fn, name):
    def new_fn(*args, **kwargs):
        @sinks
        def _dagpype_internal_fn_act(target):
            x, y = [], []
            try:
                while True:
                    target.send((yield))
            except GeneratorExit:
                fn(*args, **kwargs)
                target.close()

        return _dagpype_internal_fn_act

    new_fn.__name__ = name
    new_fn.__doc__ = """
        Convenience sink utility for corresponding function in pyplot.

        Examples:

        >>> source([1, 2, 3, 4]) | plot.hold(True) | (plot.plot() | plot.savefig('foo.png'))
        >>> source([1, 2, 3, 4]) | plot.hold(True) | (plot.plot() | plot.show())
        """

    return new_fn


_x_fns = [
    'acorr',
    'pie',
    'hist']

_xy_fns = [
    'scatter',
    'hexbin',
    'xcorr']

_none_fns = [
    'show',
    'legend',
    'savefig']

if has_matplotlib:
    _fns = ['plot'] + _x_fns + _xy_fns + _none_fns


    for fn in _x_fns:
        exec('%s = _make_x_call(pyplot.%s, "%s")' % (fn, fn, fn))
    for fn in _xy_fns:
        exec('%s = _make_xy_call(pyplot.%s, "%s")' % (fn, fn, fn))
    for fn in _none_fns:
        exec('%s = _make_call(pyplot.%s, "%s")' % (fn, fn, fn))
else:
    _fns = []


#    'vlines',
#    'hlines',
#    'bar',
#    'barh',
#    'boxplot',
#    'contour',
#    'contourf',
#    'errorbar',
#     'hexbin',
#    'hist',
#    'loglog',
#    'plot_date',
#    'semilogx',
#    'semilogy',


