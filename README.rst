=======
pypedream
=======

Forked from [DAGPype-0.1.5.1 by Ami Tavory](https://pypi.python.org/pypi/DAGPype)

This is a Python framework for scientific data-processing and data-preparation DAG (directed acyclic graph) pipelines.

It is designed to work well within Python scripts or IPython_, provide an in-Python alternative for sed_, awk_, perl_, and grep_, and complement libraries such as NumPy_/SciPy_, SciKits_, pandas_, MayaVi_, PyTables_, and so forth. Those libraries process data once it has been assembled. This library is for flexible data assembly and quick exploration, or for aggregating huge data which cannot be reasonably assembled.

.. _sed: http://www.gnu.org/software/sed/
.. _awk: http://www.gnu.org/software/gawk/
.. _perl: http://www.perl.org
.. _grep: http://www.gnu.org/software/grep/
.. _IPython: http://ipython.org/
.. _SciKits: http://scikits.appspot.com/
.. _NumPy: http://www.numpy.org/
.. _SciPy: http://www.scipy.org/
.. _pandas: http://pandas.pydata.org/
.. _MayaVi: http://mayavi.sourceforge.net/
.. _PyTables: http://www.pytables.org/moin


------------------
Motivating Example
------------------

Suppose we wish to check the correlation between the 'wind' and 'rain' columns in a `CSV`_ file, excluding all entries with values larger than 10 as outliers.

.. _`CSV`: http://en.wikipedia.org/wiki/Comma-separated_values

Here is some straightforward code that does this:
::

    r = csv.DictReader('meteo.csv', ('wind', 'rain'))

    sx, sxx, sy, syy, sxy, n = 0, 0, 0, 0, 0, 0
    for row in r:
        x, y = float(row['wind']), float(row['rain'])
        if x < 10 and y < 10:
            sx += x
            sxx += x * x
            sy += y
            sxy += x * y
            syy += y * y
            n += 1
    c = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)

This code is relatively long. The source-reading logic, filtering logic, and calculation logic, are not
cleanly separated; the code cannot flexibly deal with changes to the data format from CSV to something else, for example.

Alternatively, here is some NumPy-based code that does this:
::

    data = numpy.genfromtxt('meteo.csv', names = ('wind', 'rain'), delimiter = ',', skip_header = True)
    wind = [wind for (wind, rain) in data if wind < 10 and rain < 10]
    rain = [rain for (wind, rain) in data if wind < 10 and rain < 10]
    c = numpy.corrcoef(wind, rain)[0, 1]

This code is shorter and more separated, but the ``numpy.genfromtxt`` call loads the entire dataset into memory, which can be very inefficient.

Conversely, using this library, the code becomes (assuming having typed ``from dagpype import *``):
::

    >>> c = stream_vals('meteo.csv', (b'wind', b'rain')) | \
    ...    filt(pre = lambda (wind, rain) : wind < 10 and rain < 10) | \
    ...    corr()

which processes the data efficiently, and, moreover, is short enough to use from the command line for quick data exploration.


--------
Features
--------

The library has the following features:

* Pipelines have low memory footprint, even when processing large datasets.
* Reusable pipe stages can be written easily and combined flexibly. The resulting pipelines can be used from within scripts or Python's interactive interpreter.
* In-Python pipelines are a viable alternative to relatively-specialized utilities such as awk_, sed_, perl_, grep_, etc.
* Stage combination has the expressiveness needed for common data processing tasks:

  * Full combination of pipe elements to DAGs (Directed Acyclic Graphs)
  * On-the-fly creation, by pipe elements, of sub-pipelines, for common SQL-type operations


------------------------------------------------------
Download, Installation, Documentation, And Bugtracking
------------------------------------------------------

* The package is at PyPI_.

    .. _PyPI: http://pypi.python.org/pypi/DAGPype

* The usual setup for Python libraries is used. Type:

    ``$ pip install dagpype``

    or

    ``$ sudo pip install dagpype``

        .. Note::

            To install this package from the source distribution, the system must have a C++ compiler installed. The setup script will invoke this compiler.

            Using Python 2.* on Windows will attempt to invoke Visual Studio 2008. If you are using a Visual Studio 2010 or 2012, download and extract the archive. From within the DAGPype directory, use

            ``> SET VS90COMNTOOLS=%VS100COMNTOOLS%``

            or

            ``> SET VS90COMNTOOLS=%VS110COMNTOOLS%``

            (for Visual Studio 2010 and 2012, respectively), followed by

            ``> python setup.py install``

* The documentation is hosted at `PyPI Docs`_ and can also be found in the 'docs' directory of the distribution.

    .. _`PyPI Docs`: http://packages.python.org/DAGPype/

* Bugtracking is on `Google Code`_.

    .. _`Google Code`: http://code.google.com/p/dagpype/issues/list?can=1&q=


--------------------
A Few Quick Examples
--------------------

(See more online `sed-like`_, `perl-like`_, and `awk-like`_ examples)

.. _`sed-like`: http://packages.python.org/DAGPype/sed.html
.. _`perl-like`: http://packages.python.org/DAGPype/perl.html
.. _`awk-like`: http://packages.python.org/DAGPype/awk.html

.. Note::

    The following examples assume first typing ``from dagpype import *``

