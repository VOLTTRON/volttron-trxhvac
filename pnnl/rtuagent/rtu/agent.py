# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright (c) 2016, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.
#

# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization
# that has cooperated in the development of these materials, makes
# any warranty, express or implied, or assumes any legal liability
# or responsibility for the accuracy, completeness, or usefulness or
# any information, apparatus, product, software, or process disclosed,
# or represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does
# not necessarily constitute or imply its endorsement, recommendation,
# r favoring by the United States Government or any agency thereof,
# or Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830

#}}}

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
from pnnl.models.rturegression import RtuRegression
from pnnl.models.rtusimple import RtuSimple


utils.setup_logging()
log = logging.getLogger(__name__)
    

class RtuAgent(BuyerAgent, FirstOrderZone, RtuRegression):
    

    def __init__(self, config_path, **kwargs):
        BuyerAgent.__init__(self, config_path, **kwargs)
        FirstOrderZone.__init__(self)
        RtuRegression.__init__(self)
        self.qClear = 0.
        self.eClear = 0.
        self.pClear = None
        self.pMin = 0.
        self.pMax = 100.
        self.pWin = 288
        self.tNom = 21.11
        self.tNomUnocc = 21.11
        self.hvacAvail = 0.
        self.occupied = 0.
        self.eCurve = PolyLine()
        self.qCurve = PolyLine()
        self.wholesalePrice = []
        self.nonResponsive = False
        self.tMinUnocc = 22.
        self.tMaxUnocc = 24.
        self.tEase = 2.0
        self.timeStep = 60.
        self.minOffTime = 300.0
        self.eMin = None
        self.eMax = None
        self.tDeadband = 4.0*5.0/9.0


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(RtuAgent, self).setup(sender, **kwargs)
        self.updateTemps()
        
        
    def updateState(self):
        if self.input('HVAC_ON', 'value') is not None:
            self.hvacAvail = self.input('HVAC_ON', 'value')
            self.occupied = self.input('HVAC_ON', 'value')
        if self.input('T_OUT', 'value') is not None:
            self.tOut = self.input('T_OUT', 'value')
        if self.input('T_IN', 'value') is not None:
            self.tIn = self.input('T_IN', 'value')
        if self.input('FAN_STATUS', 'value') is not None:
            self.isFanRunning = True if self.input('FAN_STATUS', 'value') != 0 else False
        if self.input('COMPRESSOR_STATUS', 'value') is not None:
            self.isCompressorRunning = True if self.input('COMPRESSOR_STATUS', 'value') != 0 else False
        if self.input('HEAT_COOL_MODE', 'value') is not None and self.isCompressorRunning:
            self.mode = RtuSimple.COOLING if self.input('HEAT_COOL_MODE', 'value') != 0 else RtuSimple.HEATING
        if self.input('AUX_HEAT_STATUS', 'value') is not None:
            self.isAuxOn = True if self.input('AUX_HEAT_STATUS', 'value') != 0 else False
        self.updateTemps()
        
        
    def onMatchCompressorStatus(self, peer, sender, bus, topic, headers, message):
        BuyerAgent.onMatchTopic(self, peer, sender, bus, topic, headers, message)
        if self.input('COMPRESSOR_STATUS', 'value') is not None:
            self.updateRunTime()


    def updateTemps(self):
        if self.occupied:
            self.tMinAdj = self.tMin
            self.tMaxAdj = self.tMax
            self.tNomAdj = self.tNom
        else:
            self.tMinAdj = self.tMinUnocc
            self.tMaxAdj = self.tMaxUnocc
            self.tNomAdj = self.tNomUnocc


    def updateRunTime(self):
        if self.isCompressorRunning:
            self.runTime += self.timeStep
            self.offTime = 0
        else:
            self.runTime = 0
            self.offTime += self.timeStep


    def onMatchBidRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received Buy Bid Request: ' + topic + ' ' + str(message[0]))
        self.updateDemandCurve()
        self.output('bidResponse', 'value', {
            'type': Offer.BUY,
            'commodity': self.output('bidResponse', 'commodity'),
            'curve': self.eCurve.tuppleize()})
        self.publish(self.output('bidResponse'))
        
    
    def updateDemandCurve(self):
        self.updateState()
        eCurve = PolyLine()
        qCurve = PolyLine()
        # check that min and max prices are possible
        priceMin = self.calcPmin()
        priceMax = self.calcPmax()
        if priceMin >= priceMax:
            priceMax = priceMin
        # we must be bidding positive quantities :)
        if (self.hvacAvail > 0):
            self.eMin = self.getMinPower()
            self.eMax = self.getMaxPower()
            self.qMin = abs(self.getQmin())
            self.qMax = abs(self.getQmax())
        else:
            self.eMin = 0.0
            self.eMax = 0.0
            self.qMin = 0.0
            self.qMax = 0.0
        eCurve.add(Point(self.eMin, priceMax))
        eCurve.add(Point(self.eMax, priceMin))
        self.eCurve = eCurve
        qCurve.add(Point(self.qMin, priceMax))
        qCurve.add(Point(self.qMax, priceMin))
        self.qCurve = qCurve
        
    
    def onMatchClearRequest(self, peer, sender, bus, topic, headers, message):
        log.info('Received Clear Request: ' + topic + ' ' + str(message[0]))
        if message[0]['commodity'] == self.input('clearRequest', 'commodity'):
            self.updateState()
            self.updatePrice(message[0]['price'])
            self.updateTSet()
            if self.mode == RtuAgent.COOLING:
                cool = self.tSet
                heat = cool-self.tDeadband
            else:
                heat = self.tSet
                cool = heat+self.tDeadband
            self.output('T_set_cool', 'value', cool)
            self.publish(self.output('T_set_cool'))
            self.output('T_set_heat', 'value', heat)
            self.publish(self.output('T_set_heat'))
            heatCool = 'heating' if self.mode == RtuAgent.HEATING else 'cooling'
            log.info(self.name + ' Estimated ' + heatCool + ' rate: '+ str(self.qClear))
            log.info(self.name + ' Estimated ' + heatCool + ' electric power: '+ str(self.eClear))
            
            
    def updateTSet(self):
        if self.pClear is not None and not self.nonResponsive and self.hvacAvail:
            self.eClear = self.clamp(self.eCurve.x(self.pClear), self.eMax, self.eMin)
            self.qClear = self.clamp(self.qCurve.x(self.pClear), self.qMax, self.qMin)
            self.tSet = self.clamp(self.getT(self.qClear), self.tMinAdj, self.tMaxAdj)
        else:
            self.tSet = self.clamp(self.ease(self.tNomAdj, self.tSet, self.tEase), self.tMinAdj, self.tMaxAdj)
            self.qClear = 0.
            self.eClear = 0.
        if self.qClear is None:
            self.qClear = 0.
            self.eClear = 0.
            
    
    def updatePrice(self, clearPrice):
        self.pClear = clearPrice
        if clearPrice is not None:
            self.wholesalePrice = np.append(self.wholesalePrice, clearPrice)
            
            
    def onUpdateComplete(self):
        self.updateState()
        BuyerAgent.onUpdateComplete(self)
        
        
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
    
    
    def getQmin(self):
        # what if temperature is near setpoint limit and we can't increase load?
        if self.mode == RtuSimple.HEATING:
            return self.calcMinHeatCapacity()
        elif self.mode == RtuSimple.COOLING:
            return self.calcMinCoolCapacity()
        else:
            return 0.0


    def getQmax(self):
        # what if temperature is near setpoint limit and we can't increase load?
        if self.mode == RtuSimple.HEATING:
            return self.calcMaxHeatCapacity()
        elif self.mode == RtuSimple.COOLING:
            return self.calcMaxCoolCapacity()
        else:
            return 0.0
        
    
    def getMinPower(self):
        # what if temperature is near setpoint limit and we can't increase load?
        if self.mode == RtuSimple.HEATING:
            return self.calcMinHeatPower()
        elif self.mode == RtuSimple.COOLING:
            return self.calcMinCoolPower()
        else:
            return 0.0


    def getMaxPower(self):
        # what if temperature is near setpoint limit and we can't increase load?
        if self.mode == RtuSimple.HEATING:
            return self.calcMaxHeatPower()
        elif self.mode == RtuSimple.COOLING:
            return self.calcMaxCoolPower()
        else:
            return 0.0
        
    
    def calcMinCoolPower(self):
        return RtuRegression.calcMinCoolPower(self, self.timeStep)
    
    
    def calcMaxCoolPower(self):
        return RtuRegression.calcMaxCoolPower(self, self.timeStep)
    
    
    def calcMinHeatPower(self):
        return RtuRegression.calcMinHeatPower(self, self.timeStep)
    
    
    def calcMaxHeatPower(self):
        return RtuRegression.calcMaxHeatPower(self, self.timeStep)
    

    def calcMinCoolCapacity(self):
        return RtuRegression.calcMinCoolCapacity(self, self.timeStep)
    
    
    def calcMaxCoolCapacity(self):
        return RtuRegression.calcMaxCoolCapacity(self, self.timeStep)
    
    
    def calcMinHeatCapacity(self):
        return RtuRegression.calcMinHeatCapacity(self, self.timeStep)
    
    
    def calcMaxHeatCapacity(self):
        return RtuRegression.calcMaxHeatCapacity(self, self.timeStep)
    
    
    def clamp(self, value, x1, x2):
        minValue = min(x1, x2)
        maxValue = max(x1, x2)
        return min(max(value, minValue), maxValue)


    def ease(self, target, current, limit):
        return current - np.sign(current-target)*min(abs(current-target), abs(limit))
    

def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(RtuAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
