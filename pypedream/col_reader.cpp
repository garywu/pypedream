#include <Python.h>
#include <structmember.h>

#include <algorithm>
#include <cstdlib>
#include <iostream>

#include "col_reader.hpp"
#include "_line_to_array.hpp"
    
using namespace std;

struct ColReader
{
    PyObject_HEAD

    PyObject * input_iter;

    char delimit;
    bool has_comment;
    char comment;
    int skip_init_space;

    int single;

    long num_cols, num_unique_cols, num_copy_cols;
    long * cols, * unique_cols, * copy_cols;
    long max_col;
 
    long * types;
    long num_types;
};

extern PyTypeObject ColReaderType;

extern "C" int
col_reader_traverse(ColReader * self, visitproc visit, void *arg)
{
    Py_VISIT(self->input_iter);
    return 0;
}

extern "C" void
col_reader_dealloc(ColReader * self)
{
    Py_XDECREF(self->input_iter);

    if (self->cols != NULL)
        PyMem_Free(self->cols);
    if (self->unique_cols != NULL)
        PyMem_Free(self->unique_cols);
    if (self->copy_cols != NULL)
        PyMem_Free(self->copy_cols);
    if (self->types != NULL)
        PyMem_Free(self->types);

    PyObject_GC_UnTrack(self);
    PyObject_GC_Del(self);
}

extern "C" PyObject *
col_reader_new(PyTypeObject * type, PyObject *args, PyObject *keyword_args)
{
    ColReader * const self = PyObject_GC_New(ColReader, &ColReaderType);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }   

    self->num_cols = self->num_unique_cols = self->num_copy_cols = 0;
    self->input_iter = NULL;
    self->cols = self->unique_cols = self->copy_cols = NULL;
    self->num_types = 0;
    self->types = NULL;

    PyObject * iterator, * comment, * cols_iterator, * unique_cols_iterator, * copy_cols_iterator, * types_iterator;
    if (!PyArg_ParseTuple(
            args,
            "OcOiiOOOlO",
            &iterator,
            &self->delimit, &comment, &self->skip_init_space,
            &self->single,
            &cols_iterator, &unique_cols_iterator, &copy_cols_iterator,
            &self->max_col,
            &types_iterator)) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        Py_DECREF(self);
        return NULL;
    }
    
    bool err = false;
    self->input_iter = PyObject_GetIter(iterator);
    _parse_comment(comment, self->has_comment, self->comment);
    self->cols = parse_longs(cols_iterator, self->num_cols, err);
    self->unique_cols = parse_longs(unique_cols_iterator, self->num_unique_cols, err);
    self->copy_cols = parse_longs(copy_cols_iterator, self->num_copy_cols, err);
    self->types = parse_longs(types_iterator, self->num_types, err);
    if (self->input_iter == NULL || err) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        Py_DECREF(self);
        return NULL;
    }
    Py_INCREF(self->input_iter);

    PyObject_GC_Track(self);
    return (PyObject *)self;
}


static PyObject *
copy_parsed(const _ParsedT & t, long num_types, const long * const types, long i)
{
    if (t.first == t.second)
        Py_RETURN_NONE;
    if (i < num_types && types[i] == _int) 
        return _ParsedTo_int(t);
    if (i >= num_types || types[i] == _float) 
        return _ParsedTo_float(t);
    return _ParsedTo_string(t);
}

