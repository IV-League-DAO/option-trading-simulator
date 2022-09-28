import numpy as np

from py_vollib.black_scholes import black_scholes as bs
from py_vollib.black_scholes.greeks.analytical import delta,gamma,vega

def black_scholes(timestamp: float, underlying_price: float, strike: float, expiration: float, volatility: float, option):
    S = underlying_price
    K = strike
    T = max(expiration - timestamp, 0) /(86400*365)
    v = volatility

    if option == 'call':
        option = 'c'
    if option == 'put':
        option = 'p'

    return bs(option,S,K,T,0,v)

    
def black_scholes_vega_call(timestamp: float, underlying_price: float, strike: float, expiration: float, volatility: float):
    S = underlying_price
    K = strike
    T = max(expiration - timestamp, 0) /(86400*365)
    v = volatility

    return vega('c',S,K,T,0,v) 
    
def black_scholes_delta_call(timestamp: float, underlying_price: float, strike: float, expiration: float, volatility: float):
    S = underlying_price
    K = strike
    T = max(expiration - timestamp, 0) /(86400*365)
    v = volatility     

    return delta('c',S,K,T,0,v)

def black_scholes_delta_put(timestamp: float, underlying_price: float, strike: float, expiration: float, volatility: float):
    S = underlying_price
    K = strike
    T = max(expiration - timestamp, 0) /(86400*365)
    v = volatility 
    return delta('p',S,K,T,0,v)

def strike_for_delta_call(target_delta: float, timestamp: float, underlying_price: float, expiration: float, volatility: float):
    low, high = 0, 10*underlying_price
    eps = 0.01
    while True:
        strike = low + (high - low)/2
        curr_call_delta = black_scholes_delta_call(timestamp, underlying_price, strike, expiration, volatility)
        if np.abs(curr_call_delta - target_delta) <= eps:
            digits_to_round = int(np.trunc(np.log10(strike)))
            strike_t = trunc(strike,decimals=1 - digits_to_round)
            strike_c = ceil(strike, decimals=1 - digits_to_round)
            delta_t = black_scholes_delta_call(timestamp, underlying_price, strike_t, expiration, volatility)
            delta_c = black_scholes_delta_call(timestamp, underlying_price, strike_c, expiration, volatility)
            diff_t = np.abs(delta_t - target_delta)
            diff_c = np.abs(delta_c - target_delta)
            if diff_c < diff_t:
                return strike_c
            else:
                return strike_t
        if curr_call_delta > target_delta:
            low = strike
        else:
            high = strike
    
def strike_for_delta_put(target_delta: float, timestamp: float, underlying_price: float, expiration: float, volatility: float):
    low, high = 0, 10*underlying_price
    eps = 0.01
    while True:
        strike = low + (high - low)/2
        curr_put_delta = black_scholes_delta_put(timestamp, underlying_price, strike, expiration, volatility)
        if np.abs(curr_put_delta - target_delta) <= eps:
            digits_to_round = int(np.trunc(np.log10(strike)))
            strike_t = trunc(strike,decimals=1 - digits_to_round)
            strike_c = ceil(strike, decimals=1 - digits_to_round)
            delta_t = black_scholes_delta_put(timestamp, underlying_price, strike_t, expiration, volatility)
            delta_c = black_scholes_delta_put(timestamp, underlying_price, strike_c, expiration, volatility)
            diff_t = np.abs(delta_t - target_delta)
            diff_c = np.abs(delta_c - target_delta)
            if diff_c < diff_t:
                return strike_c
            else:
                return strike_t
        if curr_put_delta < target_delta:
            high = strike
        else:
            low = strike

def ceil(x, decimals = 0):
    return np.ceil(x*10**decimals)/10**decimals

def trunc(x, decimals = 0): 
    return np.trunc(x*10**decimals)/10**decimals