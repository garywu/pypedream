import unittest
import sys
import os
import csv
import numpy
import random
import collections
import re
import itertools
import string
import math
import doctest

sys.path.extend(['..', '../dagpype'])
from dagpype import *
import dagpype
if sys.version_info < (3, 0):        
    from _base2 import RandStateSaverBase as RandStateSaverBase
else:     
    from _base3 import RandStateSaverBase as RandStateSaverBase


def _wind_rain_tags():
    @filters
    def _act(target):
        try:
            while True:
                wind, rain = None, None
                while wind is None or rain is None:
                    event, element = (yield)
                    if element.tag == 'wind':
                        wind = float(element.text)
                        (yield)
                    if element.tag == 'rain':
                        rain = float(element.text)
                        (yield)
                target.send((wind, rain))
        except GeneratorExit:
            target.close()
    return _act


class _TestSeq00Basic(unittest.TestCase):
    def test_00(self):
        with open('data/data.csv', 'rb') as f:
            source(f)

    def test_01(self):
        source([1, 2, 3, 4])
        source(l for l in range(10))
        source((1, 2, 3))

    def test_02(self):
        filt()
        filt(trans = lambda x : 2 * x, pre = None, post = None)
        filt(trans = lambda x : 2 * x, pre = lambda x : x > 3)
        filt(trans = lambda x : 2 * x, post = lambda x : x > 3)

    def test_03(self):
        count()
        sum_()
        sink(3)

    def test_04(self):
        filt() | filt()

    def test_05(self):
        source([1, 2, 3, 4]) | filt() | filt()

    def test_06(self):
        source([1, 2, 3, 4]) | (filt() | filt())

    def test_07(self):
        self.assertEqual(source([1, 2, 3, 4]) | to_list(), [1, 2, 3, 4])

    def test_08(self):
        self.assertEqual(source([1, 2, 3, 4]) | sink(3), 3)
        self.assertEqual(source([]) | sink(3), 3)

    @unittest.expectedFailure
    def test_09(self):
        source([1, 2]) | source([3, 4])

    @unittest.expectedFailure
    def test_10(self):
        filt() | source([1, 2])

    def test_11(self):
        sum_() | sum_()

    def test_12(self):
        res = source([1, 2, 3]) | sink(lambda x : x ** 2)
        self.assertEqual(res, 9)

    def test_13(self):
        with self.assertRaises(NoResultError):
            source([]) | sink(lambda x : x ** 2)

    def test_14(self):
        n, f = source([1, 2, 3, 4]) | count() + nth(0)
        self.assertEqual(n, 4)
        self.assertEqual(f, 1)

    def test_15(self):
        try:            
            os.chdir('../docs')
            
            doctest_f_name = 'build/text/doctest_reference.txt'
            if os.path.exists(doctest_f_name):
                os.remove(doctest_f_name)
            os.system('make text')
            num_fails, num_tests = doctest.testfile(doctest_f_name)
        finally:        
            os.chdir('../tests')
        self.assertGreater(num_tests, 0)            
        self.assertEqual(num_fails, 0)


class _TestSeq01Streams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists('tmp_data.csv'):
            os.remove('tmp_data.csv')

        cls._num_lines = len([l for l in open('data/data.csv', 'rb')])

    @classmethod
    def tearDownClass(cls):
        os.remove('tmp_data.csv')

    def test_00(self):
        with open('data/data.csv', 'rb') as f:
            n = stream_lines(f) | count()
        self.assertEqual(n, _TestSeq01Streams._num_lines)

    def test_02(self):
        if os.path.exists('tmp_data.csv'):
            os.remove('tmp_data.csv')
        n = stream_lines(open('data/data.csv', 'rb')) | to_stream(open('tmp_data.csv', 'wb')) 
        self.assertTrue(os.path.exists('tmp_data.csv'))
        self.assertEqual(n, _TestSeq01Streams._num_lines)
        with open('tmp_data.csv', 'rb') as f:
            l = stream_lines(f) | to_list() 
        self.assertEqual(len(l), _TestSeq01Streams._num_lines)

    def test_03(self):
        if os.path.exists('tmp_data.csv'):
            os.remove('tmp_data.csv')
        n = stream_lines('data/data.csv') | \
            to_stream('tmp_data.csv') 
        self.assertTrue(os.path.exists('tmp_data.csv'))
        self.assertEqual(n, _TestSeq01Streams._num_lines)
        l = stream_lines('tmp_data.csv') | \
            to_list() 
        self.assertEqual(len(l), _TestSeq01Streams._num_lines)

    def test_04(self):
        n = stream_lines('data/data.csv', False) | count()
        self.assertEqual(n, _TestSeq01Streams._num_lines)

    def test_05(self):
        for i in range(15):
            buf_len = max(10, int(random.expovariate(1. / 60)))   
            stream_len = max(10, int(random.expovariate(1. / 1000)))  
            rand_line = lambda len_: b''.join(
                random.choice(string.ascii_letters).encode('utf-8') for _ in range(len_))
            data = [rand_line(1 + min(int(random.expovariate(1. / 20)), buf_len - 2)) for _ in range(stream_len)]
            open('long_tmp.txt', 'wb').write(b'\n'.join(data))
            source(data) | to_stream('long_tmp1.txt', buf_size = buf_len)
            open('buf_size.txt', 'wb').write(bytes(buf_len))
            data1 = stream_lines('long_tmp1.txt') | to_list()
            stream_lines('long_tmp1.txt') | to_stream('long_tmp2.txt', buf_size = buf_len)
            data2 = stream_lines('long_tmp2.txt') | to_list()
            self.assertEqual(data, data1)
            self.assertEqual(data, data2)


