#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <cstdlib>
#include <cstring>
#include <string>

#include "parser_defs.hpp"

using namespace std;

void 
_parse_comment(PyObject * comment_obj, bool & has_comment, char & comment)
{
    if (comment_obj == Py_None) {
        has_comment = false;
        comment = ' ';
        return;
    }
    
    has_comment = true;
#if PY_MAJOR_VERSION >= 3
    DBG_ASSERT(PyBytes_Size(comment_obj) == 1);
    comment = PyBytes_AsString(comment_obj)[0];
#else // #if PY_MAJOR_VERSION >= 3
    DBG_ASSERT(PyString_Size(comment_obj) == 1);
    comment = PyString_AsString(comment_obj)[0];
#endif // #if PY_MAJOR_VERSION >= 3
}

PyObject * 
_ParsedTo_string(const _ParsedT & t)
{
#if PY_MAJOR_VERSION >= 3
    PyObject * const p = PyBytes_FromStringAndSize(t.first, distance(t.first, t.second));
#else
    PyObject * const p = PyString_FromStringAndSize(t.first, distance(t.first, t.second));
#endif // #if PY_MAJOR_VERSION >= 3

    if (p == NULL)
        PyErr_NoMemory();
    return p;
}

long 
_ParsedTo_long(const _ParsedT & t, bool & err)
{
    err = false;
    char * e = const_cast<char *>(t.second);
    const long l = strtol(t.first, &e, 10);
    if (e != t.second) {
        PyErr_Format(PyExc_TypeError, ("Cannot format " + string(t.first, t.second) + " to int").c_str());
        err = true;
    }    
    return l;
}

PyObject * 
_ParsedTo_int(const _ParsedT & t)
{
    bool err;
    PyObject * const p = pyint_from_long(_ParsedTo_long(t, err));
    if (err)
        return NULL;
    if (p == NULL)
        PyErr_NoMemory();
    return p;
}

double 
_ParsedTo_double(const _ParsedT & t, bool & err)
{
    err = false;
    char * e = const_cast<char *>(t.second);
    const double d = strtod(t.first, &e);
    
    // Ugly hack
    double ff = 1;

    if (e != t.second) {
        if (strncmp(t.first, "1.#IND", strlen("1.#IND")) == 0 || strncmp(t.first, "nan", strlen("nan")) == 0)
            return log(-1.0);
        if (strncmp(t.first, "1.#INF", strlen("1.#INF")) == 0 || strncmp(t.first, "inf", strlen("inf")) == 0)
            return 1.0 / (ff * ff - 2 * ff + 1);                  
        if (strncmp(t.first, "-1.#INF", strlen("-1.#INF")) == 0 || strncmp(t.first, "-inf", strlen("-inf")) == 0)
            return -1.0 / (ff * ff - 2 * ff + 1);                  
    
        err = true;
        PyErr_Format(PyExc_TypeError, ("Cannot format " + string(t.first, t.second) + " to float").c_str());
    }    
    return d;
}

PyObject * 
_ParsedTo_float(const _ParsedT & t)
{
    bool err;
    PyObject * const p = PyFloat_FromDouble(_ParsedTo_double(t, err));
    if (p == NULL)
        PyErr_NoMemory();
    return p;
}

char * 
pystring_as_string(PyObject * o, long & len)
{
#if PY_MAJOR_VERSION >= 3
    len = PyBytes_Size(o);
    return PyBytes_AsString(o);
#else // #if PY_MAJOR_VERSION >= 3
    len = PyString_Size(o);
    return PyString_AsString(o);
#endif // #if PY_MAJOR_VERSION >= 3
}

long *
parse_longs(PyObject * iterator, long & num, bool & err)
{
    num = 0;
    err = true;

    PyObject * const iter = PyObject_GetIter(iterator);
    if (iter == NULL) 
        return NULL;

    PyObject * obj;
    long ls[max_num_cols];

    while ((obj = PyIter_Next(iter)) != NULL) {
        if (num == max_num_cols) {
            PyErr_Format(PyExc_IndexError, "max num indices exceeded %d", max_num_cols);
            return NULL;
        }

#if PY_MAJOR_VERSION >= 3
        ls[num++] = PyLong_AsLong(obj);
#else // #if PY_MAJOR_VERSION >= 3
        ls[num++] = PyInt_AsLong(obj);
#endif // #if PY_MAJOR_VERSION >= 3
    }

    err = false;

    if (num == 0) {
        Py_DECREF(iter);       
        return NULL;
    }

    long * const ret = static_cast<long *>(PyMem_Malloc(num * sizeof(long)));    
    if (ret == NULL) {
        err = true;
        PyErr_NoMemory();
        Py_DECREF(iter);
        return NULL;
    }   

    memcpy(ret, ls, num * sizeof(long));

    Py_DECREF(iter);

    return ret;
}

char * *
parse_strings(PyObject * iterator, long & num, bool & err)
{
    num = 0;
    err = true;

    PyObject * const iter = PyObject_GetIter(iterator);
    if (iter == NULL)       
        return NULL;

    PyObject * obj;
    char * ss[max_num_cols];

    while ((obj = PyIter_Next(iter)) != NULL) {
        if (num == max_num_cols) {
            PyErr_Format(PyExc_IndexError, "max num indices exceeded %d", max_num_cols);
            return NULL;
        }

        long len;
        char * s = pystring_as_string(obj, len);
        char * save_s = static_cast<char *>(PyMem_Malloc((len + 1) * sizeof(char)));
        copy(s, s + len, save_s);
        save_s[len] = 0;
        // TRACE("parsed " << s << " " << len << " " << save_s);
        ss[num++] = save_s;
    }

    err = false;

    char * * const ret = static_cast<char * *>(PyMem_Malloc(num * sizeof(char *)));    
    if (ret == NULL) {
        PyErr_NoMemory();
        err = true;
        Py_DECREF(iter);
        return NULL;
    }

    memcpy(ret, ss, num * sizeof(char *));

    Py_DECREF(iter);

    return ret;
}

extern "C" PyObject *
parser_max_field_len(PyObject *module, PyObject *args, PyObject *keyword_args)
{
    return pyint_from_long(max_field_len);
}