#. Find the correlation between the data in two different files, 'wind.txt', and 'rain.txt':
    ::

        >>> stream_vals('wind.txt') + stream_vals('rain.txt') | corr()
        0.74

#. Find the average, standard deviation, min and max, of the contents of 'rain.txt':
    ::

        >>> stream_vals('wind.txt') | mean() + stddev() + min_() + max_()
        (3, 0.4, 0, 9)

#. Truncate outliers from the 'wind' and 'rain' columns of 'meteo.csv':
    ::

        >>> stream_vals('meteo.csv', (b'wind', b'rain')) | \
        ...    filt(lambda (wind, rain) : (min(wind, 10), min(rain, 10))) | \
        ...    to_csv('fixed_data.csv', (b'wind', b'rain'))

#. Create a numpy.array from the values of 'wind.txt':
    ::

        >>> v = stream_vals('wind.txt') | np.to_array()

#. Create a list of the values of 'rain.txt', excluding the first 3 and last 4:
    ::

        >>> v = stream_vals('rain.txt') | skip(3) | skip(-4) | to_list()

#. From 'meteo.csv', summarize consecutive 'wind' values with the same 'day' value by their average and standard deviation; write the result into 'day_wind.csv':
    ::

        >>> stream_vals('meteo.csv', (b'day', b'wind')) | \
        ...     group(
        ...         key = lambda (day, wind) : day,
        ...         key_pipe = lambda day : sink(day) + (select_inds(1) | mean()) + (select_inds(1) | stddev())) | \
        ...     to_csv('day_wind.csv', (b'day', b'mean', b'stddev'))


#. Find the autocorrelation of the values of 'wind.txt', shifted 5 to the past and 5 to the future:
    ::

        >>> c = stream_vals('wind.txt') | skip_n(-5) + skip_n(5) | corr()

#. Find the correlation between smoothed versions of the 'wind' and 'rain' columns of 'meteo.csv':
    ::

        >>> c = stream_vals('meteo.csv', (b'wind', b'rain')) | \
        ...    (select_inds(0) | low_pass_filter(0.5)) + (select_inds(1) | low_pass_filter(0.5)) | \
        ...    corr()

#. Sample approximately 1% of the elements in the 'rain' column of 'meteo.csv', and use them to approximate the median:
    ::

        >>> stream_vals('meteo.csv', 'rain') | prob_rand_sample(0.01) | (to_array() | sink(lambda a : numpy.median(a))

#. Sample approximately 100 of the elements in the 'rain' column of 'meteo.csv' (with replacement), and use them to approximate the median:
    ::

        >>> stream_vals('meteo.csv', 'rain') | size_rand_sample(100) | (to_array() | sink(lambda a : numpy.median(a))


#. Use stages with regular Python conditionals. The following shows how a stage can be selected at runtime; if ``debug`` is used, a trace stage - tracing the elements piped through it - will be used, otherwise, a relay stage - passing elements passed through it - will be used:
    ::

        >>> debug = True
        >>> stream_vals('wind.txt') | (trace() if debug else relay()) | sum_()
        0 : 2.0
        1 : 4.0
        2 : 7.0
        3 : 23.0
        ...
        57 : 7.0
        58 : 23.0
        59 : 0.0
        432.0
        >>> debug = False
        >>> stream_vals('wind.txt') | (trace() if debug else relay()) | sum_()
        432.0

#. Use regular Python functions returning sub-pipes. The following function takes a file name, and returns a pipeline of the exponential average of the absolute values of its values, which is then used for finding a correlation:
    ::

        >>> def abs_exp_ave(f_name):
        ...     return stream_vals(f_name) | abs_() | exp_ave(0.5)

        >>> abs_exp_ave('foo.dat') + abs_exp_ave('bar.dat') | corr()

#. Use pipelines within regular Python list comprehension. The following creates a list of means and standard deviations of the contents of the files in some directory
    ::

        >>> stats = [stream_vals(f) | mean() + stddev() for f in glob.glob('dir/*.txt')]

#. From 'meteo.csv', summarize consecutive 'wind' values with the same 'day' value by their average; plot the cumulative average of these day averages:
    ::

        >>> stream_vals('meteo.csv', (b'day', b'wind')) | \
        ...     group(lambda (day, wind) : day, lambda day : select_inds(1) | mean()) | \
        ...     cum_ave() | (plot.plot() | plot.show())

#. From 'meteo.csv', summarize consecutive 'wind' values with the same 'day' value by their median; plot the cumulative average of these day medians:
    ::

        >>> stream_vals('meteo.csv', (b'day', b'wind')) | \
        ...     group(
        ...         lambda (day, wind) : day,
        ...         lambda day : select_inds(1) | (np.to_array() | sink(lambda a : median(a))) | \
        ...     cum_ave() | (plot.plot() | plot.show())

----------------
Acknowledgements
----------------

This library uses many ideas from David Beazley's generator talk [Beazley08]_ and coroutine talk [Beazley09]_

.. [Beazley08] http://www.dabeaz.com/generators/
.. [Beazley09] http://www.dabeaz.com/coroutines/

Many thanks to Anand Jeyahar, Brad Reisfeld, Tal Kremerman, Eran Segal, and Simon Pantzare for patches.
