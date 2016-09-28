from __future__ import absolute_import

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core
from pnnl.pubsubagent.pubsub.agent import PubSubAgent


utils.setup_logging()
log = logging.getLogger(__name__)


class MessageAgent(PubSubAgent):

    def __init__(self, config_path, **kwargs):
        super(MessageAgent, self).__init__(config_path, **kwargs)


    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(MessageAgent, self).setup(sender, **kwargs)
        
    
    @Core.receiver('onstart')
    def myonstart(self, sender, **kwargs):
        self.publishAllOutputs()


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(MessageAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
