#!/usr/bin/python3
"""
Pure-Python implementation of a coroutining facility
vaguely inspired by Twisted.
"""
from collections.abc import Iterable

class WaitingFor(object):
    def __init__(self, player, match_fn):
        self.player = player
        self.match_fn = match_fn

def maybe_gen(value):
    if isinstance(value, Iterable):
        yield from value
    return value

class Reactor(object):
    class ThreadUsedBareYield(Exception):
        """Bare 'yield' should only be used to yield to a WaitingFor.
        To yield to another asynchronous function, use 'yield from'."""
    def __init__(self):
        self.waiting = {}
    def start_thread(self, thread):
        try:
            v = next(thread)
        except StopIteration as s:
            return s.value
        if isinstance(v, WaitingFor):
            self.waiting[v] = thread
            return None
        raise self.ThreadUsedBareYield("Thread used 'yield' instead of 'yield from'.", v)
    def feed_value(self, thread, v):
        try:
            v = thread.send(v)
        except StopIteration as s:
            return s.value
        if isinstance(v, WaitingFor):
            self.waiting[v] = thread
            return None
        raise self.ThreadUsedBareYield("Thread used 'yield' instead of 'yield from'.", v)
    def progress(self, wf, value):
        thread = self.waiting.pop(wf)
        return self.feed_value(thread, value)
