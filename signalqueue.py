#!/usr/bin/python3

import queue
import threading
import time

class SignalQueue(queue.Queue):
    '''A thread-safe queue that triggers a given event whenever new data is
    inserted.
    
    In order to avoid race conditions, the Event should always be reset BEFORE
    getting data from the queue.'''

    def __init__(self, event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event

    def put(self, *args, **kwargs):
        super().put(*args, **kwargs)
        self.event.set()


class QueueSet:
    '''A set of queues that can be waited for simultaneously.'''
    
    def __init__(self):
        self.event = threading.Event()
        self.queues = [ ]

    def New(self):
        '''Create a new Queue-like object that can be waited for by this set'''

        new_queue = SignalQueue(self.event)
        self.queues.append(new_queue)

        return new_queue

    def remove(self, q):
        '''Remove a queue from this set.'''

        if not q in self.queues:
            raise KeyError()

        self.queues = [ x for x in self.queues if x != q ]

    def get(self, timeout=None):
        '''Get the next available input as a (queue,data) pair, blocking if
        necessary. If no data was received within the optionally given timeout,
        an exception of type queue.Empty is raised.

        Note that this operation does not respect the FIFO property between
        multiple queues, so e.g. starvation may occur.'''
            
        while True:
            if self.event.wait(timeout):
                self.event.clear()
                for q in self.queues:
                    try:
                        data = q.get_nowait()
                        return (q, data)
                    except queue.Empty:
                        pass
            else:
                raise queue.Empty()


#class LockedEvent(threading.Event):
#    '''An event notifier that can also be locked. It can only be reset, but not
#    set during a lock phase.
#
#    This is useful if used in a consumer-producer scheme for signalling and the
#    consumer needs to reset the Event based on some conditions. Checking this
#    condition and resetting the Event can then be done atomically to avoid
#
#    # NOT necessary if the consumer always resets the event before looking at
#    # the queues and just waits for it to be set again when no queue contains
#    # a value anymore
