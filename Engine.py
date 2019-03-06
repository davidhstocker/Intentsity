'''
Created on June 13, 2018

@author: David Stocker
'''

import threading
import time
import copy
import os
import queue
from os.path import expanduser
import sys
from types import ModuleType

import Graphyne.Graph as Graph
from . import Exceptions
from Graphyne import Fileutils
from Intentsity import PluginFacade
#from Intentsity import API



class StartupState(object):
    def __init__(self):
        self.INITIAL_STATE = 0
        self.GRAPH_STARING = 1
        self.INDEXING_MOLECULES = 3
        self.STARTING_SERVICES = 3
        self.READY_TO_SERVE = 4
        self.FAILED_TO_START = 5
        
        

class LogLevel(object):
    ''' Java style class to designate constants. ERROR = 0, WARNING = 1, INFO = 2 and ALL = -1.  '''
    def __init__(self):
        self.ERROR = 0
        self.WARNING = 1
        self.ADMIN = 2
        self.INFO = 3
        self.DEBUG = 4 
        
        
class LogType(object):
    ''' Java style class to designate constants. ERROR = 0, WARNING = 1, INFO = 2 and ALL = -1.  '''
    def __init__(self):
        self.ENGINE = 0
        self.CONTENT = 1
        
        
class Queues(object):
        
    def syndicate(self, streamData):
        #syndicate all data to the load queues
        for loadQKey in self.__dict__.keys(): 
            try:
                loadQ = self.__getattribute__(loadQKey)
                loadQ.put(streamData)
            except:
                pass       
            
             

api = None
moduleName = 'Engine'
serverLanguage = 'en' 
rmlEngine = None  
logTypes =  LogType() 
logType = logTypes.ENGINE
logLevel = LogLevel()
validateOnLoad = True
renderStageStimuli = []

import queue

queues = Queues()
templateQueues = []
#LogQ is always there and a module attribute
securityLogQ = queue.Queue()
lagLogQ = queue.Queue()

#Startup State Queues
startupStateActionEngineFinished = False


class ScriptFunction(ModuleType):

    def __init__(self, module):
        ModuleType.__init__(self, module.__name__)
        self._call = None
        if hasattr(module, '__call__'):
            self._call = module.__call__
        self.__dict__.update(module.__dict__)


    def __call__(self, *args, **keywargs):
        if self._call is not None:
            self._call(*args, **keywargs)
            
            
            
class NonThreadedPlugin(object):
    '''
        A non-threaded plugin
    '''
    
    def __init__(self, dtParams = None, rtParams = None):
        self.dtParams = dtParams
        self.rtParams = rtParams
    
        
    def execute(self, params = None):
        #override with desired behavior
        return None



class ServicePlugin(threading.Thread):
    '''The generic INtensity Plugin.  Usable for engine services, intit services and services.
    NOTE!  This extends threading.Thread, so run() and join() should also be implemented.
    override and implement execute() for specific behavior
    run() to run it.
    join() to close it'''

    def initialize(self, dtParams = None, rtParams = None):
        method = self.className + '.' + moduleName + '.' + 'initialize'
        
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , u"Design Time Parameters = %s" %(dtParams)])
        self.pluginName = rtParams['moduleName']
        try:
            name = dtParams['queue']
            self.queueName = name
        except:
            self.queueName = None
            errorMessage = "Possible Error: Plugin %s is unable acquire queue name from the configuration.  If it is supposed to have a queue, please check the configuration.  Otherwise Ignore!" %self.pluginName
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMessage])
        
        heatbeatTick = 5.0    
        try:
            heatbeatTick = float(dtParams['heatbeatTick'])
        except: pass
            
        self._stopevent = threading.Event()
        self._sleepperiod = heatbeatTick
        threading.Thread.__init__(self, name = rtParams['moduleName'])
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])



    def run(self):
        while self.isAlive():
            try:
                self.execute()
                pass
            except:
                # loader plugins run as services sleep for the duration of heatbeatTick and retry the queue.
                self._stopevent.wait(self._sleepperiod)
                return
        
    
    def join(self,timeout=None):
        """
        Stop the thread
        """
        self._stopevent.set()
        threading.Thread.join(self, 0.5)
        
    def killServers(self):
        '''
            Implement this method if the plugin is spawning its own REST API.
            If there is a server running, the thread won't be able to close when join is
            called and shutdown will hang.  These servers need to be stopped so that the
            thread can be closed and the interpreter server can be shut down
             
            It only needs to call server.server_close() and shut the server down.
        '''
        pass
        
    def execute(self):
        ''' method template of abstract class.  Override for specific behavior'''
        return True
    
    

    
    
