import os
import sys
import datetime






currentdir = os.path.dirname(os.getcwd())
sys.path.insert(0,currentdir)
start_time = datetime.datetime(2021,1,1,8,tzinfo=datetime.timezone.utc)
IV_WINDOW = 30
SAMPLE_LENGTH = 365*24 + IV_WINDOW*24

def is_expiration(d):
    return d.weekday() == 4 and d.hour == 8

def get_next_expiry(time):
    friday = time + datetime.timedelta( (4-time.weekday()) % 7 )
    return friday.replace(hour=8, minute=0,second=0,microsecond=0)


class Perpetual(object):

    def __init__(self):
        #(price at bying, size)
        self._positions = []

    def addPosition(self, size, current_price):
        self._positions.append((current_price,size))

    def close(self,idx):
        del self._positions[idx]

    def closeAll(self):
        self._positions = []

    def getPositionSize(self):
        return sum(map(lambda x:x[1],self._positions))

    def getPnL(self,current_price):
        PnL = 0
        for pos in self._positions:
            PnL += ((current_price - pos[0])/current_price)*pos[1]
        return PnL