static PyObject *
col_reader_copy_parsed(ColReader * self, long num_parsed, const _ParsedT parsed[max_num_cols])
{
    if (num_parsed == 1)
        return copy_parsed(parsed[0], self->num_types, self->types, 0);

    PyObject * const fields = PyTuple_New(num_parsed);
    if (fields == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    for (long i = 0; i < num_parsed; ++i) {
        PyObject * const p =
            copy_parsed(parsed[i], self->num_types, self->types, i);
        PyTuple_SET_ITEM(fields, i, p);
    }      
    return fields;
}

static PyObject *
col_reader_copy_parsed_from_inds(ColReader * self, long num_parsed, _ParsedT const parsed[max_num_cols])
{
    if (self->num_cols == 1)
        return copy_parsed(parsed[0], self->num_types, self->types, 0);

    PyObject * const fields = PyTuple_New(self->num_cols);
    if (fields == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    for (long i = 0; i < self->num_cols; ++i) {
        PyObject * const p =
            copy_parsed(parsed[self->copy_cols[i]], self->num_types, self->types, i);
        if (p == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        PyTuple_SET_ITEM(fields, i, p);
    }  
    return fields;
}

extern "C" PyObject *
col_reader_iternext(ColReader * self)
{
    PyObject * const lineobj = PyIter_Next(self->input_iter); 
    if (lineobj == NULL) 
        return NULL;

    long line_len;
    const char * line = pystring_as_string(lineobj, line_len);
    if (line == NULL || line_len < 0) {
        PyErr_Format(PyExc_TypeError, "No line or negative line len %p %ld", line, line_len);
        Py_DECREF(lineobj);
        return NULL;
    }

    _ParsedT parsed[max_num_cols];
    const long num_parsed = self->has_comment?
        _line_to_array(
            self->cols, self->unique_cols, 
            self->num_cols, self->max_col,
            self->delimit, self->comment, self->skip_init_space,
            line, line_len, parsed) :
        _line_to_array(
            self->cols, self->unique_cols, 
            self->num_cols, self->max_col,
            self->delimit, self->skip_init_space,
            line, line_len, parsed);
    if (num_parsed <= 0) {
        Py_DECREF(lineobj);
        return NULL;
    }
    
    PyObject * const tup = self->copy_cols != NULL?
        col_reader_copy_parsed_from_inds(self, num_parsed, parsed) :
        col_reader_copy_parsed(self, num_parsed, parsed);
   
    Py_DECREF(lineobj);

    return tup;
}

extern "C" PyObject *
col_reader_parse_string(ColReader * self, PyObject * lineobj)
{
    long line_len;
    const char * line = pystring_as_string(lineobj, line_len);
    if (line == NULL || line_len < 0) {
        PyErr_Format(PyExc_TypeError, "No line or negative line len %p %ld", line, line_len);
        return NULL;
    }

    _ParsedT parsed[max_num_cols];
    const long num_parsed = self->has_comment?
        _line_to_array(
            self->cols, self->unique_cols, 
            self->num_cols, self->max_col,
            self->delimit, self->skip_init_space,
            line, line_len, parsed) :
        _line_to_array(
            self->cols, self->unique_cols, 
            self->num_cols, self->max_col,
            self->delimit, self->comment, self->skip_init_space,
            line, line_len, parsed);
    if (num_parsed <= 0) {
        return NULL;
    }
   
    PyObject * const tup = self->copy_cols != NULL?
        col_reader_copy_parsed_from_inds(self, num_parsed, parsed) :
        col_reader_copy_parsed(self, num_parsed, parsed);

    return tup;
}

extern "C" int
col_reader_clear(ColReader * self)
{
    if (self->input_iter != NULL)
        Py_CLEAR(self->input_iter);
    return 0;
}

static PyMethodDef col_reader_methods[] = {
    { "parse_string", (PyCFunction)col_reader_parse_string, METH_O, "" },
    { NULL, NULL }
};

static PyMemberDef col_reader_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(ColReaderType_doc, "");

PyTypeObject ColReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.ColReader",               /*tp_name*/
    sizeof(ColReader),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)col_reader_dealloc,          /*tp_dealloc*/
    0,                                         /*tp_print*/
    0,                                         /*tp_getattr*/
    0,                                         /*tp_setattr*/
    0,                                          /*tp_compare*/
    0,                                        /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                            /*tp_hash*/
    0,                         /*tp_call*/
    0,                            /*tp_str*/
    0,                                      /*tp_getattro*/
    0,                                      /*tp_setattro*/
    0,                                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE |
    Py_TPFLAGS_HAVE_GC,                     /*tp_flags*/
    ColReaderType_doc,                     /*tp_doc*/
    (traverseproc)col_reader_traverse,       /*tp_traverse*/
    (inquiry)col_reader_clear,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    PyObject_SelfIter,                      /*tp_iter*/
    (getiterfunc)col_reader_iternext,        /*tp_iternext*/
    col_reader_methods,                      /*tp_methods*/
    col_reader_memberlist,                   /*tp_members*/
    0,                       /* tp_getset */
    0,                       /* tp_base */
    0,                       /* tp_dict */
    0,                       /* tp_descr_get */
    0,                       /* tp_descr_set */
    0,                       /* tp_dictoffset */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    col_reader_new,                 /* tp_new */
};
