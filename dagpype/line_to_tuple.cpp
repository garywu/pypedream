#include <Python.h>
#include <structmember.h>

#include <assert.h>

#include "defs.hpp"
#include "_line_to_array.hpp"

extern "C" PyObject *
line_to_tuple(PyObject * self, PyObject * args)
{
    char delimit;
    bool has_comment;
    char comment;
    int skip_init_space;
    PyObject * iterator, * comment_obj;
    if (!PyArg_ParseTuple(
            args, 
            "OcOi",
            &iterator, 
            &delimit, &comment_obj, &skip_init_space)) {
        return NULL;
    }

    PyObject * const iter = PyObject_GetIter(iterator);
    if (iter == NULL) {
        PyErr_SetString(PyExc_TypeError, "argument 1 must be an iterator");
        return NULL;
    }

    _parse_comment(comment_obj, has_comment, comment);

    PyObject * const lineobj = PyIter_Next(iter);
    if (lineobj == NULL) {
        PyErr_SetString(PyExc_TypeError, "String expected in first line");
        Py_XDECREF(iter);
        return NULL;
    }
    long line_len;
    char * const line = pystring_as_string(lineobj, line_len);

    _ParsedT parsed[max_num_cols];
    const long num_parsed = has_comment?
        _line_to_array(
            NULL, NULL, 
            0, 0,
            delimit, comment, skip_init_space,
            line, line_len, parsed) :
        _line_to_array(
            NULL, NULL, 
            0, 0,
            delimit, skip_init_space,
            line, line_len, parsed);
    if (num_parsed <= 0) {
        Py_XDECREF(iter);
        Py_XDECREF(lineobj);
        return NULL;
    }

    PyObject * const fields = PyTuple_New(num_parsed);
    if (fields == NULL){
        PyErr_NoMemory();
        Py_XDECREF(iter);
        Py_XDECREF(lineobj);
        return NULL;
    }
    for (long i = 0; i < num_parsed; ++i) {
        PyObject * const  p = _ParsedTo_string(parsed[i]);
        if(p == NULL) {
            Py_XDECREF(lineobj);
            Py_XDECREF(iter);
            Py_XDECREF(fields);
            return NULL;
        }        
        PyTuple_SET_ITEM(fields, i, p);        
    }

    Py_XDECREF(lineobj);
    Py_XDECREF(iter);
    return fields;
}

