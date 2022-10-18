import multiprocessing
import random
def f(l,n):
    l.append(n)

if __name__ == '__main__':
    m = multiprocessing.Manager()
    p = multiprocessing.Pool(3)
    m_dict = m.dict()
    m_list = m.list(range(4))
    p_list = []
    for i in range(10):
        p.apply_async(f,args=(m_list,i))
    p.close()
    p.join()
    print(m_list)