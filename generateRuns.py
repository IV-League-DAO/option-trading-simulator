import os,sys
import numpy as np
import pandas as pd
from tqdm import tqdm
import argparse
import pickle 
currentdir = os.path.dirname(os.getcwd())
sys.path.insert(0,currentdir)
from BlackScholes import eth_price_simulation
from Market import utils





# input median for normal returns
def YtHmu(mu):
    return np.log(mu)/(365*24)
# input std in log normal
def YtHsigma(sigma):
    return sigma/np.sqrt(365*24)


def loadStdReturns(file):
    eth = pd.read_csv(file)
    df_eth = eth.sort_values('date')

    # we need to drop 0 values at first line !!!!
    df_eth = df_eth.iloc[1:].reset_index(drop=True)
    eth_returns = eth_price_simulation.log_returns(df_eth.open,1)
    eth_returns = eth_returns.astype(np.longdouble)
    return eth_price_simulation.standardized_returns(eth_returns)


def genReturns(stdDistRet, num_paths,sample_length,**kwargs):
    min_connected=kwargs.get('min_connected',1)
    max_connected=kwargs.get('max_connected',3)
    with_replacement=kwargs.get('with_replacement',0)
    paths = []
    for i in tqdm(range(num_paths),total=num_paths):
        ret =  eth_price_simulation.create_sample_path(
        list(stdDistRet),
        sample_length = sample_length,
        min_connected_original = min_connected,
        max_connected_original = max_connected,
        with_replacement = with_replacement)
        paths.append(ret)
    return np.array(paths,dtype=np.longdouble)


    
def main(args):
    print(args)
    stdDistRet = loadStdReturns(args.pricesFile)
    sample_length = 365*24 + utils.IV_WINDOW*24
    samples = args.paths


    paths = genReturns(stdDistRet,samples,sample_length,
        min_connected=24,
        max_connected=24*3,
        with_replacement=0)
    paths = np.array(paths)
    with open(f'{args.saveDir}/{samples}.pickle', 'wb') as handle:
        pickle.dump(paths, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--saveDir", default='runGen',type=str,help="Where to save the outputs")
    parser.add_argument("-p", "--paths", default=3000,type=int, help="Number of paths per simulation")
    parser.add_argument("--pricesFile", required=True,type=str,help="1h price data")
    args = parser.parse_args()
    main(args)

