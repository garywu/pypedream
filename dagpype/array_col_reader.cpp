#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <cstdlib>
#include <cstdlib>
#include <iostream>
#include <vector>

#include "array_col_reader.hpp"
#include "_line_to_array.hpp"

using namespace std;

struct ArrayColReader
{
    PyObject_HEAD

    PyObject *input_iter;

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

    _ParsedT * missing_vals;

    long max_elems;

    PyArrayObject * * bufs;
};

extern PyTypeObject ArrayColReaderType;

extern "C" int
array_col_reader_traverse(ArrayColReader * self, visitproc visit, void *arg)
{
    Py_VISIT(self->input_iter);

    for (long j = 0; j < self->num_types; ++j)
        Py_VISIT(self->bufs[j]);

    return 0;
}

extern "C" void
array_col_reader_dealloc(ArrayColReader * self)
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
    if (self->missing_vals != NULL) {
        for (long i = 0; i < self->num_types; ++i)
            PyMem_Free(const_cast<char *>(self->missing_vals[i].first));
        PyMem_Free(self->missing_vals);
    }
    if (self->bufs != NULL) {
        for (long i = 0; i < self->num_types; ++i)
            Py_XDECREF(self->bufs[i]);
        PyMem_Free(self->bufs);
    }

    PyObject_GC_UnTrack(self);
    PyObject_GC_Del(self);
}

static _ParsedT *
array_col_reader_parse_missing_vals(PyObject * iterator, long num_types, bool & err)
{
    char * * missing_vals = parse_strings(iterator, num_types, err);
    if (err)
        return NULL;

    _ParsedT * const parsed_missing_vals = 
        static_cast<_ParsedT *>(PyMem_Malloc(num_types * sizeof(_ParsedT)));    
    if (parsed_missing_vals == NULL) {
        err = true;
        PyErr_NoMemory();
        return NULL;
    }

    for (long j = 0; j < num_types; ++j) {
        parsed_missing_vals[j] = make_pair(missing_vals[j], missing_vals[j] + strlen(missing_vals[j]));
        if (strlen(missing_vals[j]) >= max_field_len - 1) {
            err = true;
            PyErr_Format(PyExc_IndexError, "Missing value too long - max %d", max_field_len - 1);
            return NULL;
        }
    }

    return parsed_missing_vals;
}

static PyArrayObject * *
parse_arrays(PyObject * iterator, long & num, bool & err)
{
    num = 0;
    err = true;

    PyObject * const iter = PyObject_GetIter(iterator);
    if (iter == NULL)       
        return NULL;

    PyObject * obj;
    PyArrayObject * arrays[max_num_cols];

    while ((obj = PyIter_Next(iter)) != NULL) {
        if (num == max_num_cols) {
            PyErr_Format(PyExc_IndexError, "max num indices exceeded %d", max_num_cols);
            return NULL;
        }

        PyArrayObject * const a = reinterpret_cast<PyArrayObject *>(obj);

        if (!is_delightful_array(a)) {
            PyErr_SetString(PyExc_NotImplementedError, "Must be well behaved");
            return NULL;
        }

        Py_INCREF(a);
        arrays[num++] = a;
    }

    err = false;

    PyArrayObject * * const ret = static_cast<PyArrayObject * *>(PyMem_Malloc(num * sizeof(PyArrayObject *)));    
    if (ret == NULL) {
        PyErr_NoMemory();
        err = true;
        Py_DECREF(iter);
        return NULL;
    }

    memcpy(ret, arrays, num * sizeof(PyArrayObject *));

    Py_DECREF(iter);

    return ret;
}

extern "C" PyObject *
array_col_reader_new(PyTypeObject * type, PyObject *args, PyObject *keyword_args)
{
    ArrayColReader * const self = PyObject_GC_New(ArrayColReader, &ArrayColReaderType);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }   

    self->num_cols = self->num_unique_cols = self->num_copy_cols = 0;
    self->input_iter = NULL;
    self->cols = self->unique_cols = self->copy_cols = NULL;
    self->num_types = 0;
    self->types = NULL;
    self->missing_vals = NULL;

    // TRACE("Parsing");   
    PyObject * iterator, * comment, * cols_iterator, * unique_cols_iterator, * copy_cols_iterator, 
        * types_iterator, * missing_vals_iterator, * bufs_iterator;
    if (!PyArg_ParseTuple(
            args,
            "OcOiiOOOlOOlO",
            &iterator,
            &self->delimit, &comment, &self->skip_init_space,
            &self->single,
            &cols_iterator, &unique_cols_iterator, &copy_cols_iterator,
            &self->max_col,
            &types_iterator,
            &missing_vals_iterator,
            &self->max_elems,
            &bufs_iterator)) {
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
    self->missing_vals = array_col_reader_parse_missing_vals(missing_vals_iterator, self->num_types, err);
    self->bufs = parse_arrays(bufs_iterator, self->num_types, err);
    if (self->input_iter == NULL || err) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        Py_DECREF(self);
        return NULL;
    }

    Py_INCREF(self->input_iter);

    PyObject_GC_Track(self);
    return (PyObject *)self;
}

