from __future__ import absolute_import

import logging
import sys
import gevent
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core
from pnnl.pubsubagent.pubsub.agent import PubSubAgent
from volttron.platform.jsonrpc import RemoteError
from datetime import timedelta as td, datetime as dt


utils.setup_logging()
log = logging.getLogger(__name__)


class InterfaceAgent(PubSubAgent):
    '''
    This agent simply subscribes to a topic, then handles messages on that topic, forwarding a modified version to a different topic. This provides a convenient interface to the BMS from the application.
    '''
    RPC = 'RPC'
    DATE_FORMAT = '%m-%d-%y %H:%M:%S'

    def __init__(self, config_path, **kwargs):
        self.isActuating = False
        self.isConnected = False
        self.setAllPoints = False
        self.masterMax = 75.0
        self.masterMin = 70.0
        self.occCoolMax = 75.0
        self.occCoolMin = 68.0
        self.occHeatMax = 73.0
        self.occHeatMin = 66.0
        self.occTempOffset = 2.0
        self.standbyCoolMax = 77.0
        self.standbyCoolMin = 66.0
        self.standbyHeatMax = 75.0
        self.standbyHeatMin = 64.0
        self.standbyTempOffset = 4.0
        self.unoccCoolMax = 80.0
        self.unoccCoolMin = 65.0
        self.unoccHeatMax = 78.0
        self.unoccHeatMin = 63.0
        self.reservationLength = 60*1
        self.actuator_vip = None
        super(InterfaceAgent, self).__init__(config_path, **kwargs)


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(InterfaceAgent, self).setup(sender, **kwargs)
        self.rpc_target = self
        self.setup_remote_actuation()
        
        
    def setup_remote_actuation(self):
        if self.actuator_vip:
            event = gevent.event.Event()
            agent = Agent(address=self.actuator_vip)
            gevent.spawn(agent.core.run, event)
            event.wait(timeout=15)
            self.rpc_target = agent
    
    
    def onUpdateTopic(self, peer, sender, bus, topic, headers, message):
        objs = self.getInputsFromTopic(topic)
        if objs is not None:
            for obj in objs:
                if obj.has_key('forward'):
                    self.forwardTopic(obj)
        self.updateComplete()
        
        
    def onMatchIsActuating(self, peer, sender, bus, topic, headers, message):
        super(InterfaceAgent, self).onMatchTopic(peer, sender, bus, topic, headers, message)
        self.isActuating = self.input('isActuating', 'value')
        if self.isActuating:
            log.info('Interface is Actuating')
        else: 
            log.info('Interface is not Actuating')
        
        
    def onMatchIsConnected(self, peer, sender, bus, topic, headers, message):
        super(InterfaceAgent, self).onMatchTopic(peer, sender, bus, topic, headers, message)
        self.isConnected = self.input('isConnected', 'value')
        if self.isConnected:
            log.info('Interface is Connected')
        else: 
            log.info('Interface is not Connected')
            
            
    def onMatchKill(self, peer, sender, bus, topic, headers, message):
        log.info('Received Kill Command')
        self.isActuating = False
        for key in self.output():
            obj = self.output(key)
            if obj.has_key('handler'):
                if obj.get('handler') == 'handleCoolingSetPoint':
                    self.handleCoolingSetPoint(obj)
        self.isConnected = False

        
    def forwardTopic(self, inputObj):
        forwards = inputObj.get('forward')
        for item in forwards:
            value = inputObj.get('value')
            if item.has_key('field'):
                value = value.get(item.get('field'))
            if item.has_key('transform'):
                value = self.transform(value, item.get('transform'))
            if not self.output(item.get('name')):
                return
            if self.output(item.get('name')).has_key('field'):
                value = {self.output(item.get('name')).get('field') : value}
            self.output(item.get('name'), 'value', value)
            outputObj = self.output(item.get('name'))
            if outputObj.has_key('handler'):
                if (hasattr(self, outputObj.get('handler')) and 
                        callable(getattr(self, outputObj.get('handler'), None))):
                    callback = getattr(self, outputObj.get('handler'))
                    callback(outputObj)
            else:
                self.publish(outputObj)
                
                
    # this is a total freaking hack...
    def handleCoolingSetPoint(self, outputObj):
        
        if not outputObj.has_key('topic'):
            return
        
        device = outputObj.get('topic')
        
        if (device[-1] == '/'):
            device = device[0:-1]
            
        value = outputObj.get('value')
        start_dt = dt.now() #utils.get_aware_utc_now()
        start = utils.format_timestamp(start_dt)
        stop_dt = start_dt + td(seconds=self.reservationLength)
        stop = utils.format_timestamp(stop_dt)
        agent_id = 'agent_id'
        
        self.scheduleDevice(agent_id, device, start, stop)
        
        if self.isActuating:
            standby = False
            inputObjs = self.getInputsFromTopic('devices/'+device+'/all')
            if inputObjs:
                for inputObj in inputObjs:
                    valueObj = inputObj.get('value', None)
                    if valueObj:
                        standby = bool(valueObj.get('StandbyModeStatus', 0))
                    
            occupied = True
            inputObjs = self.getInputsFromTopic('devices/'+device+'/all')
            if inputObjs:
                for inputObj in inputObjs:
                    valueObj = inputObj.get('value', None)
                    if valueObj:
                        occupied = bool(valueObj.get('OccupancyMode', 0))
                    
            if standby:
                setpoints = self.calcSetpoints(value, self.standbyCoolMin, self.standbyCoolMax, self.standbyHeatMin, self.standbyHeatMax)
            elif not occupied:
                setpoints = self.calcSetpoints(value, self.unoccCoolMin, self.unoccCoolMax, self.unoccHeatMin, self.unoccHeatMax)
            else:
                setpoints = self.calcSetpoints(value, self.occCoolMin, self.occCoolMax, self.occHeatMin, self.occHeatMax)
        
            cooling = setpoints['cooling']
            heating = setpoints['heating']
             
        else :
            cooling = None
            heating = None
               
        self.setSetpoint(agent_id, device, "ZoneCoolingTemperatureSetPoint", cooling)
        self.setSetpoint(agent_id, device, "ZoneHeatingTemperatureSetPoint", heating)
        self.unscheduleDevice(agent_id, device)


    def calcSetpoints(self, value, coolMin, coolMax, heatMin, heatMax):
        # clamp the desired value
        cooling = max(min(value,coolMax),coolMin)
        heating = heatMin
        return {"cooling" : cooling, "heating" : heating}
      
            
    def scheduleDevice(self, agent_id, device, start, stop):
        
        if self.isConnected:
            try:
                result = self.rpc_target.vip.rpc.call(
                    'platform.actuator',    #Target agent
                    'request_new_schedule', #Method to call
                    agent_id,               #Requestor
                    device+'/set_point_task',                 #TaskID
                    'HIGH',                 #Priority
                    [[device, start, stop]] #Request message
                    ).get(timeout=10)
                if self.rpcFailed(result):
                    log.warn('Failed to schedule {} (unavailable) '.format(device))
            except Exception as ex:
                log.warning("Failed to schedule {} (Exception): {}".format(device, str(ex)))
        else:
            log.info("self.vip.rpc.call('platform.actuator', 'request_new_schedule', "+agent_id+", 'set_point_task', 'HIGH', [['"+device+"', '"+start+"', '"+stop+"']]).get(timeout=10)")

                
                
    def unscheduleDevice(self, agent_id, device):
        
        if self.isConnected:
            try:
                result = self.rpc_target.vip.rpc.call(
                    'platform.actuator',    #Target agent
                    'request_cancel_schedule', #Method to call
                    agent_id,               #Requestor
                    device+'/set_point_task'                 #TaskID
                    ).get(timeout=10)
                if self.rpcFailed(result):
                    log.warn('Failed to unschedule {} (unavailable) '.format(device))
            except Exception as ex:
                log.warning("Failed to unschedule {} (Exception): {}".format(device, str(ex)))
        else:
            log.info("self.vip.rpc.call('platform.actuator', 'request_cancel_schedule', "+agent_id+", 'set_point_task').get(timeout=10)")


    
    def setSetpoint(self, agent_id, device, point, value):
        
        if self.isConnected:
            try:
                result = self.rpc_target.vip.rpc.call(
                   'platform.actuator',    #Target agent
                   'set_point',            #Method to call
                   agent_id,               #Requestor
                   device+"/"+point,       #Point to set
                   value,                  #New value
                   ).get(timeout=10)
                if self.rpcFailed(result):
                    log.warn('Failed to set {} on {} (unavailable) '.format(point, device))
            except Exception as ex:
                log.warning("Failed to set {} on {} (Exception): {}".format(point, device, str(ex)))
        else:
            log.info("self.vip.rpc.call('platform.actuator', 'set_point', '"+agent_id+"', '"+device+"/"+point+"', '"+str(value)+"').get(timeout=10)")

    
    def rpcFailed(self, result):
        if isinstance(result, dict):
            if 'result' in result:
                if result['result'] == 'FAILURE':
                    return True
        return False
    
    
    def transform(self, value, transformation):
        return UnitConverter.transform(value, transformation)
    
    
class UnitConverter(object):
    '''
    Converts units. Duh.
    '''
    C2F = "C2F"
    F2C = "F2C"
    CFM2KGS = "CFM2KGS"
    IN2PA = "IN2PA"

    def __init__(self, params):
        pass
        
    @staticmethod
    def transform(value, transformation):
        if value is None:
            return None
        if transformation == UnitConverter.C2F:
            return float(value)*9.0/5.0+32.0
        if transformation == UnitConverter.F2C:
            return (float(value)-32.0)*5.0/9.0
        if transformation == UnitConverter.CFM2KGS:
            return float(value)*0.000471947*1.2041
        if transformation == UnitConverter.IN2PA:
            return float(value)*248.84


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(InterfaceAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
