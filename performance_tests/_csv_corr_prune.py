import os
import sys
import math
import csv
import time
import numpy

import _src
sys.path.extend(['..', '../..'])
from dagpype import *


_f_name = 'perf.csv'


def _csv():
    r = csv.reader(open(_f_name, 'rb'))

    fields = next(r)
    ind0, ind1 = fields.index('0'), fields.index('1')

    sx, sxx, sy, syy, sxy, n = 0, 0, 0, 0, 0, 0
    try:        
        while True:
            row = next(r)
            x, y = float(row[ind0]), float(row[ind1])
            if x < 0.5 and y < 0.5:
                sx += x
                sxx += x * x
                sy += y
                sxy += x * y
                syy += y * y
                n += 1
    except StopIteration:
        c = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)


def _dict():
    r = csv.DictReader(open(_f_name, 'rb'), ('0', '1'))

    sx, sxx, sy, syy, sxy, n = 0, 0, 0, 0, 0, 0
    for row in r:
        x, y = float(row['0']), float(row['1'])
        if x < 0.5 and y < 0.5:
            sx += x
            sxx += x * x
            sy += y
            sxy += x * y
            syy += y * y
            n += 1
    c = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)


def _csv_pipes():
    c = stream_vals(_f_name, ('0', '1')) | \
        filt(pre = lambda x_y : x_y[0] < 0.5 and x_y[1] < 0.5) | \
        corr()


def _chunking_csv_pipes():
    c = np.chunk_stream_vals(_f_name, cols = ('0', '1')) | \
        filt(pre = lambda (x, y): 
            (x[numpy.logical_and(x[0] < 0.5, y[1] < 0.5)], y[numpy.logical_and(x < 0.5, y < 0.5)])) | \
        np.corr()


def _numpy():
    xy = numpy.genfromtxt(_f_name, usecols = (0, 1), delimiter = ',')    
    xy = xy[numpy.logical_and(xy[:, 0] < 0.5, xy[:, 1] < 0.5)]
    c = numpy.corrcoef((xy[:, 0], xy[:, 1]))


def _run_test(fn, num_rows, num_cols, num_its):
    _src.make_header_csv_file(_f_name, num_rows, num_cols)
    start = time.time()
    for i in range(num_its):
        fn()
    end = time.time()
    diff = (end - start) / num_its
    os.remove(_f_name)
    return diff


def run_tests(names, num_rows, num_cols, num_its):
    fns = dict([
        ('csv.reader', lambda : _csv()),
        ('chunking dagpype', lambda: _chunking_csv_pipes()),
        ('dagpype', lambda: _csv_pipes()),
        ('csv.DictReader', lambda : _dict()),
        ('numpy', lambda: _numpy())])
    t = dict([])        
    for name in names:        
        t[name] = _run_test(fns[name], num_rows, num_cols, num_its)
    return t

