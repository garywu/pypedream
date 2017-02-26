from __future__ import print_function
import random
import sys


class _Node(object):
    def __init__(self, val):    
        self.val = val
        self.p = self.l = self.r = None
        self.size = 1
        self.priority = random.random()

    def fix_size_to_top(self):
        self.size = 1
        for c in [self.l, self.r]:
            if c is not None:
                self.size += c.size 
       
        if self.p is not None:
            self.p.fix_size_to_top()

    def assert_valid(self, lt):
        if self.l is None:
            l_size = 0
        else:
            assert self.l.p is self
            assert not lt(self.val, self.l.val)
            assert self.l.priority >= self.priority
            l_size = self.l.assert_valid(lt)
        if self.r is None:
            r_size = 0
        else:
            assert self.r.p is self
            assert not lt(self.r.val, self.val)
            assert self.r.priority >= self.priority
            r_size = self.r.assert_valid(lt)
        assert l_size + 1 + r_size == self.size
        return self.size

    def print_(self, indent):
        if self.p is not None and self.p.l is self:
            print(' ' * indent, 'l', self.val)
        elif self.p is not None and self.p.r is self:
            print(' ' * indent, 'r', self.val)
        else:
            print(' ' * indent, 't', self.val)
        if self.l is not None:
            self.l.print_(indent + 1)
        if self.r is not None:
            self.r.print_(indent + 1)

    def rotate_left(self):
        p, b, q = self, self.r.l, self.r
        assert p is not None and q is not None

        parent = p.p
        if parent is not None:
            is_l = parent.l is p

        p.make_right_child(b)
        q.make_left_child(p)

        if parent is not None:
            if is_l:
                parent.make_left_child(q)
            else:
                parent.make_right_child(q)
        else:
            q.p = None

    def rotate_right(self):
        p, b, q = self.l, self.l.r, self
        assert p is not None and q is not None

        parent = q.p
        if parent is not None:
            is_l = parent.l is q

        q.make_left_child(b)
        p.make_right_child(q)

        if parent is not None:
            if is_l:
                parent.make_left_child(p)
            else:
                parent.make_right_child(p)
        else:
            p.p = None

    def make_left_child(self, other):
        self.l = other
        self._make_child(other)
    
    def make_right_child(self, other):
        self.r = other
        self._make_child(other)

    def _make_child(self, other):
        if other is not None:
            other.p = self
    
        self.size = 1
        for c in [self.l, self.r]:
            if c is not None:
                self.size += c.size

        
class Treap(object):
    def __init__(self, lt):
        self._root = None
        self._lt = lt

    def insert(self, v):
        n = _Node(v)

        if self._root is None:
            self._root = n
            return n

        ins = self._root
        while True:
            if self._lt(v, ins.val):
                if ins.l is None:
                    ins.make_left_child(n)
                    n.fix_size_to_top()
                    self._ins_fix(n)
                    return n
                ins = ins.l
            else:
                if ins.r is None:
                    ins.make_right_child(n)
                    n.fix_size_to_top()
                    self._ins_fix(n)
                    return n
                ins = ins.r

    def erase(self, n):         
        if n.l is None and n.r is None:
            if n.p is None:
                assert self._root is n
                self._root = None
                return

            if n.p.l is n:
                n.p.l = None
            else:
                n.p.r = None
            n.p.fix_size_to_top()

            return

        if n.l is None:
            if n.p is None:
                assert self._root is n
                self._root, n.r.p = n.r, None
                return

            if n.p.l is n:
                n.p.l = n.r
            else:
                n.p.r = n.r
            n.r.p = n.p
            n.p.fix_size_to_top()

            return

        if n.r is None:
            if n.p is None:
                assert self._root is n
                self._root, n.l.p = n.l, None
                return

            if n.p.l is n:
                n.p.l = n.l
            else:
                n.p.r = n.l
            n.l.p = n.p
            n.p.fix_size_to_top()

            return

        if n.l.priority < n.r.priority:
            if n is self._root:
                self._root = n.l
            n.rotate_right()                
        else:
            if n is self._root:
                self._root = n.r
            n.rotate_left()
        self.erase(n)            
        
    def kth(self, k):
        node = self._root
        while True:
            assert node is not None
            assert node.size > k
            l = 0 if node.l is None else node.l.size
            if l == k:
                return node.val
            elif l > k:
                node = node.l
            else:
                node, k = node.r, k - l - 1
        
    def size(self):
        return 0 if self._root is None else self._root.size

    def assert_valid(self):
        if self._root is not None:
            assert self._root.p is None
            self._root.assert_valid(self._lt)

    def _ins_fix(self, n):
        p = n.p

        if p is None or p.priority <= n.priority:
            return

        if p.l is n:
            p.rotate_right()
        else:
            p.rotate_left()

        if p is self._root:
            self._root = n
        else:
            self._ins_fix(n)


