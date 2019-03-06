'''
Created on June 13, 2018

@author: David Stocker
'''
import sys
import importlib

import Graphyne.Graph as Graph

    
    
#Globals
moduleName = 'PluginFacade'
#rml = RML()
engineServices = []
archiveServices = []
initServices = []
initUtils = []
services = {}
utilities = {}
logType = Graph.logTypes.ENGINE
logLevel = Graph.LogLevel()



def initPlugins(plugins):
    """ This method handles the importing of all plugin modules.  They come as a list of dict objects
        The format is as follows:
        self.plugins = {'name' : 'ActionEngine',
                            'pluginType' : 'EngineService',
                            'Module' : 'ActionEngine.ActionEngine',
                            'PluginParemeters': {'heatbeatTick' : 1}
                        },
                        {'name' : 'StimulusEngine',
                            'pluginType' : 'EngineService',
                            'Module' : 'StimulusEngine.StimulusEngine',
                            'PluginParemeters': {'heatbeatTick' : 1}
                        },
                        {'name' : 'RegressionTestBroadcaster',
                            'pluginType' : 'EngineService',
                            'Module' : 'Broadcasters.RegressionTestBroadcaster',
                            'PluginParemeters': {'heatbeatTick' : 1, 'broadcasterID' : 'Test'}
                        }
        """
    method = moduleName + '.initPlugins'
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    Graph.logQ.put( [logType , logLevel.INFO , method , 'Starting to intialize the plugins'])
 
    # For general plugins, there are four types declared in the 'pluginType' attribute:
    #    EngineService - Plugin class extends threading.Thread.  Plugin.run() will run for the lifetime of the server
    #    Service - Plugin class extends threading.Thread.  Plugin.run() and Plugin.join() will be called as needed
    #    Utility - Plugin is normal callable object.  Plugin.execute() returns a value and is called as needed
    
    Graph.logQ.put( [logType , logLevel.INFO , method , '..Initializing service and utility plugins'])
    
    for pluginKey in plugins:
        plugin = plugins[pluginKey]
        pluginType = plugin["pluginType"] 
        name = plugin["name"]
        modName = "Intentsity.Plugins." + plugin["Module"]
        try:
            mod = importlib.import_module(modName)
        except Exception as e:
            #raise e
            #debug
            #mod = Fileutils.getModuleFromResolvedPath(modName)
            pass
        
        dtParams = plugin["PluginParemeters"]
        plugin['module'] = mod
        plugin['moduleName'] = moduleName
        plugin['params'] = dtParams

        
        Graph.logQ.put( [logType , logLevel.INFO , method , '....%s plugin from module %s cataloged as %s' %(pluginType, modName, name)])
        if pluginType == "EngineService":
            engineServices.append(plugin)
        elif pluginType == "ArchiveService":
            archiveServices.append(plugin)
        elif pluginType == "InitService":
            initServices.append(plugin)
        elif pluginType == "Service":
            services[name] = plugin
        elif pluginType == "InitUtility":
            initUtils.append(plugin)
        else:
            utilities[name] = plugin



  
                
        
    

