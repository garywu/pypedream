from matplotlib.pyplot import *

import _foo_bar_baz
import _line_numbering
import _min
import _csv_corr_prune
import _col_mean
import _binary_corr
import _binary_corr_trunc
import _binary_corr_prune
import _csv_mean


class _Plotter(object):
    def __init__(self, xlabel_, ylabel_):
        clf()
        xlabel(xlabel_)
        ylabel(ylabel_)
        self._x_vals = []
        self._results = dict([])

    def add_results(self, x_val, res):
        print(res)
        self._x_vals.append(x_val)
        for n in list(res.keys()):
            if n not in self._results:
                self._results[n] = []
            self._results[n].append(res[n])

    def to_file(self, f_name):
        maxes = []
        for n in list(self._results.keys()):
            maxes.append((n, max(self._results[n])))
        maxes.sort(key = lambda nm: nm[1])
        for n in [nm[0] for nm in maxes]:
            hold(True)
            plot(self._x_vals, self._results[n], label = n)
        legend([n for (n, m) in maxes], loc = 'upper left')
        savefig(f_name)
        hold(False)


if __name__ == '__main__':
    num_cols = 10
    num_its = 5
    #num_its = 1

    base = 10000
    #base = 10

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['dagpype', 'chunking dagpype', 'numpy']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _csv_mean.run_tests(algs, num_rows, 10, num_its))
    p.to_file('CSVMean.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['dagpype', 'chunking dagpype', 'csv.reader', 'csv.DictReader', 'numpy']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _csv_corr_prune.run_tests(algs, num_rows, 10, num_its))
    p.to_file('CSVCorrPrune.png')
    
    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['dagpype', 'chunking dagpype', 'perl', 'numpy']        
    for num_rows in (base * i / 10 for i in range(1, 5)):
        print('running', num_rows)
        p.add_results(num_rows, _min.run_tests(algs, num_rows, 10, num_its))
    p.to_file('Min.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['dagpype', 'chunking dagpype', 'numpy']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _min.run_tests(algs, num_rows, 10, num_its))
    p.to_file('MinNoPerl.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['chunking dagpype', 'c', 'numpy']        
    for num_elems in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_elems)
        p.add_results(num_elems, _binary_corr_prune.run_tests(algs, num_elems, num_its))
    p.to_file('BinaryCorrPrune.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['chunking dagpype', 'c', 'numpy']        
    for num_elems in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_elems)
        p.add_results(num_elems, _binary_corr_trunc.run_tests(algs, num_elems, num_its))
    p.to_file('BinaryCorrTrunc.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['chunking dagpype', 'c', 'numpy']        
    for num_elems in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_elems)
        p.add_results(num_elems, _binary_corr.run_tests(algs, num_elems, num_its))
    p.to_file('BinaryCorr.png')

    p = _Plotter('# Rows', 'Time (sec)')
    algs = ['dagpype', 'chunking dagpype', 'numpy']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _col_mean.run_tests(algs, num_rows, 10, num_its))
    p.to_file('ColMean.png')

    p = _Plotter('# Lines', 'Time (sec)')
    algs = ['chunking dagpype', 'dagpype', 'awk', 'sed', 'perl', 'standard Python']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _line_numbering.run_tests(algs, num_rows, 60, num_its))
    p.to_file('LineNumbering.png')

    p = _Plotter('# Lines', 'Time (sec)')
    algs = ['chunking dagpype', 'dagpype', 'awk', 'sed', 'perl', 'standard Python']        
    for num_rows in (base * i for i in range(1, 30) if i % 3 == 0):
        print('running', num_rows)
        p.add_results(num_rows, _foo_bar_baz.run_tests(algs, num_rows, 60, num_its))
    p.to_file('FooBarBaz.png')