class _TestSeq02CSV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists('tmp_data.csv'):
            os.remove('tmp_data.csv')

        cls._num_lines = len([l for l in open('data/data.csv', 'rb')])

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove('tmp_data.csv')
            os.remove('rain.csv')
            os.remove('wind.csv')
        except WindowsError:
            sys.stderr.write('Failed to close!')

    def test_01(self):
        stream_vals('data/data.csv', (b'day', b'wind', b'rain')) | \
            to_stream('tmp_data.csv', (b'day', b'wind', b'rain'))
        l = stream_vals('tmp_data.csv', (b'day', b'wind', b'rain')) | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], (1, 2, 4))
        self.assertEqual(l[-1], (29, 0, 1))

    def test_02(self):
        stream_vals(open('data/data.csv', 'rb'), b'day') | \
            to_stream(open('tmp_data.csv', 'wb'), b'day')
        l = stream_vals(open('tmp_data.csv', 'rb'), b'day') | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], 1.0)
        self.assertEqual(l[-1], 29)

    def test_03(self):
        stream_vals(open('data/data.csv', 'rb'), b'day', bytes) | \
            to_stream(open('tmp_data.csv', 'wb'), b'day')
        l = stream_vals(open('tmp_data.csv', 'rb'), b'day') | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], 1.0)
        self.assertEqual(l[-1], 29)

    def test_04(self):
        stream_vals(open('data/neat_data.csv', 'rb'), (0, 1, 3)) | \
            to_stream(open('tmp_data.csv', 'wb'))
        l = stream_vals(open('tmp_data.csv', 'rb'), None) | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], (1, 2, 4))
        self.assertEqual(l[-1], (29, 0, 1))

    def test_05(self):
        stream_vals(open('data/neat_data.csv', 'rb'), 0, bytes) | \
            to_stream(open('tmp_data.csv', 'wb'))
        l = stream_vals(open('tmp_data.csv', 'rb'), None) | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], 1)
        self.assertEqual(l[-1], 29)

    def test_06(self):
        stream_vals(open('data/data.csv', 'rb'), (b'wind', b'rain')) | \
            (select_inds(0) | to_stream(open('wind.csv', 'wb'))) + \
            (select_inds(1) | to_stream(open('rain.csv', 'wb')))

    def test_07(self):
        stream_vals('data/data.csv', b'day', bytes) | \
            to_stream('tmp_data.csv', b'day')
        l = stream_vals('tmp_data.csv', b'day') | \
            to_list()
        self.assertEqual(len(l), _TestSeq02CSV._num_lines - 1)
        self.assertEqual(l[0], 1.0)
        self.assertEqual(l[-1], 29)

    def test_08(self):
        try:
            stream_vals('data/data.csv', b'fooby', bytes) | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)

    def test_09(self):
        try:
            stream_vals('data/data.csv', b'fooby', bytes) | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)

    def test_10(self):
        try:
            stream_vals('data/data.csv', ('wind', b'fooby'), bytes) | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)

    def test_11(self):
        n = stream_vals('data/data.csv', types_ = str) | count()
        self.assertEqual(n, _TestSeq02CSV._num_lines)        

    def test_12(self):
        n = stream_vals('data/data.csv', types_ = (str, bytes, bytes, bytes)) | count()
        self.assertEqual(n, _TestSeq02CSV._num_lines)        

    def test_13(self):
        n, f = stream_vals('data/data.csv', (b'wind', b'rain', b'day', b'rain')) | \
            count() + nth(0)
        self.assertEqual(n, _TestSeq02CSV._num_lines - 1)        
        self.assertEqual(f, (2, 4, 1, 4))

    def test_14(self):
        n = stream_vals('data/data.csv', cols = (0, 1, 2, 3), types_ = (str, bytes, bytes, bytes)) | count()
        self.assertEqual(n, _TestSeq02CSV._num_lines)        

    def test_15(self):
        n = stream_vals('data/neat_data.csv', cols = (0, 1, 2, 3)) | count()
        self.assertEqual(n, _TestSeq02CSV._num_lines - 1)        

    def test_16(self):
        n = stream_vals('data/tmp_act.tsv', delimit = b'\t') | count()
        self.assertEqual(n, 34)

    def test_17(self):
        v = stream_vals(open('data/data.csv', 'rb'), (b'day', b'wind'), (int, float)) | \
            trace() | \
            nth(1)
        self.assertTrue(isinstance(v[0], int))
        self.assertTrue(isinstance(v[1], float))
        self.assertEqual(v, (1, 4))

    def test_18(self):
        n = stream_vals((b' day |wind ',), delimit = b'|', skip_init_space = False, types_ = (bytes, bytes)) | \
            nth(0)
        self.assertEqual(n, (b' day ', b'wind '))
        n = stream_vals((b' day |wind ',), delimit = b'|', skip_init_space = True, types_ = (bytes, bytes)) | \
            nth(0)
        self.assertEqual(n, (b'day ', b'wind '))

    def test_19(self):
        n = stream_vals((b' day |wind ',), delimit = b'|', skip_init_space = False, types_ = (bytes)) | \
            nth(0)

    def test_20(self):
        try:
            stream_vals('data/data.csv', ('wind', b'fooby'), bytes, delimit = 'foo') | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)

    def test_21(self):
        try:
            stream_vals('data/data.csv', ('wind', b'fooby'), bytes, comment = 'foo') | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)

    def test_22(self):
        try:
            stream_vals('data/data.csv', ('wind', 1), bytes, comment = 'foo') | \
                to_stream('tmp_data.csv', b'fooby')
        except ValueError as e:
            return
        self.assertTrue(False)
                

    def test_23(self):
        l = stream_vals((b'1|2', b'0|4'), delimit = b'|', types_ = (bool, bool)) | nth(-1)
        self.assertEqual(l, (True, True))
        l = stream_vals((b'1|2', b'0'), delimit = b'|', types_ = (bool, bool)) | nth(-1)
        self.assertEqual(l, (True, None))
        l = stream_vals((b'1|2', b'0|4'), delimit = b'|', types_ = (bool)) | nth(-1)
        self.assertEqual(l, True)

    @unittest.expectedFailure
    def test_24(self):
        stream_vals('data/bad_data.csv', b'day', int) | sum_()
    
    @unittest.expectedFailure
    def test_25(self):
        stream_vals('data/bad_data.csv', b'hail', int) | sum_()

    def test_26(self):
        l = stream_vals('data/quirky_data.csv', b'day', int) | to_list()
        self.assertEqual(l, [1, 1, None, 4])
        l = stream_vals('data/quirky_data.csv', b'day') | to_list()
        self.assertEqual(l, [1.0, 1.0, None, 4.0])
        l = stream_vals('data/quirky_data.csv', b'day', float) | to_list()
        self.assertEqual(l, [1.0, 1.0, None, 4.0])

    def test_27(self):
        l = stream_vals('data/neat_quirky_data.csv') | to_list()
        self.assertEqual(l, [(1.0, None, None, 4.0), (1.0, 4.0, None), (None, None, None, None), (4.0, 3.0, 2.0, 1.0)])
        l = stream_vals('data/neat_quirky_data.csv', types_ = (float, int, float, int)) | to_list()
        self.assertEqual(l, [(1.0, None, None, 4), (1.0, 4, None, None), (None, None, None, None), (4.0, 3, 2.0, 1)])
        l = stream_vals('data/neat_quirky_data.csv', types_ = (float, int, float, int, bytes, bytes)) | to_list()
        self.assertEqual(
            l, 
            [(1.0, None, None, 4, None, None), (1.0, 4, None, None, None, None), (None, None, None, None, None, None), (4.0, 3, 2.0, 1, None, None)])
        l = stream_vals('data/neat_quirky_data.csv', types_ = (bytes, bytes, float, int, float, int)) | to_list()
        self.assertEqual(
            l, 
            [(b'1', None, None, 4, None, None), (b'1', b'4', None, None, None, None), (None, None, None, None, None, None), (b'4', b'3', 2.0, 1, None, None)])
   
    def test_28(self):
        with open('tmp.tsv', 'w') as f:
            for i in range(10):
                f.write('\t'.join([str(random.random()) for i in range(100)]) + '\n')
        c = stream_vals('tmp.tsv', delimit = b'\t') | count()
        self.assertEqual(c, 10)
        
    def test_29(self):
        l = stream_vals('data/ieee_bad_data.csv', cols = b'day') | to_list()
        self.assertTrue(math.isnan(l[0]))
        self.assertEqual(l[1: ], [1., 2.])        
        l = stream_vals('data/ieee_bad_data.csv', cols = b'wind') | to_list()
        self.assertEqual(l, [2., 4., 7.])        
        l = stream_vals('data/ieee_bad_data.csv', cols = b'hail') | to_list()
        self.assertTrue(math.isinf(-l[1]))
        l = stream_vals('data/ieee_bad_data.csv', cols = b'rain') | to_list()
        self.assertTrue(math.isinf(-l[0]))
        self.assertTrue(math.isnan(l[2]))