class Plugin(ServicePlugin):
    '''The generic INtensity Plugin.  Usable for engine services, intit services and services.
    NOTE!  This extends threading.Thread, so run() and join() should also be implemented.
    override and implement execute() for specific behavior
    join() to close it'''
    
    def run(self):
        while self.isAlive():
            try:
                self.execute()
            except:
                # loader plugins run as services sleep for the duration of heatbeatTick and retry the queue.
                self._stopevent.wait(self._sleepperiod)
                
    



class Broadcaster(Plugin):
    ''' 
        Core Broadcaster Class
    '''
    className = 'DefaultBroadcaster'  #Override
    broadcasterID = None
    
    def onAfterInitialize(self, adminParams = None, engineParams = None):
        pass
    
    def onStimulusReport(self, stimulusReport):
        pass
    
    def onBeforeShutdown(self):
        pass
        
    def initialize(self, script, dtParams = None, rtParams = None):
        method = moduleName + '.' +  self.className + '.initialize'
        
        try:
            try:
                self.broadcasterID = dtParams["broadcasterID"]
            except KeyError:
                errorMsg = "Unable to register broadcaster of unknown ID.  An ID parameter must be provided as the first parameter of the initialize() method, or a dictionary must be provided as the second parameter with a 'broadcasterID'.  No Id parameter given.  Dictionary present, but no such key exists.  Broadcaster can't register itself without a key"
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise Exceptions.NoSuchBroadcasterError(errorMsg)
            except TypeError:
                errorMsg = "Unable to register broadcaster of unknown ID.  An ID parameter must be provided as the first parameter of the initialize() method, or a dictionary must be provided as the second parameter with a 'broadcasterID'.  No Id parameter given and no dictionary given.  Broadcaster can't register itself without a key"
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise Exceptions.NoSuchBroadcasterError(errorMsg)
        
            try:
                global broadcasterRegistrar
                broadcasterRegistrar.registerBroadcaster(self.broadcasterID)

                self._stopevent = threading.Event()
                self._sleepperiod = 0.03
                threading.Thread.__init__(self, name = rtParams['moduleName'])
            except Exceptions.QueueError as qe:
                errorMsg = "Unable to acquire queue for broadcaster %s.  Traceback = %s" %(self.broadcasterID, qe)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise qe
            except Exceptions.NoSuchBroadcasterError as nsbe:
                errorMsg = "Unable to register broadcaster %s.  Traceback = %s" %(self.broadcasterID, nsbe)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise nsbe
            except Exception as e:
                errorMsg = "Unable to start broadcaster %s.  Traceback = %s" %(self.broadcasterID, e)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise e
            
            self.onAfterInitialize(dtParams, rtParams)
        
        except Exceptions.NoSuchBroadcasterError as e:
            raise e
        except Exception as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on starting broadcaster %s.  %s, %s" %(self.broadcasterID, errorID, errorMsg)
            tb = sys.exc_info()[2]
            raise ValueError(responseMessage).with_traceback(tb)
         
        
    def run(self):
        """
            Engine.broadcasterRegistrar.broadcasterIndex[self.broadcasterID] is a broadcast queue registered 
            with the Engine's broadcast registrar.   
        """
        method = moduleName + '.' +  self.className + '.run'
        while self.isAlive():
            try:
                if self.broadcasterID not in Engine.broadcasterRegistrar.broadcasterIndex:
                    errorMsg = "%s has no queue to manage.  Shutting plugin down." %self.broadcasterID
                    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                    self.join()
                else:
                    #pop the report from myQueue and fire self.onStimulusReport()
                    stimulusReport = Engine.broadcasterRegistrar.broadcasterIndex[self.broadcasterID].get_nowait()
                    self.onStimulusReport(stimulusReport)
            except queue.Empty:
                if not self._is_stopped:
                    self._stopevent.wait(self._sleepperiod)
                else: 
                    self.exit()
                
            except Exception as e:
                errorMsg = "Error encountered while trying to transfer stimulus report to response queue. Traceback = %e" %e
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        dummyCatch = "this thread is being shut down"
        

    def join(self):
        """
        Stop the thread
        """
        method = moduleName + '.' + self.className + '.' + 'join'
        shutdownMessage = "......Broadcaster %s shut down" %self.broadcasterID
        Graph.logQ.put( [logType , logLevel.ADMIN , method , shutdownMessage])
        self.onBeforeShutdown()
        self._stopevent.set()
        threading.Thread.join(self, 0.5)    
    
            
            


