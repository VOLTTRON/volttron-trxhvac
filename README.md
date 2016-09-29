# README #

This repository contains a multi-agent transactive market controller for a commercial building VAV system. Details regarding the controller and implementation will be published in separate PNNL documents. This README contains instructions for installing dependencies and running an example transactive market co-simulation using EnergyPlus.

## DEPENDENCIES ##

The following instructions assume you have already cloned this repository, and that you have already installed the [PubSub](https://github.com/VOLTTRON/volttron-pubsub), [Market](https://github.com/VOLTTRON/volttron-market), and [Models](https://github.com/VOLTTRON/volttron-models) modules into the VOLTTRON environment's site-packages directory. To run the example market simulation with EnergyPlus, you must also clone the [EnergyPlus](https://github.com/VOLTTRON/volttron-energyplus) modules. To run the plotter agent included in the example you must install the matplotlib module in the VOLLTRON virtual environment, or preferably, put an existing installation of the module on your Python path. The TkAgg backend is needed.

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
~~~
~~~
...

...
~~~
You should also see three plot windows appear showing the clearing prices, cleared quantities and setpoints.
 
Once the simulation ends, the agents will stop sending messages. You may re-start the simulation by stopping and restarting the agents.