class _TestSeq03Control(unittest.TestCase):
    def test_01(self):
        self.assertEqual(source([1, 2, 3, 4]) | nth(1), 2)
        self.assertEqual(source([1, 2, 3, 4]) | nth(-1), 4)
        self.assertEqual(source([1, 2, 3, 4]) | nth(2), 3)
        self.assertEqual(source([1, 2, 3, 4]) | nth(-2), 3)
        self.assertEqual(source([1, 2, 3, 4]) | nth(-3), 2)
        self.assertEqual(source([1, 2, 3, 4]) | nth(0), 1)

    def test_02(self):
        with self.assertRaises(NoResultError):
            source([1, 2, 3, 4]) | nth(5)

    @unittest.expectedFailure
    def test_03(self):
        source([1, 2, 3, 'd']) | sum_()

    def test_04(self):
        source([1, 2, 3, 4]) | sum_()

    def test_05(self):
        self.assertEqual(source([('1', '2', '3')]) | cast((float, int, int)) | to_list(), [(1, 2, 3)])

    def test_06(self):
        self.assertEqual(source([(1, 2, 3)]) | select_inds(0) | nth(0), 1)
        self.assertEqual(source([(1, 2, 3)]) | select_inds(1) | nth(0), 2)
        self.assertEqual(source([(1, 2, 3)]) | select_inds((0, 1)) | nth(0), (1, 2))
        self.assertEqual(source([(1, 2, 3)]) | select_inds(()) | nth(0), ())

    def test_07(self):
        with self.assertRaises(IndexError):
            source([(1, 2, 3)]) | select_inds(4) | nth(0)

    def test_08(self):
        e =  stream_vals(open('data/data.csv', 'rb'), b'hail') | \
            cast(int) | \
            nth(2)        
        self.assertEqual(e, 29)

    def test_09(self):
        self.assertEqual(source([1, 2, 3, 4]) | skip(2) | to_list(), [3, 4])
        self.assertEqual(source([1, 2, 3, 4, 5, 6]) | skip(-2) | to_list(), [1, 2, 3, 4])
        self.assertEqual(source([1, 2, 3, 4]) | skip(1) | to_list(), [2, 3, 4])
        self.assertEqual(source([1, 2, 3, 4]) | skip(0) | to_list(), [1, 2, 3, 4])
    
    def test_10(self):
        n = 99999
        p = 0.7
        r = (source(range(n)) | prob_rand_sample(0.7) | count()) / float(n)
        self.assertAlmostEqual(r, 0.7, delta = 0.1)        

    def test_11(self):
        d = source(((1, 'a'), (2, 'b'), (3, 'b'), (4, 'j'))) | to_dict()
        self.assertEqual(len(d), 4)
        self.assertEqual(d[2], 'b')

    def test_12(self):
        self.assertEqual(source([1]) | append(2) | to_list(), [1, 2])
        self.assertEqual(source([1]) | prepend(2) | to_list(), [2, 1])

    def test_13(self):
        f = source([(1, 2, 3, 4), (1, 2, 3, 4)]) | select_inds((0, 3, 2, 1, 0, 1, 2, 3)) | to_list()
        self.assertEqual(f, [(1, 4, 3, 2, 1, 2, 3, 4), (1, 4, 3, 2, 1, 2, 3, 4)])

    def test_13(self):
        f = source([(1, 2, 3, 4), (2, 3, 4, 6)]) | select_inds((0, 3, 2, 1, 0, 1, 2, 3)) | to_list()
        self.assertEqual(f, [(1, 4, 3, 2, 1, 2, 3, 4), (2, 6, 4, 3, 2, 3, 4, 6)])

    def test_14(self):
        f = source([(1, 2, 3, 4)]) | select_inds((0, 0, 0)) | nth(0)
        self.assertEqual(f, (1, 1, 1))

    def test_15(self):
        f = source([(1, 2)]) | cast((str, str)) | nth(0)
        self.assertEqual(f, ('1', '2'))

    def test_16(self):
        f = source([(1, 2, 3)]) | cast((str, str, float)) | nth(0)
        self.assertEqual(f, ('1', '2', 3))

    def test_17(self):
        f = source([(1, 2, 3, 5), (1, 2, 3, 6)]) | cast((str, str, float, int)) | to_list()
        self.assertEqual(f, [('1', '2', 3, 5), ('1', '2', 3, 6)])

    def test_18(self):
        self.assertEqual(source([b'aa', b'aab', b'b']) | grep(b'b') | to_list(), [b'aab', b'b'])
        self.assertEqual(source([b'aa', b'aab', b'b']) | grep(re.compile(b'(a+)b')) | to_list(), [b'aab'])

    def test_19(self):
        n = 1000
        tot = [0, 0]
        for _ in range(n):
            l = source(range(100)) | size_rand_sample(2)
            self.assertEqual(len(l), 2)
            tot[0] += l[0]
            tot[1] += l[1]
        for j in range(2):
            tot[j] /= float(n)
            self.assertAlmostEqual(tot[j] / (99. / 2), 1, 1)
            
    def test_20(self):
        l = source([1, 2, 3, 4, 3, 2, 1]) | from_(2) | to_list()
        self.assertEqual(l, [2, 3, 4, 3, 2, 1])

        l = source([1, 2, 3, 4, 3, 2, 1]) | from_(2, False) | to_list()
        self.assertEqual(l, [3, 4, 3, 2, 1])

        l = source([1, 2, 3, 4, 3, 2, 1]) | from_(lambda d: d % 3 == 0) | to_list()
        self.assertEqual(l, [3, 4, 3, 2, 1])

    def test_21(self):
        l = source([1, 2, 3, 4, 3, 2, 1]) | to(2) | to_list()
        self.assertEqual(l, [1, 2])        
       
        l = source([1, 2, 3, 4, 3, 2, 1]) | to(2, False) | to_list()
        self.assertEqual(l, [1])        

        l = source([1, 2, 3, 4, 3, 2, 1]) | to(lambda d: d % 3 == 0) | to_list()
        self.assertEqual(l, [1, 2, 3])

    def test_22(self):
        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3) | to_list()
        self.assertEqual(l, [2, 3, 2, 1, 3, 2])

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False) | to_list()
        self.assertEqual(l, [3, 1, 3])

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, to_inclusive = False) | to_list()
        self.assertEqual(l, [2, 2, 1, 2])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | \
            from_to(2, 3, from_inclusive = False, to_inclusive = False) | to_list()
        self.assertEqual(l, [1])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, strict = True) | to_list()
        self.assertEqual(l, [2, 3, 2, 1, 3])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False, strict = True) | to_list()
        self.assertEqual(l, [3, 1, 3])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, to_inclusive = False, strict = True) | to_list()
        self.assertEqual(l, [2, 2, 1])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | \
            from_to(2, 3, from_inclusive = False, to_inclusive = False, strict = True) | to_list()
        self.assertEqual(l, [1])
            
        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(lambda d: d % 2 == 0, lambda d: d % 4 == 0) | to_list()
        self.assertEqual(l, [2, 3, 4, 2, 1, 3, 7, 2])        

        l = source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(lambda d: d % 2 == 0, lambda d: d % 4 == 0, strict = True) | to_list()
        self.assertEqual(l, [2, 3, 4])        
        
    def test_23(self):
        l = source(range(100)) | slice_(10) | to_list()
        self.assertEqual(l, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])        

        l = source(range(100)) | slice_(0, 100, 10) | to_list()
        self.assertEqual(l, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90])        

        l = source(range(100)) | slice_(0, 10) | to_list()
        self.assertEqual(l, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])            

        l = source(range(20)) | slice_(3, None, 7) | to_list()
        self.assertEqual(l, [3, 10, 17])            

        l = source(range(20)) | slice_(None, None, 7) | to_list()
        self.assertEqual(l, [0, 7, 14])            

        l = source(range(5)) | slice_(3) | to_list()
        self.assertEqual(l, [0, 1, 2])            

    @unittest.expectedFailure
    def test_24(self):
        source(range(5)) | slice_() | to_list()

    def test_25(self):
        l = source(range(10)) | tail(4) | to_list()
        self.assertEqual(l, [6, 7, 8, 9])

        l = source(range(10)) | tail(0) | to_list()
        self.assertEqual(l, [])

        l = source(range(2)) | tail(4) | to_list()
        self.assertEqual(l, [0, 1])

    def test_26(self):
        self.assertEqual(source(['1', '2', '3', '4']) | sum_(), '1234')

    def test_27(self):
        self.assertEqual(source(['a', 'b', 'c', 'd']) | enumerate_() | to_list(), [(0, 'a'), (1, 'b'), (2, 'c'), (3, 'd')])
        self.assertEqual(source(['a', 'b', 'c', 'd']) | enumerate_(1) | to_list(), [(1, 'a'), (2, 'b'), (3, 'c'), (4, 'd')])
        self.assertEqual(source(['a', 'b', 'c', 'd']) | enumerate_(-1) | to_list(), [(-1, 'a'), (0, 'b'), (1, 'c'), (2, 'd')])


