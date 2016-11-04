# README #

This repository contains a multi-agent transactive market controller for a commercial building VAV system. Details regarding the controller and implementation will be published in separate PNNL documents. This README contains instructions for installing dependencies and running an example transactive market co-simulation using EnergyPlus.

## DEPENDENCIES ##

The following instructions assume you have already cloned this repository, and that you have already installed the [PubSub](../../../volttron-pubsub), [Market](../../../volttron-market), and [Models](../../../volttron-models) modules into the VOLTTRON environment's site-packages directory. To run the example market simulation with EnergyPlus, you must also clone the [EnergyPlus](../../../volttron-energyplus) modules. To run the plotter agent included in the example you must install the matplotlib module in the VOLLTRON virtual environment, or preferably, put an existing installation of the module on your Python path. The TkAgg backend is needed.

## AGENT CONFIGURATION FOR EXAMPLE ##

EnergyPlus needs to know where to find the model and weather files used for simulation. You will need to edit the 'EnergyPlus' configuration file included in the [volttron-trxhvac repository location]/config/ directory if you are running the agents from the command line. If running from your IDE, you may nor may not have to modify the paths depending on how the IDE is configured. Specifically, the following parameters need to be updated:
~~~
...
	"model" : "[volttron-trxhvac repository location]/eplus/BUILDING1.idf",
	"weather" : "[volttron-trxhvac repository location]/eplus/USA_WA_Pasco-Tri.Cities.AP.727845_TMY3.epw",
	"bcvtb_home" : "[volttron-energyplus repository location]/bcvtb/",
...
~~~
If you do not have the USA_WA_Pasco-Tri.Cities.AP.727845_TMY3.epw weather file, simply substitute for another.

## PACKAGING AND RUNNING EXAMPLE ##

Navigate to VOLTTRON source directory
~~~
$ cd [VOLTTRON repository location]
~~~
Enable the VOLTTRON virtual environment (if not already enabled).
~~~
$ . env/bin/activate
~~~
Run VOLTTRON
~~~
$ volttron -vv -l [logfilepath.log] &
~~~
The market simulation involves a number of agents. To make launching the simulation easy, a shell script has been provided. To launch the script:

