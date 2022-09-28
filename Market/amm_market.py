import math
from BlackScholes import black_scholes
class Market:
    strike = None
    expiration = None
    
    def __init__(self, strike, expiration):
        self.strike = strike
        self.expiration = expiration
        
    def getSettlementAmounts(self, settlementPrice, option):
        if (option == 'call'):
            if (settlementPrice <= self.strike):
                # OTM
                writerShare = 1.0;
                buyerShare = 0.0;
            else:
                # ITM
                writerShare = self.strike / settlementPrice
                buyerShare = 1.0 - writerShare
        else:
            
            if (settlementPrice >= self.strike):
                # OTM
                writerShare = self.strike;
                buyerShare = 0.0;
            else:
                # ITM
                writerShare = settlementPrice 
                buyerShare = self.strike - writerShare
            
        return buyerShare, writerShare
    
    def __str__(self):
        return "Strike: {}, Expiration Date: {} \n".format(self.strike, self.expiration)

class MinterAmm:
    markets = []
    bTokenReserve = []
    wTokenReserve = []
    collateralReserve = 0.0
    feePercent = 0.0
    settledMarkets = []
    currentPrice = None
    timestamp = None
    IV = None
    targetIV = None
    ivUpdated = None
    ivDecayRate = None
    impactMultiplier = None
    accruedFees = 0.0
    
    def __init__(self, collateralReserve, feePercent, markets, targetIV, ivDecayRate, timestamp):
        self.markets = markets
        self.bTokenReserve = [0.0 for i in range(len(markets))]
        self.wTokenReserve = [0.0 for i in range(len(markets))]
        self.settledMarkets = [False for i in range(len(markets))]
        self.IV = [targetIV for i in range(len(markets))]
        self.timestamp = timestamp
        self.ivUpdated = [timestamp for i in range(len(markets))]
        self.targetIV = targetIV
        self.collateralReserve = collateralReserve
        self.feePercent = feePercent
        self.ivDecayRate = ivDecayRate
        
    def setCurrentPrice(self, price):
        self.currentPrice = price
        
    def addMarkets(self, markets):
        index = len(self.markets)
        for market in markets:    
            self.markets.append(market)
            self.IV.append(self.targetIV)
            self.bTokenReserve.append(0.0)
            self.wTokenReserve.append(0.0)
            self.ivUpdated.append(self.timestamp.timestamp())
            self.settledMarkets.append(False)
    
    def setTimestamp(self, timestamp):
        self.timestamp = timestamp  
        
    def setTargetIV(self, targetIV):
        self.targetIV = targetIV    
        
    # Return IV for a market with decay
    def getCurrentIV(self, marketIndex):
        # the iv is quoted in seconds
        iv = self.IV[marketIndex]
        # decay = self.getExposure(marketIndex) * self.ivDecayRate * (self.timestamp.timestamp() - self.ivUpdated[marketIndex])
        decay = self.ivDecayRate * (self.timestamp.timestamp() - self.ivUpdated[marketIndex])
        
        if iv < self.targetIV:
            return min(self.targetIV, iv + decay)
        else:
            return max(self.targetIV, iv - decay)
    
    def updateIV(self, marketIndex, priceWithSlippage, optionType):
        market = self.markets[marketIndex]
        spotPrice = self.getPriceForMarket(marketIndex, optionType)
                
        currentIV = self.getCurrentIV(marketIndex) * math.sqrt(86400*365)        
        
        # vega - change in price based on change in iv
        vega = black_scholes.black_scholes_vega_call(self.timestamp.timestamp(), self.currentPrice,  market.strike, market.expiration.timestamp(), currentIV)/self.currentPrice
        # vega = max(vega, 1e-4)
        
        # change IV to reflect the slippage
        priceDiff = priceWithSlippage - spotPrice
                
        newIV = (currentIV + priceDiff / vega) / math.sqrt(86400*365)
        
        #if newIV > 0.000356:
        #    print('High IV:', newIV, priceWithSlippage, spotPrice, vega, self.collateralReserve, self.timestamp, market.expiration, self.getCurrentIV(marketIndex), self.currentPrice)
        
        # min 20%, max 200%
        self.IV[marketIndex] = max(min(newIV, 0.000356), 0.0000356)
        self.ivUpdated[marketIndex] = self.timestamp.timestamp()
        
    def getVirtualReserves(self, marketIndex, optionType):
        bTokenBalance = self.bTokenBalance(marketIndex)
        wTokenBalance = self.wTokenBalance(marketIndex)
        
        bTokenBalanceMax = bTokenBalance + self.collateralReserve
        wTokenBalanceMax = wTokenBalance + self.collateralReserve
        
        bTokenPrice = self.getPriceForMarket(marketIndex, optionType)
        wTokenPrice = 1.0 - bTokenPrice
        
        bTokenVirtualBalance = 0.0
        wTokenVirtualBalance = 0.0
        
        if (bTokenPrice <= wTokenPrice):
            # Rb >= Rw, Pb <= Pw
            bTokenVirtualBalance = bTokenBalanceMax
            wTokenVirtualBalance = bTokenVirtualBalance * bTokenPrice / wTokenPrice
            # Sanity check that we don't exceed actual physical balances
            # In case this happens, adjust virtual balances to not exceed maximum
            # available reserves while still preserving correct price
            if (wTokenVirtualBalance > wTokenBalanceMax):
                wTokenVirtualBalance = wTokenBalanceMax
                bTokenVirtualBalance = wTokenVirtualBalance * wTokenPrice / bTokenPrice
        else:
            # if Rb < Rw, Pb > Pw
            wTokenVirtualBalance = wTokenBalanceMax
            bTokenVirtualBalance = wTokenVirtualBalance * wTokenPrice / bTokenPrice

            # Sanity check
            if (bTokenVirtualBalance > bTokenBalanceMax):
                bTokenVirtualBalance = bTokenBalanceMax
                wTokenVirtualBalance = bTokenVirtualBalance * bTokenPrice / wTokenPrice
        
        return bTokenVirtualBalance, wTokenVirtualBalance
    
    def getPriceForMarket(self, marketIndex, optionType):
        market = self.markets[marketIndex]
        iv = self.getCurrentIV(marketIndex)*math.sqrt(86400*365)
        price = black_scholes.black_scholes(self.timestamp.timestamp(), self.currentPrice,  market.strike, market.expiration.timestamp(),iv, optionType )/self.currentPrice
        # set lower bound on option price
        return price # max(price, 0.0001)
        
    # sell bToken    
    def bTokenGetCollateralOut(self, marketIndex, bTokenAmount, optionType):
        bTokenBalance, wTokenBalance = self.getVirtualReserves(marketIndex, optionType)
        toSquare = bTokenAmount + bTokenBalance + wTokenBalance;
        collateralAmount = (toSquare - (math.sqrt(toSquare ** 2 - (bTokenAmount * wTokenBalance * 4)))) / 2
        
        fee = self.calcFee(bTokenAmount, collateralAmount)
        return collateralAmount - fee, fee
    
    # buy bToken
    def bTokenGetCollateralIn(self, marketIndex, bTokenAmount, optionType):
        bTokenBalance, wTokenBalance = self.getVirtualReserves(marketIndex, optionType)

        sumBalance = bTokenBalance + wTokenBalance
        if sumBalance > bTokenAmount:
            toSquare = sumBalance - bTokenAmount;
        else:
            toSquare = bTokenAmount - sumBalance;

        collateralAmount = (math.sqrt(
            toSquare ** 2 + (bTokenAmount * wTokenBalance * 4)
        ) + bTokenAmount - bTokenBalance - wTokenBalance) / 2
        
        fee = self.calcFee(bTokenAmount, collateralAmount)
        return collateralAmount + fee, fee
    
    # sell wToken
    def wTokenGetCollateralOut(self, marketIndex, wTokenAmount, optionType):
        bTokenBalance, wTokenBalance = self.getVirtualReserves(marketIndex, optionType)
        toSquare = wTokenAmount + wTokenBalance + bTokenBalance;
        collateralAmount = (toSquare - (math.sqrt(toSquare ** 2 - (wTokenAmount * bTokenBalance * 4)))) / 2

        fee = self.calcFee(wTokenAmount, wTokenAmount - collateralAmount)
        return collateralAmount - fee, fee
                
    # buy wToken
    def wTokenGetCollateralIn(self, marketIndex, wTokenAmount, optionType):        
        bTokenBalance, wTokenBalance = self.getVirtualReserves(marketIndex, optionType)
        
        sumBalance = wTokenBalance + bTokenBalance
        toSquare = sumBalance - wTokenAmount        
        collateralAmount = (math.sqrt(
            toSquare ** 2 + (wTokenAmount * bTokenBalance * 4)
        ) + wTokenAmount - wTokenBalance - bTokenBalance) / 2
        
        fee = self.calcFee(wTokenAmount, wTokenAmount - collateralAmount)
        return collateralAmount + fee, fee
    
    def getSlippage(self, marketIndex, bTokenAmount, optionType, buy=True,):
        if buy:
            collateralAmount, fee = self.bTokenGetCollateralIn(marketIndex, bTokenAmount, optionType)
        else:
            collateralAmount, fee = self.bTokenGetCollateralOut(marketIndex, bTokenAmount, optionType)
        priceWithSlippage = collateralAmount / bTokenAmount 
        spotPrice = self.getPriceForMarket(marketIndex)
        return (priceWithSlippage / spotPrice - 1)*100
        
    def bTokenBuy(self, marketIndex, bTokenAmount, optionType):      
        if self.settledMarkets[marketIndex]: raise Exception("Market already settled")
            
        collateralAmount, fee = self.bTokenGetCollateralIn(marketIndex, bTokenAmount, optionType)
        self.collateralReserve += collateralAmount - fee
        self.accruedFees += fee
        
        bTokenBalance = self.bTokenBalance(marketIndex)
        
        # Mint tokens
        toMint = bTokenAmount - bTokenBalance
        if (toMint > 0):
            self.collateralReserve -= toMint
            self.bTokenReserve[marketIndex] += toMint
            self.wTokenReserve[marketIndex] += toMint
        
        self.bTokenReserve[marketIndex] -= bTokenAmount
        # Update IV
        self.updateIV(marketIndex, (collateralAmount - fee) / bTokenAmount)
        
        return collateralAmount

    def bTokenSell(self, marketIndex, bTokenAmount, optionType):  
        if self.settledMarkets[marketIndex]: raise Exception("Market already settled")
            
        priorExposure = self.getExposure(marketIndex)
        
        collateralAmount, fee = self.bTokenGetCollateralOut(marketIndex, bTokenAmount, optionType)
        self.collateralReserve -= collateralAmount + fee   
        self.accruedFees += fee
        
        self.bTokenReserve[marketIndex] += bTokenAmount
        
        bTokenBalance = self.bTokenBalance(marketIndex)
        wTokenBalance = self.wTokenBalance(marketIndex)
        
        # Close tokens
        toClose = min(bTokenBalance, wTokenBalance)
        if (toClose > 0):
            self.collateralReserve += toClose
            self.bTokenReserve[marketIndex] -= toClose
            self.wTokenReserve[marketIndex] -= toClose
            
        # Update IV
        self.updateIV(marketIndex, (collateralAmount + fee) / bTokenAmount)
                
        return collateralAmount
    
    def wTokenBuy(self, marketIndex, wTokenAmount):      
        if self.settledMarkets[marketIndex]: raise Exception("Market already settled")
            
        priorExposure = self.getExposure(marketIndex)
        
        collateralAmount, fee = self.wTokenGetCollateralIn(marketIndex, wTokenAmount)
        self.collateralReserve += collateralAmount - fee
        self.accruedFees += fee
        
        wTokenBalance = self.wTokenBalance(marketIndex)
        
        # Mint tokens
        toMint = wTokenAmount - wTokenBalance
        if (toMint > 0):
            self.collateralReserve -= toMint
            self.bTokenReserve[marketIndex] += toMint
            self.wTokenReserve[marketIndex] += toMint
        
        self.wTokenReserve[marketIndex] -= wTokenAmount
        
        # Update IV
        self.updateIV(marketIndex, 1 - (collateralAmount - fee) / wTokenAmount)
        
        return collateralAmount

    def wTokenSell(self, marketIndex, wTokenAmount, optionType):   
        if self.settledMarkets[marketIndex]: raise Exception("Market already settled")
            
        priorExposure = self.getExposure(marketIndex)
        
        collateralAmount, fee = self.wTokenGetCollateralOut(marketIndex, wTokenAmount, optionType)
        self.collateralReserve -= collateralAmount + fee        
        self.accruedFees += fee
        
        self.wTokenReserve[marketIndex] += wTokenAmount
        
        bTokenBalance = self.bTokenBalance(marketIndex)
        wTokenBalance = self.wTokenBalance(marketIndex)
        
        # Close tokens
        toClose = min(bTokenBalance, wTokenBalance)
        if (toClose > 0):
            self.collateralReserve += toClose
            self.bTokenReserve[marketIndex] -= toClose
            self.wTokenReserve[marketIndex] -= toClose
                
        # Update IV
        self.updateIV(marketIndex, 1 - (collateralAmount + fee) / wTokenAmount)
                
        return collateralAmount
    
    def bTokenBuyDirect(self, marketIndex, bTokenAmount, collateralAmount, option):
        self.collateralReserve += collateralAmount
        
        market = self.markets[marketIndex]
        
        bTokenBalance = self.bTokenBalance(marketIndex)
        
        # Mint tokens
        toMint = bTokenAmount - bTokenBalance
        if (toMint > 0):
            if(option == 'call'):
                self.collateralReserve -= toMint
            else:
                self.collateralReserve -= toMint * market.strike
            self.bTokenReserve[marketIndex] += toMint
            self.wTokenReserve[marketIndex] += toMint
        
        self.bTokenReserve[marketIndex] -= bTokenAmount
        
        return collateralAmount
        
        
    def bTokenBalance(self, marketIndex):
        return self.bTokenReserve[marketIndex]

    def wTokenBalance(self, marketIndex):
        return self.wTokenReserve[marketIndex]
        
    def getPriceB(self, marketIndex, deltaB, optionType):
        # Positive = sell, negative = buy
        collateralAmount, fee = self.bTokenGetCollateralOut(marketIndex, deltaB, optionType) if deltaB > 0 else self.bTokenGetCollateralIn(marketIndex, -deltaB, bTokenBuy)
        return collateralAmount / abs(deltaB)

    def getPriceW(self, marketIndex, deltaW, optionType):
        # Positive = sell, negative = buy
        collateralAmount, fee = self.wTokenGetCollateralOut(marketIndex, deltaW, optionType) if deltaW > 0 else self.wTokenGetCollateralIn(marketIndex, -deltaW)
        return collateralAmount / abs(deltaW)
    
    def getExposure(self, marketIndex):
        bBalance = self.bTokenBalance(marketIndex)
        wBalance = self.wTokenBalance(marketIndex)
        return bBalance - wBalance
    
    def calcFee(self, notionalAmount, collateralAmount):
        collateralFeeCap = 12.5
        notionalFee = notionalAmount * self.feePercent / 100
        collateralFee = collateralAmount * collateralFeeCap / 100
        
        return min(notionalFee, collateralFee)    
    
    def settle(self, option, hedged_value = 0):
        settledIV = []
        buyerShares = []
        writerShares = []
        self.collateralReserve+=hedged_value
        for i in range(len(self.markets)):
            market = self.markets[i]
            if not self.settledMarkets[i] and market.expiration <= self.timestamp:
                # print("Settled")
                bBalance = self.bTokenBalance(i)
                wBalance = self.wTokenBalance(i)
                buyerShare, writerShare = market.getSettlementAmounts(self.currentPrice, option)
                #print(buyerShare, writerShare)
                self.collateralReserve += bBalance * buyerShare + wBalance * writerShare
                self.bTokenReserve[i] = 0.0
                self.wTokenReserve[i] = 0.0
                self.settledMarkets[i] = True
                settledIV.append(self.getCurrentIV(i))
                buyerShares.append(buyerShare)
                writerShares.append(writerShare)
        return settledIV, buyerShares, writerShares
                
    def force_settle_all_markets(self, option):
        for i in range(len(self.markets)):
            market = self.markets[i]
            if not self.settledMarkets[i]:
                # print("Settled")
                bBalance = self.bTokenBalance(i)
                wBalance = self.wTokenBalance(i)
                buyerShare, writerShare = market.getSettlementAmounts(self.currentPrice, option)
                #print(buyerShare, writerShare)
                self.collateralReserve += bBalance * buyerShare + wBalance * writerShare
                self.bTokenReserve[i] = 0.0
                self.wTokenReserve[i] = 0.0
                self.settledMarkets[i] = True
                
    
    def getPoolValue(self, bPrices):
        poolValue = self.collateralReserve
        ny_settled = list(filter(lambda x: x == False, self.settledMarkets))
        for i in range(len(ny_settled)):
            bPrice = bPrices[i]
            wPrice = 1 - bPrice
            bBalance = self.bTokenBalance(i)
            wBalance = self.wTokenBalance(i)
            poolValue += bPrice * bBalance + wPrice * wBalance
            
        return poolValue
    # def hedge(poolDelta):
        
        