import os,sys
import numpy as np
import pandas as pd
import datetime
from joblib import Parallel, delayed
import itertools 
import argparse
import inspect
import pickle


currentdir = os.path.dirname(os.getcwd())
sys.path.insert(0,currentdir)

from BlackScholes import volatility,eth_price_simulation
from Market import simulation, strategy, utils


strategies = list(filter(lambda x: inspect.isclass(x[1]),inspect.getmembers(strategy)))


# input median for normal returns
def YtHmu(mu):
    return np.log(mu)/(365*24)
# input std in log normal
def YtHsigma(sigma):
    return sigma/np.sqrt(365*24)


def run_simulation(flag, paths, mu,sigma, ivC,minIV, p0, collateralReserve,sample_length, strategy_setup):
    print('#'*30)
    print(flag, mu, sigma,p0)

    unStdPaths = [eth_price_simulation.unstandardized_returns(path,YtHmu(mu), YtHsigma(sigma)) for path in paths]
    prices = [eth_price_simulation.get_price_np(path,p0) for path in unStdPaths]
    start_time = utils.start_time
    dateRange = pd.date_range(start=str(start_time), end=str(start_time + datetime.timedelta(hours=sample_length)), freq='1H',tz=datetime.timezone.utc)

    unStdPaths = pd.DataFrame(unStdPaths).T
    unStdPaths['date'] = dateRange[1:]
    unStdPaths = unStdPaths.set_index(unStdPaths['date']).drop(['date'],axis=1)

    prices = pd.DataFrame(prices).T
    prices['date'] = dateRange
    prices = prices.set_index(prices['date']).drop(['date'],axis=1)
    
    ivs = []
    dfs = []
    pool_values = []
    selected_strategy,strategyArgs, targetDelta = strategy_setup
    for epoch_id in range(len(paths)):
        rv = volatility.calculateRV(prices[epoch_id],utils.IV_WINDOW,24)
        iv = volatility.calculateIVConstant(rv,ivC, 2.7)
        start_timestamp = iv.index[0]
        my_strategy = dict(strategies)[selected_strategy](*strategyArgs)
        if flag == 'c' or flag == 'p':
            df, pool_value = simulation.simulation(
                    epoch_id, 
                    prices[epoch_id], 
                    iv, 
                    start_timestamp,
                    collateralReserve,
                    my_strategy,
                    min_iv = minIV,
                    target_delta = targetDelta,
                    isPut=flag == 'p')
        else:
            raise ValueError("Invalid flag")
        ivs.append(iv)
        dfs.append(df)
        pool_values.append(pool_value)
    return unStdPaths, prices, pd.concat(dfs), pd.concat(pool_values) 


def job(params,paths,ivC,minIV,p0,initcollateralReserve,sample_length,saveDir,strategy_setup):
        flag, dist = params
        mu, sigma = dist
        selected_strategy,_, _ = strategy_setup 
        unStdPaths, prices, dfs,pool_values = run_simulation(flag,paths,mu,sigma,ivC,minIV,p0,initcollateralReserve,sample_length,strategy_setup)
        unStdPaths.to_csv(f'{saveDir}/unStdPaths-{selected_strategy}-{paths.shape[0]}-{flag}-{mu}-{sigma}.csv')
        prices.to_csv(f'{saveDir}/prices-{selected_strategy}-{paths.shape[0]}-{flag}-{mu}-{sigma}.csv') 
        dfs.to_csv(f'{saveDir}/dfs-{selected_strategy}-{paths.shape[0]}-{flag}-{mu}-{sigma}.csv')
        pool_values.to_csv(f'{saveDir}/pool_values-{selected_strategy}-{paths.shape[0]}-{flag}-{mu}-{sigma}.csv')

def parseStrategyArgs(args):
    out = []
    for x in args:
        var, t = x.split(':')
        if t == 'str':
            out.append(var)
        elif t == 'int':
            out.append(int(var))
        elif t == 'float':
            out.append(float(var))
        elif t == 'h':
            out.append(datetime.timedelta(hours=int(var)))
        else:
            raise ValueError("Invalid type")
    return out


def main(args):
    print(args)
    sample_length = utils.SAMPLE_LENGTH
    p0 = args.initPrice
    ivC = args.ivc
    initcollateralReserve = 10e8
    cores = args.cores
    targetDelta = args.targetDelta

    dists = list(zip(args.mus, args.sigmas))
    minIV = args.minIV
    flags = []
    if args.calls:
        flags.append('c')
    if args.puts:
        flags.append('p')

    strategyArgs = parseStrategyArgs(args.strategyArgs)
    print("[*] Args strategy: ",strategyArgs)
    strategy_setup = (args.strategy, strategyArgs,targetDelta) 
    with open(args.runs, 'rb') as handle:
        paths = pickle.load(handle)
    Parallel(n_jobs=cores,verbose=100,backend='multiprocessing')(delayed(job)(params,paths,ivC,minIV,p0,initcollateralReserve,sample_length,args.saveDir,strategy_setup) for params in itertools.product(flags,dists))
    
    

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mus', action='store',
                    type=float, nargs='+',required=True,
                    help="Log APY: -m 0.1 1")
    parser.add_argument('-s', '--sigmas', action='store',
                    type=float, nargs='+', required=True,
                    help="Volatility: -s 0.1 1")
    parser.add_argument("-c", "--cores", default=2,type=int,help="Number of cores to use (do not include virtuals)")
    parser.add_argument("--saveDir", default='output',type=str,help="Where to save the outputs")
    parser.add_argument("-r", "--runs",required=True,type=str, help="pickle file of runs")
    parser.add_argument("--strategy",required=True,choices=list(map(lambda x:x[0],strategies)), help="strategy")
    parser.add_argument("--strategyArgs", nargs="*", default=[], help="Arguments to startegy: 1.2:float \"asd:str\" 1:int")
    parser.add_argument("--ivc", default=0.05,type=float, help="IV premium/constant added to Realized Volatility 30 day window")
    parser.add_argument("--minIV", default=0.00,type=float, help="Minimal IV for selling option")
    parser.add_argument("--initPrice", default=2000,type=float, help='InitialPrice for simulation')
    parser.add_argument("--targetDelta", default=0.1,type=float, help='Simulation finds closest Strike price, whichs delta is closed to the targetDelta')
    group = parser.add_argument_group(title='Option type')
    group.add_argument("--calls", help="find calls",
                    action="store_true")
    group.add_argument("--puts", help="find puts",
                    action="store_true")
    args = parser.parse_args()
    if not args.calls and not args.puts:
        parser.error("Option type required")
    if args.calls and args.puts:
        parser.error("Just One option type must be specified")
    if args.calls and not (0.0 <= args.targetDelta <= 1.0):
        parser.error("Terget delta for calls has to be in <0,1> interval")
    if args.puts and not (-1.0 <= args.targetDelta <= 0.0):
        parser.error("Terget delta for puts has to be in <-1,0> interval")
    main(args)

