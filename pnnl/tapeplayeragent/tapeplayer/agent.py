from __future__ import absolute_import

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from pnnl.pubsubagent.pubsub.agent import PubSubAgent


utils.setup_logging()
log = logging.getLogger(__name__)


class TapePlayerAgent(PubSubAgent):
    def __init__(self, config_path, **kwargs):
        self.tapeFile = None
        self.tapeObj = None
        self.publishRate = 10
        super(TapePlayerAgent, self).__init__(config_path, **kwargs)


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(TapePlayerAgent, self).setup(sender, **kwargs)
        if self.tapeFile is not None:
            self.loadTapeFile()
            self.core.periodic(self.publishRate, self.trigger)
    

    def trigger(self):
        if self.tapeObj is None:
            return
        entry = self.tapeObj[self.tapeIndex]
        if entry is None:
            return
        if not entry.get('Topic', None) or not entry.get('Message', None):
            return
        topic = entry.get('Topic')
        message = entry.get('Message')
        if not self.output(topic):
            self.OUTPUTS[topic] = {"topic" : topic}
        self.output(topic, 'value', message)
        self.publish(self.output(topic))
        self.tapeIndex = (self.tapeIndex + 1) % len(self.tapeObj)


    def loadTapeFile(self):
        self.tapeObj = utils.load_config(self.tapeFile)
        self.tapeIndex = 0


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(TapePlayerAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