Navigate to volttron-trxhvac source directory
~~~
$ cd [volttron-trxhvac repository location]
~~~
Run the script
~~~
$ . make_agent_group.sh [VOLTTRON repository location] example1.txt
~~~
View the log. You will observe the agents log the messages sent back and forth during the market simulation.
~~~
$ tail -f [logfilepath.log]
...
2016-09-29 12:13:47,626 (market-0.1 31803) <stdout> INFO: ElectricityMarket does not have enough BUY offers.
2016-09-29 12:13:47,589 (vav-0.1 870) vav.agent INFO: Received Buy Bid Request: markets/PNNL/BUILDING1/air/offer/request {'commodity': 'air'}
2016-09-29 12:13:47,589 (vav-0.1 870) pnnl.pubsubagent.pubsub.agent INFO: Sending: markets/PNNL/BUILDING1/air/offer/response [{'curve': [(0.0, 100.0), (0.0, 10.0)], 'type': 'BUY', 'commodity': 'air'}, {}]
2016-09-29 12:13:47,563 (energyplus-0.1 2360) pnnl.pubsubagent.pubsub.agent INFO: Sending: devices/PNNL/BUILDING1/AHU1/VAV150/all [{'ZoneAirFlow': 0.0, 'ZoneTemperature': 24.64955922789747, 'ZoneDischargeAirTemperature': 23.93867519019122}, {'ZoneAirFlow': {'units': 'cubicMetersPerSecond', 'type': 'float', 'tz': 'US/Pacific'}, 'ZoneTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}, 'ZoneDischargeAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}}]
2016-09-29 12:13:47,568 (energyplus-0.1 2360) pnnl.pubsubagent.pubsub.agent INFO: Sending: devices/PNNL/BUILDING1/AHU1/VAV120/all [{'ZoneAirFlow': 0.0, 'ZoneTemperature': 24.96123670423383, 'ZoneDischargeAirTemperature': 23.93867519019122}, {'ZoneAirFlow': {'units': 'cubicMetersPerSecond', 'type': 'float', 'tz': 'US/Pacific'}, 'ZoneTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}, 'ZoneDischargeAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}}]
2016-09-29 12:13:47,608 (energyplus-0.1 2360) pnnl.pubsubagent.pubsub.agent INFO: Sending: devices/PNNL/BUILDING1/AHU1/all [{'MixedAirTemperature': 23.93867519019122, 'DischargeAirFlow': 0.0, 'ReturnAirTemperature': 23.93867519019122, 'SupplyFanStatus': 0.0, 'DischargeAirTemperature': 23.93867519019122, 'OutdoorAirTemperature': 17.0}, {'MixedAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}, 'DischargeAirFlow': {'units': 'cubicMetersPerSecond', 'type': 'float', 'tz': 'US/Pacific'}, 'ReturnAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}, 'SupplyFanStatus': {'units': 'Enum', 'type': 'float', 'tz': 'US/Pacific'}, 'DischargeAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}, 'OutdoorAirTemperature': {'units': 'degreesCentigrade', 'type': 'float', 'tz': 'US/Pacific'}}]
2016-09-29 12:13:47,544 (market-0.1 31803) market.agent INFO: Received Reservation: 6307fcbb-7cce-42f4-8356-d47a36de465d {'curve': None, 'type': 'SELL', 'commodity': 'electricity'}
2016-09-29 12:13:47,554 (market-0.1 31803) market.agent INFO: Received Reservation: 3f56b8fe-a8a5-4e9a-ac11-0a62ccf06ac8 {'curve': None, 'type': 'BUY', 'commodity': 'electricity'}
2016-09-29 12:13:47,564 (market-0.1 31803) pnnl.pubsubagent.pubsub.agent INFO: Sending: markets/PNNL/BUILDING1/electricity/offer/request [{'commodity': 'electricity'}, {}]
2016-09-29 12:13:47,611 (market-0.1 31803) market.agent INFO: Received Offer: 6307fcbb-7cce-42f4-8356-d47a36de465d {'curve': [[0.0, 65.0], [1000000.0, 65.0]], 'type': 'SELL', 'commodity': 'electricity'}
2016-09-29 12:13:47,479 (market-0.1 31920) market.agent INFO: Received Reservation: a353a443-e3c0-4eae-9ff3-2af35a747fb9 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,486 (market-0.1 31920) market.agent INFO: Received Reservation: 9bff0fb6-c41c-4d59-a499-544c3464c651 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,487 (market-0.1 31920) market.agent INFO: Received Reservation: 00b74a89-d9fa-4655-8eed-a306a320e60d {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,496 (market-0.1 31920) market.agent INFO: Received Reservation: 78d9d0d9-25f3-4cde-94d6-23be8cb6fcda {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,496 (market-0.1 31920) market.agent INFO: Received Reservation: 3f56b8fe-a8a5-4e9a-ac11-0a62ccf06ac8 {'curve': None, 'type': 'SELL', 'commodity': 'air'}
2016-09-29 12:13:47,499 (market-0.1 31920) market.agent INFO: Received Reservation: 26cff7a1-934a-46b6-8538-6e092eb306b4 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,503 (market-0.1 31920) market.agent INFO: Received Reservation: 61770601-0c3a-4fcb-97a8-097d50df4106 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,504 (market-0.1 31920) market.agent INFO: Received Reservation: e9a51bf4-4be4-4258-957f-d3a3ba1023e3 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,508 (market-0.1 31920) market.agent INFO: Received Reservation: 8c296a85-f786-4c70-a8c2-44cf90ba6cad {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,520 (market-0.1 31920) market.agent INFO: Received Reservation: bb60eadd-11f0-4767-83fc-f3a2d97b8c3c {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,520 (market-0.1 31920) market.agent INFO: Received Reservation: b6088699-1d23-4ca1-ac92-b900d5e60c71 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,520 (market-0.1 31920) market.agent INFO: Received Reservation: 8e02db99-c786-4251-b638-3f368c541b79 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,526 (market-0.1 31920) market.agent INFO: Received Reservation: 36355ee8-8907-46a0-b166-ac6a8c4a214c {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,532 (market-0.1 31920) market.agent INFO: Received Reservation: f497a28f-ac16-428a-b88c-e1118160bac2 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,538 (market-0.1 31920) market.agent INFO: Received Reservation: fd53a1aa-adcc-4e8d-9b85-24e372213e53 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,542 (market-0.1 31920) market.agent INFO: Received Reservation: 23d5dee7-db09-46ca-9541-b01976f10dbf {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,560 (market-0.1 31920) market.agent INFO: Received Reservation: 643557f7-0a32-486c-8177-b633871eaf18 {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,560 (market-0.1 31920) market.agent INFO: Received Reservation: dd797111-9a10-40df-b2ea-02d5f85902cb {'curve': None, 'type': 'BUY', 'commodity': 'air'}
2016-09-29 12:13:47,566 (market-0.1 31920) pnnl.pubsubagent.pubsub.agent INFO: Sending: markets/PNNL/BUILDING1/air/offer/request [{'commodity': 'air'}, {}]
...
~~~
You should also see three plot windows appear showing the clearing prices, cleared quantities and setpoints.
 
Once the simulation ends, the agents will stop sending messages. You may re-start the simulation by stopping and restarting the agents.