class ActionRequest(object):
    """
        A class for creating action messages
    """    
    def __init__(self, actionMemeName, insertionType, rtparams, subjectID, objectID = None, controllerID = None, decoratingLandmarks = []):
        """
            decoratingLandmarks are landmarks uuids that are explicitly added to the action request at runtime and not part of the action definition 
        """
        try:
            actionEntityID = Graph.api.createEntityFromMeme(actionMemeName)
            actionEntity = Graph.api.getEntity(actionEntityID)
            
            self.actionID = None
            self.action = None
            self.actionMeme = actionEntity.memePath
            self.insertionType = insertionType
            self.rtParams = rtparams
            self.subjectID = subjectID
            self.objectID= objectID
            self.controllerID= controllerID
            self.shutdownBlockID = None
            self.decoratingLandmarks = decoratingLandmarks
        except Exception as e:
            raise e
        
        
        
        
class ActionInsertionType(object):
    APPEND = 0
    HEAD = 1
    HEAD_CLEAR = 2
        
        
class StimulusReport(object):
    """ A class for messaging stimuli on the external (broadcaster) side.  
        This is the object type that is placed in the various broadcaster queues
    """
    def __init__(self, stimulusID, stimulusMeme, agentSet, resolvedDescriptor, isDeferred = False, anchors = [], dependentConditions = None):
        self.stimulusID = stimulusID #The uuid of the stimulus
        self.stimulusMeme = stimulusMeme #Let's keep the cleartext ID of the meme
        self.agentSet = agentSet #The agents that are supposed to get this stimulus
        self.isDeferred = isDeferred #if filtering of the stimulus is deferred until rendering, this will be true 
        self.anchors = anchors #a list of anchor stimuli UUIDs that this stimulus is dependent on.  A free stimulus will have an empty list
        self.resolvedDescriptor = resolvedDescriptor  #This will be in the format created by the resolver  


class StimulusMessage(object):
    """ A class for messaging stimuli on the internal (SiQ) side.  This is the object type that is placed in the SiQ"""
    def __init__(self, stimulusID, argumentMap, targetAgents = []):
        self.stimulusID = stimulusID
        self.targetAgents = targetAgents
        self.argumentMap = argumentMap
        


class LinkType(object):
    ATOMIC = 0
    SUBATOMIC = 1
    ALIAS = 2    



