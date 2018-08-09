# -*- coding: utf-8 -*-
"""
Refrence: https://github.com/QuantumLiu/tf_gpu_manager/issues/1 
"""

import argparse
import os
import sys

def get_args():
    parser = argparse.ArgumentParser(description='GPU selector')
    parser.add_argument('--count', type=int, default=1,
                        help='Specify number of gpu')
    parser.add_argument('--set', type=str, default=None,
                        help='Choose gpu from this set')
    parser.add_argument('--memory-at-least', type=int, default=None,
                        help='Specify memory lower bound')
    parser.add_argument('--process-limit', type=int, default=6)
    return parser.parse_args()

def check_gpus():
    '''
    GPU available check
    http://pytorch-cn.readthedocs.io/zh/latest/package_references/torch-cuda/
    '''
    if not 'NVIDIA System Management' in os.popen('nvidia-smi -h').read():
        print("'nvidia-smi' tool not found.", file=sys.stderr)
        return False
    return True

def parse(line,qargs):
    numberic_args = ['memory.free', 'memory.total', 'power.draw', 'power.limit']
    power_manage_enable=lambda v:(not 'Not Support' in v)
    to_numberic=lambda v:float(v.upper().strip().replace('MIB','').replace('W',''))
    process = lambda k,v:((int(to_numberic(v)) if power_manage_enable(v) else 1) if k in numberic_args else v.strip())
    return {k:process(k,v) for k,v in zip(qargs,line.strip().split(','))}

def query_gpu(qargs=[], usable_idx=None, memory_at_least=None):
    qargs =['index','gpu_name', 'memory.free', 'memory.total', 'power.draw', 'power.limit']+ qargs
    cmd = 'nvidia-smi --query-gpu={} --format=csv,noheader'.format(','.join(qargs))
    results = os.popen(cmd).readlines()

    gpus = []
    for line in results:
        gpu = parse(line,qargs)
        usable = True

        if usable_idx and gpu['index'] not in usable_idx:
            usable = False
        if memory_at_least and gpu['memory.free'] < memory_at_least:
            usable = False

        if usable:
            gpus.append(gpu)

    return gpus

def by_power(d):
    power_infos=(d['power.draw'],d['power.limit'])
    if any(v==1 for v in power_infos):
        print('Power management unable for GPU {}'.format(d['index']), file=sys.stderr)
        return 1
    return float(d['power.draw'])/d['power.limit']

class GPUManager():
    def __init__(self,qargs=[],usable_idx=None,memory_at_least=None):
        self.qargs=qargs
        self.usable_idx=usable_idx
        self.memory_at_least=memory_at_least

        if self.usable_idx:
            print('User restricts usable GPU index to {}'.format(self.usable_idx), file=sys.stderr)

        self.gpus=query_gpu(qargs,usable_idx,self.memory_at_least)
        for gpu in self.gpus:
            gpu['specified']=False

        self.gpu_num=len(self.gpus)

    def _sort_by_memory(self,gpus,by_size=False):
        if by_size:
            print('Sorted by free memory size', file=sys.stderr)
            return sorted(gpus,key=lambda d:d['memory.free'],reverse=True)
        else:
            print('Sorted by free memory rate', file=sys.stderr)
            return sorted(gpus,key=lambda d:float(d['memory.free'])/ d['memory.total'],reverse=True)

    def _sort_by_power(self,gpus):
        return sorted(gpus,key=by_power)
    
    def _sort_by_custom(self,gpus,key,reverse=False,qargs=[]):
        if isinstance(key,str) and (key in qargs):
            return sorted(gpus,key=lambda d:d[key],reverse=reverse)
        if isinstance(key,type(lambda a:a)):
            return sorted(gpus,key=key,reverse=reverse)
        raise ValueError("The argument 'key' must be a function or a key in query args,please read the documention of nvidia-smi")

    def auto_choice(self, mode=0):
        for old_infos,new_infos in zip(self.gpus,query_gpu(self.qargs,self.usable_idx,self.memory_at_least)):
            old_infos.update(new_infos)
        unspecified_gpus=[gpu for gpu in self.gpus if not gpu['specified']] or self.gpus

        if len(unspecified_gpus) == 0:
            return None
        
        if mode==0:
            print('Choosing the GPU device has largest free memory...', file=sys.stderr)
            chosen_gpu=self._sort_by_memory(unspecified_gpus,True)[0]
        elif mode==1:
            print('Choosing the GPU device has highest free memory rate...', file=sys.stderr)
            chosen_gpu=self._sort_by_power(unspecified_gpus)[0]
        elif mode==2:
            print('Choosing the GPU device by power...', file=sys.stderr)
            chosen_gpu=self._sort_by_power(unspecified_gpus)[0]
        else:
            print('Given an unaviliable mode,will be chosen by memory', file=sys.stderr)
            chosen_gpu=self._sort_by_memory(unspecified_gpus)[0]
        chosen_gpu['specified']=True
        index=chosen_gpu['index']
        print('Using GPU {i}:\n{info}'.format(i=index,info='\n'.join([str(k)+':'+str(v) for k,v in chosen_gpu.items()])), file=sys.stderr)
        return int(index)

def get_gpu_running_process():
    cmd = 'nvidia-smi --query-compute-apps=pid --format=csv,noheader'
    results = os.popen(cmd).readlines()
    return results
    

def main(args):
    if check_gpus():
        running_process = get_gpu_running_process()
        running_process_cnt = len(running_process)
        if running_process_cnt >= args.process_limit:
            print('There are already {} (>= {})process running in GPU(s)'.format(running_process_cnt, args.process_limit), file=sys.stderr)
            return

        usable_idx = args.set.split(',') if args.set else None
        gm = GPUManager(usable_idx=usable_idx, memory_at_least=args.memory_at_least)
        gpu_idx = []
        for i in range(args.count):
            gpu = gm.auto_choice()
            if gpu != None:
                gpu_idx.append(str(gpu))
        print(','.join(gpu_idx))

if __name__ == '__main__':
    main(get_args())
