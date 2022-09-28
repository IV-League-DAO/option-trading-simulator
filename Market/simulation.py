

import os
import pandas as pd
import numpy as np
import sys
import datetime
from datetime import timedelta

currentdir = os.path.dirname(os.getcwd())
sys.path.insert(0,currentdir)

from BlackScholes import black_scholes
from Market import amm_market, utils

# Simulation of perpetual
# Position ->
def simulation(
    epoch_id,
    price_series,
    implied_vol_series,
    start_time,
    collateralReserve,
    my_strategy,
    min_iv = 0.0,
    target_delta = 0.1,
    isPut=False
    ):
    df = []
    pool_value = []
    ivTooLow = False
    if isPut:
        optionType = 'put'
    else:
        optionType = 'call'


    # We move to closest friday at 8:00 UTC from_start_time
    # and print the difference
    current_time = utils.get_next_expiry(start_time)
    #print("Moving to 8:00 UTC friday as start time", current_time - start_time)
    #start_time = current_time


    IV = implied_vol_series[current_time]
    amm = amm_market.MinterAmm(collateralReserve, 0.0, [], IV, 0, current_time.timestamp())

    my_strategy.setAmm(amm)
    my_strategy.getNewTradeSize() # We init trade_size
    trade_size = np.NaN
    theoretical_price = np.NaN

    #convert To numpy to speed up
    price_series = price_series[current_time:].to_numpy()
    implied_vol_series = implied_vol_series[current_time:].to_numpy()

    

    # implied_vol_series.indexes[-1] is end time
    for i in range(implied_vol_series.size):
        price = price_series[i]
        IV = implied_vol_series[i]
        amm.setTimestamp(current_time)
        amm.setCurrentPrice(price)
        # If its friday do a direct buy and settle your current options if they are ITM
        settledPoolValue = np.NaN
        buyerShare = np.NaN
        writerShare = np.NaN

        # Here we hedge our deltas with perpetuals
        perDelta = np.NaN
        perPnL = np.NaN
        # The first run have to be friday and we setup market!!!!!!!
        if utils.is_expiration(current_time):
            ivTooLow = False
            # we calculate PnL from hedging
            perPnL = my_strategy.getPnL(price)
            _, buyerShares, writerShares = amm.settle(optionType,perPnL)
            if len(buyerShares) > 1 or len(writerShares) > 1:
                raise ValueError("We should have just one market")
            if len(buyerShares) > 0:
                buyerShare = buyerShares[0]
            if len(writerShares) > 0:
                writerShare = writerShares[0]
            settledPoolValue = amm.collateralReserve

            # We close the remaining positions
            my_strategy.expired()
            perDelta = my_strategy.getDelta() 

            # We do not sell below some value
            if IV < min_iv:
                ivTooLow = True
            else: 
                expiration = utils.get_next_expiry(current_time + datetime.timedelta(days=1)) # we have to move to the next week to calculate expiration
                if isPut:
                    strike = black_scholes.strike_for_delta_put(target_delta, current_time.timestamp(), price, expiration.timestamp(), IV)
                else:
                    strike = black_scholes.strike_for_delta_call(target_delta, current_time.timestamp(), price, expiration.timestamp(), IV)
                market = amm_market.Market(strike, expiration)
                amm.addMarkets([market])


                #trade_size from strategy
                #trade_size = amm.collateralReserve
                trade_size = my_strategy.getNewTradeSize()

                market_index = len(amm.markets) - 1
                market = amm.markets[market_index]
                theoretical_price = black_scholes.black_scholes(current_time.timestamp(), price, market.strike, market.expiration.timestamp(), IV, optionType) / price
                payment_amount = trade_size * theoretical_price
                amm.bTokenBuyDirect(market_index, trade_size, payment_amount, optionType)

                #strategyUpdate
                my_strategy.setMarket(market)


        if not ivTooLow:
            # we hedge here
            trade_size = my_strategy.getLastTradeSize()
            my_strategy.hedge(current_time, price, IV)
            perPnL = my_strategy.getPnL(price)
            perDelta = my_strategy.getDelta()
          


        # Consolidate results

        poolValue = amm.collateralReserve
        poolPositionDelta = 0
        poolExposure = 0
        bBalance = np.NaN
        wBalance = np.NaN
        strike = np.NaN
        market_index = np.NaN
        if not ivTooLow:
            # get value of all open markets
            #eps = np.finfo(np.longdouble).eps
            #toRound = -int(np.log(eps))
            market_index = len(amm.markets) - 1
            m = amm.markets[market_index]
            bTokenPrice = black_scholes.black_scholes(current_time.timestamp(), price, m.strike, m.expiration.timestamp(), IV, optionType)
            bPrice =  bTokenPrice/ price
            wPrice = 1 - bPrice
            bBalance = amm.bTokenBalance(market_index)
            wBalance = amm.wTokenBalance(market_index)
            poolValue += bPrice * bBalance + wPrice * wBalance
            if isPut:
                marketPositionDelta = - black_scholes.black_scholes_delta_put(current_time.timestamp(), price, m.strike, m.expiration.timestamp(), IV)
            else:
                marketPositionDelta = - black_scholes.black_scholes_delta_call(current_time.timestamp(), price, m.strike, m.expiration.timestamp(), IV) 
            poolPositionDelta += marketPositionDelta
            poolExposure += amm.getExposure(market_index)

            strike = market.strike


        df.append([current_time,
            epoch_id,
            market_index,
            trade_size,
            IV,
            bBalance,
            wBalance,
            price,
            theoretical_price,
            strike,
            poolPositionDelta,
            perDelta]
        )
        
        pool_value.append([
            current_time,
            epoch_id, 
            poolValue * price,
            poolValue,
            perPnL,
            settledPoolValue,
            buyerShare,
            writerShare,
            amm.collateralReserve
        ])

        # at the end we inceremnt time
        current_time += timedelta(hours=1)

        ############# end for loop ################### 


    df = pd.DataFrame(df, columns=[ 'date',
        'epoch_id', 'market_index', 'volume_buy', 'implied_vol','reserve_b','reserve_w','underlying_price',
        'theoretical_price', 'strike', 'pool_position_delta', 'per_position_delta'
    ])
    pool_value = pd.DataFrame(pool_value,columns=[
        'date','epoch_id',
        'pool_value_usd', 'pool_value', 'hedge_value','settled_pool_value',
        'buyerShare', 'writerShare','collateral_reserve'
    ])
    df = df.set_index('date')
    pool_value = pool_value.set_index('date')
    return df, pool_value