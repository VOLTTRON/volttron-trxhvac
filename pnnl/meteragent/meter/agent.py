from __future__ import absolute_import

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from pnnl.offer import Offer
from pnnl.polyline import PolyLine, Point
from pnnl.selleragent.seller.agent import SellerAgent


utils.setup_logging()
log = logging.getLogger(__name__)


class MeterAgent(SellerAgent):
    
    FIXEDPRICE = "FIXEDPRICE"
    FIXEDPRICEDEMANDLIMIT = "FIXEDPRICEDEMANDLIMIT"
    VARIABLEPRICE = "VARIABLEPRICE"
    VARIABLEPRICEDEMANDLIMIT = "VARIABLEPRICEDEMANDLIMIT"
    DEMANDLIMIT = "DEMANDLIMIT"
    

    def __init__(self, config_path, **kwargs):
        self.mode = "FixedPrice"
        self.price = None
        self.demand = Offer.HUGE
        self.priceFile = None
        self.priceList = None
        self.fileIndex = None
        super(MeterAgent, self).__init__(config_path, **kwargs)


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(MeterAgent, self).setup(sender, **kwargs)
        if self.priceFile is not None:
            self.loadPriceFile()


    def loadPriceFile(self):
        self.priceList = []
        f = open(self.priceFile, 'rb')
        for line in f:
            arry = [float(el.strip()) for el in line.split(",")]
            if len(arry) == 1:
                arry.append(self.demand)
            self.priceList.append(arry)
        f.close()
        self.incrementPrice()

        
    def onMatchBidRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received: ' + topic + ' ' + str(message[0]))
        curve = self.makeSupplyCurve()
        commodity = self.output('bidResponse', 'commodity')
        self.output('bidResponse', 'value', {'type': Offer.SELL, 'commodity': commodity, 'curve': curve.tuppleize()})
        self.publish(self.output('bidResponse'))
        
        
    def makeSupplyCurve(self):
        if self.mode == MeterAgent.FIXEDPRICE:
            return self.makePriceCurve()
        if self.mode == MeterAgent.FIXEDPRICEDEMANDLIMIT:
            return self.makePriceWithDemandLimitCurve()
        if self.mode == MeterAgent.VARIABLEPRICE:
            return self.makePriceCurve()
        if self.mode == MeterAgent.VARIABLEPRICEDEMANDLIMIT:
            return self.makePriceWithDemandLimitCurve()
        if self.mode == MeterAgent.DEMANDLIMIT:
            return self.makeDemandLimitCurve()
        

    def makePriceCurve(self):
        curve = PolyLine()
        curve.add(Point(0,self.price))
        curve.add(Point(self.demand,self.price))
        return curve
    
    def makePriceWithDemandLimitCurve(self):
        curve = PolyLine()
        curve.add(Point(0,self.price))
        curve.add(Point(self.demand,self.price))
        curve.add(Point(self.demand,Offer.HUGEPOS))
        return curve
    
    def makeDemandLimitCurve(self):
        curve = PolyLine()
        if self.price is not None:
            curve.add(Point(self.demand,self.price))
        else:
            curve.add(Point(self.demand,Offer.HUGENEG))
        curve.add(Point(self.demand,Offer.HUGEPOS))
        return curve
    
    
    def onMatchClearRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received Clear Request: ' + topic + ' ' + str(message[0]))
        if message[0]['commodity'] == self.input('clearRequest', 'commodity'):
            self.incrementPrice()
            
            
    def incrementPrice(self):
        if self.priceList is not None:
            self.fileIndex = self.fileIndex+1 if self.fileIndex is not None else 0
            if self.fileIndex >= len(self.priceList):
                self.fileIndex = 0
            self.price = self.priceList[self.fileIndex][0]
            self.demand = self.priceList[self.fileIndex][1]
    

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(MeterAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
