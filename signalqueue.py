#!/usr/bin/python3

import queue
import threading
import time

class SignalQueue(queue.Queue):
    '''A thread-safe queue that triggers a given event whenever new data is
    inserted.'''

    def __init__(self, events, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = events

    def put(self, *args, **kwargs):
        super().put(*args, **kwargs)
        self.events.put(self)


class QueueSet:
    '''A set of queues that can be waited for simultaneously.'''
    
    def __init__(self):
        self.events = queue.Queue()
        self.queues = [ ]

    def New(self):
        '''Create a new Queue-like object that can be waited for by this set'''

        new_queue = SignalQueue(self.events)
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
        an exception of type queue.Empty is raised.'''
        
        while True:
            start_wait = time.monotonic()
            from_queue = self.events.get(timeout=timeout)

            if from_queue not in self.queues:
                # wait for next queue entry, because this queue has been
                # removed in the meantime
                
                timeout = time.monotonic() - start_wait

                if timeout <= 0.0:
                    raise queue.Empty()

                continue
            
            else:
                return (from_queue, from_queue.get())

