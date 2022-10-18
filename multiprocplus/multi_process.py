import multiprocessing
import time
import os

__all__ = ["MultiprocessRunner", "MultiprocessFor", "multiprocess_for", "mp_for"]


class Task(object):
    def __init__(self, idx, func, args, cost):
        self.idx = idx
        self.func = func
        self.args = args
        self.cost = cost

    def __str__(self):
        return f"<T{self.idx}: cost={self.cost}>"

    def __repr__(self):
        return self.__str__()


class MultiprocessRunner(object):
    """
    param:
     num_process: 0, 1 will not run in multi process but using for, -1 will using all cpu to run.
    we advise set num_process=0/1 while debug to make sure passed func have no problem.

    There are some problems that have no warning and errors, but fail to execute  while in multiprocess solver:
        1. passed func declaration mismatch with args
        2. passed func have bugs
        3. passed func must be a global function or member function of global class.

    manager.list()/dict(), the var passed to new process must keep ref in cur process, or will got access error.

    cost assign works well while shared data is big.

    addition:
     1) pool.apply_async do not contains any time of copy passed args and running passed func, all these time are in new process.
     2) the same passed args to two different process will cost (two * copy time), even same args will copy twice.
        so we should only pass process-specified args to each process.
     3)
    """

    def __init__(self, num_process=multiprocessing.cpu_count(), debug_info=False):
        if num_process < 0:
            num_process = multiprocessing.cpu_count()
        self.num_process = num_process
        # self.pool = multiprocessing.Pool(self.num_process)
        self.debug_info = debug_info

    def __call__(self, func, args_list, share_data_list, cost_list=None):
        self.func = func
        if self.num_process == 1 or self.num_process == 0:
            if self.debug_info:
                print(f"[MultiprocessRunner] start run in single process for {len(args_list)} tasks")
            results = []
            for i, args in enumerate(args_list):
                args = args + tuple(share_data_list)
                results.append(func(*args))
            return results

        if cost_list is not None:
            return self.run_with_cost(func, args_list, share_data_list, cost_list)
        return self.run(func, args_list, share_data_list)

    def run(self, func, args_list, share_data_list=[]):
        num_process = min(self.num_process, len(args_list))
        # will not delete shared memory after return compare to with multiprocessing.Manager() as manager
        manager = multiprocessing.Manager()
        pool = multiprocessing.Pool(num_process)

        if self.debug_info:
            print(f"[MultiprocessRunner] start run async in {num_process} processes for {len(args_list)} tasks")
        results = manager.dict()
        share_data_list = self.to_shared_memory_var(manager, share_data_list)
        args_list = [self.to_shared_memory_var(manager, args) for i, args in enumerate(args_list)]
        for i, args in enumerate(args_list):  # the loop not contains time of copy args and running
            # print(f"{i}-th process:", time.time())
            args = (i, results,) + args + share_data_list
            # print(f"start {i}-th process.")
            pool.apply_async(self.func_wrapper, args=args)  # generate new process, new process copy args firstly.
        pool.close()
        pool.join()
        return self.dict_to_list(results)

    def run_with_cost(self, func, args_list, share_data_list=[], cost_list=[]):
        assert len(args_list) == len(cost_list), f"{len(args_list)} vs {len(cost_list)}"
        tasks_group = self.assign_task_group(func, args_list, cost_list)
        # print(tasks_group)

        num_process = min(self.num_process, len(tasks_group))
        # will not delete shared memory after return compare to with multiprocessing.Manager() as manager
        manager = multiprocessing.Manager()
        pool = multiprocessing.Pool(num_process)

        if self.debug_info:
            print(f"[MultiprocessRunner] start run async in {num_process} processes "
                  f"for {len(tasks_group)} groups ({len(args_list)} tasks)")
        # the manger var must keep ref during new process running
        results = manager.dict()
        share_data_list = self.to_shared_memory_var(manager, share_data_list)
        task_group_ids = self.to_shared_memory_var(manager, [[task.idx for task in tasks] for tasks in tasks_group])
        task_group_args = self.to_shared_memory_var(manager, [[task.args for task in tasks] for tasks in tasks_group])
        for gid, tasks in enumerate(tasks_group):
            args = (gid, task_group_ids[gid], results) + (task_group_args[gid], share_data_list)
            pool.apply_async(self.multi_func_wrapper, args=args)  # generate new process, new process copy args firstly.
        pool.close()
        pool.join()
        return self.dict_to_list(results)

    def multi_func_wrapper(self, gid, tasks_id, results, multi_args, share_data_list):
        try:
            tic = time.time()
            for i, task_id in enumerate(tasks_id):
                tic2 = time.time()
                self.func_wrapper(task_id, results, *multi_args[i], *share_data_list)
                # print(f"[MultiprocessRunner:({gid})] complete {task_id}-th task ({i + 1}/{len(tasks_id)}, {time.time()-tic2}s).")
            if self.debug_info:
                print(f"[MultiprocessRunner:({gid})] finished all {len(tasks_id)} tasks "
                      f"({time.time() - tic}s) --------------------------")
        except BaseException as b:
            print(f"[MultiprocessRunner:({gid})] {b}")
            raise b

    def func_wrapper(self, i, results, *args, **kwargs):
        try:
            # print(results)
            results[i] = self.func(*args, **kwargs)
        except BaseException as b:
            print(f"[MultiprocessRunner:({i})] {b}")
            raise b

    def assign_task_group(self, func, args_list, cost_list):
        tasks = [Task(i, func, args, cost) for i, (args, cost) in enumerate(zip(args_list, cost_list))]
        tasks = sorted(tasks, key=lambda task: -task.cost)
        std_cost = tasks[0].cost * 3
        tasks_gorup = []
        cur_cost, cur_group = 0, []
        for i in range(len(tasks) - 1, -1, -1):
            cur_cost += tasks[i].cost
            if cur_cost <= std_cost:
                cur_group.append(tasks[i])
            else:
                if cur_cost - std_cost <= std_cost - (cur_cost - tasks[i].cost):  # add cur task is better than not add
                    cur_group.append(tasks[i])
                    tasks_gorup.append(cur_group)
                    cur_cost, cur_group = 0, []
                else:  # not add is beeter than add, keep cur task to next group
                    tasks_gorup.append(cur_group)
                    cur_cost, cur_group = tasks[i].cost, [tasks[i]]
        if len(cur_group) > 0:
            tasks_gorup.append(cur_group)
        return tasks_gorup

    def dict_to_list(self, data):
        new_data = []
        for idx in range(len(data)):
            new_data.append(data[idx])
        return new_data

    def to_shared_memory_var(self, manager, var_list):
        m_share_data_list = []
        for data in var_list:
            if isinstance(data, list):
                data = manager.list(data)
            elif isinstance(data, dict):
                data = manager.dict(data)
            elif isinstance(data, (int, float)):
                pass
            else:
                raise TypeError("shared data must be list or dict")
            m_share_data_list.append(data)
        return tuple(m_share_data_list)


def multiprocess_for(func, args_list, share_data_list=[], cost_list=None, num_process=multiprocessing.cpu_count()):
    """
    multiprocess_for can be utilized to replace for loop:
        results = []
        for args in args_list:
            args = args + (share_data_list,)
            results.append(func(*args))
        return results
    """
    return MultiprocessRunner(num_process)(func, args_list, share_data_list, cost_list)


MultiprocessFor = MultiprocessRunner
mp_for = multiprocess_for