class ControllerCatalog(object):
    className = "ControllerCatalog"
    
    def __init__(self):
        self.indexByType = {}
        self.indexByID = {}
        
    def addController(self, controller):
        #method = moduleName + '.' +  self.className + '.addController'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        #try:
        if controller.uuid not in self.indexByID:
            # We'll need to update both the typelist and the indexByID list
            typeList = []
            try:
                typeList = self.indexByType[controller.path.fullTemplatePath]
            except:
                #This will always happen the first time we instantiate a controller of a given type
                pass
            if controller.uuid not in typeList:
                typeList.append(controller.uuid)
                self.indexByType[controller.path.fullTemplatePath] = typeList
            else:
                raise Exceptions.DuplicateControllerError ("Controller %s already in the controller catalog under the indexByType list" % controller.id)
            
            self.indexByID[controller.uuid] = controller
        else:
            #The controller already has an entry
            raise Exceptions.DuplicateControllerError ("Controller %s already in the controller catalog" % controller.id)
        #except Exception as e:
            #raise Exceptions.ControllerUpdateError(e)
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    
    def removeController(self, controllerID):
        #method = moduleName + '.' +  self.className + '.removeController'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            if controllerID in self.indexByID:
                pass
                '''# We'll need to update both the typelist and the indexByID list
                typeList = self.indexByType[controller.templateName] 
                if controller.id in typeList:
                    del typeList[controller.id]
                    typeList.remove(controller.id)
                    self.indexByType[controller.templateName] = typeList
                else:
                    raise Exceptions.InvalidControllerError ("Controller %s in the controller catalog under the indexByID list, but not the indexByType list" % controller.id)
                del self.indexByID[controller.id]'''
            else:
                #The controller already has an entry
                raise Exceptions.InvalidControllerError ("Controller %s is not in the controller catalog" % controllerID)
        except Exception as e:
            raise Exceptions.ControllerUpdateError(e)
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    
    def getControllersByType(self, controllerType):
        method = moduleName + '.' +  self.className + '.getControllersByType'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        returnList = []
        try:
            returnList = self.indexByType[controllerType]
        except Exception as e:
            errorMsg = "Failed to find any controllers of type %s.  Traceback = %s" % (controllerType, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        return returnList   





class BroadcasterRegistrar(object):
    className = "BroadcasterRegistrar"
    
    broadcasterIndex = {}   
    metamemeIndex = {}
    memeIndex = {}
    stimulusIndex = {}
    registeredBroadcasters = [] 
    defaultBroadcasters = []     
    
    def indexDescriptorMetamemes(self, broadcasterID, metamemeIDs):
        for metamemeID in metamemeIDs:
            try:
                existingBroadcasterSet = self.metamemeIndex[metamemeID]
                existingBroadcasterSet.add(metamemeID)
                self.metamemeIndex[metamemeID] = existingBroadcasterSet
                
                #Make a recursive call to cover all extending metamemes as well
                metamemeChildren = api.getExtendingMetamemes(metamemeID)
                self.indexDescriptorMetamemes(broadcasterID, metamemeChildren)
            except KeyError:
                newBroadcasterSet = set([metamemeID])
                self.metamemeIndex[metamemeID] = newBroadcasterSet
            except Exception as e:
                raise e
                
    
    def indexDescriptorMemes(self, broadcasterID, memeIDs):
        for memeID in memeIDs:
            try:
                if memeID == "*":
                    self.stimulusIndex["*"] = broadcasterID
                else:
                    existingBroadcasterSet = self.memeIndex[memeID]
                    existingBroadcasterSet.add(broadcasterID)
                    self.memeIndex[memeID] = existingBroadcasterSet
            except KeyError:
                newBroadcasterSet = set([broadcasterID])
                self.memeIndex[memeID] = newBroadcasterSet
            except Exception as e:
                raise e
            

    def indexBroadcaster(self, broadcasterID):
        if broadcasterID is not None:
            try:
                self.broadcasterIndex[broadcasterID] = queue.Queue()
            except Exception as e:
                raise e
        else:
            errorMsg = "Can't register broadcaster with value None"
            raise Exceptions.NullBroadcasterIDError(errorMsg)
        
    def registerBroadcaster(self, broadcasterID):
        try:
            queuePointer = self.broadcasterIndex[broadcasterID]  
            testQueue = queue.Queue()
            if type(queuePointer) != type(testQueue):
                errorMsg = "No queue defined for broadcaster %s" %broadcasterID
                raise Exceptions.QueueError(errorMsg)
            else:
                self.registeredBroadcasters.append(broadcasterID)
                return queuePointer
        except Exceptions.QueueError as qe:
            raise qe
        except KeyError:
            errorMsg = "No such broadcaster (%s) registered" %broadcasterID
            raise Exceptions.NoSuchBroadcasterError(errorMsg)
        except Exception as e:
            raise e
        
        
    def indexDescriptor(self, descriptorID):
        method = moduleName + '.' +  self.className + '.indexDescriptor'
        
        #There is only one descriptor and the list length is 1,so use descriptors[0] for the descriptor uuid
        try:
            descriptorMeme = api.getEntityMemeType(descriptorID)
            descriptorMetaMeme = api.getEntityMetaMemeType(descriptorID)
        except Exception as e:
            raise e           
        
        broadcasterList = set([])
        for memeKey in self.memeIndex:
            if memeKey == descriptorMeme:
                broadcasterListByMeme = self.memeIndex[memeKey]
                broadcasterList.update(broadcasterListByMeme)
        for metaMemeKey in self.metamemeIndex:
            if metaMemeKey == descriptorMetaMeme:
                broadcasterListByMetaMeme = self.metamemeIndex[metaMemeKey]
                broadcasterList.update(broadcasterListByMetaMeme)
        self.stimulusIndex[descriptorID] = broadcasterList
        Graph.logQ.put( [logType , logLevel.INFO , method , "Descriptor %s registered with broadcasters %s" %(descriptorMeme, broadcasterList)])
        
        
        
    def getBroadcastQueue(self, stimulusUUID):
        try:
            broadcasterIDList = self.stimulusIndex[stimulusUUID] 
            try:
                defaultBroadcasterID = self.stimulusIndex["*"] 
                queueList = [defaultBroadcasterID]
            except:
                queueList = []
            try:
                for broadcasterID in broadcasterIDList:
                    if broadcasterID in self.registeredBroadcasters:
                        #Return the ID of the broadcast queue.  This way we can directly access it in the original dict, without scope issues
                        queueList.append(broadcasterID)  
                    else:
                        errorMsg = "Broadcaster %s not registered.  Please check configuration XML" %broadcasterID
                        raise Exceptions.NoSuchBroadcasterError(broadcasterID)
            except KeyError:
                errorMsg = "No queue defined for broadcaster %s" %broadcasterID
                raise Exceptions.QueueError(errorMsg)
            except Exceptions.NoSuchBroadcasterError as e:
                raise Exceptions.NoSuchBroadcasterError(e)
            return queueList
        except KeyError:
            keyList = list(self.stimulusIndex.keys())
            memeIDList = []
            badMemeID = None
            try:
                badMemeID = api.getEntityMemeType(stimulusUUID)
                for keyID in keyList:
                    memeID = api.getEntityMemeType(keyID)
                    memeIDList.append(memeID)
            except: pass
            errorMsg = "Descriptor %s No among registered descriptors in broadcast registrar.   Registered Descriptors = %s" %(badMemeID, memeIDList)
            raise Exceptions.NullBroadcasterIDError(errorMsg)
        except Exceptions.NoSuchBroadcasterError as e:
            raise Exceptions.NoSuchBroadcasterError(e)
        except Exceptions.QueueError as e:
            raise Exceptions.QueueError(e)    
    


#Globals



class Engine(object):
    className = "Engine"
    ''' The generic Engine core class. '''
    
    def __init__(self, validateOnLoad = False, processName = 'intentsity'):
        global logLevel   
        self.rtParams = {}     
        self.engineQueues = {'pyLoader' : False, 'mmLoadQ' : True, 'mLoadQ' : True, 'restLoadQ' : True}
        self.scriptLanguages = {"Python" : ['PythonScriptHandler', 'PythonScriptValidator']}
        self.consoleLogLevel = logLevel.WARNING
        self.persistenceArg = None
        self.persistenceType = None
        self.additionalRepos = []
        self.processName= processName
        self.noMainRepo = False
        self.broadcasters = {'default' : {'memes' : ['*'], 'metaMemes' : ['*']}}
        self.startupState = StartupState()
        self.serverState = 0
        self.validateOnLoad = validateOnLoad 
        
        self.scriptDefinitions = {"getAllAgentsInAgentScope" : ["Agent", "getAllAgentsInAgentScope"],
                            "getAllLandmarksInAgentScope" : ["Agent", "getAllLandmarksInAgentScope"],
                            "getAllAgentsInAgentView" : ["Agent", "getAllAgentsInAgentView"],
                            "getAllLandmarksInAgentView" : ["Agent", "getAllLandmarksInAgentView"],
                            "getAllAgentsWithAgentView" : ["Agent", "getAllAgentsWithAgentView"],
                            "getAllLandmarksWithAgentView" : ["Agent", "getAllLandmarksWithAgentView"],
                            "getAllAgentsInSpecifiedPage" : ["Agent", "getAllAgentsInSpecifiedPage"],
                            "getAllAgentsWithViewOfSpecifiedPage" : ["Agent", "getAllAgentsWithViewOfSpecifiedPage"],
                            "getAgentView" : ["Agent", "getAgentView"],
                            "getAgentsWithViewOfStimulusScope" : ["Agent", "getAgentsWithViewOfStimulusScope"],
                            "getStimulusScope" : ["Agent", "getStimulusScope"],
                            "getAgentScope" : ["Agent", "getAgentScope"]}
        
        self.plugins = {
                        'ActionEngine' : {'name' : 'ActionEngine',
                            'pluginType' : 'EngineService',
                            'Module' : 'ActionEngine.ActionEngine',
                            'PluginParemeters': {'heatbeatTick' : 1}
                            },
                        'StimulusEngine' : {'name' : 'StimulusEngine',
                            'pluginType' : 'EngineService',
                            'Module' : 'StimulusEngine.StimulusEngine',
                            'PluginParemeters': {'heatbeatTick' : 1}
                            }
                        }




    def addBroadcaster(self, newDefID, newDef):
        pass
        #test that memes and metamemes are in and structured correctly
        
    def removeBroadcaster(self, defID):
        pass
    
    def setScriptDefinition(self, newDefID, newDef):
        pass
    
    def setPersistence(self, persistenceArg, persistenceType):
        self.persistenceArg = persistenceArg
        self.persistenceType = persistenceType
        
    def addRepo(self, repo):
        self.additionalRepos.append(repo)
        
    def addPlugin(self, newDefID, newDef):
        pass
    
    def removePlugin(self, defID):
        pass
    
    def setRuntimeParam(self, paramID, paramValue):
        self.rtParams[paramID] = paramValue
        
    
    def start(self, startWithStandardRepo = True):
        '''
            processName = process attribute value from Logging.Logger in AngelaMasterConfiguration.xml.
                The process name must be one of the ones defined in the configuration file
            manualAutoVal = an optional boolean (True or False) overriding the validateOnLoad setting in 
                AngelaMasterConfiguration.xml.  If this is not given, or is not boolean, the engine will
                use the setting defined in the configuration file
        '''
        
        method = moduleName + '.' +  self.className + '.start'
        global queues
        global logQ
        global validateOnLoad

        #server language
        try:
            global serverLanguage
            serverLanguage = self.serverLanguage
        except: pass
        
        #validate on load
        try:        
            global validateOnLoad    
            validateOnLoad = self.validateOnLoad
        except: pass

        for queueName in self.engineQueues.keys():
            loadQueue = self.engineQueues[queueName]
            Graph.logQ.put( [logType , logLevel.ADMIN , method , "Creating queue %s, template loader = %s" %(queueName, loadQueue)])
            newQueue = queue.Queue()
            #queues[queueName] = newQueue
            queues.__setattr__(queueName, newQueue)
            if loadQueue == True:
                templateQueues.append(queueName)
        print(("queues = %s" %self.engineQueues.keys()))
        
        #Get All Repositories
        objectMap = {}
        for repoLocation in self.additionalRepos:
            sys.path.append(repoLocation)
            objectMap = Fileutils.walkRepository(repoLocation, objectMap)
        
            
        if startWithStandardRepo is True:
            try:
                childDirectory = os.path.dirname(Exceptions.__file__)
                parentDirectory = os.path.split(childDirectory)
                objectMap = Fileutils.walkRepository(parentDirectory[0], objectMap)
            except Exception as e:
                errorMessage = "Error: startWithStandardRepo is set to true, but default package (Memetic) can't be bootstrapped.  Please install it and ensure that it is in the PYTHONPATH.  Traceback = %s" %e
                print(errorMessage)
                raise Exceptions.TemplatePathError(errorMessage)
        
        Graph.logQ.put( [logType , logLevel.INFO , method , "Python Path %s" %(sys.path)])
        
        for repoDir in self.additionalRepos:
            Graph.logQ.put( [logType , logLevel.INFO , method , "Memetic Repository at %s" %(repoDir)])
        
        #syndicate all data to the load queues
        for packagePath in objectMap.keys():
            try:
                Graph.logQ.put( [logType , logLevel.INFO , method , "Memetic Repository Module %s" %(packagePath)])
                print(("module = %s" %(packagePath)))
                fileData = objectMap[packagePath]
                for fileStream in fileData.keys():
                    codepage = fileData[fileStream]
                    streamData = [fileStream, codepage, packagePath]
                    queues.syndicate(streamData)
            except Exception as e:
                Graph.logQ.put( [logType , logLevel.ERROR , method , "problem syndicating file in repository %s.  Traceback = %s" %(packagePath, e)])
 

            
        #Before starting any plugins, initialize the broadcaster registrar
        #queues
        for broadcasterID in self.broadcasters.keys():
            broadcasterDeclaration = self.broadcasters[broadcasterID]
            broadcasterRegistrar.indexBroadcaster(broadcasterID)
            memeIDs = []
            metamemeIDs = []           
            try:
                memeIDs = broadcasterDeclaration['memes']
            except KeyError: pass
            except Exception as e:
                raise e
            
            try:
                metamemeIDs = broadcasterDeclaration['metaMemes']
            except KeyError: pass
            except Exception as e:
                raise e
            
            try:
                broadcasterRegistrar.indexDescriptorMemes(broadcasterID, memeIDs)
                broadcasterRegistrar.indexDescriptorMetamemes(broadcasterID, metamemeIDs)
                broadcasterRegistrar.registerBroadcaster(broadcasterID)
            except Exceptions.NullBroadcasterIDError as e:
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Can't index broadcaster %s.  Traceback = %s" %(broadcasterID, e)])
            except Exception as e:
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Problem indexing broadcaster %s and descriptor ownership %s.  Traceback = %s" %(broadcasterID, memeIDs, e)])



        # Monkey Patching Alert!  We will decorate the Graphyne.Graph.Scriptacade class with additional script commands before initializing it
        #MasterScriptFunctions
        # /Monkey Patching.  We can now start the Graph.  :)
        
        
        #By default, the engine runs at log level warning, but the wrapper that calls Engine may supply a 'consoleLogLevel' paremeter
        lLevel = logLevel.WARNING
        try:
            lLevel = self.consoleLogLevel
        except: pass

        #Memetic Repositories
        # Intentsity needs its standard repo.  That's hardcoded in
        # There is a default location for repository info: /usr/Intentsity/Repository
        # The user can also define other locations
        # If the user gives a repo location for the main Memetic (technical) Repository

        #Main Repo
        if self.noMainRepo is False: 
            userRoot =  expanduser("~")
            mainRepo = os.path.join(userRoot, "Intentsity", "MemeticRepository")
            Fileutils.ensureDirectory(mainRepo)
            self.additionalRepos.append(mainRepo)
         
        #Depricated, as the Intentsity repo has been moved out of this package   
        #Standard Intentsity Schema
        #myLocation = os.path.dirname(os.path.abspath(__file__))
        #tiogaRepo = os.path.join(myLocation, "IntentsityRepository")
        #self.additionalRepos.append(tiogaRepo)
        
        self.serverState = self.startupState.GRAPH_STARING
                            
        Graph.startLogger(lLevel, "utf-8", True, self.persistenceType)
        Graph.startDB(self.additionalRepos, self.persistenceType, self.persistenceArg, True, False, False, validateOnLoad)
        
        global api
        api = Graph.api.getAPI()
        #/Start Graphyne
                
        #Initialize Other Plugins
        PluginFacade.initPlugins(self.plugins)
                
        #Yeah baby!  Start dem services!
        #rtParams[u"responseQueue"]
        self.rtParams['processName'] = self.processName
        self.rtParams['engineService'] = True
        self.archiveServices = []
        self.services = []
        self.threadNames = []

        while Graph.readyToServe == False:
            time.sleep(5.0)   
            Graph.logQ.put( [logType , logLevel.DEBUG , method, "...Intentsity Engine waiting for initial loading of templates and entities to finish"])
        Graph.logQ.put( [logType , logLevel.ADMIN , method, "Templates and Entities are ready.  Intentsity Engine ready to start action indexer"])        
                     
        #now, we should make sure that all singleton memes are instantiated.
        Graph.logQ.put( [logType , logLevel.INFO , method ,"Loading Action and Stimulus Indexers"])
        self.serverState = self.startupState.INDEXING_MOLECULES
        actions = api.getEntitiesByMetaMemeType("Action.Action")
        for actionID in actions:
            actionIndexerQ.put(actionID)
            
        desriptors = api.getEntitiesByMetaMemeType("Stimulus.Descriptor")
        for desriptorID in desriptors:
            stimulusIndexerQ.put(desriptorID)
        Graph.logQ.put( [logType , logLevel.INFO , method ,"Finished initial loading of Action and Stimulus Indexers"])
         
        
        self.serverState = self.startupState.STARTING_SERVICES
        #Now we can start the service plugins
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting engine services"])
        print("starting engine services")
        for plugin in PluginFacade.engineServices:
            engineService = plugin['module']
            self.rtParams['moduleName'] = plugin['moduleName']
            dtParams = plugin['params']
            try:
                tmpClass = getattr(engineService, 'Plugin')
                service = tmpClass()
                apiCopy = copy.deepcopy(api)
                service.initialize(apiCopy, dtParams, self.rtParams)
                print(("starting = %s" %service.__class__))
                service.start()
                self.services.append(service)
                self.threadNames.append(service.getName())
                Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting %s as thread ID %s" %(service.__class__, service.getName())])
            except Exception as e:
                print(("Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)))
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)])
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "finished starting engine services"])
        print("finished starting engine services")
        
        #The modulename param, that we introduced in the loop above is obsolete, no longer relevant and we don't know what it contains
        del self.rtParams['moduleName']
        
        #init services!
        self.rtParams['engine'] = self
        self.rtParams['objectMap'] = objectMap
        self.rtParams['engineService'] = False
        self.initServices = []
        
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting init services"])
        print("starting init services")
        print((PluginFacade.initServices))
        for plugin in PluginFacade.initServices:
            engineService = plugin['module']
            self.rtParams['moduleName'] = plugin['moduleName']
            dtParams = plugin['params']
            #try:
            tmpClass = getattr(engineService, 'Plugin')
            service = tmpClass()
            service.initialize(dtParams, self.rtParams)
            Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting %s" %service.__class__])
            print(("starting = %s" %service.__class__))
            service.start()
            self.initServices.append(service)
            #except Exception as e:
                #print("Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)
                #Graph.logQ.put( [logType , logLevel.ERROR, method , "Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)])
        Graph.logQ.put( [logType , logLevel.ADMIN, method , "finished starting init services"])
        print("finished starting init services")

        Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting initialization plugins"])        
        print("starting initialization plugins")
        for plugin in PluginFacade.initUtils:
            dtParams = plugin['params']
            util = plugin['module']
            try:
                tmpClass = getattr(util, 'Plugin')
                service = tmpClass()
                service.initialize(dtParams, self.rtParams)
                Graph.logQ.put( [logType , logLevel.ADMIN , method , "executing %s" %tmpClass.__class__])
                print(("executing = %s" %service.__class__))
                service.execute()
            except Exception as e:
                print(("Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)))
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Failed to start Plugin %s.  Traceback = %s" %(str(engineService), e)])
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "finished executing initialization plugins"])
        print("finished executing initialization plugins")
        
        
        #Now signal to all of the init services that they should shut down when finished with their queues
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "shutting down initialization services"])
        print("shutting down initialization services")
        for initService in self.initServices:
            print(("stopping %s" %service.__class__))
            initService.join()
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "finished shuting down initialization services"])
        print("finished shuting down initialization services")
        self.serverState = self.startupState.READY_TO_SERVE
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        
        
    def shutdown(self):
        method = moduleName + '.' +  self.className + '.shutdown'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Engine Shutdown Started."])
        print("Finished waiting.  Shutting down service plugins.")
        for service in self.services:
            print("stopping %s thread ID %s %s" %(service.__class__, service._name, service.name))
            try:
                service.join()
                service.killServers()
                service.join()
            except Exception as e:
                print(( 'Exception while waiting for service thread to shut down. Traceback = %s' %(e)))

        print("Shutdown Started.  Waiting sixty seconds to allow log and database queues to be cleared before shutting archive services down.")
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Engine Services shut down.  Waiting twenty seconds to allow log and database queues to be cleared before shutting archive services down."])
        time.sleep(60.0)
        
        try:
            if len(threading.enumerate()) > 0:
                self.shutdownWait()
        except Exception as e:
            print(( 'Exception while waiting for child threads to shut down. Traceback = %s' %(e)))
            
        Graph.stopLogger()            
        print("Finished shutting down service and archive plugins.  Shutting Down engine")

        
        
        
    def shutdownWait(self):
        """ 
            This method is a bit wonky,as it substitutes recursive calls for a while loop. 
            It is a hackish solution to fill the need to poll the the threads that are still up
        """
        main_thread = threading.currentThread()
        canStopNow = True
        for t in threading.enumerate():
            canStopNow = True
            threadName = t.getName()
            if t is main_thread:
                continue
            elif threadName in self.threadNames:
                canStopNow = False
                print(( 'Engine waiting for thread %s to finish shutting down' %threadName))   
        if canStopNow == False:
            time.sleep(6.0)    
            self.shutdown()
        


