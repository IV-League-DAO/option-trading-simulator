import pandas as pd
import numpy as np
import random

def log_returns(price_series,interval):
    return (np.log(price_series/
    price_series.shift(interval))).dropna()

def standardized_returns(returns):
    mu=np.mean(returns)
    sig = np.std(returns)
    return (returns-np.repeat(mu,len(returns)))/sig

def unstandardized_returns(returns, mu,sig):
    tmp = np.array(returns,dtype=np.longdouble)*sig+mu
    return tmp
    #return np.where(tmp > -1, tmp, -0.99999)
    #return [x if x> -1 else -0.99 for x in tmp]

def get_price_series(returns,p0):
    tmp=[]
    for j in range(0,len(returns)+1):
        if(j == 0):
            tmp.append(p0)
        else:
            tmp.append(tmp[-1]*np.exp(returns[j-1]))
    return tmp

def get_price_np(arr,p0):
    prices = np.exp(np.cumsum(arr))*p0
    return np.insert(prices,0,p0)

def create_sample_path(returns, **kwargs):
    sample_length=kwargs.get('sample_length',10) #desired length of output sample 
    min_connected_original=kwargs.get('min_connected_original',1) #minimum amount of subsequent datapoints that are drawn together
    max_connected_original=kwargs.get('max_connected_original',1) #see above, but upper limit - should be interval where autocorrelation is insignificant
    with_replacement = kwargs.get('with_replacement',1) #draw with (1) or without (0) replacement from original sample

    length = 0
    sample_path=[]
    
    if (with_replacement==0) & (sample_length >= len(returns)):
        print('Cant do without replacement to achieve sample length, do with replacement')
        with_replacement = 1

    returns_copy = returns.copy() 
    while length < sample_length:
        this_length = random.randint(min_connected_original,max_connected_original)
        if length + this_length>sample_length:
            this_length = sample_length-length

        start = random.randint(1,len(returns_copy)-this_length)
        sample_path += returns_copy[start:start+this_length]
        if with_replacement==0:
            del returns_copy[start:start+this_length]
        length += this_length
    
    return sample_path

def make_df_price_simulation(series_returns,num_paths,sample_length, p0, **kwargs):
    #creates simulated pathes based on input timeseries
    #series_returns: input timeseries of log returns
    #num_paths: how many paths we want to simulate
    #sample_length: length of each path (in timesteps of input timeseries)
    #p0: initial price of simualated price series
    
    #mu: average log-returns should be in same scale as series_returns!!! 1h to 1h, or 1y to 1y
    #sigma:  drift of log-returns should be in same scale as series_returns!!! 1h to 1h, or 1y to 1y
    #return_df: what format shall be returned:
    #   just simulated price paths -> return_df='prices'
    #   just simulated log returns -> return_df='returns'
    #   just simulated standardized returns -> return_df='std_returns'
    #   all of the above dataframes (as dictionary) -> return_df='' (default)
    #min_connected: minimum length of timesteps (of input timeseries) that are drawn as block from initial series of returns (to preserve parts of the Autocorrelation of the input timeseries)
    #max_connected: same as above, but the max length of timesteps (should be interval where autocorrelation is insignificant). The actual  length of timesteps drawn together as block is a random integer (uniform) between min and max
    #with_replacement: draw with (1) or without (0) replacement from original sample

    
    mu = kwargs.get('mu',1) # We will use our mu, not adjusting
    sigma = kwargs.get('sigma',1) # We will use our sigma, not adjusting
    return_df=kwargs.get('return_df','')
    min_connected=kwargs.get('min_connected',1)
    max_connected=kwargs.get('max_connected',3)
    with_replacement=kwargs.get('with_replacement',1)

    dct_prices={}
    dct_returns={}
    dct_std_returns={}

    

    
    series_std_returns=standardized_returns(series_returns)

    for j in range(num_paths):
            
        sample_std_returns = create_sample_path(list(series_std_returns),
                                        sample_length = sample_length,
                                        min_connected_original = min_connected,
                                        max_connected_original = max_connected,
                                        with_replacement = with_replacement)
        sample_returns=unstandardized_returns(sample_std_returns,mu,sigma) # we will use our distribution
        dct_returns[str(j)]=sample_returns
        dct_std_returns[str(j)]=sample_std_returns
        dct_prices[str(j)] = get_price_series(sample_returns,p0)

    df_prices=pd.DataFrame.from_dict(dct_prices)
    df_returns = pd.DataFrame.from_dict(dct_returns)
    df_std_returns =pd.DataFrame.from_dict(dct_std_returns)

    if return_df =='prices':
        return df_prices
    elif return_df=='returns':
        return df_returns
    elif return_df=='std_returns':
        return df_std_returns
    else:
        return {'df_prices':df_prices,
            'df_returns':df_returns,
            'df_std_returns':df_std_returns}