class _TestSeq04Xml(unittest.TestCase):
    def test_01(self):
        c = parse_xml(open('data/data.xml', 'rb')) | \
            _wind_rain_tags() | \
            filt(pre = lambda wind_rain3 : wind_rain3[0] < 10 and wind_rain3[1] < 10) | \
            corr()
        self.assertAlmostEqual(c, 0.402186690128789)

    def test_02(self):
        c = parse_xml('data/data.xml') | \
            _wind_rain_tags() | \
            filt(pre = lambda wind_rain4 : wind_rain4[0] < 10 and wind_rain4[1] < 10) | \
            corr()
        self.assertAlmostEqual(c, 0.402186690128789)


class _Test05Numeric(unittest.TestCase):
    def test_00(self):
        n = source([1, 2, 3, 4]) | count()
        self.assertEqual(n, 4)

    def test_01(self):
        n = os_walk('data') | filename_filt('*/data*.csv') | count()
        self.assertEqual(n, 2)

    def test_02(self):
        c = stream_vals(open('data/data.csv', 'rb'), (b'wind', b'rain')) | \
            filt(pre = lambda wind_rain5 : wind_rain5[0] < 10 and wind_rain5[1] < 10) | \
            corr()
        self.assertAlmostEqual(c, 0.402186690128789)

    def test_03(self):
        c =  stream_vals(open('data/data.csv', 'rb'), b'wind') + \
                stream_vals(open('data/data.csv', 'rb'), b'rain') | \
            corr()
        self.assertNotEqual(c, 1)

    def test_04(self):
        self.assertEqual(source([2, 4, 4, 4, 5, 5, 7, 9]) | stddev(0), 2)
        self.assertAlmostEqual(source([2, 4, 4, 4, 5, 5, 7, 9]) | stddev(), 2.138, delta = 0.001)

    def test_05(self):
        self.assertEqual(source([1, 2, 3]) | min_(), 1)
        self.assertEqual(source([1, 2, 3]) | max_(), 3)

    def test_06(self):
        self.assertEqual(source([1, 2, 3]) | (sum_() | sum_()), 6)
        self.assertEqual(source([1, 2, 3]) | (sum_() | count()), 1)        

    def test_07(self):
        self.assertEqual(source([1, 2, 3, 4]) + source([1, 2, 3, 4]) | corr(), 1)
        c = source([(60, 3.1), (61, 3.6), (62, 3.8), (63, 4), (65, 4.1)]) | corr()
        self.assertAlmostEqual(c, 0.9119, delta = 0.0001)

    def test_08(self):
        c = stream_vals(open('data/data.csv', 'rb'), b'rain') | \
            relay() + relay() | \
            corr()
        self.assertAlmostEqual(c, 1)
        c = stream_vals(open('data/data.csv', 'rb'), b'rain') | \
            relay() + skip(2) | \
            corr()
        self.assertLess(c, 1)


class _Test06Fan(unittest.TestCase):
    def test_00(self):
        n0, n1 = source([1, 2, 3, 4]) | count() + count()
        self.assertEqual(n0, 4)
        self.assertEqual(n1, 4)

    def test_01(self):
        n0 = source([1, 2, 3, 4]) | \
            (filt(pre = lambda x : x % 2 == 0) | count())
        self.assertEqual(n0, 2)
        n1 = source([1, 2, 3, 4]) | \
            (filt(pre = lambda x : x % 2 == 1) | count())
        self.assertEqual(n1, 2)

        n0, n1 = source([1, 2, 3, 4]) | \
            (filt(pre = lambda x : x % 2 == 0) | count()) + (filt(pre = lambda x : x % 2 == 1) | count())
        self.assertEqual(n0, 2)
        self.assertEqual(n1, 2)

    def test_02(self):
        c = source([1., 2., 3., 4.]) + source([2., 3., 4., 5.]) | corr()
        self.assertAlmostEqual(c, 1)

    def test_03(self):
        l = source(open('data/data.csv', 'rb')) + source(open('data/data.csv', 'rb')) | to_list()
        self.assertEqual(l[0], l[0])