#Globals
controllerCatalog = None
scriptLanguages = {}
logQ = queue.Queue()
aQ = queue.Queue() # action queue
siQ = queue.Queue()
actionIndexerQ = queue.Queue()
stimulusIndexerQ = queue.Queue()
stagingQ = queue.Queue() 
logType = LogType()
logLevel = LogLevel()     
linkTypes = LinkType()  


broadcasterRegistrar = BroadcasterRegistrar()
broadcasterRegistrar.indexBroadcaster('hello')

helloQ = broadcasterRegistrar.broadcasterIndex['hello']
helloQ.put("world")



def getUUIDAsString(uuidToParse):
    #ensure that the uuid given as a parameter is in unicode format
    try:
        testStr = 'x'
        testUnicode = 'x'

        if type(uuidToParse) == type(testStr):
            uuidAsString = str(uuidToParse)
            return uuidAsString
        elif type(uuidToParse) == type(testUnicode):
            #nothing to do
            return uuidToParse
        else:
            stringURN = uuidToParse.get_urn()
            partStringURN = stringURN.rpartition(":")
            uuidAsString = partStringURN[2]
            return uuidAsString
    except Exception as e:
        return "Traceback = %s" %e  


def filterListDuplicates(listToFilter):
    # Not order preserving
    keys = {}
    for e in listToFilter:
        keys[e] = 1
    return list(keys.keys())


def runscript(script):
    PluginFacade.utilities
                
