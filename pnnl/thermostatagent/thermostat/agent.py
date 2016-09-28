from __future__ import absolute_import

import logging
import sys
import numpy as np
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from pnnl.offer import Offer
from pnnl.polyline import PolyLine, Point
from pnnl.buyeragent.buyer.agent import BuyerAgent
from pnnl.models.firstorderzone import FirstOrderZone


utils.setup_logging()
log = logging.getLogger(__name__)


class ThermostatAgent(BuyerAgent, FirstOrderZone):
    

    def __init__(self, config_path, **kwargs):
        BuyerAgent.__init__(self, config_path, **kwargs)
        FirstOrderZone.__init__(self)
        self.qClear = 0.
        self.pClear = None
        self.pMin = 0.
        self.pMax = 100.
        self.pWin = 288
        self.tEase = 0.25
        self.tSupHvac = 12.78
        self.tNom = 21.11
        self.mDotMin = 0.0
        self.mDotMax = 10.0
        self.tSup = 0.
        self.mDot = 10. #kg/s
        self.hvacAvail = 0.
        self.standby = 0.
        self.occupied = 1.
        self.demandCurve = PolyLine()
        self.wholesalePrice = []
        self.nonResponsive = False
        self.tMinStandby = 22.
        self.tMaxStandby = 24.
        self.tNomStandby = 24.
        self.tMinUnocc = 22.
        self.tMaxUnocc = 24.
        self.tNomUnocc = 24.


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(ThermostatAgent, self).setup(sender, **kwargs)
        self.tMinAdj = self.tMin
        self.tMaxAdj = self.tMax
        self.tNomAdj = self.tNom

        
    def updateState(self):
        if self.input('HVAC_ON', 'value') is not None:
            self.hvacAvail = self.input('HVAC_ON', 'value')
        if self.input('HVAC_T_sup', 'value') is not None:
            self.tSupHvac = self.input('HVAC_T_sup', 'value')
        if self.input('T_out', 'value') is not None:
            self.tOut = self.input('T_out', 'value')
        if self.input('M_dot', 'value') is not None:
            self.mDot = self.input('M_dot', 'value')
        if self.input('T_sup', 'value') is not None:
            self.tSup = self.input('T_sup', 'value')
        if self.input('T_in', 'value') is not None:
            self.tIn = self.input('T_in', 'value')
        if self.input('STANDBY', 'value') is not None:
            self.standby = float(self.input('STANDBY', 'value'))
        if self.input('OCCUPIED', 'value') is not None:
            self.occupied = float(self.input('OCCUPIED', 'value'))
        self.qHvacSens = self.mDot*1006.*(self.tSup-self.tIn)
        self.qMin = min(0, self.mDotMin*1006.*(self.tSupHvac-self.tIn))
        self.qMax = min(0, self.mDotMax*1006.*(self.tSupHvac-self.tIn))
        if self.occupied:
            self.tMinAdj = self.tMin
            self.tMaxAdj = self.tMax
            self.tNomAdj = self.tNom
        else:
            self.tMinAdj = self.tMaxUnocc
            self.tMaxAdj = self.tMaxUnocc
            self.tNomAdj = self.tNomUnocc
        if self.standby:
            self.tMinAdj = self.tMinStandby
            self.tMaxAdj = self.tMaxStandby
            self.tNomAdj = self.tNomStandby
            
        
    def onMatchBidRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received Buy Bid Request: ' + topic + ' ' + str(message[0]))
        self.updateDemandCurve()
        self.output('bidResponse', 'value', {
            'type': Offer.BUY,
            'commodity': self.output('bidResponse', 'commodity'),
            'curve': self.demandCurve.tuppleize()})
        self.publish(self.output('bidResponse'))
        
    
    def updateDemandCurve(self):
        self.updateState()
        curve = PolyLine()
        pMin = self.calcPmin()
        pMax = self.calcPmax()
        qMin = abs(self.getQMin())
        qMax = abs(self.getQMax())
        if (self.hvacAvail > 0):
            curve.add(Point(min(qMin, qMax), max(pMin, pMax)))
            curve.add(Point(max(qMin, qMax), min(pMin, pMax)))
        else:
            curve.add(Point(0.0, max(pMin, pMax)))
            curve.add(Point(0.0, min(pMin, pMax)))
        self.demandCurve = curve
        
    
    def onMatchClearRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received Clear Request: ' + topic + ' ' + str(message[0]))
        if message[0]['commodity'] == self.input('clearRequest', 'commodity'):
            self.updateState()
            self.updatePrice(message[0]['price'])
            self.updateTSet()
            self.output('T_set', 'value', self.tSet)
            self.publish(self.output('T_set'))
            log.info(self.name + ' Estimated cooling rate: '+ str(self.qClear))
            
            
    def updateTSet(self):
        if self.pClear is not None and not self.nonResponsive and self.hvacAvail:
            self.qClear = self.clamp(-self.demandCurve.x(self.pClear), self.qMax, self.qMin)
            self.tSet = self.clamp(self.getT(self.qClear), self.tMinAdj, self.tMaxAdj)
        else:
            self.tSet = self.clamp(self.ease(self.tNomAdj, self.tSet, self.tEase), self.tMinAdj, self.tMaxAdj)
            self.qClear = self.clamp(self.getQ(self.tSet), self.qMax, self.qMin)
        if self.qClear is None:
            self.qClear = 0.

    
    def updatePrice(self, clearPrice):
        self.pClear = clearPrice
        if clearPrice is not None:
            self.wholesalePrice = np.append(self.wholesalePrice, clearPrice)   
        
        
    def calcPmin(self):
        sizeWholesalePrice = len(self.wholesalePrice)
        if sizeWholesalePrice < self.pWin:
            priceMin = self.pMin
        else:
            sample = self.wholesalePrice[sizeWholesalePrice - self.pWin:sizeWholesalePrice]
            priceMin = np.mean(sample)-np.std(sample)
        return priceMin


    def calcPmax(self):
        sizeWholesalePrice = len(self.wholesalePrice)
        if sizeWholesalePrice < self.pWin:
            priceMax = self.pMax
        else:
            sample = self.wholesalePrice[sizeWholesalePrice - self.pWin:sizeWholesalePrice]
            priceMax = np.mean(sample)+np.std(sample)
        return priceMax


    def getQMin(self):
        t = self.clamp(self.tSet+self.tDel, self.tMinAdj, self.tMaxAdj)
        q = self.clamp(self.getQ(t), self.qMax, self.qMin)
        return q


    def getQMax(self):
        t = self.clamp(self.tSet-self.tDel, self.tMinAdj, self.tMaxAdj)
        q = self.clamp(self.getQ(t), self.qMax, self.qMin)
        return q


    def clamp(self, value, x1, x2):
        minValue = min(x1, x2)
        maxValue = max(x1, x2)
        return min(max(value, minValue), maxValue)


    def ease(self, target, current, limit):
        return current - np.sign(current-target)*min(abs(current-target), abs(limit))


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(ThermostatAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
