import os
from queue import Queue
from multiprocessing import Pool, Manager, Lock, Value


class PoolHolder:
    POOLS: set["PoolHolder"] = set()

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        cls.POOLS.add(obj)
        return obj

    def __init__(self, num_workers: int = os.cpu_count()):
        self.pool = Pool(num_workers, initializer=os.setpgrp)
        self.manager = None

    def queue(self) -> Queue:
        if self.manager is None:
            self.manager = Manager()
        return self.manager.Queue()

    def lock(self) -> Lock:
        if self.manager is None:
            self.manager = Manager()
        return self.manager.Lock()

    def value(self, *args, **kwargs) -> Value:
        if self.manager is None:
            self.manager = Manager()
        return self.manager.Value(*args, **kwargs)

    def submit(self, func, *args, **kwargs):
        return self.pool.apply_async(func, args, kwargs)

    def shutdown(self, wait: bool = True):
        if self.pool:
            print("PoolHolder: shutdown ing")
            if wait:
                self.pool.close()
            else:
                self.pool.terminate()
            self.pool.join()

            if self.manager:
                self.manager.shutdown()
                self.manager = None

            self.pool = None
            self.POOLS.remove(self)

    def __del__(self):
        if self.pool:
            self.shutdown(wait=True)
