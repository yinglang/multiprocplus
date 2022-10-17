import multiprocessing
import time
import os


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
    def __init__(self, num_process=multiprocessing.cpu_count()):
        if num_process < 0:
            num_process = multiprocessing.cpu_count()
        self.num_process = num_process
        # self.pool = multiprocessing.Pool(self.num_process)

    def __call__(self, func, args_list, share_data_list, cost_list=None):
        self.func = func
        if self.num_process == 1 or self.num_process == 0:
            print(f"[MultiprocessRunner] start run in single process for {len(args_list)} tasks")
            results = []
            for i, args in enumerate(args_list):
                args = args + tuple(share_data_list)
                results.append(func(*args))
            return results

        if cost_list is not None:
            return self.run_with_cost(func, args_list, share_data_list, cost_list)
        return self.run(func, args_list, share_data_list)

    def run(self, func, args_list, share_data_list):
        num_process = min(self.num_process, len(args_list))
        # will not delete shared memory after return compare to with multiprocessing.Manager() as manager
        manager = multiprocessing.Manager()
        pool = multiprocessing.Pool(num_process)

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

    def run_with_cost(self, func, args_list, share_data_list, cost_list):
        tasks_group = self.assign_task_group(func, args_list, cost_list)
        # print(tasks_group)

        num_process = min(self.num_process, len(tasks_group))
        # will not delete shared memory after return compare to with multiprocessing.Manager() as manager
        manager = multiprocessing.Manager()
        pool = multiprocessing.Pool(num_process)

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
            print(f"[MultiprocessRunner:({gid})] finished all {len(tasks_id)} tasks "
                  f"({time.time() - tic}s) --------------------------")
        except BaseException as b:
            print(f"[MultiprocessRunner:({gid})] {b}")

    def func_wrapper(self, i, results, *args, **kwargs):
        # print(results)
        results[i] = self.func(*args, **kwargs)

    def assign_task_group(self, func, args_list, cost_list):
        tasks = [Task(i, func, args, cost) for i, (args, cost) in enumerate(zip(args_list, cost_list))]
        tasks = sorted(tasks, key=lambda task: -task.cost)
        std_cost = tasks[0].cost * 3
        tasks_gorup = []
        cur_cost, cur_group = 0, []
        for i in range(len(tasks)-1, -1, -1):
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


def multiprocess_run(func, args_list, share_data_list, cost_list=None, num_process=multiprocessing.cpu_count()):
    """
    to replace:
        results = []
        for i, (args, kwargs) in enumerate(zip(args_list, kwargs_list)):
            results.append(func(args, args_list, results))
        return results
    """
    return MultiprocessRunner(num_process)(func, args_list, share_data_list, cost_list)


class MyTest(object):
    def func(self, idx, dataA, dataB):
        print(f"start {idx}")
        da = dataA[idx]
        sum_res = {}
        for k, v in dataB.items():
            sum_res[k] = da + v
        import time
        time.sleep(3)
        print(f"finish {idx}")
        return sum_res

    def func2(self, idx, da, dataB):
        print(f"start {idx}")
        sum_res = {}
        da = da[0]
        for k, v in dataB.items():
            sum_res[k] = da + v
        import time
        time.sleep((idx+1)*2)
        print(f"finish {idx}")
        return sum_res
        # return idx

    def mytest1(self):
        """
        the shared data can be list or dict, even numpy data inside them.
        """
        import numpy as np
        n = 5
        dataA = [np.arange(n), np.arange(n)+5, np.arange(n)+10, np.arange(n)+15, np.arange(n)+20]  # data
        dataB = {"a": np.arange(n), "b": 2, "c": 3}

        # # for a, b in zip(dataA, dataB):
        # #     func(a, b)
        # res = MultiprocessRunner(num_process=3)(self.func, [(i,) for i in range(5)], share_data_list=[dataA, dataB])
        # print(len(res), res[1])
        # res = MultiprocessRunner(num_process=0)(self.func, [(i,) for i in range(5)], share_data_list=[dataA, dataB])
        # print(len(res), res[1])
        # # print(res)
        # # print(res[0])
        # # res = multiprocess_run(self.func, [(i,) for i in range(5)], share_data_list=[dataA, dataB], num_process=3)
        # # print(res[1])
        #
        # res = multiprocess_run(self.func2, [(i, [dataA[i]]) for i in range(5)], share_data_list=[dataB],
        #                        num_process=3)
        # print(len(res), res[1])

        res = multiprocess_run(self.func2, [(i, [dataA[i]]) for i in range(5)], share_data_list=[dataB],
                               cost_list=[1, 2, 3, 4, 5],
                               num_process=3)
        print(len(res), res[1])
        return res

    def mytest2(self, res):
        """
            the returned result can be passed cross function.
        """
        print(res[0])


if __name__ == "__main__":
    # res = mytest1()
    # mytest2(res)
    m = MyTest()
    m.mytest2(m.mytest1())