class _Test07Subgroup(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if os.path.exists('day_wind.csv'):
            os.remove('day_wind.csv')

    def test_00(self):
        l =  stream_vals(open('data/data.csv', 'rb'), (b'day', b'wind')) | \
            consec_group(
                lambda day_wind : day_wind[0],
                lambda day : select_inds(1) | mean()) | \
            to_list()    
        self.assertEqual(l[0 : 3], [3.0, 15.0, 0.0])        

    def test_01(self):
        l =  stream_vals(open('data/data.csv', 'rb'), (b'day', b'wind'), (int, float)) | \
            consec_group(
                lambda day_wind : day_wind[0],
                lambda day : sink(day) + (select_inds(1) | mean())) | \
            to_list()    
        self.assertEqual(l[0 : 3], [(1, 3.0), (2, 15.0), (3, 0.0)])        

    def test_02(self):
        l = os_walk('data') | \
            filename_filt(os.path.join('*', 'data*.csv')) | \
            chain(lambda f_name : \
                stream_vals(open(f_name, 'rb'), (b'wind', b'rain')) | \
                filt(lambda wind_rain : (f_name, wind_rain[0], wind_rain[1]))) | \
            prepend(('f_name', 'wind', 'rain')) | \
            to_list() 
        self.assertTrue(l[0] == ('f_name', 'wind', 'rain'))
        self.assertTrue((os.path.join('data', 'data1.csv'), 0, 0) in l)
        self.assertTrue((os.path.join('data', 'data.csv'), 2, 4) in l)
        self.assertTrue((os.path.join('data', 'data.csv'), 4, 6) in l)

    def test_03(self):
        stream_vals(open('data/data.csv', 'rb'), (b'day', b'wind'), (int, float, float)) | \
            consec_group(
                key = lambda day_wind : day_wind[0],
                key_pipe = \
                    lambda day : sink(day) + (select_inds(1) | mean()) + (select_inds(1) | stddev())) | \
            to_stream(open('day_wind.csv', 'wb'), (b'day', b'ave', b'stddev'))

    def test_04(self):
        d = stream_vals('data/employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
            dict_join(
                stream_vals('data/dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
                lambda name_id_dept : name_id_dept[2],
                lambda dept, manager : filt(lambda name_id_dept : (name_id_dept[0], dept)),
                None, 
                None) | \
            to_dict()
        self.assertEqual(d[b'Harriet'], b'Sales')

    def test_05(self):
        d = stream_vals('data/employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
            dict_join(
                stream_vals('data/dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
                lambda name_id_dept : name_id_dept[2],
                lambda dept, manager : filt(lambda name_id_dept : (name_id_dept[0], manager)),
                None, 
                None) | \
            to_dict()
        self.assertEqual(d[b'Harriet'], b'Harriet')

    def test_06(self):
        d = stream_vals('data/employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
            dict_join(
                stream_vals('data/dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
                lambda name_id_dept : name_id_dept[2],
                lambda dept, manager : sink(manager) + count(),
                None, 
                None) | \
            to_dict()
        self.assertEqual(d[b'Harriet'], 2)

    def test_07(self):
        d = stream_vals('data/employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
            dict_join(
                stream_vals('data/dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
                lambda name_id_dept : name_id_dept[2],
                lambda dept, manager : filt(lambda name_id_dept : (name_id_dept[0], manager)),
                filt(lambda name_id_dept : (name_id_dept[0], None)), 
                None) | \
            to_dict()
        self.assertEqual(d[b'Harriet'], b'Harriet')
        self.assertEqual(d[b'Nelson'], None)

    def test_08(self):
        d = stream_vals('data/employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
            dict_join(
                stream_vals('data/dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
                lambda name_id_dept : name_id_dept[2],
                lambda dept, manager : sink(manager) + count(),
                None, 
                filt(lambda dept_manager : (dept_manager[1], 0))) | \
            to_dict()
        self.assertEqual(d[b'Harriet'], 2)
        self.assertEqual(d[b'Charles'], 0)

    def test_09(self):
        l = source([(1, 1), (1, 455), (13, 0)]) | \
            consec_group(
                lambda p : p[0], 
                lambda k : sink(k) + count()) | \
            to_list()
        self.assertEqual(l, [(1, 2), (13, 1)])

    def test_10(self):
        l = source([(1, 1), (13, 0), (1, 455)]) | \
            group(
                lambda p : p[0], 
                lambda k : sink(k) + count()) | \
            to_list()
        self.assertEqual(l, [(1, 2), (13, 1)])


class _Test09FreezeThaw(unittest.TestCase):
    def test_00(self):
        s = freeze(sum_())
        for i in range(4):
            source([1, 2, 3, 4]) | s
        self.assertEqual(thaw(s), 40)

    def test_01(self):
        s = freeze(sum_())
        for i in range(4):
            source([1, 2, 3, 4]) | filt(lambda x : 2 * x) | s
        self.assertEqual(thaw(s), 80)

    def test_02(self):
        s = freeze(filt(lambda x : 2 * x) | sum_())
        for i in range(4):
            source([1, 2, 3, 4]) | s
        self.assertEqual(thaw(s), 80)

    def test_03(self):
        s = freeze(count())
        for i in range(4):
            source([1, 2, 3, 4]) + source([1, 2, 3, 4]) | s
        self.assertEqual(thaw(s), 16)

    def test_04(self):
        s = freeze(filt(lambda xy : xy[0] % 2 == 0) | count())
        for i in range(4):
            source([1, 2, 3, 4]) + source([1, 2, 3, 4]) | s
        self.assertEqual(thaw(s), 16)


# Tmp Ami - complete
class _Test10Filenames(unittest.TestCase):
    def test_00(self):
        l = os_walk('data') | count()
                    
        #filename_filt('*/data*.csv') | \
        

class _Test11Numpy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._num_vals = 100000
    
        cls._f_name = 'tmp_data.dat'

        if os.path.exists(cls._f_name):
            os.remove(cls._f_name)

        a = numpy.arange(cls._num_vals, dtype = numpy.float)

        with open(cls._f_name, 'wb') as f:
            f.write(a.tostring())        

    @classmethod
    def tearDownClass(cls):
        os.remove(cls._f_name)

    def test_00(self):
        a = source([1, 2, 3, 4]) | np.to_array()
        self.assertTrue(numpy.allclose(a, numpy.array([1, 2, 3, 4])))

    def test_01(self):
        a = source([(1, 2), (3, 4)]) | np.to_array()
        self.assertTrue(numpy.allclose(a, numpy.array([(1, 2), (3, 4)])))

    def test_02(self):
        a = source([(1, 2), (3, 4)]) | np.to_array(dtype = bool)
        self.assertTrue(numpy.allclose(a, numpy.array([(1, 2), (3, 4)], dtype = bool)))

    def test_03(self):
        a = source([(1, 2), (3, 4)]) | np.to_array(dtype = numpy.float64)
        self.assertTrue(numpy.allclose(a, numpy.array([(1, 2), (3, 4)], dtype = numpy.float64)))

    def test_04(self):
        m = source([1, 2, 3, 4, 5]) | (np.to_array() | sink(lambda a : numpy.median(a)))
        self.assertEqual(m, 3)
    def test_05(self):
        m = source([1, 2, 3, 4, 5]) | \
            (np.to_array() | sink(lambda a : numpy.median(a)) + sink(lambda a : numpy.median(a)))
        self.assertEqual(m, (3, 3))

    def test_06(self):
        with self.assertRaises(TypeError):
            source([1, 2, 3, 4, 5]) | np.to_array() | sink(lambda a : numpy.median(a))

    def test_07(self):
        s = np.chunk_stream_bytes(_Test11Numpy._f_name) | filt(lambda a : numpy.sum(a)) | sum_()
        self.assertEqual(s, _Test11Numpy._num_vals * (_Test11Numpy._num_vals - 1) / 2.0)

    def test_08(self):
        s = source(range(_Test11Numpy._num_vals)) | np.chunk() | filt(lambda a : numpy.sum(a)) | sum_()
        self.assertEqual(s, _Test11Numpy._num_vals * (_Test11Numpy._num_vals - 1) / 2.0)

    def test_09(self):
        n = source(((d, d) for d in range(_Test11Numpy._num_vals))) | \
            np.chunk() | filt(lambda a : len(a)) | sum_()
        self.assertEqual(n, _Test11Numpy._num_vals)

    def test_10(self):
        last, n = source(range(_Test11Numpy._num_vals)) | np.chunk() | np.unchunk() | \
            nth(-1) + count()
        self.assertEqual(n, _Test11Numpy._num_vals)

    def test_11(self):
        last, n = source(((d, d) for d in range(_Test11Numpy._num_vals))) | \
            np.chunk() | np.unchunk() | nth(-1) + count()
        self.assertEqual(n, _Test11Numpy._num_vals)

    def test_12(self):
        s = source([1, 2, 3, 4]) | np.chunk() | np.sum_()
        self.assertEqual(s, 10)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.sum_()
        self.assertEqual(s, 10)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.sum_(axis = 0)
        self.assertTrue(numpy.allclose(s, [4, 6]))

    def test_13(self):
        s = source([1, 2, 3, 4]) | np.chunk() | np.min_()
        self.assertEqual(s, 1)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.min_()
        self.assertEqual(s, 1)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.min_(axis = 0)
        self.assertTrue(numpy.allclose(s, [1, 2]))

    def test_14(self):
        s = source([1, 2, 3, 4]) | np.chunk() | np.max_()
        self.assertEqual(s, 4)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.max_()
        self.assertEqual(s, 4)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.max_(axis = 0)
        self.assertTrue(numpy.allclose(s, [3, 4]))

    def test_15(self):
        s = source([1, 2, 3, 4]) | np.chunk() | np.count()
        self.assertEqual(s, 4)
        s = source([(1, 2), (3, 4)]) | np.chunk() | np.count()
        self.assertEqual(s, 2)

    def test_16(self):
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(2) | np.unchunk() | to_list()
        self.assertEqual(l, [3, 4, 5, 6])
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(5) | np.unchunk() | to_list()
        self.assertEqual(l, [6])
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(3) | np.unchunk() | to_list()
        self.assertEqual(l, [4, 5, 6])
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(-2) | np.unchunk() | to_list()
        self.assertEqual(l, [1, 2, 3, 4])
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(-3) | np.unchunk() | to_list()
        self.assertEqual(l, [1, 2, 3])
        l = source([1, 2, 3, 4, 5, 6]) | np.chunk(3) | np.skip(-5) | np.unchunk() | to_list()
        self.assertEqual(l, [1])

    def test_17(self):
        tmp_f_name = 'tmp_' + _Test11Numpy._f_name
        s = np.chunk_stream_bytes(_Test11Numpy._f_name) | \
            (np.unchunk() | to_list()) + np.chunks_to_stream_bytes(tmp_f_name)             
        s1 = np.chunk_stream_bytes(tmp_f_name) | np.unchunk() | to_list()
        self.assertEqual(s[0], s1)
        os.remove(tmp_f_name)

    def test_18(self):
        l = np.chunk_stream_bytes(_Test11Numpy._f_name, num_cols = 2) | np.unchunk() | to_list()
        self.assertEqual(l[0], (0, 1))

    def test_19(self):
        c = source(((random.random(), random.random()) for i in range(10000))) | \
            np.chunk() | np.corr()
        self.assertAlmostEqual(c, 0, delta = 0.1)

    def test_20(self):
        c = (source((random.random() for i in range(10000))) | np.chunk()) + \
                (source((random.random() for i in range(10000))) | np.chunk()) | \
            np.corr()
        self.assertAlmostEqual(c, 0, delta = 0.1)

    def test_21(self):
        m = source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.vstack_chunks()
        self.assertTrue(numpy.allclose(m, numpy.array([[1, 2, 3, 4], [5, 6, 7, 8]])))

    def test_22(self):
        s = source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.chunks_sum()
        self.assertTrue(numpy.allclose(s, numpy.array([6, 8, 10, 12])))

    def test_23(self):
        a = source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.chunks_mean()
        self.assertTrue(numpy.allclose(a, numpy.array([3, 4, 5, 6])))

    def test_24(self):
        s = source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.chunks_stddev()
        self.assertTrue(numpy.allclose(s, s[0]))

    def test_25(self):
        s, m, st, (cs, cm, cst) = source(random.random() for i in range(10000)) | \
            sum_() + mean() + stddev() + \
                (filt(lambda x : numpy.array([x, x])) | \
                    np.chunks_sum() + np.chunks_mean() + np.chunks_stddev())
        self.assertEqual(s, cs[0])
        self.assertEqual(s, cs[1])
        self.assertEqual(m, cm[0])
        self.assertEqual(m, cm[1])
        self.assertEqual(st, cst[0])
        self.assertEqual(st, cst[1])

    def test_26(self):
        self.assertEqual(source([1, 2, 3, 4]) | np.chunk() | np.mean(), 2.5)
        self.assertEqual(
            source([(1, 2), (3, 4)]) | np.chunk() | np.mean(),
            2.5)
        self.assertTrue(numpy.allclose(
            source([(1, 2), (3, 4)]) | np.chunk() | np.mean(axis = 0),
            [2, 3]))

    def test_27(self):
        a, b = source((random.random() for _ in range(99999))) | mean() + (np.chunk() | np.mean())
        self.assertAlmostEqual(a, b)

    def test_28(self):
        a, b = source((random.random() for _ in range(99999))) | \
            (np.chunk() | np.cum_ave() | np.concatenate_chunks()) + (cum_ave() | np.to_array())
        self.assertTrue(numpy.allclose(a, b))
        
    def test_29(self):
        a, b = source((random.random() for _ in range(99999))) | \
            (np.chunk() | np.exp_ave(0.7) | np.concatenate_chunks()) + (exp_ave(0.7) | np.to_array())
        self.assertTrue(numpy.allclose(a, b))

    def test_30(self):
        np.chunk_stream_vals('data/data.csv', (b'day', b'wind'), (float, float), (b'moshe', 0)) | np.corr()

    def test_31(self):
        a, b = source((random.random() for _ in range(99999))) | \
            (np.chunk() | np.cum_sum() | np.concatenate_chunks()) + (cum_sum() | np.to_array())
        self.assertTrue(numpy.allclose(a, b))

    def test_32(self):
        for i in range(5):
            chunk_len = max(10, random.expovariate(60))   
            stream_len = max(10, random.expovariate(1000))     
            npc, c = source((i, random.random()) for i in range(stream_len)) | \
                (np.chunk(chunk_len) | np.corr()) + corr()
        self.assertAlmostEqual(npc, c)
        
    def test_33(self):
        l, r = source([random.random() for i in range(3000)]) | \
            (np.chunk(max_elems = 99) | np.enumerate_() | (select_inds(0) | np.unchunk()) + (select_inds(1) | np.unchunk())) + \
                enumerate_() | \
            nth(-1)
        self.assertEqual(l, r)                        


class _Test12MovingAggs(unittest.TestCase):
    def test_00(self):
        a = source([1., 2., 3., 4.]) | window_simple_ave(2) | to_list()
        self.assertEqual(a, [1., 1.5, 2.5, 3.5])

    def test_01(self):
        a = source([1., 2., 3., 4.]) | cum_ave() | to_list()
        self.assertEqual(a, [1., 1.5, 2, 2.5])

    def test_02(self):
        a = source([1., 2., 3., 4.]) | exp_ave(0) | to_list()
        self.assertEqual(a, [1., 1., 1., 1.])
        a = source([1., 2., 3., 4.]) | exp_ave(0.75) | to_list()
        self.assertEqual(a, [1., 1.75, 2.6875, 3.671875])

    def test_03(self):
        a = source([1, 2, 3, 4, 1, 0, 4, 4]) | window_min(2) | to_list()
        self.assertEqual(a, [1, 1, 2, 3, 1, 0, 0, 4])

    def test_04(self):
        a = source([1, 2, 3, 4, 1, 0, 4, 4]) | window_max(2) | to_list()
        self.assertEqual(a, [1, 2, 3, 4, 4, 1, 4, 4])

    def test_05(self):
        a = [random.random() for _ in range(1000)]
        a_min, a_max = source(a) | \
            (window_min(10) | to_list()) + (window_max(10) | to_list())
        self.assertEqual([min(a[max(0, i - 10) : i]) for i in range(1, 1001)], a_min)
        self.assertEqual([max(a[max(0, i - 10) : i]) for i in range(1, 1001)], a_max)

    def test_07(self):
        l = source([1, 4, 2, 4, 6, 9, 2, 4, 5]) | window_quantile(2, 0.5) | to_list()
        self.assertEqual(l, [1, 4, 4, 4, 6, 9, 9, 4, 5])
        l = source([1, 4, 2, 4, 6, 9, 2, 4, 5]) | window_quantile(3, 0.5) | to_list()
        self.assertEqual(l, [1, 4, 2, 4, 4, 6, 6, 4, 4])
    
    def test_08(self):
        a = source([1., 2., 3., 4.]) | cum_sum() | to_list()
        self.assertEqual(a, [1., 3., 6., 10.])


class _Test13Plotting(unittest.TestCase):
    _a = numpy.arange(0, 2, 0.3)

    def test_01(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) | \
                plot.figure(1) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot() | plot.savefig('fig_1.png'))       
        except ImportError:
            pass

    def test_02(self):
        try:
            import matplotlib
            source(_Test13Plotting._a) + source(numpy.exp(_Test13Plotting._a)) | \
                plot.figure(2) |  \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.scatter() | plot.savefig('fig_2.png'))       
        except ImportError:
            pass

    def test_03(self):
        try:
            import matplotlib
            source(_Test13Plotting._a) | \
                plot.figure(3) |  \
                plot.title('pie') | \
                (plot.pie() | plot.savefig('fig_3.png'))       
        except ImportError:
            pass

    def test_04(self):
        try:
            import matplotlib
            source(numpy.random.randn(1000)) + source(numpy.random.randn(1000) + 5) | \
                plot.figure(4) |  \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.hexbin() | plot.savefig('fig_4.png'))       
        except ImportError:
            pass

    def test_05(self):
        try:
            import matplotlib
            source(numpy.random.randn(1000)) | \
                plot.figure(5) |  \
                plot.title('acorr') | \
                (plot.acorr() | plot.savefig('fig_5.png'))       
        except ImportError:
            pass

    def test_06(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) + source(_Test13Plotting._a) | \
                plot.figure(6) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot() | plot.savefig('fig_6.png'))       
        except ImportError:
            pass

    @unittest.expectedFailure
    def test_07(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) + source(_Test13Plotting._a) + source(_Test13Plotting._a) | \
                plot.figure(7) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot() | plot.savefig('fig_7.png'))       
        except ImportError:
            pass

    def test_08(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) + source(_Test13Plotting._a) + source(_Test13Plotting._a) + source(numpy.exp(_Test13Plotting._a)) | \
                plot.figure(8) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot() | plot.savefig('fig_8.png'))       
        except ImportError:
            pass

    def test_09(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) | \
                plot.figure(9) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot('g-') | plot.savefig('fig_9.png'))       
        except ImportError:
            pass

    def test_10(self):    
        try:
            import matplotlib
            source(_Test13Plotting._a) + source(_Test13Plotting._a) + source(_Test13Plotting._a) + source(numpy.exp(_Test13Plotting._a)) | \
                plot.figure(10) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.plot('r+', 'g-') | plot.savefig('fig_10.png'))       
        except ImportError:
            pass

    def test_11(self):    
        try:
            import matplotlib
            source(range(1000)) + source(numpy.sin(range(1000))) | \
                plot.figure(11) | \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xcorr') | \
                (plot.xcorr() | plot.savefig('fig_11.png'))       
        except ImportError:
            pass

    def test_12(self):
        try:
            import matplotlib
            source(_Test13Plotting._a) | \
                plot.figure(12) |  \
                plot.title('pie') | \
                (plot.pie(explode = [random.random() for _ in _Test13Plotting._a]) | plot.savefig('fig_12.png'))       
        except ImportError:
            pass

    def test_13(self):
        try:
            import matplotlib
            source(numpy.random.randn(1000)) + source(numpy.random.randn(1000) + 5) | \
                plot.figure(13) |  \
                plot.xlabel('x') | plot.ylabel('y') | plot.title('xy') | \
                (plot.hexbin(alpha = 0.5, marginals = True) | plot.savefig('fig_13.png'))       
        except ImportError:
            pass

    def test_14(self):
        try:
            import matplotlib
            mu, sigma = 100, 15
            x = mu + sigma * numpy.random.randn(10000)
            source(x) | \
                plot.figure(14) |  \
                (plot.hist(normed=1, facecolor='green', alpha=0.75) | plot.savefig('fig_14.png'))
        except ImportError:
            pass
            

class _Test14NumpyCSV(unittest.TestCase):
    def test_00(self):
        for type_ in [int, bytes, float]:
            self.assertEqual(
                np.chunk_stream_vals('data/data.csv', b'wind', type_, b'moshe') | np.unchunk() | to_list(),
                stream_vals('data/data.csv', b'wind', type_) | to_list())

    def test_01(self):
        for (type_, missing) in [(int, 13), (bytes, b'13'), (float, 13.0)]:
            self.assertEqual(
                np.chunk_stream_vals('data/quirky_data.csv', b'wind', type_, missing) | np.unchunk() | to_list(),
                stream_vals('data/quirky_data.csv', b'wind', type_) | filt(lambda x : missing if x is None else x) | to_list())

    @unittest.expectedFailure
    def test_03(self):
        np.chunk_stream_vals('data/quirky_data.csv', b'wind', int, b'moshe') | np.unchunk() | to_list()

    @unittest.expectedFailure
    def test_04(self):
        np.chunk_stream_vals('data/quirky_data.csv', b'wind', float, b'moshe') | np.unchunk() | to_list()

    @unittest.expectedFailure
    def test_05(self):
        np.chunk_stream_vals('data/bad_data.csv', b'day', int, 0) | np.unchunk() | to_list()

    @unittest.expectedFailure
    def test_06(self):
        np.chunk_stream_vals('data/bad_data.csv', b'day', float, 0) | np.unchunk() | to_list()

    def test_07(self):
        self.assertEqual(
            np.chunk_stream_vals('data/data.csv', (b'day', b'wind'), (int, float), (b'moshe', 0)) | \
                filt(lambda xy: xy[0]) | np.unchunk() | to_list(),
            stream_vals('data/data.csv', b'day', int) | to_list())
        self.assertEqual(
            np.chunk_stream_vals('data/data.csv', (b'day', b'wind'), (int, float), (b'moshe', 0)) | \
                filt(lambda xy: xy[1]) | np.unchunk() | to_list(),
            stream_vals('data/data.csv', b'wind', float) | to_list())

    def test_08(self):
        self.assertEqual(
            np.chunk_stream_vals('data/data.csv', (b'wind', b'day'), (float, int), (b'moshe', 0)) | \
                filt(lambda xy: xy[1]) | np.unchunk() | to_list(),
            stream_vals('data/data.csv', b'day', int) | to_list())
        self.assertEqual(
            np.chunk_stream_vals('data/data.csv', (b'wind', b'day'), (float, int), (b'moshe', 0)) | \
                filt(lambda xy: xy[0]) | np.unchunk() | to_list(),
            stream_vals('data/data.csv', b'wind', float) | to_list())

    def test_09(self):
        for type_ in [int, bytes, float]:
            self.assertEqual(
                np.chunk_stream_vals('data/quirky_data.csv', b'wind', type_) | np.unchunk() | to_list(),
                stream_vals('data/quirky_data.csv', b'wind', type_) | filt(lambda x : type_(0) if x is None else x) | to_list())

    def test_10(self):
        payload = [(i, random.random(), random.random()) for i in range(100000)]
        s = sum([p[1] for p in payload], 0.0)
        source(payload) | np.chunk() | np.chunks_to_stream('data/tmp_foo.csv')
        ds = np.chunk_stream_vals('data/tmp_foo.csv', cols = (0, 1, 2)) | filt(lambda t : t[1]) | np.sum_()
        self.assertAlmostEqual(s, ds, delta = 0.1)        
        os.remove('data/tmp_foo.csv')


class _TestSeq15filterCSV(unittest.TestCase):
    def test_00(self):
        l = source([b'foo,bar,wind', b'0,1,2', b'2,3.24,4']) | csv_split(cols = (b'foo',b'bar'), types_ = (float, float)) | to_list()
        self.assertEqual(l, [(0, 1), (2, 3.24)])

    def test_01(self):
        l = source([b'foo,bar,wind', b'0,1,2', b'2,3.24,4']) | csv_split(cols = b'bar', types_ = float) | to_list()
        self.assertEqual(l, [1, 3.24])

    def test_02(self):
        l = source([b'0,1,2', b'2,3.24,4']) | csv_split(cols = 1, types_ = float) | to_list()
        self.assertEqual(l, [1, 3.24])


class _TestSeq16Sed(unittest.TestCase):
    def test_02(self):
        stream_lines('data/foo_sed_2.txt') | filt(lambda l: l + b'\n', pre = lambda l: l.strip()) | to_stream('tmp2.txt')
        self.assertEqual(open('tmp2.txt').read(), open('data/bar_sed_2.txt').read())
        
    def test_04(self):
        stream_lines('data/foo_sed_4.txt') | enumerate_() | \
            consec_group(lambda nl: int(nl[0] / 2), lambda d: select_inds(1) | nth(0))  | \
            to_stream('tmp4.txt')
        self.assertEqual(open('tmp4.txt').read(), open('data/bar_sed_4.txt').read())

    def test_10(self):
        source((int(l.strip() != ''), l.strip()) for l in open('data/foo_sed_10.txt')) | \
            (select_inds(0) | cum_sum()) + select_inds(1) | \
            filt(lambda nl: '{} {}'.format(nl[0], nl[1]) if nl[1] else '') | \
            to_stream('tmp10.txt')
        self.assertEqual(open('tmp10.txt').read(), open('data/bar_sed_10.txt').read())

    def test_29(self):
        stream_lines('data/foo_sed_29.txt') | \
            filt(lambda l: b'foo'.join(l.split(b'foo', 4)[: 4]) + b'bar' + b''.join(l.split(b'foo', 4)[4: ]) \
                if len(l.split(b'foo')) > 3 else l) | \
            to_stream('tmp29.txt')
        self.assertEqual(open('tmp29.txt').read(), open('data/bar_sed_29.txt').read())

    def test_38(self):
        stream_lines('data/foo_sed_38.txt') | enumerate_() | \
            consec_group(
                lambda n_: int(n_[0] / 2), 
                lambda d: select_inds(1) | (to_list() | sink(lambda l: b'\t'.join(l))))  | \
            to_stream('tmp38.txt')
        self.assertEqual(open('tmp38.txt').read(), open('data/bar_sed_38.txt').read())

    def test_39(self):
        c = [0]
        stream_lines('data/foo_sed_39.txt') | \
            consec_group(
                lambda l: (c[0], c.__setitem__(0, c[0] + int(len(l) == 0 or l[-1] != (b'\\')[0]))), 
                lambda d: filt(lambda l: l[: -1] if len(l) > 0 and l[-1] == (b'\\')[0] else l) | sum_())  | \
            to_stream('tmp39.txt')
        self.assertEqual(open('tmp39.txt').read(), open('data/bar_sed_39.txt').read())

    def test_40(self):
        c = [0]
        stream_lines('data/foo_sed_40.txt') | \
            consec_group(
                lambda l: (c[0], c.__setitem__(0, c[0] + int(len(l) == 0 or l[0] != (b'=')[0]))), 
                lambda d: filt(lambda l: l[1 :] if len(l) > 0 and l[0] == (b'=')[0] else l) | sum_())  | \
            to_stream('tmp40.txt')
        self.assertEqual(open('tmp40.txt').read(), open('data/bar_sed_40.txt').read())

    def test_43(self):
        stream_lines('data/foo_sed_43.txt') | enumerate_(1) | \
            filt(lambda nl: nl[1] if nl[0] % 5 else (nl[1] + b'\n')) | to_stream('tmp43.txt')
        self.assertEqual(open('tmp43.txt').read(), open('data/bar_sed_43.txt').read())

    def test_52(self):
        r = re.compile(r'foo(.+?)bar')
        stream_lines('data/foo_sed_52.txt') | \
            to(lambda l: r.search(l.decode('utf-8'))) | (nth(-2) | to_stream('tmp52.txt'))
        self.assertEqual(open('tmp52.txt').read(), open('data/bar_sed_52.txt').read())

    def test_53(self):
        r = re.compile(r'foo(.+?)bar')
        stream_lines('data/foo_sed_53.txt') | \
            from_(lambda l: r.search(l.decode('utf-8'))) | (nth(1) | to_stream('tmp53.txt'))
        self.assertEqual(open('tmp53.txt').read(), open('data/bar_sed_53.txt').read())

    def test_54(self):
        r = re.compile(b'foo(.+?)bar')
        l = stream_lines('data/foo_sed_54.txt') | \
            (to(lambda l: r.search(l)) | (nth(-2))) + \
            (from_(lambda l: r.search(l)) | (nth(1))) + \
            (enumerate_() | filt(pre = lambda nl: r.search(nl[1])) | nth(0))
        self.assertEqual(l, (b'bfoo', b'', (2, b'cfoodbar')))

    def test_58(self):
        stream_lines('data/foo_sed_58.txt') | \
            consec_group(
                lambda l: l.strip() == b'',
                lambda is_para: to_list()) | \
            filt(
                lambda ls: b'\n'.join(ls) + b'\n', 
                pre = lambda ls: sum([b'AAA' in l for l in ls]) > 0) | \
            to_stream('tmp58.txt')
        self.assertEqual(open('tmp58.txt').read(), open('data/bar_sed_58.txt').read())
        
    def test_66(self):        
        l = source(range(20)) | slice_(3, None, 7) | to_list()
        self.assertEqual(l, [3, 10, 17])

    def test_69(self):        
        l = source([1, 1, 2, 1, 1, 4, 4, 2, 3, 5]) | \
            consec_group(lambda l: l, lambda l: nth(0)) | to_list()
        self.assertEqual(l, [1, 2, 1, 4, 2, 3, 5])

    def test_70(self):        
        l = source([1, 1, 2, 1, 1, 4, 4, 2, 3, 5]) | \
            group(lambda l: l, lambda l: nth(0)) | to_list()
        self.assertEqual(l, [1, 2, 4, 3, 5])


if __name__ == '__main__':
    unittest.main()


