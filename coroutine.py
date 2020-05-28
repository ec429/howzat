#!/usr/bin/python3
"""
Pure-Python implementation of a coroutining facility
vaguely inspired by Twisted.
"""

def dummy_generator():
    yield 1

generator = type(dummy_generator())

class WaitingFor(object):
    def __init__(self, player, match_fn):
        self.player = player
        self.match_fn = match_fn

class Value(object):
    def __init__(self, value):
        self.value = value

class Reactor(object):
    def __init__(self, debug=False):
        self.waiting = {}
        self.dbg = debug
    def debug(self, *args):
        if self.dbg:
            print(*args)
    def start_thread(self, runner):
        v = self.step_thread(runner)
        self.debug('started', v)
        if isinstance(v, Value):
            self.debug('thread finished with result', v.value)
    def throw(self, stack, e):
        if not stack:
            raise e
        self.debug('throw', stack, e)
        left = stack[:-1]
        thread = stack[-1]
        try:
            v = thread.throw(e)
        except StopIteration:
            v = Value(None)
        except Exception as e:
            self.throw(left, e)
        self.debug('throw v', v)
        self.value_fed(left, thread, v, stack)
    def step_thread(self, thread, stack=()):
        self.debug('step', thread, stack)
        if isinstance(thread, generator):
            try:
                v = next(thread)
            except StopIteration:
                v = Value(None)
            except Exception as e:
                self.throw(stack, e)
            self.debug('step v', v)
            if isinstance(v, WaitingFor):
                self.waiting[v] = stack + (thread,)
                return None
            if isinstance(v, Value):
                if stack:
                    self.waiting[v] = stack
                    return None
                    #return self.feed_value(stack, v.value)
                return v
            if isinstance(v, generator):
                return self.step_thread(v, stack=stack + (thread,))
            return self.step_thread(v, stack=stack + (thread,))
        while stack:
            thread = self.feed_value(stack, thread)
            self.debug('step fed', thread, stack)
            if isinstance(thread, Value):
                stack = stack[:-1]
            else:
                return None
        return thread
    def feed_value(self, stack, v):
        self.debug('feed', stack, v)
        assert stack, stack
        left = stack[:-1]
        thread = stack[-1]
        try:
            v = thread.send(v)
        except StopIteration:
            v = Value(None)
        except Exception as e:
            self.throw(left, e)
        self.debug('feed v', v)
        self.value_fed(left, thread, v, stack)
    def value_fed(self, left, thread, v, stack):
        if isinstance(v, WaitingFor):
            self.waiting[v] = stack
            return None
        if isinstance(v, Value):
            if left:
                self.waiting[v] = left
                return None
                #return self.feed_value(left, v.value)
            return v
        return self.step_thread(v, stack=stack)
    def step_running(self):
        for wf in self.waiting:
            if isinstance(wf, WaitingFor):
                continue
            if isinstance(wf, Value):
                self.progress(wf, wf.value)
                return True
        return False
    def progress(self, wf, value):
        stack = self.waiting.pop(wf)
        v = self.feed_value(stack, value)
        self.debug('progressed', v)
        if isinstance(v, Value):
            self.debug('thread finished with result', v.value)
