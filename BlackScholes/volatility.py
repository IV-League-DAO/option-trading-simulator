import numpy as np

def log_returns(price_series,interval):
    return (np.log(price_series/
    price_series.shift(interval))).dropna()

def calculateRV(data, window, factor):
  # data -> date start from top to bottom
  # 0 idx -> oldest price
  # last idx -> newest price
  logPrices = log_returns(data,1)
  RV = logPrices.rolling(window*factor).std(ddof=0)*np.sqrt(factor*365)
  RV = RV.dropna()
  return RV

def calculateIVConstant(RV, c,clap):
  return np.minimum(RV + c,clap)