static bool
array_col_reader_copy_int_parsed_col(
    const _ParsedT & t, 
    const _ParsedT & missing_val,
    PyArrayObject * ret, 
    long i)
{
    bool err;
    ((long *)ret->data)[i] = _ParsedTo_long(t.first == t.second? missing_val : t, err);
    return !err;
}

static bool
array_col_reader_copy_float_parsed_col(
    const _ParsedT & t, 
    const _ParsedT & missing_val,
    PyArrayObject * ret, 
    long i)
{
    bool err;
    ((double *)ret->data)[i] = _ParsedTo_double(t.first == t.second? missing_val : t, err);
    return !err;
}

static void
array_col_reader_copy_str_parsed_col(
    const _ParsedT & t, 
    const _ParsedT & missing_val,
    PyArrayObject * ret, 
    long i)
{
    char buf[4];
    const _ParsedT & pt = t.first == t.second? missing_val : t;
    sprintf(buf, "%03d", static_cast<int>(distance(pt.first, pt.second)));
    copy(buf, buf + 3, (char *)ret->data + i * max_field_len);
    copy(pt.first, pt.second, (char *)ret->data + i * max_field_len + 3);
}

static bool
array_col_reader_copy_parsed_col(
    ArrayColReader * self, 
    const _ParsedT & t, 
    long j, 
    long i)
{
    DBG_VERIFY(j < self->num_types);
    switch (self->types[j]) {
        case _int:
            return array_col_reader_copy_int_parsed_col(t, self->missing_vals[j], self->bufs[j], i);
        case _float:
            return array_col_reader_copy_float_parsed_col(t, self->missing_vals[j], self->bufs[j], i);
        case _str:
            array_col_reader_copy_str_parsed_col(t, self->missing_vals[j], self->bufs[j], i);
            return true;
        default:
            DBG_VERIFY(false);
    }
    return false;
}

static bool
array_col_reader_copy_parsed(
    ArrayColReader * self, 
    const _ParsedT parsed[max_num_cols],
    long i)
{
    if (self->num_types == 1)
        return array_col_reader_copy_parsed_col(self, parsed[0], 0, i);

    for (long j = 0; j < self->num_types; ++j) 
        if (!array_col_reader_copy_parsed_col(self, parsed[j], j, i))
            return false;
    return true;
}

static bool
array_col_reader_copy_parsed_from_inds(
    ArrayColReader * self, 
    const _ParsedT parsed[max_num_cols],
    long i)
{
    if (self->num_cols == 1)
        return array_col_reader_copy_parsed_col(self, parsed[0], 0, i);

    for (long j = 0; j < self->num_cols; ++j) 
        if (!array_col_reader_copy_parsed_col(self, parsed[self->copy_cols[j]], j, i))
            return false;
    return true;
}

static bool 
array_col_reader_parse_line(ArrayColReader * self, _ParsedT parsed[max_num_cols])
{
    PyObject * const lineobj = PyIter_Next(self->input_iter); 
    if (lineobj == NULL) 
        return false;

    long line_len;
    const char * line = pystring_as_string(lineobj, line_len);
    if (line == NULL || line_len < 0) {
        PyErr_Format(PyExc_TypeError, "No line, or negative line len %p %ld", line, line_len);
        Py_DECREF(lineobj);
        return false;
    }

    long num_parsed = self->has_comment?
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
        return false;
    }
    while (num_parsed < self->num_types) 
        parsed[num_parsed++] = make_pair((char *)NULL, (char *)NULL);
   
    Py_DECREF(lineobj);

    return true;
}

extern "C" PyObject *
array_col_reader_iternext(ArrayColReader * self)
{
    long i;
    _ParsedT parsed[max_num_cols];
    for (i = 0; i  < self->max_elems; ++i) {
    
        if (!array_col_reader_parse_line(self, parsed)) 
            break;
        
        if (self->copy_cols != NULL?
                !array_col_reader_copy_parsed_from_inds(self, parsed, i) :
                !array_col_reader_copy_parsed(self, parsed, i))
            return NULL;
    }

    return pyint_from_long(i);
}

extern "C" int
array_col_reader_clear(ArrayColReader * self)
{
    Py_CLEAR(self->input_iter);
    for (long j = 0; j < self->num_types; ++j)
        Py_CLEAR(self->bufs[j]);
    return 0;
}

static PyMethodDef array_col_reader_methods[] = {
    { NULL, NULL }
};

static PyMemberDef array_col_reader_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(ArrayColReaderType_doc, "");

PyTypeObject ArrayColReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.ArrayColReader",               /*tp_name*/
    sizeof(ArrayColReader),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)array_col_reader_dealloc,          /*tp_dealloc*/
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
    ArrayColReaderType_doc,                     /*tp_doc*/
    (traverseproc)array_col_reader_traverse,       /*tp_traverse*/
    (inquiry)array_col_reader_clear,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    PyObject_SelfIter,                      /*tp_iter*/
    (getiterfunc)array_col_reader_iternext,        /*tp_iternext*/
    array_col_reader_methods,                      /*tp_methods*/
    array_col_reader_memberlist,                   /*tp_members*/
    0,                       /* tp_getset */
    0,                       /* tp_base */
    0,                       /* tp_dict */
    0,                       /* tp_descr_get */
    0,                       /* tp_descr_set */
    0,                       /* tp_dictoffset */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    array_col_reader_new,                 /* tp_new */
};
