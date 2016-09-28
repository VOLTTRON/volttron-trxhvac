from __future__ import absolute_import

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from pnnl.polyline import PolyLine, Point
from pnnl.middlemanagent.middleman.agent import MiddlemanAgent
from pnnl.models.ahuchiller import AhuChiller


utils.setup_logging()
log = logging.getLogger(__name__)


class AhuChillerAgent(MiddlemanAgent, AhuChiller):
    

    def __init__(self, config_path, **kwargs):
        MiddlemanAgent.__init__(self, config_path, **kwargs)
        AhuChiller.__init__(self)


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(AhuChillerAgent, self).setup(sender, **kwargs)
        
        
    def updateState(self):
        if self.input('T_mix', 'value') is not None:
            self.tAirMixed = self.input('T_mix', 'value')
        if self.input('T_ret', 'value') is not None:
            self.tAirReturn = self.input('T_ret', 'value')
        if self.input('T_sup', 'value') is not None:
            self.tAirSupply = self.input('T_sup', 'value')
        if self.input('M_dot_air', 'value') is not None:
            self.mDotAir = self.input('M_dot_air', 'value')
        if self.input('P_static', 'value') is not None:
            self.staticPressure = self.input('P_static', 'value')
            

    def updateBuyBidCurve(self):
        self.updateState()
        log.info('Current Electric Demand: ' + str(self.calcTotalPower()))
        curve = PolyLine()
        for point in self.demandCurve.points:
            curve.add(Point(self.calcTotalLoad(point.x), point.y))
        self.buyBidCurve = curve
        
    
    def onMatchBuyClearRequest(self, peer, sender, bus, topic, headers, message):
        super(AhuChillerAgent, self).onMatchBuyClearRequest(peer, sender, bus, topic, headers, message)
        mssg = {"fanPower" : self.pFan, "chillerLoad" : self.coilLoad/self.COP, "coilLoad" : self.coilLoad}
        log.info('Estimated Fan and Chiller Power: ' + str(mssg))


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(AhuChillerAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
