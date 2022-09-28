from . import utils

from BlackScholes import black_scholes
import numpy as np


class AbstractStrategy(object):
    """
    The strategy can not modify state of Amm and market
    """

    def __init__(self):
        self.amm = None
        self.currentMarket = None
        self.lastTradeSize = None


    def setAmm(self,amm):
        self.amm = amm

    def setMarket(self,market):
        self.currentMarket = market

    def getPnL(self,price):
        return 0

    def getDelta(self):
        return 0

    def getPerpetualDelta(self):
        return 0

    def expired(self):
        pass

    def getNewTradeSize(self):
        self.lastTradeSize = self.amm.collateralReserve
        return self.lastTradeSize

    def getLastTradeSize(self):
        return self.lastTradeSize

    def hedge(self,current_time, price, IV):
        pass

class DeltaAbstractHedgeStrategy(AbstractStrategy):

    def __init__(self,interval):
        super().__init__()
        self.interval = interval
        self.lasthedged = utils.start_time
        self.perpetual = utils.Perpetual()

    def getPnL(self,price):
        return self.perpetual.getPnL(price)

    def getDelta(self):
        # return relative delta of perpetual position
        # We need to do a trade
        if self.getLastTradeSize() is not None:
            return self.perpetual.getPositionSize()/self.getLastTradeSize()
        return 0

    def expired(self):
        self.perpetual.closeAll()

    def hedge(self,current_time):
        pass

    def canHedge(self,current_time):
        if (current_time - self.lasthedged) < self.interval:
            return False
        self.lasthedged = current_time
        return True
        
        
class DeltaIntervalHedgeStrategy(DeltaAbstractHedgeStrategy):
    def __init__(self,interval, target_delta, range):
        super().__init__(interval)
        self.target_delta = target_delta
        self.range = range

    def hedge(self,current_time, price, IV):
        if not self.canHedge(current_time):
            return
        # Do hedging
        tradeSize = self.getLastTradeSize()
        delta = - black_scholes.black_scholes_delta_call(
            current_time.timestamp(),
            price,
            self.currentMarket.strike,
            self.currentMarket.expiration.timestamp(),
            IV)
        # We calculate relative delta to trade_size
        perDelta = self.perpetual.getPositionSize()/tradeSize

        # Now we do hedging 
        totalDelta = delta + perDelta
        diff = np.abs(totalDelta - self.target_delta)
        if  diff >= self.range:
            size = self.target_delta - totalDelta
            self.perpetual.addPosition(size*tradeSize, price)


class DeltaNonPositiveHedgeStrategy(DeltaAbstractHedgeStrategy):
    def __init__(self, interval, max_negative):
        super().__init__(interval)
        self.max_negative = max_negative

    def hedge(self,current_time, price, IV):
        if not self.canHedge(current_time):
            return
        tradeSize = self.getLastTradeSize()
        delta = - black_scholes.black_scholes_delta_call(
            current_time.timestamp(),
            price,
            self.currentMarket.strike,
            self.currentMarket.expiration.timestamp(),
            IV)
        # We calculate relative delta to trade_size
        perDelta = self.perpetual.getPositionSize()/tradeSize

        # Now we do hedging 
        totalDelta = delta + perDelta
        if totalDelta >= 0:
            # We need to sell, because we hold too much of perpetuals
            self.perpetual.addPosition(-totalDelta*tradeSize, price)

        if totalDelta <= self.max_negative:
            size = totalDelta - self.max_negative
            self.perpetual.addPosition(-size*tradeSize, price)


