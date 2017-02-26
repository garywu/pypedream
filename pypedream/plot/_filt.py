import numpy
has_matplotlib = True
try:
    from matplotlib import pyplot, figure
except ImportError:
    has_matplotlib = False 

from dagpype._core import filters


def _make_relay_call(fn, name):
    def new_fn(*args, **kwargs):
        @filters
        def _dagpype_internal_fn_act(target):
            try:
                while True:
                    target.send((yield))
            except GeneratorExit:
                fn(*args, **kwargs)
                target.close()

        return _dagpype_internal_fn_act

    new_fn.__name__ = name
    new_fn.__doc__ = """
        Convenience filter utility for corresponding function in pyplot.

        Example:

        >>> source([1, 2, 3, 4]) | plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | (plot.plot() | plot.savefig('foo.png'))
        """

    return new_fn


_try_fns = [
    'annotate',
    'arrow',   
    'autogen_docstring',
    'autoscale',
    'autumn',
    'axes',
    'axhline',
    'axhspan',
    'axis',
    'axvline',
    'axvspan',
    'barbs',
    'bone',
    'box',
    'broken_barh',
    'cla',
    'clabel',
    'clf',
    'clim',
    'cm',
    'cohere',
    'colorbar',
    'colormaps',
    'colors',
    'connect',
    'cool',
    'copper',
    'csd',
    'dedent',
    'delaxes',
    'docstring',
    'draw',
    'figaspect',
    'figimage',
    'figlegend',
    'figtext',
    'figure',
    'fill',
    'fill_between',
    'fill_betweenx',
    'flag',
    'gca',
    'gcf',
    'gci',
    'get',
    'gray',
    'grid',
    'hold',
    'hot',
    'hsv',
    'jet',
    'locator_params',
    'margins',
    'minorticks_off',
    'minorticks_on',
    'normalize',
    'over',
    'pcolor',
    'pcolormesh',
    'pink',
    'plotfile',
    'plotting',
    'polar',
    'prism',
    'psd',
    'quiver',
    'quiverkey',
    'rc',
    'register_cmap',
    'rgrids',
    'sca',
    'sci',
    'set_cmap',
    'setp',
    'silent_list',
    'specgram',
    'spectral',
    'spring',
    'spy',
    'stem',
    'step',
    'subplot',
    'subplot2grid',
    'subplot_tool',
    'subplots',
    'subplots_adjust',
    'summer',
    'suptitle',
    'table',
    'text',
    'thetagrids',
    'tick_params',
    'ticklabel_format',
    'tight_layout',
    'title',
    'tricontour',
    'tricontourf',
    'tripcolor',
    'triplot',
    'twinx',
    'twiny',
    'winter',
    'xlabel',
    'xlim',
    'xscale',
    'xticks',
    'ylabel',
    'ylim',
    'yscale',
    'yticks']

_fns = []
if has_matplotlib:
    for fn in _try_fns:
        try:
            exec('%s = _make_relay_call(pyplot.%s, "%s")' % (fn, fn, fn))
            _fns.append(fn)
        except AttributeError:
            pass

