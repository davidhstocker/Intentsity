'''
Created on June 13, 2018

@author: David Stocker
'''

import threading
import time
import copy
import os
import uuid
import queue
from os.path import expanduser
import sys
from types import ModuleType

import Graphyne.Graph as Graph
from . import Exceptions
from Graphyne import Fileutils
from Intentsity import PluginFacade


class WorkerTerminationRequestStep(object):
    def __init__(self):
        self.START = 0
        self.ROLLBACK = 1
        self.COMMIT = 2
    
    
class WorkerTerminationVerificationMessage(object):
    def __init__(self):
        self.COMMIT = 0
        self.ROLLBACK = 1
        self.ERROR = 2


class StartupState(object):
    def __init__(self):
        self.INITIAL_STATE = 0
        self.GRAPH_STARING = 1
        self.INDEXING_MOLECULES = 3
        self.STARTING_SERVICES = 3
        self.READY_TO_SERVE = 4
        self.FAILED_TO_START = 5

class ActionInsertionType(object):
    def __init__(self):
        self.APPEND = 0
        self.HEAD = 1
        self.HEAD_CLEAR = 2        
        

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
serverLanguage = 'en' 
logTypes =  LogType() 
logType = logTypes.ENGINE
logLevel = LogLevel()
validateOnLoad = True
renderStageStimuli = []
terminationSteps = WorkerTerminationRequestStep()
terminationVerificationMsg = WorkerTerminationVerificationMessage()
actionInsertionTypes = ActionInsertionType()


queues = Queues()
templateQueues = []
#LogQ is always there and a module attribute
securityLogQ = queue.Queue()
lagLogQ = queue.Queue()

#Globals
controllerCatalog = None
scriptLanguages = {}
aQ = queue.Queue() # action queue
siQ = queue.Queue()
actionIndexerQ = queue.Queue()
stimulusIndexerQ = queue.Queue()
stagingQ = queue.Queue() 
logType = LogType()
logLevel = LogLevel()     


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
    stoprequest = threading.Event()

    def initialize(self, graphAPI, dtParams = None, rtParams = None):
        method = self.className + '.' + os.path.splitext(os.path.basename(__file__))[0] + '.' + 'initialize'
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , u"Design Time Parameters = %s" %(dtParams)])
        self.pluginName = rtParams['moduleName']
        try:
            name = dtParams['queue']
            self.queueName = name
            self.graphAPI = graphAPI
        except:
            self.queueName = None
            errorMessage = "Possible Error: Plugin %s is unable acquire queue name from the configuration.  If it is supposed to have a queue, please check the configuration.  Otherwise Ignore!" %self.pluginName
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMessage])
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        
    def run(self):
        while self.isAlive():
            try:
                self.execute()
            except:
                # loader plugins run as services sleep for the duration of heatbeatTick and retry the queue.
                self._stopevent.wait(self._sleepperiod)

    
    

    

    



class Broadcaster(ServicePlugin):
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
        
    def initialize(self, dtParams = None, rtParams = None):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.initialize'
        
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
            broadcasterRegistrar.broadcasterIndex[self.broadcasterID] is a broadcast queue registered 
            with the Engine's broadcast registrar.   
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.run'
        while self.isAlive():
            try:
                if self.broadcasterID not in broadcasterRegistrar.broadcasterIndex:
                    errorMsg = "%s has no queue to manage.  Shutting plugin down." %self.broadcasterID
                    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                    self.join()
                else:
                    #pop the report from myQueue and fire self.onStimulusReport()
                    stimulusReport = broadcasterRegistrar.broadcasterIndex[self.broadcasterID].get_nowait()
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
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'join'
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
    
linkTypes = LinkType() 



class ControllerCatalog(object):
    className = "ControllerCatalog"
    
    def __init__(self):
        self.indexByType = {}
        self.indexByID = {}
        
    def addController(self, controller):
        #method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.addController'
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
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.getControllersByType'
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
                metamemeChildren = Graph.api.getExtendingMetamemes(metamemeID)
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
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.indexDescriptor'
        
        #There is only one descriptor and the list length is 1,so use descriptors[0] for the descriptor uuid
        try:
            descriptorMeme = Graph.api.getEntityMemeType(descriptorID)
            descriptorMetaMeme = Graph.api.getEntityMetaMemeType(descriptorID)
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
                badMemeID = Graph.api.getEntityMemeType(stimulusUUID)
                for keyID in keyList:
                    memeID = Graph.api.getEntityMemeType(keyID)
                    memeIDList.append(memeID)
            except: pass
            errorMsg = "Descriptor %s No among registered descriptors in broadcast registrar.   Registered Descriptors = %s" %(badMemeID, memeIDList)
            raise Exceptions.NullBroadcasterIDError(errorMsg)
        except Exceptions.NoSuchBroadcasterError as e:
            raise Exceptions.NoSuchBroadcasterError(e)
        except Exceptions.QueueError as e:
            raise Exceptions.QueueError(e)    
    


class StimulusAPI(object):
    
    '''
    def getAllAgentsInAgentScope(self, agentID):
        """
            Returns all agents in the same scope as the supplied agent
        """
        
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
        
       
    def getAllLandmarksInAgentScope(self, agentID):
        """
            Returns all landmarks (of other agents) in the same scope as the supplied agent
        """
        
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark"
        ownLandmarks = Graph.api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
    
    
    
    def getAllAgentsInSpecifiedPage(self, pageUUID):
        """
            Returns agents with a scope on the supplied page
        """
        
        scopePath = "Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = Graph.api.getLinkCounterpartsByType(pageUUID, scopePath, None)
        return peers
    '''

        
        
    
    def getAllAgentsWithViewOfSpecifiedPage(self, pageUUID):
        """
            Returns agents with a view on the supplied page
        """
        scopePath = "Agent.View::Agent.Landmark::Agent.Agent"
        peers = Graph.api.getLinkCounterpartsByMetaMemeType(pageUUID, scopePath, None)
        return peers
        
    
    
    def getAgentsWithViewOfStimulusScope(self, stimulusID):
        #Given a stimulus, find all agents that are linked to the scope of the stimulus
        try:
            agentSet = set([])
            pageList = self.getStimulusScope(stimulusID)
            for pageID in pageList:
                localAgentList = self.getAllAgentsWithViewOfSpecifiedPage(pageID)
                localAgentSet = set(localAgentList)
                agentSet.update(localAgentSet)
            agentList = list(agentSet)
            return agentList
        except Exceptions.InvalidStimulusProcessingType as e:
            raise e
        except Exceptions.ScriptError as e:
            raise e
        except Exception as e:
            raise Exceptions.ScriptError(e)
    
    
            
    '''
    def getAllAgentsInAgentView(self, agentID):
        """
            Get all agents that have active scope in the view of the supplied agent
        """
        scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
     
     
        
    
    def getAllLandmarksInAgentView(self, agentID):
        """
            Get all landmarks (of other agents) that have active scope in the view of the supplied agent
        """
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark"
        ownLandmarks = Graph.api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
            
            
    
    def getAllAgentsWithAgentView(self, agentID):
        """
            Get all agents with an active view of the scope of the supplied agent
        """
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark::Agent.Agent"
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
    
        
    
    def getAllLandmarksWithAgentView(self, agentID):
        """
            Get all landmarks of other agents, where those agents have an active view of the scope of the supplied agent.
        """
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark"
        ownLandmarks = Graph.api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
     
     
    
    def getAgentView(self, agentID):
        """
            Return the pages on the supplied agent's current view.
        """
        scopePath = "Agent.Landmark::Agent.View::Agent.Page"
        viewedPages = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        return viewedPages   
        
        
    
    def getAgentScope(self, agentID):
        """
            Return the pages on the supplied agent's current scope.
        """
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page"
        peers = Graph.api.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
    '''    
        
    
    def getStimulusScope(self, stimulusID):
        """
            Return the pages on the supplied stimulus' current scope.
        """
        stimulusChoicePath = "Stimulus.StimulusChoice"
        conditionalStimulusPath = "Stimulus.ConditionalStimulus"
        stimulusPath = "Stimulus.Stimulus"
        
        metamemeType = Graph.api.getEntityMetaMemeType(stimulusID)
    
        try:
            ''' Three params: entity, metaMemePath, linkType'''
            pageIDList = []
            if metamemeType.count(stimulusChoicePath) > 0:
                localPageIDList = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                pageIDList.extend(localPageIDList)    
            elif metamemeType.count(conditionalStimulusPath) > 0:
                localPageIDListFree = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                localPageIDListAn = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                pageIDList.extend(localPageIDListFree)    
                pageIDList.extend(localPageIDListAn)
            elif metamemeType.count(stimulusPath) > 0:
                localPageIDListFree = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                localPageIDListAn = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                pageIDList.extend(localPageIDListFree)    
                pageIDList.extend(localPageIDListAn)
            else:
                #seriously, we should never need to  throw this, but let's be defensive anyway
                errorMsg = "StimulusScope methods take only the types Stimulus.Stimulus, Stimulus.ConditionalStimulus and Stimulus.StimulusChoice asarguments, not %s" %metamemeType
                raise Exceptions.InvalidStimulusProcessingType(errorMsg)  
            return pageIDList
        except Exception as e:
            errorMsg = "Unknown error selecting pages of stimulus %s.  Traceback = %s" %(stimulusID, e)
            raise Exceptions.ScriptError(errorMsg)
        
    
    
    def oc(self, stimulusID):
        """
            Return the agents with view of the supplied stimulus' current scope.
        """
        global stimulusAPI
        try:
            pageList = stimulusAPI.getStimulusScope(stimulusID)
            agentSet = set([])
            for page in pageList:
                localAgentList = stimulusAPI.getAllAgentsWithViewOfSpecifiedPage(page)
                localAgentSet = set(localAgentList)
                agentSet.update(localAgentSet)
            agentList = list(agentSet)
            return agentList
        except Exceptions.InvalidStimulusProcessingType as e:
            raise e
        except Exceptions.ScriptError as e:
            raise e
            #self.execute(stimulusID)
        except Exception as e:
            raise Exceptions.ScriptError(e)
        
        
        
stimulusAPI = StimulusAPI()

#Globals


###################
# Actiion Engine
###################

class ActionEngine(ServicePlugin):
    className = "Plugin"

    def initialize(self, dummiAPIParam, dtParams = None, rtParams = None):
        # This method overrides the initialize from the parent class.
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'initialize'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            
            self.aQ = rtParams['aQ']
            self.actionIndex = {}
            self.indexer = ActionIndexer(self.actionIndex)
            self.commQueue = queue.Queue()
            self.workerQueues = {}
            self.depricatedWorkerQueues = {}
            self._stopevent = threading.Event()
            self._sleepperiod = 0.03
            threading.Thread.__init__(self, name = "ActionEngine")
        except Exception as e:
            errorMsg = "Fatal Error while starting Action Engine. Traceback = %s" %e
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        

    def run(self):
        #method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'
        #try:
        global startupStateActionEngineFinished
        
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Engine waiting for initial loading of templates and entities to finish before it can start the registrar"])
        while Graph.readyToServe == False:
            time.sleep(5.0)
            Graph.logQ.put( [logType , logLevel.DEBUG , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run' , "...Action Engine waiting for initial loading of templates and entities to finish"])
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run' , "Templates and Entities are ready.  action indexer may now be started"])
                
        self.indexer.start()
        
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Engine waiting for action indexer to be finished before starting to serve actions"])
        while self.indexer.startupStateActionsFinished == False:
            time.sleep(10.0)
            Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "...Action Engine waiting for action indexer to be finish starting"])
        
        for actionToBeInflatedKey in self.actionIndex:
            actionToBeInflated = self.actionIndex[actionToBeInflatedKey]
            actionToBeInflated.inflateMembers()
        startupStateActionEngineFinished = True
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run' , "Action Indexer is ready.  Action Engine started"])
               
        #while not self._stopevent.isSet(  ):
        while not self.stoprequest.isSet():
            try:
                #actionInvoc = stagingQ.get_nowait()
                actionInvoc = self.aQ.get_nowait()
                
                self.brokerAction(actionInvoc)
                try:
                    request = self.commQueue.get_nowait()
                    self.manageWorkers(request)
                except queue.Empty:
                    #aQ not empty, but comm queue is. No worries
                    pass
                #except Exception as e:
                    #errorMsg = "Unknown error while trying to process action.  Traceback = %s" %e
                    #Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except queue.Empty:
                try:
                    request = self.commQueue.get_nowait()
                    self.manageWorkers(request)
                except queue.Empty:
                    #Both the aQ and comm queue are empty.  Let's sleep before trying again
                    self._stopevent.wait(self._sleepperiod)
                #except Exception as e:
                    #errorMsg = "Unknown error while trying to process worker communication.  Traceback = %s" %e
                    #Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            #except Exception as e:
            #    errorMsg = "Unknown error in action engine.  Traceback = %s" %e
            #    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                
                    
                

    def brokerAction(self, actionInvocation):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'brokerAction'
        # actionInvoc = [actionID, rtparams, insertionType]
        #actionMessage = [subjectID, objectID, controllerID, rtparams]
        
        try:
            #First, assert that we even have this action indexed
            assert actionInvocation.actionMeme.fullTemplatePath in self.actionIndex
            try:
                #DEBUG - comment out when not debugging in pydev
                #sys.path.append(r'/Applications/eclipse/plugins/org.python.pydev_3.9.0.201411111611/pysrc')
                #import pydevd
                #pydevd.settrace()
                
                #Add the action object from the registrar
                actionInvocation.action = copy.deepcopy(self.actionIndex[actionInvocation.actionMeme.fullTemplatePath])
                actionInvocation.action.refreshInstanceID()
            except AssertionError:
                securityMessage = [actionInvocation.actionMeme.fullTemplatePath, \
                                    actionInvocation.controllerID,\
                                    actionInvocation.insertionType, \
                                    actionInvocation.objectID, \
                                    actionInvocation.subjectID, \
                                    actionInvocation.rtParams]  
                errorMsg = "Unindexed action %s requested by controller %s. Security log message generated." %(actionInvocation.actionMeme.fullTemplatePath, actionInvocation.controllerID)
                Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
                securityLogQ.put(securityMessage)
            except Exception as e:
                errorMsg = "unknown error during action copy and instance ID refresh. Traceback = %s" %e
                Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
                raise e
            
            #Add the master landmark infromation
            masterLandmarkEntity = Graph.api.getEntity(actionInvocation.action.masterLandmark)
            actionInvocation.masterLandmarkUUID = masterLandmarkEntity.uuid
            
            #Remote Debugger
            #pydevd.settrace()
                
            try:
                #first the active worker threads
                assert actionInvocation.masterLandmarkUUID in self.workerQueues
                worker = self.workerQueues[actionInvocation.masterLandmarkUUID]
                if actionInvocation.insertionType == actionInsertionTypes.APPEND:
                    worker.dQueue.put( actionInvocation )
                elif actionInvocation.insertionType == actionInsertionTypes.HEAD:
                    #empty and refill the queue
                    worker.dQueue.acquire()
                    todos = []
                    inLoop = True
                    while inLoop == True:
                        try:
                            newItem = worker.dQueue.get_nowait()
                            todos.append(newItem)
                        except:
                            inLoop = False
                    worker.dQueue.put_nowait(actionInvocation)
                    for todo in todos:
                        worker.dQueue.put_nowait(todo)
                    worker.dQueue.release()
                else:
                    #HEAD_CLEAR
                    worker.dQueue.empty()
                    worker.dQueue.put_nowait(actionInvocation)
            except AssertionError:
                #now the deferred queues (because the worker threads that are trying to close themselves)
                try:
                    assert actionInvocation.masterLandmarkUUID in self.depricatedWorkerQueues
                    self.deferAction(actionInvocation.masterLandmarkUUID, actionInvocation)
                except AssertionError:
                    #no workers; active or shutting down.  We are free to make a new entry
                    worker = WorkerThread(actionInvocation.masterLandmarkUUID, self.commQueue, self.actionIndex)
                    worker.dQueue.put(actionInvocation)
                    worker.start()
                    self.workerQueues[actionInvocation.masterLandmarkUUID] = worker
                except Exception as e:
                    actionInfo = "actionID = %s,  subjectID = %s,  controllerID = %s, objectID = %s" %(actionInvocation.actionMeme, actionInvocation.subjectID, actionInvocation.controllerID, actionInvocation.objectID)
                    Graph.logQ.put( [logType , logLevel.WARNING , method , "Unknown error trying to broker action: %s, Traceback = %s " %(actionInfo, e)])

        except AssertionError:
            #Laglog candidate
            errorMsg = "Unknown Action Request: Controller = %s, subjectID = %s, actionID = %s" %(actionInvocation.controllerID, actionInvocation.subjectID, actionInvocation.actionMeme.fullTemplatePath)
            Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
        except Exceptions.UnknownAction as e:
            Graph.logQ.put( [logType , logLevel.WARNING , method , e]) 
        except Exception as e:
                actionInfo = "actionID = %s,  subjectID = %s,  controllerID = %s, objectID = %s" %(actionInvocation.actionMeme, actionInvocation.subjectID, actionInvocation.controllerID, actionInvocation.objectID)
                Graph.logQ.put( [logType , logLevel.WARNING , method , "Unknown error trying to pre-broker action: %s, Traceback = %s " %(actionInfo, e)])

            
            
    def manageWorkers(self, request):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'manageWorkers'
        # request = ([actionID, commandParams, insertionType])
        try:
            #request[0] == workerthread.self (the worker thread passes itself a as parameter
            #request[1] == request type
            #request[2] == response queue
            worker = request[0]
            respondToWorkerQueue = request[2]
            if request[1] == terminationSteps.START:
                try:
                    assert worker.queueID in self.workerQueues
                    self.depricatedWorkerQueues[worker.queueID] = []
                    del(self.workerQueues[worker.queueID])
                    respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                except AssertionError:
                    try:
                        assert worker.queueID in self.depricatedWorkerQueues
                        respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                    except AssertionError:
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Can't start closure of worker thread for landmark queue %s because it is not indexed." %worker.queueID])
                        respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                        self.deleteQueues(worker.queueID)
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , method , "Unknown error on start closure of worker thread for landmark queue %s.  Traceback = %s" %(worker.queueID, e)])
                    respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                    self.deleteQueues(worker.queueID)
    
            elif request[1] == terminationSteps.ROLLBACK:
                try:
                    # worker thread is rolling back the request
                    worker = request[0]
                    assert worker.queueID in self.depricatedWorkerQueues
                    self.workerQueues[worker.queueID] = worker
                    worker.dQueue.extend(self.depricatedWorkerQueues[worker.queueID])
                    del(self.depricatedWorkerQueues[worker.queueID])
                    respondToWorkerQueue.put(terminationVerificationMsg.ROLLBACK)
                except AssertionError:
                    try:
                        assert worker.queueID in self.workerQueues
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Disallowed request to rollback closure of worker thread for landmark queue %s because it is currently indexed as an active thread!" %(worker.queueID)])
                        respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                        self.deleteQueues(worker.queueID)
                    except AssertionError:
                        respondToWorkerQueue.put(terminationVerificationMsg.ROLLBACK)
                except Exception as e:
                    try:
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Disallowed request to rollback closure of depricated worker thread for landmark queue %s.  Traceback = %s" %(worker.queueID, e)])
                        respondToWorkerQueue.put(terminationVerificationMsg.ERROR)
                        self.deleteQueues(worker.queueID)
                    except Exception as e2:
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Syntax error in request to rollback closure of depricated worker thread for landmark queue.  Request structure should be [<workerthread>, 1].  Was actually %s.  Traceback = %s  %s." %(request, e2, e)])
                        respondToWorkerQueue.put(terminationVerificationMsg.ERROR)
                        self.deleteQueues(worker.queueID)
            else:
                try:
                    #assert worker.queueID in self.depricatedWorkerQueues
                    if len(self.depricatedWorkerQueues[worker.queueID]) > 1:
                        #There has been no activity since the worker began shutdown.  We can close the queue
                        try:
                            #This is a bug that seems to happen when dealing with action sets.  There is a dissonance between
                            #    the different queue indexes.  It appears that the worker is being deleted from both too early
                            #    Just remark out the assert for now and note it as a potential problem later.
                            #assert worker.queueID in self.workerQueues
                            del(self.depricatedWorkerQueues[worker.queueID])
                            respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                            self.deleteQueues(worker.queueID)
                        except AssertionError:
                            Graph.logQ.put( [logType , logLevel.ERROR , method , "Disallowed request to finalize closure of depricated worker thread for landmark queue %s because it is neither indexed as an active or depricated thread!" %(worker.queueID)])
                            respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)    
                            self.deleteQueues(worker.queueID)                    
                    else:
                        try:
                            if len(self.depricatedWorkerQueues[worker.queueID]) > 0:
                                #New tasks have come in while the worker was shutting down.  
                                #  We must re-initialize a new worker for this queue
                                newWorker = WorkerThread(worker.queueID, self.commQueue, self.actionIndex)
                                for actionMessage in self.depricatedWorkerQueues[worker.queueID]:
                                    newWorker.dQueue.append(actionMessage)
                                newWorker.start()
                                self.workerQueues[newWorker.queueID] = newWorker
                                #todo - actionmessage is not in scope
                            del(self.depricatedWorkerQueues[worker.queueID])
                            respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                        except Exception as e:
                            try:
                                Graph.logQ.put( [logType , logLevel.ERROR , method , "Problematic request to finalize closure of depricated worker thread for landmark queue %s.  Traceback = %s" %(worker.queueID, e)])
                                respondToWorkerQueue.put(terminationVerificationMsg.ERROR)
                                self.deleteQueues(worker.queueID)
                            except Exception as e2:
                                Graph.logQ.put( [logType , logLevel.ERROR , method , "Syntax error in request to finalize closure of depricated worker thread for landmark queue.  Request structure should be [<workerthread>, 1].  Was actually %s.  Traceback = %s  %s." %(request, e2, e)])
                                respondToWorkerQueue.put(terminationVerificationMsg.ERROR)
                                self.deleteQueues(worker.queueID)
                except AssertionError:
                    try:
                        assert worker.queueID in self.workerQueues
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Disallowed request to finalize closure of worker thread for landmark queue %s because it is currently indexed as an active thread!" %(worker.queueID)])
                        respondToWorkerQueue.put(terminationVerificationMsg.COMMIT)
                        self.deleteQueues(worker.queueID)
                    except AssertionError:
                        Graph.logQ.put( [logType , logLevel.ERROR , method , "Disallowed request to finalize closure of depricated worker thread for landmark queue %s because it is neither indexed as an active or depricated thread!" %(worker.queueID)])
                        respondToWorkerQueue.put(terminationVerificationMsg.ERROR) 
                        self.deleteQueues(worker.queueID)                       
        except queue.Empty:
            respondToWorkerQueue.put(True)
        except Exception as e:
            Graph.logQ.put( [logType , logLevel.ERROR , method , "Unknown error trying to manage worker thread. Traceback = %s " %(e)])
  
        
            
    def deferAction(self, masterLandmarkUUID, actionMessage):
        """Puts the action into the deferment purgatory of self.depricatedWorkerQueues for later use.
            Stash the request there for the time being while the worker thread sort's its situation out
            The request has been deferred until either the worker rolls back its termination, or commits it; 
                in which case we'll be adding these requests to a new one.
        """
        deferredActions = self.depricatedWorkerQueues[masterLandmarkUUID]
        deferredActions.append(actionMessage)
        
        
        
    def deleteQueues(self, queueIDToDelete):
        """
            This method is used to remove any queues associated with a worker thread.
        """
        #method = moduleName + '.' + self.className + '.' + 'deleteQueues'
        #errorMsg = "Forcing deletion of management infrastructure for worker queue %s" %queueIDToDelete
        #Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        try: del self.workerQueues[queueIDToDelete]
        except: pass
        try: del self.depricatedWorkerQueues[queueIDToDelete]
        except: pass
        
            
            
    def join(self,timeout = None):
        """
        Stop the thread
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'join'
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Action Engine initiating shutdown"])
        
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "...terminating workers"])
        workerCount = 0
        keyList = []
        
        for workerKeyID in self.workerQueues.keys():
            keyList.append(workerKeyID)
            
        for workerKey in keyList:
            try:
                workerToBeTerminated = self.workerQueues[workerKey]
                workerToBeTerminated.join(0.5)
                workerCount = workerCount + 1
                Graph.logQ.put( [logType , logLevel.DEBUG , method , "......terminated worker thread for action queue %s" %(workerKey)])
            except Exception as e:
                Graph.logQ.put( [logType , logLevel.ERROR , method , "...Problem trying to terminate worker thread %s.  Traceback = %s" %(workerKey, e)])
        Graph.logQ.put( [logType , logLevel.INFO , method , "...terminated %s active workers" %(workerCount)])
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "...finished terminating workers"])
        
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "...shutting down indexer"])
        self.indexer.join(0.5)
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "...indexer shut down"])
        
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Action Engine shutting down"])
        #self._stopevent.set()
        #threading.Thread.join(self, 0.5)
        self.stoprequest.set()
        super(ActionEngine, self).join(0.5)
        

class WorkerThread(threading.Thread):
    className = "WorkerThread"
    
    def __init__(self, queueID, commQueue, actionIndex):
        """
            queueID = the uuid of the entity landmark that the queue is associated with.  The workerQueues dictionary object uses
                this value as the key for the worker thread's entry.  The worker needs to track this value because it communicates 
                with the main AE thread via queue object and the UID is used as the identifier.
            commQueue = the queue object that the worker uses to communicate with the main AE thread
            registrarQueryQueue = the queue object that the worker uses to communicate with the action registrar
            actionIndex - a pointer to the main AE actionIndex, so that unpacked child actions in sets can be verified.
        """
        #self.name = "ActionEngineWorkerThread_%s" %queueID
        self.queueID = queueID
        #self.dQueue = queue
        self.dQueue = queue.Queue()
        self.commQueue = commQueue # the commQueue of the plugin object
        self.localCommQueue = queue.Queue() # a local queue object for processing receipt verification of commQueue tasks
        self.registrarCommQueue = queue.Queue()
        self._stopevent = threading.Event()
        self._sleepperiod = 0.1
        self.terminationStarted = False
        self.actionCount = 0
        self.actionIndex = actionIndex
        threading.Thread.__init__(self)

        
    def run(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'
        while self.isAlive():
            actionInvocation = None
            try:
                #toBeLogged = the memeID
                #actionInvocation = self.dQueue.popleft()
                actionInvocation = self.dQueue.get_nowait()
            except queue.Empty as e:
                try:
                    self.shutdown()
                except Exceptions.WorkerThreadTerminationRollback:
                    #nothing to do.we have broken out of the termination
                    pass
            except Exception as e:
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Error popping action from worker dQueue %s.  Clearing Queue.  Traceback = %s" %(actionInvocation, e)])
                self.dQueue.empty()
                
            
            try:
                if actionInvocation is None:
                    self.shutdown()
                else:
                    
                    #If actionInvocation is the flagged AcrionRequest that we have been waiting for 
                    #    (stored in self.shutdownBlockingAction), then we can remove that blocking action flag.
                    self.actionCount = self.actionCount + 1
                    
                    testKeyFrame = Action.KeyFrame()
                    testActionSet = Action.ActionSet()
                    testThrow = Action.Throw()
                    testCatch = Action.Catch()
                    
                    if self.terminationStarted == True:
                        self.commQueue.put( [self, terminationSteps.ROLLBACK, self.localCommQueue] )
                        self.terminationStarted = False
                        
                    #debug
                    #debugMessage = "popping action invocation %s from action queue %s" %(actionInvocation.actionMeme.fullTemplatePath, self.queueID)
                    #debug
                        
                    if type(testActionSet) == type(actionInvocation.action):
                        """
                            Voodoo Warning!  
                                - We have an ActionSet that must be unpacked and posted to the left side of the dQueue.
                                - Additionally,we are going to need registrar access to fully build the action request objects of the keyframes
                                
                            Strategy:
                                1 - Open up the ActionSet, and create a new list of ActionRequestobjects;one for each keyframe
                                2 - Make sure that they are all head insert.
                                3 - reverse the order of the list (last keyframe in the sequence first.  first keyframe in the sequence last.)
                                4 - In the new order,post these new action requests.
                                5 - Because each has a head revision, they are added to the dQueue in reverse order from how they were posted to the aQ. They are now in the proper order
                        """
                        
                        #first, test the landmarks and and throw the whole choreography out if they don't work out
                        landmarksOK = actionInvocation.action.checkLandmarks(actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
                        if landmarksOK == True:
                            actionSetKeyframes = []
                            #debug
                            debugMessage = "%s is an ActionSet" %actionInvocation.actionMeme.fullTemplatePath
                            Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                            memenames = []
                            actionSetChildren = Graph.api.getLinkCounterpartsByMetaMemeType(actionInvocation.action.uuid, "Action.ChoreographyStep", None, False)
                            for actionSetChild in actionInvocation.action.packedMemberList:
                                try:
                                    memenames.append(actionSetChild)
                                except:
                                    pass
                            debugMessage = "ActionSet %s has members: %s" %(actionInvocation.actionMeme.fullTemplatePath, memenames)
                            Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                            #/debug
                            
                            #for taskItem in actionInvocation.action.memberList:
                            for taskItem in actionInvocation.action.packedMemberList:
                                actionSubInvocation = ActionRequest(taskItem, actionInsertionTypes.HEAD, actionInvocation.rtParams, actionInvocation.subjectID, actionInvocation.objectID, actionInvocation.controllerID, actionInvocation.decoratingLandmarks)
                                actionSetKeyframes.append(actionSubInvocation)
                            
                            #actionSetKeyframes.reverse()
                            for actionSetKeyframe in actionSetKeyframes:
                                #aQ.put(actionSetKeyframe)
                                try:
                                    #This is an abbreviated version of the plugin.brokerAction() method.  Basically, the child actionSetKeyframe
                                    #  Needs to go back into the queue, at the head position.  We'll do this directly from within the worker.run()
                                    #  method to endure that the relative execution order of the children stays the same.  We are appending to the 
                                    #  head of the queue, which means FILO.  If we cycled back through the main Action Engine queue and it was idle,
                                    # then it would processing later step actions before earlier step actions were even placed in the queue.
                                    
                                    
                                    #First, assert that we even have this action indexed
                                    assert actionSetKeyframe.actionMeme.fullTemplatePath in self.actionIndex
                                    try:
                                        actionSetKeyframe.action = copy.deepcopy(self.actionIndex[actionSetKeyframe.actionMeme.fullTemplatePath])
                                        actionSetKeyframe.action.refreshInstanceID()
                                    except AssertionError:
                                        securityMessage = [actionSetKeyframe.actionMeme.fullTemplatePath, \
                                                            actionSetKeyframe.controllerID,\
                                                            actionSetKeyframe.insertionType, \
                                                            actionSetKeyframe.objectID, \
                                                            actionSetKeyframe.subjectID, \
                                                            actionSetKeyframe.rtParams]  
                                        errorMsg = "Unindexed action %s requested by controller %s. Security log message generated." %(actionSetKeyframe.actionMeme.fullTemplatePath, actionSetKeyframe.controllerID)
                                        Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
                                        securityLogQ.put(securityMessage)
                                    except Exception as e:
                                        errorMsg = "unknown error during action copy and instance ID refresh. Traceback = %s" %e
                                        Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
                                        raise e
                                    
                                    #Add the master landmark infromation
                                    masterLandmarkEntity = Graph.api.getEntity(actionSetKeyframe.action.masterLandmark)
                                    actionSetKeyframe.masterLandmarkUUID = masterLandmarkEntity.uuid
                                        
                                    #self.dQueue.appendleft(actionSetKeyframe)
                                    self.dQueue.put_nowait(actionSetKeyframe)
                                    #debug
                                    debugMessage = "posting choreography %s member %s to action queue" %(actionInvocation.actionMeme.fullTemplatePath, actionSetKeyframe.actionMeme.fullTemplatePath)
                                    Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                                    #/debug 
                                    
                                except AssertionError:
                                    #Laglog candidate
                                    errorMsg = "Unknown Action Request: Controller = %s, subjectID = %s, actionID = %s" %(actionSetKeyframe.controllerID, actionSetKeyframe.subjectID, actionSetKeyframe.actionMeme.fullTemplatePath)
                                    Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
                                except Exceptions.UnknownAction as e:
                                    Graph.logQ.put( [logType , logLevel.WARNING , method , e]) 
                                except Exception as e:
                                        actionInfo = "actionID = %s,  subjectID = %s,  controllerID = %s, objectID = %s" %(actionSetKeyframe.actionMeme, actionSetKeyframe.subjectID, actionSetKeyframe.controllerID, actionSetKeyframe.objectID)
                                        Graph.logQ.put( [logType , logLevel.WARNING , method , "Unknown error trying to pre-broker action: %s, Traceback = %s " %(actionInfo, e)])                           
                    elif type(testCatch) == type(actionInvocation.action):
                        pass  # only react on catch inside of catchQueueException() 
                    elif type(testThrow) == type(actionInvocation.action):
                        self.catchQueueException()
                    else:
                        #keyframe processing
                        try:
                            self.processKeyFrame(actionInvocation)
                        except Exceptions.ActionKeyframeExecutionError as e:
                            self.catchQueueException()
                        except Exception as e:
                            #keyframe processing
                            try:
                                self.processKeyFrame(actionInvocation)
                            except Exceptions.ActionKeyframeExecutionError:
                                self.catchQueueException()
                            except Exception as e:
                                fullerror = sys.exc_info()
                                errorMsg = str(fullerror[1])
                                errorID = str(fullerror[0])
                                #tb = sys.exc_info()[2]
                                #raise Exceptions.ScriptError(ex).with_traceback(tb)
                                errorMsg = "Uncaught exception [%s] occurred while processing keyframe %s from controller %s.  Traceback = %s" %(errorID, actionInvocation.actionMeme.fullTemplatePath, actionInvocation.controllerID, errorMsg)
                                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except IndexError as e:
                dummyErrorMsg = e
                try:
                    self.shutdown()
                except Exceptions.WorkerThreadTerminationRollback:
                    #nothing to do.we have broken out of the termination
                    pass
                except:
                    self._stopevent.set()
            except AttributeError as e:

                errorMsg = "Unregistered Action: actionID = %s,  subjectID = %s,  controllerID = %s, objectID = %s.  Traceback = %s" %(actionInvocation.actionMeme, actionInvocation.subjectID, actionInvocation.controllerID, actionInvocation.objectID,e)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except Exception as e:
                fullerror = sys.exc_info()
                errorMsg = str(fullerror[1])
                errorID = str(fullerror[0])
                errorMsg = "Uncaught exception [%s] occurred while processing action queue %s.  Traceback = %e" %(errorID, actionInvocation, errorMsg)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                Graph.logQ.put( [logType , logLevel.ERROR , method , "Unknown error processing action queue %s.  Traceback = %s" %(actionInvocation, e)])
                try:
                    self.shutdown()
                except Exceptions.WorkerThreadTerminationRollback:
                    #nothing to do.we have broken out of the termination
                    pass
                except:
                    self._stopevent.set()
    
    
    def catchQueueException(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'catchQueueException'
        try:
            while True:
                nextTask = self.dQueue.get_nowait()
                nextTaskType = nextTask.action.__class__.__name__
                nextTaskMeme = nextTask.actionMeme.fullTemplatePath
                if nextTaskType == 'Catch':
                    #Todo: lagLog
                    logMessage = "%s cleared action %s from action engine worker queue %s.  Subject = %s, Object = %s.  Action is catch.  Queue clearing halted." %(method, nextTask.actionMeme.fullTemplatePath, nextTask.actionID, nextTask.subjectID, nextTask.objectID)
                    Graph.logQ.put( [logType , logLevel.DEBUG , method , logMessage])
                    break
                else:
                    #Todo: lagLog
                    logMessage = "%s cleared action %s from action engine worker queue %s.  Subject = %s, Object = %s.  Action is not a catch and the queue will continue to be cleared." %(method, nextTask.actionMeme.fullTemplatePath, nextTask.actionID, nextTask.subjectID, nextTask.objectID)
                    Graph.logQ.put( [logType , logLevel.DEBUG , method , logMessage])
        except queue.Empty as e:
            #we have an empty dQueue and are not awaiting a any unpacked keyframes.  Go ahead and start shutting down
            try:
                self.shutdown()
            except Exceptions.WorkerThreadTerminationRollback:
                #nothing to do.we have broken out of the termination
                pass
        except Exception as e:
            Graph.logQ.put( [logType , logLevel.ERROR , method , "Error popping action from worker dQueue %s.  Clearing Queue.  Traceback = %s" %(self.__name, e)])
            self.dQueue.empty()
        
        
    def processKeyFrame(self, actionInvocation):
        #since object selection will call conditions on several occasions, we'll use x as the conditions' argumentMap
        #    We'll have to add the action, subject and controller info
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'processKeyFrame'
        try:
            actionInvocation.rtParams["_intentsity_actionID_local"] = actionInvocation.action.instanceID
            actionInvocation.rtParams["_intentsity_processorID"] = self.queueID
            actionInvocation.rtParams["actionID"] = actionInvocation.action.uuid
            actionInvocation.rtParams["subjectID"] = actionInvocation.subjectID 
            actionInvocation.rtParams["controllerID"] = actionInvocation.controllerID
            actionInvocation.rtParams["_stimulusQueue"] = siQ
        
            #First check for validity
            landmarksOK = actionInvocation.action.checkLandmarks(actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
            conditionsOK = actionInvocation.action.checkConditions(actionInvocation.rtParams)
            if (landmarksOK == False) or (conditionsOK == False):
                errorMsg = ""
                actionMeme = Graph.api.getEntityMemeType(actionInvocation.rtParams["actionID"])
                subjectMeme = Graph.api.getEntityMemeType(actionInvocation.rtParams["subjectID"])
                if (landmarksOK == False):
                    #debug
                    landmarksOK = actionInvocation.action.checkLandmarks(actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
                    #/debug
                    errorMsg = "Landmarks Invalid for action %s by subject %s.  " %(actionMeme, subjectMeme)
                if (conditionsOK == False):
                    errorMsg = "Conditions Invalid for action %s by subject %s.  " %(actionMeme, subjectMeme)
                raise Exceptions.ActionKeyframeExecutionError(errorMsg)
            
            startTime = time.time()
            
            objectList = actionInvocation.action.selectObjects(actionInvocation.rtParams, actionInvocation.objectID)
            actionInvocation.rtParams["objectID"] = objectList

            actionInvocation.action.changeStates(actionInvocation.rtParams)
            actionInvocation.action.broadcastStimuli(actionInvocation.rtParams)
            try:
                #rtParams, subjectID, controllerID, objectIDs
                #Execute any logic specific to the action
                
                actionInvocation.action.invoke(actionInvocation.rtParams)
                
            except Exception as e:
                errorMsg = "Error while invoking script on keyframe %s on landmark %s.  Subject = %s, object = %s  Traceback = %s" %(actionInvocation.actionMeme, self.queueID, actionInvocation.subjectID, actionInvocation.objectID, e)
                Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
                raise Exceptions.ActionKeyframeExecutionError(e)
                        
            #Now ensure that the action takes the required time
            endTime = time.time()
            duration = endTime - startTime
            #requiredTime = Graph.api.evaluateEntity(action.timescale, rtParams, action.uuid, subjectID, controllerID, True)
            requiredTime = 0.0
            cooldown = requiredTime - duration
            if cooldown > 0:
                time.sleep(cooldown) 
        except Exceptions.ActionKeyframeExecutionError as e:
            actionMeme = None
            subjectMeme = None
            objectMeme = None
            try:
                actionMeme = Graph.api.getEntityMemeType(actionInvocation.rtParams["actionID"])
            except: pass
            try:
                subjectMeme = Graph.api.getEntityMemeType(actionInvocation.subjectID)
            except: pass
            try:
                objectMeme = Graph.api.getEntityMemeType(actionInvocation.objectID)
            except: pass
            errorMsg = "Nested Exceptions.ActionKeyframeExecutionError Error while processing keyframe %s on landmark %s.  Subject = %s, object = %s  Traceback = %s" %(actionMeme, self.queueID, subjectMeme, objectMeme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            raise Exceptions.ActionKeyframeExecutionError(errorMsg) 
        except Exception as e:
            actionMeme = None
            subjectMeme = None
            objectMeme = None
            try:
                actionMeme = Graph.api.getEntityMemeType(actionInvocation.rtParams["actionID"])
            except: pass
            try:
                subjectMeme = Graph.api.getEntityMemeType(actionInvocation.subjectID)
            except: pass
            try:
                objectMeme = Graph.api.getEntityMemeType(actionInvocation.objectID)
            except: pass
            errorMsg = "Error while processing keyframe %s on landmark %s.  Subject = %s, object = %s  Traceback = %s" %(actionMeme, self.queueID, subjectMeme, objectMeme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            raise Exceptions.ActionKeyframeExecutionError(errorMsg)
            


    def shutdown(self):
        """
        We have reached the end of the deque (encountered an IndexError) or have caught an unknown exception.  
            Our work is either done, or there is a fatal problem.  In order for a concurrency-safe shutdown to occur:
            1 - We have to inform the manager that we wish to shut down.  The manager will then switch over to the 
                to deferring actions requests to the depricated queue
            2 - A new work item may have come into self.dQueue between the exception reading it and the termination request
                being processed by the manage.  Therefore, we need to wait a bit and check again (after this method returns)
                before actually closing 
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'shutdown'
        if self.terminationStarted == False:
            #inform the manage that we wish to terminate
            #  Then wait 50 miliseconds before retrying dQueue
            self.terminationStarted = True
            self.commQueue.put( [self, terminationSteps.START, self.localCommQueue] )
            self._stopevent.wait(self._sleepperiod) 
            try:
                self.awaitVerification()
                self.finalizeShutdown()
                #raise SystemExit()
                sys.exit()
            except Exceptions.WorkerThreadTerminationRollback:
                raise Exceptions.WorkerThreadTerminationRollback()
            except Exceptions.WorkerThreadIndexError:
                # AE returned terminationVerificationMsg.ERROR
                self.finalizeShutdown(False)
                raise SystemExit()
            except Exception as e:
                errorMsg = "Abnormal termination start of worker thread %s, for landmark %s.  Traceback = %s" %(self._Thread__name, self.queueID, e)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                self.finalizeShutdown(False)
                raise SystemExit(errorMsg)
        else:
            #We are truly ready to close
            try:
                self.finalizeShutdown()
            except Exceptions.WorkerThreadTerminationRollback:
                raise Exceptions.WorkerThreadTerminationRollback()
            except Exception:
                #errors already logged in the finalizeShutdown method
                pass




    def awaitVerification(self):
        """
            When a worker thread proposes a shutdown, it should wait for message verification from the AE
            before continuing so that the internal state of the thread does not get out of sync with the AE.
            In essence, while awaitVerification() is running, the worker is no longer a free running thread,
            but is forced into a temporary lockstep with the parent AE.
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'awaitVerification'
        while True:
            try:
                self._stopevent.wait(self._sleepperiod)
                verification = self.localCommQueue.get_nowait()
                if verification == terminationVerificationMsg.COMMIT:
                    #The parent AE agrees that we can shutdown.  Terminate
                    break
                elif verification == terminationVerificationMsg.ROLLBACK:
                    #Roll back the termination
                    raise Exceptions.WorkerThreadTerminationRollback()
                elif verification == terminationVerificationMsg.ERROR:
                    errorMsg = "Worker thread for landmark %s is improperly indexed" %self.queueID
                    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                    raise Exceptions.WorkerThreadIndexError(errorMsg)
                else:
                    #Should not happen
                    errorMsg = "Unexpected shutdown verification response for worker thread on landmark %s" %self.queueID
                    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                    raise Exceptions.WorkerThreadIndexError(errorMsg)
                break
            except queue.Empty:
                pass
            except Exceptions.WorkerThreadTerminationRollback:
                raise Exceptions.WorkerThreadTerminationRollback()
            except Exception as e:
                errorMsg = "Unexpected error during shutdown verification process for worker thread on landmark %s.  Traceback= %s" %(self.queueID, e)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
                raise e
            
            
    def finalizeShutdown(self, awaitVerification = True):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'finalizeShutdown'
        self.commQueue.put( [self, terminationSteps.COMMIT, self.localCommQueue] )
        try:
            if awaitVerification == True:
                self.awaitVerification()
            self._stopevent.set()
            #raise SystemExit()
            sys.exit()
        except Exceptions.WorkerThreadTerminationRollback:
            raise Exceptions.WorkerThreadTerminationRollback()
            # AE returned terminationVerificationMsg.ERROR
        except Exception as e:
            errorMsg = "Abnormal termination commit of worker thread for landmark %s.  Traceback = %s" %(self.queueID, e)
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            self._stopevent.set()
            raise SystemExit()

                  
                    
    
    def join(self, timeout = 0.5):
        """
        Stop the thread
        """
        self.dQueue.empty()
        self._stopevent.set()
        threading.Thread.join(self, 0.5)

class ActionIndexer(threading.Thread):
    className = "ActionIndexer"
    
    def __init__(self, actionIndex, useActionIndexerQ = True):
        """
            indexOver = a Queue.Queue object: iterate over it in the run loop.  (continual indexing of loaded action singletons)
            indexOver = None.  Index over the Entity repository ( Engine.entityRepository ) once, looking for actions.
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + '__init__'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
        self.actionIndex = actionIndex
        self.useActionIndexerQ = useActionIndexerQ
        
        #It may be possible that multiple registrars are in use (such as in module testing)
        #    In those cases, we want to ensure that the registrar will only set startupStateActionsFinished to true
        #    the first time that we complete indexing of the repo, or run into an empty index queue and not on every loop
        self.startupStateActionsFinished = False
        
        self._stopevent = threading.Event()
        self._sleepperiod = 30.0
        threading.Thread.__init__(self)
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Action Indexer ready start caching action entities"])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])

        
    def run(self):
        Graph.logQ.put( [logType , logLevel.INFO , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer Starting"])
        startTime = time.time()
        
        #Remote debugging support
        #pydevd.settrace()
        
        if self.useActionIndexerQ == False:
            #index directly off of the entity repository; no later updates
            
            # if we iterate over the repo, there is always the danger of it changing while we work.  let's take a snapshot
            repoEntries = []
            entityList = Graph.api.getAllEntities()
            for entityID in entityList:
                repoEntries.append(entityID)
            
            numberOfEntities = len(repoEntries)
            Graph.logQ.put( [logType , logLevel.INFO , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Indexer has %s entities to check" %numberOfEntities])
            #Now filter this list down to ones with "Action.Action" in their taxonomy
            fullMetamemeTaxonomyEntries = []
            nth = 1
            for entityID in repoEntries:
                try:
                    memeID = Graph.api.getEntityMemeType(entityID)
                    fullMetamemeTaxonomy = Graph.api.getTaxonomy(memeID)
                    if "Action.Action" in fullMetamemeTaxonomy:
                        #actionIndexerQ.put(entityID)
                        fullMetamemeTaxonomyEntries.append(entityID)
                    Graph.logQ.put( [logType , logLevel.INFO , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Determined taxonomy on %s of %s entities" %(nth, numberOfEntities)])
                    nth = nth + 1
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Unknown error indexing action %s.  Traceback = %s" %(entityID, e)])
                  
            #Now index the actions
            numberOfActions = len(fullMetamemeTaxonomyEntries)  
            Graph.logQ.put( [logType , logLevel.INFO , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Indexer has %s actions to index" %numberOfActions])      
            jth = 1
            for toBeIndexed in fullMetamemeTaxonomyEntries:
                try:
                    self.indexItem(toBeIndexed)
                    Graph.logQ.put( [logType , logLevel.INFO , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Indexed %s of %s actions" %(jth, numberOfActions)])
                    jth = jth + 1
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Unknown error indexing action %s.  Traceback = %s" %(entityID, e)])

            
            endTime = time.time()
            deltaT = endTime - startTime
            self.startupStateActionsFinished = True
            Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Finished ad hoc load run"])
            Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Indexed %s actions in %s seconds" %(len(fullMetamemeTaxonomyEntries), deltaT)])
            Graph.logQ.put( [logType , logLevel.DEBUG , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "exiting"])
        else:
            #index off of the chosen queue
            nTh = 0
            finishedInitialIndexing = False
            while self.isAlive():
                try:
                    #toBeLogged = the memeID
                    Graph.logQ.put( [logType , logLevel.DEBUG , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Checking Action Indexer Q.  Current number of estimated workitems = %s" %(actionIndexerQ.qsize())])
                    toBeIndexed = actionIndexerQ.get_nowait()
                    try:
                        Graph.logQ.put( [logType , logLevel.DEBUG , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer off of the chosen queue - Index %s" %(toBeIndexed)])
                        self.indexItem(toBeIndexed)
                        nTh = nTh + 1
                    except Exception as e:
                        Graph.logQ.put( [logType , logLevel.ERROR , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Problem indexing action %s.  Traceback = %s" %(toBeIndexed, e)])
                except queue.Empty:
                    if finishedInitialIndexing == False:
                        finishedInitialIndexing = True
                        endTime = time.time()
                        deltaT = endTime - startTime
                        self.startupStateActionsFinished = True
                        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Finished initial loading from engine action indexer queue"])
                        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Indexed %s actions in %s seconds" %(nTh, deltaT)])
                    self._stopevent.wait(self._sleepperiod)
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Action Indexer - Unknown Error.  Traceback = %s" %e])
                    self._stopevent.wait(self._sleepperiod)
                   


    def join(self, timeout = 0.5):
        '''
        Stop the thread
        '''
        try:
            method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'join'
            Graph.logQ.put( [logType , logLevel.ADMIN , method , '......Action Indexer shutting down'])
            self._stopevent.set()
            threading.Thread.join(self, 0.5)
        except Exception as e:
            unusedDebugCatch = e
                    
                    


    def indexItem(self, toBeIndexed):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'indexItem' 
        #toto - revert to .INFO
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"]) 
        try:
            action = getActionIndexItem(toBeIndexed)
            
            #Actions are initially created with an empty dict for action index.
            #Add the action index to the actions so that they can later run getInflatedMemberList()
            action.actionIndex = self.actionIndex
            
            #Actions are indexed by meme path
            #self.registrar.actionIndex[action.meme] = action
            self.actionIndex[action.meme] = action
            Graph.logQ.put( [logType , logLevel.INFO , method, "Indexed %s to action registrar" %action.meme])
        except Exceptions.ScriptError as e:
            actionMeme = Graph.api.getEntityMemeType(toBeIndexed)
            errorMsg = "Error indexing action %s %s.  Traceback = %s" %(actionMeme, toBeIndexed, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
            raise e
        except Exception as e:
            actionMeme = Graph.api.getEntityMemeType(toBeIndexed)
            errorMsg = "Error indexing action %s %s.  Traceback = %s" %(actionMeme, toBeIndexed, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
            raise e
        finally:
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
            pass
        
        
class Action(object):
    className = 'Action'
    actionIndex = {}  # parameter is the action engine's action index and is used later to inflate member lists
    
    def initialize(self, uuid, actionID):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'initialize'
        """
            uuid = the uuid of the child action element (KeyFrame, Catch, Throw, etc.)
            actionID = the uuid of the parent Action element
        """
        Graph.logQ.put( [logType , logLevel.DEBUG , method, "entering"])
        try:
            self.uuid = uuid
            self.meme = Graph.api.getEntityMemeType(actionID)
            self.actionID = actionID
            self.instanceID = None
        except Exception as e:
            errorMsg = "Unknown error initializing action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "exiting"])
        
        
    def refreshInstanceID(self):
        """
            Actions are singletons and self.uuid points back to the uuid of the memetic entity in the entity repository.
            Actions are initialized as singletons for performance reasons (to frontload the initialization overhead to server startup)
            and because actions of a given type are fungible.  However, we still want to have each instance of an action to have a 
            unique tracking ID for the lag-log's action life cycle tracking.
            
            Calling this method will generate a new UUID
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'refreshInstanceID'
        try:
            self.instanceID = uuid.uuid1()
        except Exception as e:
            errorMsg = "Unknown error refreshing instance UUID on action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
        
            
    def getInflatedMemberList(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'getInflatedMemberList'
        try:
            return [self.meme]
        except:
            errorMsg = "Can't run getInflatedMemberList() on initialized action" 
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            return []  
        
        
    def inflateMembers(self):
        #this method is only relevant for sets
        pass       
    
    
            
    def addLandMarks(self):
        """
            Find all of the landmarks attached to the keyframe
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addLandMarks'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            
            # The template paths of the various types of landmarks
            #lmExPath = "Action.RequiredLandmarks::Action.RequiredlandmarksExclusive::Action.RequiredLandmark::Agent.Landmark"
            #lmMPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
            #lmNoExPath = "Action.RequiredLandmarks::Action.RequiredLandmark::Agent.Landmark"
            
            lmExPath = "**::Action.RequiredlandmarksExclusive::Action.RequiredLandmark::Agent.Landmark"
            lmMPath = "**::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
            lmNoExPath = "**::Action.RequiredLandmark::Agent.Landmark"
            
            # Get the actual uuids of the various landmarks
            self.landmarksNonExclusive = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, lmNoExPath)
            self.landmarksExclusive = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, lmExPath)
            masterLandmarkList = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath)
            try:
                self.masterLandmark = masterLandmarkList[0]
            except IndexError:
                #No Master Landmarks turned up.  This might be because of a badly crafted action cluster
                #  Graphene.graph.getLinkCounterpartsByMetaMemeType() currently has no ability to traverse ancestor metamemes
                #  Intensity's built in actions use the Agent.TagMM metameme in place of Agent.Landmark.  TagMM is subclassed  
                #  from Landmark, This means that Intensity's built in actions won't show any landmarks and won't register
                #  as actions.  This is a workaround to make this work, until an optional 'family tree traverse' can be added
                #  to Graphene.graph.getLinkCounterpartsByMetaMemeType()
                try:
                    lmMPath = "**::Action.MasterLandmark::Action.RequiredLandmark::Agent.TagMM"
                    masterLandmarkList = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath)
                    self.masterLandmark = masterLandmarkList[0]
                except Exception as e:
                    errorMsg = "Action %s has no master landmark defined" %self.meme
                    raise Exceptions.MemeMembershipValidationError(errorMsg)
            except Exceptions.MemeMembershipValidationError as e:
                raise e
            except Exception as e:
                masterLandmarkList = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath)
                errorMsg = "Action %s has no master landmark defined" %self.meme
                raise Exceptions.MemeMembershipValidationError(errorMsg)
            
            #Remote Debugger
            #pydevd.settrace()
            
            #self.landmarkTransforms = []
            reqLMRootPath = "**::Action.RequiredLandmark"
            reqLMPath = "Agent.Landmark"
            #reqLMTransformPath = "Action.LandmarkTransform"
            reqLMRoots = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, reqLMRootPath)
            for reqLMRoot in reqLMRoots:
                reqLMs = Graph.api.getLinkCounterpartsByMetaMemeType(reqLMRoot, reqLMPath)
                #reqLMTransforms = Graph.api.getLinkCounterpartsByMetaMemeType(reqLMRoot, reqLMTransformPath)
                # Action.LandmarkTransform is optional, but a transform element only makes sense if one exists
                '''
                if len(reqLMTransforms) > 0:
                    #Agent.Offset
                    deltaX = None
                    deltaY = None
                    deltaZ = None
                    offsetDelta = Graph.api.getLinkCounterpartsByMetaMemeType(reqLMTransforms[0], "Agent.Offset")
                    if len(offsetDelta) > 0:
                        deltaX = Graph.api.getEntityPropertyValue(offsetDelta[0], "x")
                        deltaY = Graph.api.getEntityPropertyValue(offsetDelta[0], "y")
                        deltaZ = Graph.api.getEntityPropertyValue(offsetDelta[0], "z")
                        
                    #Agent.EuerAngles
                    rotationX = None
                    rotationY = None
                    rotationZ = None
                    euerAngles = Graph.api.getLinkCounterpartsByMetaMemeType(reqLMTransforms[0], "Agent.EuerAngles")
                    if len(euerAngles) > 0:
                        rotationXList = Graph.api.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationX")
                        rotationYList = Graph.api.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationY")
                        rotationZList = Graph.api.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationZ")
                        rotationX = Graph.api.getEntityPropertyValue(rotationXList[0], "Angle")
                        rotationY = Graph.api.getEntityPropertyValue(rotationYList[0], "Angle")
                        rotationZ = Graph.api.getEntityPropertyValue(rotationZList[0], "Angle")
                        
                    transformDict = {"deltaX" : deltaX, "deltaY" : deltaY, "deltaZ" : deltaZ, "rotationX" : rotationX, "rotationY" : rotationY, "rotationZ" : rotationZ}
                    self.landmarkTransforms.append([reqLMs[0], transformDict])
                '''
        except Exceptions.MemeMembershipValidationError as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        except Exception as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            #tb = sys.exc_info()[2]
            errorMsg = "Error adding landmarks to keyframe object of action %s.  Traceback = %s, %s" %(self.meme, errorID, errorMsg)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "exiting"])
            
            
            
    def checkLandmarks(self, agentUUID, additionalLandmarks = []):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'checkLandmarks'
        """
            additionalLandmarks allows us to pass an arbitrary set of landmark UUIDs at runtime, as an additional check
        """
        allTrue = False
        try:
            exTrue = self.checkExLists(agentUUID)
            nonExTrue = Graph.api.map(self.mapFunctionLandmarks, self.landmarksNonExclusive, agentUUID)
            masterTrue = Graph.api.map(self.mapFunctionLandmarks, [self.masterLandmark], agentUUID)
            allLandmarks = []
            allLandmarks.extend(exTrue)
            allLandmarks.extend(nonExTrue)
            allLandmarks.extend(masterTrue)
            
            if len(additionalLandmarks) > 0:
                #additionalLandmarks lists contain only UUIDs and not traverse paths, so we don't know the exact traverse paths to search.  Simply 
                #    ensure that additionalLandmarks landmarks are in the same cluster.  This is useful for decorated landmarks in action requests.  
                clustermembers = []
                cluster = Graph.api.getCluster(agentUUID)
                for clusterMember in cluster['nodes']:
                    #dict: {'metaMeme': 'Agent.View', 'meme': 'Agent.DefaultView', 'id': '008e23c0-e0e0-11e8-885b-720005fb5740'}
                    clustermembers.append(clusterMember['meme'])
                    
                additionalLandmarkMemes = []
                for additionalLandmark in additionalLandmarks:
                    landmarkMeme = Graph.api.getEntityMemeType(additionalLandmark)
                    additionalLandmarkMemes.append(landmarkMeme)
                additionalLandmarksSet = set(additionalLandmarkMemes)
                clustermembersSet = set(clustermembers)
                if additionalLandmarksSet.issubset(clustermembersSet):
                    adTrue = [True]
                else:
                    adTrue = [False]
                allLandmarks.extend(adTrue)
            
            if False not in allLandmarks:
                allTrue = True
        except Exception as e:
            errorMsg = "Unknown error checking landmarks for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return allTrue    
    
    def checkExLists(self, agentUUID):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'checkExLists'
        try:
            exTrue = Graph.api.map(self.mapFunctionLandmarks, self.landmarksExclusive, agentUUID)
            return exTrue
        except Exception as e:
            errorMsg = "Unknown error checking exclusive landmarks for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
        
        
    def mapFunctionLandmarks(self, landMarkID, agentUUID):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionLandmarks'
        try:
            landMarkPath = Graph.api.getEntityMemeType(landMarkID)
            localResult = Graph.api.getHasCounterpartsByType(agentUUID, landMarkPath)
            return localResult 
        except Exception as e:
            errorMsg = "Unknown error mapping landmark %s for keyframe object of action %s.  Traceback = %s" %(landMarkPath, self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False   
        
        
        
    def bootstrap(self):
        pass    
        
        
        
class ConditionalAction(object):
    className = 'ConditionalAction'
    
    def addConditions(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addConditions'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            self.conditions = []
            """ Adds conditions to those actions (KeyFrame, Throw) that require them  """
            conditionPath = "Graphyne.Condition.Condition"
            conditionElements = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, conditionPath)
            for conditionElement in conditionElements:
                errorMsg = "adding condition %s to action %s" %(conditionElement, self.uuid)
                Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
                
                self.conditions.append(conditionElement)
        except Exception as e:
            actionID = None
            try: actionID = self.meme
            except: pass
            errorMsg = "Unknown error adding conditions to action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "exiting"])
            
        
    def mapFunctionConditions(self, conditionUUID, argumentMap):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionConditions'
        try:
            localResult = Graph.api.evaluateEntity(conditionUUID, argumentMap, argumentMap["actionID"], argumentMap["subjectID"], argumentMap["controllerID"])
            return localResult  
        except Exception as e:
            actionID = None
            try: actionID = self.meme
            except: pass
            errorMsg = "Unknown error testing individual condition on action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def checkConditions(self, argumentMap):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'checkConditions'
        try:
            conditionResults = Graph.api.map(self.mapFunctionConditions, self.conditions, argumentMap)
            conditionsTrue = True
            if False in conditionResults:
                conditionsTrue = False
            return conditionsTrue
        except Exception as e:
            actionID = None
            try: actionID = self.meme
            except: pass
            errorMsg = "Unknown error testing conditions on action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    
class ActionSet(Action): 
    className = 'ActionSet'
    
    def bootstrap(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'bootstrap'
        try:
            self.memberList = []
            self.packedMemberList = []
            self.addLandMarks()
            actionSetChildren = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.ChoreographyStep")
            tempPrio = {}
            try: #lv2
                for actionSetChild in actionSetChildren:
                    priority = Graph.api.getEntityPropertyValue(actionSetChild, "Priority")
                    action = Graph.api.getLinkCounterpartsByMetaMemeType(actionSetChild, "Action.Action")
                    tempPrio[priority] = action[0]#there should only be one action counterpart per ChoreographyStep
                    
                try: #lv3
                    implicitCatch = Graph.api.getEntityPropertyValue(self.uuid, "ImplicitCatch")
                    if implicitCatch == True:
                        #If implicitCatch is true, then create a Action.DefaultCatch 
                        #    and append it to self.packedMemberList before adding any other members
                        landmarkPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
                        landmarkID = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, landmarkPath)
                        defaultCatchID = Graph.api.getEntityPropertyValue(landmarkID[0], 'DefaultCatch')
                        defaultCatchUUID = uuid.UUID(defaultCatchID)
                        defaultCatchMeme = Graph.api.getEntityMemeType(defaultCatchUUID)
                        self.packedMemberList.append(defaultCatchMeme)
                except Exception as e:
                    #level 3
                    pass
                try: #lv4
                    prioList = sorted(tempPrio.keys())
                    for prio in prioList:
                        sortedMemberUUID = tempPrio[prio]
                        sortedMember = Graph.api.getEntityMemeType(sortedMemberUUID)
                        #debug
                        #errorMsg = "Entity meme %s uuid = %s" %(sortedMemberUUID, tempPrio[prio])
                        #logProxy.log(logProxy.logType, logProxy.WARNING , method , errorMsg)
                        #/debug
                        self.packedMemberList.append(sortedMember)
                except Exception as e:
                    errorMsg = "Unknown error setting up ChoreographyStep members on action %s.Traceback = %s" %(self.meme, e)
                    sortedMember = Graph.api.getEntityMemeType(sortedMemberUUID)
                    Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            except Exception as e:
                #level 2
                pass
        except Exception as e:
            errorMsg = "Unknown error bootstrapping choreography %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            #debug
            try:
                self.addLandMarks()
                actionSetChildren = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.ChoreographyStep")
                tempPrio = {}
                for actionSetChild in actionSetChildren:
                    priority = Graph.api.getEntityPropertyValue(actionSetChild, "Priority")
                    action = Graph.api.getLinkCounterpartsByMetaMemeType(actionSetChild, "Action.Action")
                    tempPrio[priority] = action
                    
                implicitCatch = Graph.api.getEntityPropertyValue(self.uuid, "ImplicitCatch")
                if implicitCatch == True:
                    #If implicitCatch is true, then create a Action.DefaultCatch 
                    #    and append it to self.packedMemberList before adding any other members
                    landmarkPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
                    landmarkID = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, landmarkPath)
                    defaultCatchID = Graph.api.getEntityPropertyValue(landmarkID[0], 'DefaultCatch')
                    defaultCatchUUID = uuid.UUID(defaultCatchID)
                    defaultCatchMeme = Graph.api.getEntityMemeType(defaultCatchUUID)
                    self.packedMemberList.append(defaultCatchMeme)
                prioList = sorted(tempPrio)
                for prio in prioList:
                    sortedMemberUUID = uuid.UUID(tempPrio[prio])
                    sortedMember = Graph.api.getEntityMemeType(sortedMemberUUID)
                    self.packedMemberList.append(sortedMember)
            except:
                pass
        
      
            
    def getInflatedMemberList(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'getInflatedMemberList'
        returnList = []
        for taskItem in self.packedMemberList:
            #First, assert that we even have this action indexed
            try:
                assert taskItem in self.actionIndex
                memberEntity = self.actionIndex[taskItem]
                memberEntityMembers = memberEntity.getInflatedMemberList()
                returnList.extend(memberEntityMembers)
            except AssertionError:
                errorMsg = "Action set %s has member %s, which is not indexed in action engine" %(self.meme, taskItem)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        #debug
        #debugMessage = "Action set %s has the following members: %s" %(self.meme, returnList)
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , debugMessage])
        #/debug
        return returnList
    
    
    
    def inflateMembers(self):
        inflatedmemberList = self.getInflatedMemberList() 
        self.memberList = inflatedmemberList


    
class KeyFrame(Action, ConditionalAction):
    className = 'KeyFrame'
    
    def bootstrap(self):
        self.addLandMarks()
        self.addConditions()
        self.addObjectSelectionConditions()
        self.addStateChanges()
        self.addStimuli()
        self.addControllers()
        self.addRestrictedView()
        self.addTimescale()
        
    
        
    def addObjectSelectionConditions(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addObjectSelectionConditions'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            conditionPath = "Action.ObjectSelectionCondition::Graphyne.Condition.Condition"
            self.objectSelectionConditions = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, conditionPath)
        except Exception as e:
            errorMsg = "Unknown error adding object selection conditions to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])

        
        
    def addStateChanges(self):  
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addStateChanges'
        #Action.StateChangeSet
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            self.stateChangesSimple = [] 
            self.stateChangesJoin = [] 
            self.stateChangesBreak = []
            self.stateChangeSuccessor = []
            
            stateChangeElements = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.StateChangeSet")
            if len(stateChangeElements) > 0:
                #StateChangeSet is a switch and will have one of the following children:
                #    SimpleStateChange, LinkJoin, LinkBreak or SuccessorAction
                scElements = Graph.api.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.SimpleStateChange")
                ljElements = Graph.api.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.LinkJoin")
                lbElements = Graph.api.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.LinkBreak")
                saElements = Graph.api.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.SuccessorAction")
                
                for scElement in scElements:
                    #SimpleStateChange have two mandatory elements, a Change and a State, the latter of which extends Intentsity.Condition.AgentAttributeArgument
                    changeElements = Graph.api.getLinkCounterpartsByMetaMemeType(scElement, "Action.Change")
                    conditionIDs = Graph.api.getLinkCounterpartsByMetaMemeType(scElement, "Graphyne.Condition.Condition")
                    
                    stateElements = Graph.api.getLinkCounterpartsByMetaMemeType(scElement, "Action.State")
                    statePath = Graph.api.getEntityPropertyValue(stateElements[0], "SubjectArgumentPath")
                    
                    conditionalStimuli = self.getConditionalStimuli(scElement)
                    stateChange = StateChangeSimple(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(changeElements[0], statePath)
                    self.stateChangesSimple.append(stateChange)
                    
                for ljElement in ljElements:
                    conditionIDs = Graph.api.getLinkCounterpartsByMetaMemeType(ljElement, "Graphyne.Condition.Condition")
                    subjectPath = Graph.api.getEntityPropertyValue(ljElement, "SubjectArgumentPath")
                    objectPath = Graph.api.getEntityPropertyValue(ljElement, "ObjectArgumentPath")
                    linkTypeStr = Graph.api.getEntityPropertyValue(ljElement, "LinkType")
                    
                    linkType = 0
                    if linkTypeStr == "SubAtomic":
                        linkType = 1
                    conditionalStimuli = self.getConditionalStimuli(ljElement)
                    stateChange = StateChangeJoin(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(subjectPath, objectPath, linkType)
                    self.stateChangesJoin.append(stateChange)
                    
                for lbElement in lbElements:
                    conditionIDs = Graph.api.getLinkCounterpartsByMetaMemeType(lbElement, "Graphyne.Condition.Condition")
                    subjectPath = Graph.api.getEntityPropertyValue(lbElement, "SubjectArgumentPath")
                    objectPath = Graph.api.getEntityPropertyValue(lbElement, "ObjectArgumentPath")
                    conditionalStimuli = self.getConditionalStimuli(lbElement)
                    stateChange = StateChangeBreak(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(subjectPath, objectPath)
                    self.stateChangesBreak.append(stateChange)
                    
                for saElement in saElements:
                    conditionIDs = Graph.api.getLinkCounterpartsByMetaMemeType(saElement, "Graphyne.Condition.Condition")
                    priority = Graph.api.getEntityPropertyValue(conditionIDs[0], "priority")
                    followOnActions = Graph.api.getLinkCounterpartsByMetaMemeType(saElement, "Action.Action")
                    insertionTypeStr = Graph.api.getEntityPropertyValue(saElement, "InsertionType")
                    
                    insertionType = actionInsertionTypes.APPEND
                    if insertionTypeStr == "Head":
                        linkType = 1
                    elif insertionTypeStr == "HeadClear":
                        linkType = 2
                    conditionalStimuli = self.getConditionalStimuli(saElement)
                    stateChange = StateChangeSuccessorAction(conditionIDs[0], conditionalStimuli) 
                    stateChange.prime(followOnActions[0], insertionType, priority)
                    self.stateChangeSuccessor.append(stateChange)
                    
                    #Lastly, resort the successor action list to ensure that the new SA is positioned by priority
                    tempMap = {}
                    for currentEntry in self.stateChangeSuccessor:
                        tempMap[currentEntry.priority] = currentEntry
                    prioList = sorted(tempMap)
                    prioList.reverse()
                    
                    self.stateChangeSuccessor = [] 
                    for prio in prioList:
                        self.stateChangeSuccessor.append(tempMap[prio])
        except Exception as e:
            errorMsg = "Unknown error adding state change information to kexframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])

        
        
    def addStimuli(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addStimuli'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        #Stimulus.ConditionalStimulus
        try:
            self.conditionalStimuli = self.getConditionalStimuli(self.uuid)
        except Exception as e:
            errorMsg = "Unknown error adding stimuli information to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
        

    def getConditionalStimuli(self, rootNodeID):
        """
        Keyframes may link to ConditionalStimulus elements directly, or indirectly via StateChange.  
            Also, general keyframe conditional stimuli are stored directly on the keyframe, while
            those associated with a state change belong to the state change and are only added 
            self.conditionalStimuli immediately prior to stimuli distribution, which follows state changes.
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'getConditionalStimuli'
        try:
            #Stimulus.StimulusChoice
            conditionalStimuli = []
            conditionalStimuli = Graph.api.getLinkCounterpartsByMetaMemeType(rootNodeID, "Stimulus.StimulusChoice")
            return conditionalStimuli
        except Exception as e:
            errorMsg = "Unknown error getting conditional stimuli for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
    
    
    def addRequiredCondition(self):
        #toto
        pass
        
        
    def addControllers(self):
        #Todo
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addControllers'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            controllerBlacklist = None
            controllerWhitelist = None
            self.controllerBlacklist = controllerBlacklist
            self.controllerWhitelist = controllerWhitelist
        except Exception as e:
            errorMsg = "Unknown error adding controllers to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
        
    def addTimescale(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addTimescale'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            self.timescale = None
            timescaleElem = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.Timescale")
            if len(timescaleElem) > 1:
                self.timescale = timescaleElem[0]
        except Exception as e:
            errorMsg = "Unknown error adding tiimescale to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            
            
    def addRestrictedView(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'addRestrictedView'
        #logProxy.log(logProxy.logType, logProxy.DEBUG , method , "entering"])
        try:
            self.view = None
            viewElem = Graph.api.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.View::Agent.Page")
            if len(viewElem) > 1:
                self.view = viewElem[0]
        except Exception as e:
            errorMsg = "Unknown error adding view to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])

        
    def mapFunctionObjects(self, objectID, rtParams):
        #We'll be adding objectID, passing on to Graph.api.map and really don't need any concurrency nonsense
        #    Hence the deepcopy
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionObjects'
        try:
            argumentMap = {}
            try:
                #If _intentsity_actionEngineModTest_responseQueue is a key in rtParams, then we are running in test mode.
                #    The key in question holds a queue object for the test action Graph.api.  Queue objects can't be copied!
                #    So we need to remove it from rtParams before making the copy and then re-add it to the copy.
                assert '_intentsity_actionEngineModTest_responseQueue' in rtParams
                responseQueue = rtParams['_intentsity_actionEngineModTest_responseQueue']
                del rtParams['_intentsity_actionEngineModTest_responseQueue']
                argumentMap = copy.deepcopy(rtParams)
                #now add the queue back to rtParams and to argumentMap...
                argumentMap['_intentsity_actionEngineModTest_responseQueue'] = responseQueue
                rtParams['_intentsity_actionEngineModTest_responseQueue'] = responseQueue
            except AssertionError:
                #We are not in test mode and can blindly take rtParams 
                argumentMap = copy.deepcopy(rtParams)
            except copy.Error as e:
                raise e
            except Exception as e:
                errorMsg = "Copy Error.  Traceback = %s" %(e)
                raise Exception(errorMsg)
            argumentMap["objectID"] = objectID
            localResult = None
            conditionResultSet = Graph.api.map(self.mapFunctionConditions, self.childConditions, argumentMap)
            if False not in conditionResultSet:
                localResult = objectID
            return localResult    
        except Exception as e:
            errorMsg = "Unknown error mapping objects for keyframe object of action %s.  rtparams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return None
    
    
    def mapFunctionCheckEulerTransforms(self, landmarkTransform):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionCheckEulerTransforms'
        try:
            transformDict = landmarkTransform[1]
            transformResult = self.checkEulerAngles(landmarkTransform[0], transformDict["rotationX"], transformDict["rotationY"], transformDict["rotationZ"])
            return transformResult
        except Exception as e:
            errorMsg = "Unknown error mapping euler transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def mapFunctionCheckDeltaTransforms(self, landmarkTransform):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionCheckDeltaTransforms'
        try:
            transformDict = landmarkTransform[1]
            transformResult = self.checkDeltas(landmarkTransform[0], transformDict["deltaX"], transformDict["deltaY"], transformDict["deltaZ"])
            return transformResult
        except Exception as e:
            errorMsg = "Unknown error mapping transform deltas for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def mapFunctionStateChangesInner(self, stateChange, argumentMap):
        #self.conditionID = conditionID
        #self.stateChangeStimuli = stateChangeStimuli
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionStateChangesInner'
        try:
            conditionResult = Graph.api.evaluateEntity(stateChange.conditionID, argumentMap, argumentMap["actionID"], argumentMap["subjectID"], argumentMap["controllerID"])
            if conditionResult == True:
                stateChange.execute(argumentMap["subjectID"], argumentMap["objectID"])
                self.conditionalStimuli.extend(stateChange.stateChangeStimuli)
        except Exception as e:
            errorMsg = "Unknown error mapping state change for keyframe object of action %s.  argumentMap = %s Traceback = %s" %(self.meme, argumentMap, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return None
            
    
    def mapFunctionStateChangesOuter(self, objectID, rtParams):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionStateChangesOuter'
        try:
            argumentMap = {}
            try:
                #If _intentsity_actionEngineModTest_responseQueue is a key in rtParams, then we are running in test mode.
                #    The key in question holds a queue object for the test action Graph.api.  Queue objects can't be copied!
                #    So we need to remove it from rtParams before making the copy and then re-add it to the copy.
                assert '_intentsity_actionEngineModTest_responseQueue' in rtParams
                responseQueue = rtParams['_intentsity_actionEngineModTest_responseQueue']
                del rtParams['_intentsity_actionEngineModTest_responseQueue']
                argumentMap = copy.deepcopy(rtParams)
                #now add the queue back to rtParams and to argumentMap...
                argumentMap['_intentsity_actionEngineModTest_responseQueue'] = responseQueue
                rtParams['_intentsity_actionEngineModTest_responseQueue'] = responseQueue
            except AssertionError:
                #We are not in test mode and can blindly take rtParams 
                argumentMap = copy.deepcopy(rtParams)
            except copy.Error as e:
                raise e
            except Exception as e:
                errorMsg = "Copy Error.  Traceback = %s" %(e)
                raise Exception(errorMsg)
            #argumentMap = copy.deepcopy(rtParams)
            argumentMap["objectID"] = objectID
            unusedReturn = self.Graph.api.map(self.mapFunctionStateChangesInner, self.stateChangesBreak, argumentMap)
            unusedReturn = self.Graph.api.map(self.mapFunctionStateChangesInner, self.stateChangesJoin, argumentMap)
            unusedReturn = self.Graph.api.map(self.mapFunctionStateChangesInner, self.stateChangesSimple, argumentMap)
            unusedReturn = self.Graph.api.map(self.mapFunctionStateChangesInner, self.stateChangeSuccessor, argumentMap)
        except copy.Error as e:
            #Logged as error instead of warning because an uncopyable paramater payload from a client may be indicative of an attempted attack.
            errorMsg = "Unable to map state change for keyframe object of action %s because runtime parameters contains an uncopyable object!  rtParams = %s" %(self.meme, rtParams)
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        except Exception as e:
            errorMsg = "Unknown error mapping state change for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return None
    
    
    def mapFunctionSetEulerTransforms(self, landmarkTransform):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionSetEulerTransforms'
        try:
            transformDict = landmarkTransform[1]
            landmarkID = landmarkTransform[0]
            eulerElem = Graph.api.getLinkCounterpartsByMetaMemeType(landmarkID, "Agent.Offset::Agent.EuerAngles")
            if len(eulerElem) > 0:
                eulerXElem = Graph.api.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                eulerYElem = Graph.api.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                eulerZElem = Graph.api.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                unusedEulerX = Graph.api.setEntityPropertyValue(eulerXElem[0], "Angle", transformDict["rotationX"])
                unusedEulerY = Graph.api.setEntityPropertyValue(eulerYElem[0], "Angle", transformDict["rotationY"])
                unusedEulerZ = Graph.api.setEntityPropertyValue(eulerZElem[0], "Angle", transformDict["rotationZ"])
        except Exception as e:
            errorMsg = "Unknown error mapping euler transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return True
    
    
    def mapFunctionSetDeltaTransforms(self, landmarkTransform):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionSetDeltaTransforms'
        try:
            transformDict = landmarkTransform[1]
            landmarkID = landmarkTransform[0]
            offsetElem = Graph.api.getLinkCounterpartsByMetaMemeType(landmarkID, "Agent.Offset")
            if len(offsetElem) > 0:
                unusedDeltaX = Graph.api.setEntityPropertyValue(offsetElem[0], "x", transformDict["deltaX"])
                unusedDeltaY = Graph.api.setEntityPropertyValue(offsetElem[0], "y", transformDict["deltaY"])
                unusedDeltaZ = Graph.api.setEntityPropertyValue(offsetElem[0], "z", transformDict["deltaZ"])
        except Exception as e:
            errorMsg = "Unknown error mapping delta transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return True
        
    # /Landmarks
 
    
    # objects
    def selectObjects(self, rtParams, objectID = None):
        """
            Select all object agents in scope of view that also meet the conditions required for selection:
                'Action.ObjectSelectionCondition::Graphyne.Condition.Condition'
            Here are the rules:
                If there is a view with an action perspective, we limit ourselves to that scope
                    If there are no selection conditions and no objectID, all agents in scope are selected
                    If objectID is selected and it is not in scope, the action is dropped
                    If objectID is selected and in scope, the action goes to that object, plus others in scope meeting conditions
                    If objectID is not in scope, but other objects are and meet the conditions, they get the action, but not objectID
                If there is no action perspective (View directly off of KeyFrame instead of via Landmark on subject)
                    If there are no selection conditions and no objectID; dropped
                    If there are no selection conditions, but objectID; the action goes to that object 
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'selectObjects'
        try:
            if self.view is not None:
                #Use 'action perspective' view
                if (len(self.objectSelectionConditions) < 1) and (objectID is None):
                    viewList = stimulusAPI.getAllAgentsInSpecifiedPage(self.view)
                    return viewList
                elif (len(self.objectSelectionConditions) < 1) and (objectID is not None):
                    viewList = stimulusAPI.getAllAgentsInSpecifiedPage(self.view)
                    if objectID in viewList:
                        return [objectID]
                    else:
                        return []
                else:
                    intersectedObjects = stimulusAPI.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = Graph.api.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    return viewList
            else:
                #Use 'subject perspective' view
                if (len(self.objectSelectionConditions) < 1) and (objectID is None):
                    return []
                elif (len(self.objectSelectionConditions) < 1) and (objectID is not None):
                    return [objectID]
                elif objectID is not None:
                    intersectedObjects = stimulusAPI.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = Graph.api.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    if objectID not in viewList:
                        viewList.append(objectID)
                    return viewList
                else:
                    intersectedObjects = stimulusAPI.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = Graph.api.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    return viewList
        except Exception as e:
            errorMsg = "Unknown error selecting object entities for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return []
    # /objects
    
    
    # State Changes
    def changeStates(self, rtParams):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'changeStates'
        try:
            self.Graph.api = Graph.api
            stateChangeStimuli = Graph.api.map(self.mapFunctionStateChangesOuter, rtParams["objectID"], rtParams)
            self.conditionalStimuli.extend(stateChangeStimuli)
        except Exception as e:
            errorMsg = "Unknown error changing states for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
    #/ State Changes
    

    
    
    # Stimuli
    def broadcastStimuli(self, rtParams):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'broadcastStimuli'
        try:
            for conditionalStimulus in self.conditionalStimuli:
                if conditionalStimulus is not None:
                    stimulusMessage = None
                    #StimulusMessage def __init__(self, stimulusID, argumentMap, targetAgents = []):
                    if ("stimuliRecipients" in rtParams) == True:
                        targets = rtParams["stimuliRecipients"]
                        stimulusMessage = StimulusMessage(conditionalStimulus, rtParams, targets)
                    else:
                        stimulusMessage = StimulusMessage(conditionalStimulus, rtParams, [])
                    siQ.put(stimulusMessage)
        except Exception as e:
            errorMsg = "Unknown error broadcasting stimuli for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])


    def invoke(self, rtParams):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'invoke'
        try:
            #todo - refactor Graph.api.evaluateEntity to add objects
            Graph.api.evaluateEntity(self.uuid, rtParams, rtParams['actionID'], rtParams['subjectID'], rtParams['objectID'])
        except Exception as e:
            errorMsg = "Unknown error invoking keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        



class Catch(Action, ConditionalAction):
    className = 'Catch'
    
    def bootstrap(self):
        self.addConditions()
        self.addLandMarks()




class Throw(Action, ConditionalAction):
    className = 'Throw'
    def bootstrap(self):
        self.addConditions()
        self.addLandMarks()



class StateChange(object):
    def __init__(self, conditionID, stateChangeStimuli = []):
        self.conditionID = conditionID
        self.stateChangeStimuli = stateChangeStimuli
                
       
class StateChangeBreak(StateChange):
    def prime(self, subjectPath, objectPath):
        self.subjectPath = subjectPath
        self.objectPath = objectPath    
    
    def execute(self, subjectID, objectID):
        Graph.api.removeEntityLink(subjectID, objectID)
        self
        
        
class StateChangeJoin(StateChange):
    def prime(self, subjectPath, objectPath, linkType):
        self.linkType = linkType
        self.subjectPath = subjectPath
        self.objectPath = objectPath
    
    def execute(self, subjectID, objectID):
        subjectMountPoint = Graph.api.getLinkCounterpartsByMetaMemeType(subjectID, self.subjectPath)
        objectMountPoint = Graph.api.getLinkCounterpartsByMetaMemeType(subjectID, self.objectPath)
        Graph.api.addEntityLink(subjectMountPoint[0], objectMountPoint[0], {}, self.linkType)
        
        
class StateChangeSimple(StateChange):
    def prime(self, changeID, path):
        #channgeID is the uuid of the relevant Numeric.Function entity
        #stateID is the path to be changed
        self.changeID = changeID 
        self.path = path
        
    def execute(self, subjectID, objectID):
        delta = Graph.api.evaluateEntity(self.changeID)
        oldPropValue = Graph.api.getEntityPropertyValue(objectID, self.path)
        newPropValue = oldPropValue + delta
        Graph.api.setEntityPropertyValue(objectID, self.path, newPropValue) 
    

    
class StateChangeSuccessorAction(StateChange):
    def prime(self, actionID, insertionType, priority):
        self.actionID = actionID 
        self.insertionType = insertionType
        self.priority = priority
        
    def execute(self, subjectID, objectID):
        #todo -
        actionInvoc = {"actionID" : self.actionID, "subjectID" : subjectID, "objectID" : objectID, "controllerID" : None, "insertionType" : self.insertionType, "rtparams" : {}}
        aQ.put(actionInvoc) 
        
        
#globals



def getActionIndexItem(toBeIndexed):
    method = os.path.splitext(os.path.basename(__file__))[0] + '.' + 'getActionIndexItem'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , " - entering"])
    
    
    try:
        actionMemes = []
        action = None
        
        actionMemes = Graph.api.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Throw")
        if len(actionMemes) > 0:
            memeName = Graph.api.getEntityMemeType(toBeIndexed)
            errorMsg =  "Action %s is a Throw" %memeName
            Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
            try:
                action = Throw()
                action.initialize(actionMemes[0], toBeIndexed)
            except Exception as e:
                actionMeme = None
                try: actionMeme = actionMemes[0]
                except: pass
                errorMsg = "Member Action.Throw entity %s is invalid" %actionMeme
                raise Exceptions.TemplatePathError(errorMsg)
        else:
            actionMemes = Graph.api.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Catch")
            if len(actionMemes) > 0:
                errorMsg =  "Action %s is a Catch" %toBeIndexed
                Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
                try:
                    action = Catch()
                    action.initialize(actionMemes[0], toBeIndexed)
                except Exception as e:
                    actionMeme = None
                    try: actionMeme = actionMemes[0]
                    except: pass
                    errorMsg = "Member Action.Catch entity %s is invalid" %actionMeme
                    raise Exceptions.TemplatePathError(errorMsg)
            else:
                memeName = Graph.api.getEntityMemeType(toBeIndexed)
                actionMemes = Graph.api.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Choreography")
                if len(actionMemes) > 0:
                    errorMsg =  "Action %s is a Choreography" %memeName
                    Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
                    try:
                        action = ActionSet()
                        action.initialize(actionMemes[0], toBeIndexed)
                    except Exception as e:
                        actionMeme = None
                        try: actionMeme = actionMemes[0]
                        except: pass
                        errorMsg = "Member Action.Choreography entity %s is invalid" %actionMeme
                        raise Exceptions.TemplatePathError(errorMsg)
                else:
                    actionMemes = Graph.api.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.KeyFrame")
                    if len(actionMemes) > 0:
                        errorMsg = "Action %s is a KeyFrame" %memeName
                        Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
                        try:
                            action = KeyFrame()
                            action.initialize(actionMemes[0], toBeIndexed)
                        except Exception as e:
                            actionMeme = None
                            try: actionMeme = actionMemes[0]
                            except: pass
                            errorMsg = "Member Action.KeyFrame entity %s is invalid" %actionMeme
                            raise Exceptions.TemplatePathError(errorMsg)
                    else:
                        linkOverview = Graph.api.getEntityCounterparts(toBeIndexed)
                        errorMsg = "Action %s has no valid child type.  Link overview = %s" %(memeName, linkOverview)
                        Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #now finish creating the action object
        action.bootstrap()
        errorMsg = "Bootstrapped %s %s" %(type(action), action.meme)
        Graph.logQ.put( [logType , logLevel.DEBUG , method , errorMsg])
        Graph.logQ.put( [logType , logLevel.DEBUG , method , " - exiting"])
        return action
    except Exceptions.ActionIndexerError as e:
        actionMeme = Graph.api.getEntityMemeType(toBeIndexed)
        errorMsg = "Error in method while creating action index item %s.  Traceback = %s" %(actionMeme, e)
        Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        raise e        
    except Exception as e:
        actionMeme = Graph.api.getEntityMemeType(toBeIndexed)
        errorMsg = "Error creating action index item %s.  Traceback = %s" %(actionMeme, e)
        Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        raise e

######################
# /Action Engine
######################

######################
#  Stimulus Engine
######################


class StimulusProfile(object):
    """
        This class contains acts as a container for a single stimulus report.  When finished, it contains:
        A stimulus ID
        A list of all agents that need to have this stimulus resolved and rendered
        A list of any render stage conditions that need to be resolved
    """
    className = "StimulusProfile"
    
    def __init__(self, stimulusID1, conditionSet1 = [], anchors = [], isDeferred = False, dependentConditions = None):
        self.stimulusID = stimulusID1
        self.conditionSet = conditionSet1
        self.agentSet = set([])
        self.isDeferred = isDeferred
        self.dependentConditions = dependentConditions
        self.anchors = anchors
        self.stimulusMeme = "(unknown)"
        try: self.stimulusMeme = Graph.api.getEntityMemeType(self.stimulusID)
        except: pass
        
        
    def addAgents(self, agentSet):
        self.agentSet = agentSet
        
    def resolve(self, runtimeVariables):
        method = self.className + '.' + os.path.splitext(os.path.basename(__file__))[0] + '.' + 'resolve'
        descriptorPath = "*::Stimulus.Descriptor::*"
        try:
            descriptorIDList = self.getDescriptors() 
            descriptorID = descriptorIDList[0] #Descriptor is a switch and only ever has one child
            self.descriptorID = descriptorID
            self.resolvedDescriptor = Graph.api.evaluateEntity(descriptorID, runtimeVariables)
        except Exceptions.MemeMembershipValidationError as e:
            pass
        except IndexError as e:
            fullDescriptorPath = "%s%s" %(self.stimulusMeme, descriptorPath) 
            errorMsg = "Stimulus %s has null descriptor at path %s.  Check the meme!" %(self.stimulusMeme, fullDescriptorPath)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])             
        except Exception as e:
            errorMsg = "Error while trying to resolve stimulus %s %s for agents %s.  Traceback = %s" %(self.stimulusMeme, self.stimulusID, self.agentSet, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])    
            
            
    def getDescriptors(self):
        descFreePath = "Stimulus.FreeStimulus::Stimulus.Descriptor"
        descAnchoredMPath = "Stimulus.AnchoredStimulus::Stimulus.Descriptor"   
        freeStimulusDescriptors = Graph.api.getLinkCounterpartsByMetaMemeType(self.stimulusID, descFreePath)
        anchoredStimulusDescriptors = Graph.api.getLinkCounterpartsByMetaMemeType(self.stimulusID, descAnchoredMPath)  
        if (len(freeStimulusDescriptors) > 0) and (len(anchoredStimulusDescriptors) <= 0):
            #We are a free stimulus and use this descriptor path
            return freeStimulusDescriptors
        elif (len(freeStimulusDescriptors) <= 0) and (len(anchoredStimulusDescriptors) > 0):
            #We are an anchored stimulus and use this descriptor path
            return anchoredStimulusDescriptors 
        else:
            #We should never see this with properly validated stimuli, 
            #    but it is always possible that the user it trying to load invalid memes
            errorMsg = "Can't find the descriptor for stimulus %s.  Meme has invalid structure!  Please correct and validate!" %self.stimulusMeme
            raise Exceptions.MemeMembershipValidationError(errorMsg)
 
        


class Report(object):
    ''' A StimulusChoice is made up of one or more ConditionalStimulus memes.  Any one of these may
        have RenderStageFiltering set to True.  If so, we'll need to defer filtering based on this 
        stimulus until the render stage.   E.g. if Angela is being used below the torque engine, whether
        a player has an agent in his/her field of view may be highly dependent on where the player has 
        the camera pointed during any given tick. 
        
        This class is for early filter stage managing ordered lists of conditional stimuli  
    '''
    buckets = None
    lastBucketDeferred = False
    className = "Report"
    

    def __init__(self, conditionalStimulusID):
        self.descriptorIDs = {}
        self.resolvedDescriptors = {}
        try:
            self.createBucketLists(conditionalStimulusID)
        except Exceptions.InvalidStimulusProcessingType as e:
            raise e
        except Exception as e:
            raise e



    def createBucketLists(self, conditionalStimulusID):
        '''
            If we add a stimulus choice to this method, we'll get back an object of the following structure:
                An ordered list of bucketsgiving bucket priority and the conditions nested underneath
                orderedBucketList {prio0 : orderedConditionList, prio1 : orderedConditionList, ...}
                
            Within each bucket, we order the conditions into sorted lists:
                orderedConditionList {prio0 : a ConditionalStimulus, prio1 : another ConditionalStimulus, ...}
                
            If instead of a StimulusChoice, we are directly using a Stimulus, then the structure is as follows:
                orderedBucketList {0:{0 : StimulusID}}
        '''
        method = self.className + '.' + os.path.splitext(os.path.basename(__file__))[0] + '.' + 'getBucketLists'
        orderedBucketList = {}
        
        stimulusChoicePath = "Stimulus.StimulusChoice"
        conditionalStimulusPath = "Stimulus.ConditionalStimulus"
        stimulusPath = "Stimulus.Stimulus"
        conditionPath = "Graphyne.Condition.Condition"  #We'll be using this in multiple places later
        anchorPath = "Stimulus.AnchoredStimulus::Stimulus.Anchor::Stimulus.Stimulus" #This is relative to Stimulus.Stimulus
        metamemeType = Graph.api.getEntityMetaMemeType(conditionalStimulusID)
        
        stimulusProfile = None

        if (metamemeType == stimulusPath):
            #The simplest case.  There are no conditions to worry about
            anchorList = Graph.api.getLinkCounterpartsByMetaMemeType(conditionalStimulusID, anchorPath)
            #stimulusID, conditionSet, anchors = [], isDeferred = False, dependentConditions = None
            stimulusProfile = StimulusProfile(conditionalStimulusID, [], anchorList)
            orderedBucketList = {0 : stimulusProfile}         
        elif metamemeType == stimulusChoicePath:
            conditionElements = Graph.api.getLinkCounterpartsByMetaMemeType(conditionalStimulusID, conditionalStimulusPath)
            
            #now, determine the "buckets"
            masterdeferredList = {}
            for conditionElement in conditionElements:
                memeName = Graph.api.getEntityMemeType(conditionElement)
                if memeName in renderStageStimuli:
                    prio = 0
                    hasPriority = Graph.api.getEntityHasProperty(conditionElement, "Priority")
                    if hasPriority is True:
                        prio = Graph.api.getEntityPropertyValue(conditionElement, "Priority")
                    masterdeferredList[prio, conditionElement]
                    
            #Now, make a second pass, this time looking at everything
            for conditionElement in conditionElements:
                dependentList = []
                prio = 0
                hasPriority = Graph.api.getEntityHasProperty(conditionElement, "Priority")
                if hasPriority is True:
                    prio = Graph.api.getEntityPropertyValue(conditionElement, "Priority")
                for deferredKey in masterdeferredList.keys():
                    if prio < deferredKey:
                        dependentList.append(masterdeferredList[deferredKey])
                        
                stimulusID = Graph.api.getLinkCounterpartsByMetaMemeType(conditionElement, stimulusPath)
                conditionID = Graph.api.getLinkCounterpartsByMetaMemeType(conditionElement, conditionPath)
                anchorList = Graph.api.getLinkCounterpartsByMetaMemeType(stimulusID, anchorPath)
                        
                memeName = Graph.api.getEntityMemeType(conditionElement)
                if memeName in renderStageStimuli:
                    stimulusProfile = StimulusProfile(stimulusID[0], conditionID, anchorList, True, dependentList)
                else:
                    stimulusProfile = StimulusProfile(stimulusID[0], conditionID, anchorList, False, dependentList)
                    
                orderedBucketList[prio] = stimulusProfile
                
        else:
            errorMsg = "The Stimulus Engine may only take the types Stimulus.Stimulus and Stimulus.StimulusChoice.  Stimulus Request contained a meme of metameme type %s" %metamemeType
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            raise Exceptions.InvalidStimulusProcessingType(errorMsg)            
        self.buckets = orderedBucketList    
        
        
        
        
    def filter(self, argumentMap, targetAgents = None):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'filter'
        
        
        for  indexKey in sorted(self.buckets.keys()): 
            stimulusProfile = self.buckets[indexKey]
            if stimulusProfile.isDeferred is not True:
                
                try:
                    conditionProcessor = ConditionProcessor()
                    
                    #stimulusProfile.conditionSet
                    #stimulusProfile.stimulusID
                    #stimulusProfile.agentSet
                    
                    stimulusAgentsSet = None
                    if len(stimulusProfile.conditionSet) < 1:
                        # We are testing a stimulus with no conditions.  Get all agents that can view the page
                        if targetAgents is not None:
                            stimulusAgentsSet = conditionProcessor.selectAgents(stimulusProfile.stimulusID, None, targetAgents)
                        else: 
                            stimulusAgentsSet = conditionProcessor.selectAgents(stimulusProfile.stimulusID)
                        try:
                            stimulusProfile.agentSet.update(stimulusAgentsSet)
                        except Exception as e:
                            pass
                        logMessage = "Stimulus Agents that can view scope of message: = %s" %(stimulusAgentsSet)
                        Graph.logQ.put( [logType , logLevel.DEBUG , method , logMessage])
                    else:
                        fullAgentSet = set([])
                        checkedBefore = False
                        
                        if len(stimulusProfile.conditionSet) > 0:
                            #If we have conditions,use them to shape fullAgentSet 
                            for conditionID in stimulusProfile.conditionSet:
                                #We're testing a conditional stimulus and need to get the condition and test it
                                
                                if targetAgents is not None:
                                    stimulusAgentsSet = conditionProcessor.checkCondition(conditionID, stimulusProfile.stimulusID, argumentMap, None, targetAgents)
                                else: 
                                    stimulusAgentsSet = conditionProcessor.checkCondition(conditionID, stimulusProfile.stimulusID, argumentMap)
                                if checkedBefore is False:
                                    #On the first pass,we take all available agents to prime fullAgentSet 
                                    fullAgentSet.update(stimulusAgentsSet)
                                    checkedBefore = True
                                else:
                                    #On later passes, we filter fullAgentSet down using union
                                    fullAgentSet.union(stimulusAgentsSet)
                        else:
                            #Just select all agents with a view of the scope of the stimulus
                            if targetAgents is not None:
                                fullAgentSet = conditionProcessor.selectAgents(stimulusProfile.stimulusID, None, targetAgents)
                            else: 
                                fullAgentSet = conditionProcessor.selectAgents(stimulusProfile.stimulusID)
                        try:    
                            stimulusProfile.agentSet.update(fullAgentSet)
                        except Exception as e:
                            pass
                    
                    #conditionResults = Graph.api.map(self.mapFunctionConditions, conditions, argumentMap)
                    #conditionsTrue = True
                    #if False in conditionResults:
                        #conditionsTrue = False
                    #return conditionsTrue
                except Exception as e:
                    conditionMeme = "unknown"
                    stimulusMeme = "unknown"
                    try:
                        conditionMeme = Graph.api.getEntityMemeType(stimulusProfile.conditionSet)
                        stimulusMeme = Graph.api.getEntityMemeType(stimulusProfile.stimulusID)
                    except Exception as e: 
                        pass
                    errorMsg = "Unknown error testing condition %s on stimulus %s.  Traceback = %s" %(conditionMeme, stimulusMeme, e)
                    Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
                    return False
                
                
    def normalize(self, argumentMap):
        """
            This method ensures that each agent appears in one and only one bucket.
            I.E - it will see only one resolved and rendered stimulus from a conditional set
            
            The algorithm works as follows:
            There are two nested loops.
            1 - Works from  left to right over the complete set, from i to k, where k is the last 
                bucket index and i is the bucket being currently evaluated.  i increases by one per 
                iteration
            2 - For each step in the outer loop, loops from j to k,with j being i+1.  If an agent is in i,
                then it may not be in the segment from j to k.  In English, if an agent already has a higher
                priority, then the lower priority stimuli that might be possible are no longer relevant.
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'normalize'
        
        
        #Create a list of indices that we'll use later to control a for loop.  flowControlList governs the value j
        #    in the inner loop.  It contains a list of bucket indices.  flowControlList will be destructively evaluated
        #    by removing i at each iteration of the outer loop, so we want to start a copy of the key list.  
        flowControlList = list(self.buckets.keys())
            
        for  indexKey in sorted(self.buckets.keys()):
            #Outer loop,from i to k
            try:
                flowControlList.remove(indexKey)
                if  len(flowControlList) >= 1:
                    #Take the agents from the current bucket.
                    #  Iterate over the rest to make sure that the agents from the current bucket don't appear in any
                    stimulusProfile = self.buckets[indexKey]
                    try:
                        if len(stimulusProfile.agentSet) > 0:
                            for flowControlListKey in flowControlList:
                                #inner loop,from j to k
                                nextStimulusProfile = self.buckets[flowControlListKey]
                                nextStimulusProfile.agentSet.difference_update(stimulusProfile.agentSet)
                    except Exception as e:
                        stimulusMeme = Graph.api.getEntityMemeType(stimulusProfile.stimulusID)
                        errorMsg = "Can't disentangle lower prio conditional stimulus %s agent set from higher prio agent set.  Traceback = %s" %(stimulusMeme,e)
                        Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except Exception as e:
                errorMsg = ""
                try:
                    remaining = len(flowControlList)
                    stimulusProfile = self.buckets[indexKey]
                    stimulusMeme = Graph.api.getEntityMemeType(stimulusProfile.stimulusID)
                    errorMsg = "Can't normalize conditional stimulus %s agent set with regard to lower prio stimuli.  %s lower prio stimuli unnormalized.  Traceback = %s" %(stimulusMeme, remaining, e)
                except Exception as ee:
                    errorMsg = "Unexpected error %s occurred while trying to normalized conditional stimulus set.  Traceback = %s" %(ee, e)
                finally:
                    Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            
                
                
                
    def resolve(self, argumentMap):
        for  indexKey in sorted(self.buckets.keys()): 
            stimulusProfile = self.buckets[indexKey]
            if len(stimulusProfile.agentSet) > 0:
                stimulusProfile.resolve(argumentMap)
                self.resolvedDescriptors[indexKey] = stimulusProfile.resolvedDescriptor
                self.descriptorIDs[indexKey] = stimulusProfile.descriptorID
            else:
                #Don't waste time resolving a descriptor with no Recipients
                pass

class StimulusEngine(ServicePlugin):
    className = "StimulusEngine"
    portID = 1049
    exposeSIQToAPI = 0 #This is normally not used; only to test if the sIQ is functioning properly.  It presents a security risk otherwise
    
    def initialize(self, dummiAPIParam, dtParams = None, rtParams = None):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' 'initialize'
        
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.siQ = rtParams['siQ']
            
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , u"Design Time Parameters = %s" %(dtParams)])
            self._sleepperiod = 0.03    
            self._stopevent = threading.Event()
            self.startupIndexingFinished = False
            threading.Thread.__init__(self, name = "StimulusEngine")
        except Exception as e:
            errorMsg = "Fatal Error while starting Stimulus Engine. Traceback = %s" %e
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        
        
        
    def run(self):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'
 
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run'  , "Stimulus Engine waiting for initial loading of templates and entities to finish before it can start"])
        while Graph.readyToServe == False:
            time.sleep(5.0)
            Graph.logQ.put( [logType , logLevel.DEBUG , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run' , "...Stimulus Engine waiting for initial loading of templates and entities to finish"])
        Graph.logQ.put( [logType , logLevel.ADMIN , os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'run' , "Templates and Entities are ready.  Stimulus Engine Registrar may now be started"])
       
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Stimulus Engine Starting"])
        while not self.stoprequest.isSet():
            
            try:
                if self.startupIndexingFinished == False:
                    self.indexStimuli()
                    self.startupIndexingFinished = True
                else:
                    try:
                        '''Pop the oldest stimulus from the siq. It comes as a StimulusMessage,
                            which consists of a stimulusID, rtparams (as argumentMap) and agent list
                        '''
                        
                        stimulusSignal = siQ.get_nowait()                       
                        self.processStimulus(stimulusSignal)
                    except queue.Empty:
                        if not self._is_stopped:
                            self._stopevent.wait(self._sleepperiod)
                        else: 
                            self.exit()
                    except Exception as e:
                        errorMsg = "Unknown error while trying to process stimulus.  Traceback = %s" %e
                        Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except Exception as e:
                errorMsg = "Unknown error in stimulus engine.  Traceback = %s" %e
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])                



    def processStimulus(self, stimulusSignal):
        ''' 1- Build a broadcast packet, which is a dict of key = resolved stimulus, value = list of agents
            2- Send each off to the correct bQ
        
            stimulusSignal (an StimulusMessage) has the following attributes
            stimulusID - should always be present.  We have a problem if it is not
            targetAgents - this list might be empty.  Throw an exception if it is not a list
        '''
        method = self.className + '.' + os.path.splitext(os.path.basename(__file__))[0] + '.' + 'processStimulus'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
        
        #Debug
        #import sys;sys.path.append(r'/Applications/eclipse/plugins/org.python.pydev_3.9.0.201411111611/pysrc')
        #import pydevd;pydevd.settrace()
        

        stimulusSignal.argumentMap["stimulusID"] = stimulusSignal.stimulusID
       
        try:
            #Start by declaring a dict which will hold all agents and resolved stiimuli 
            report = Report(stimulusSignal.stimulusID)
            if (len(stimulusSignal.targetAgents) > 0):
                report.filter(stimulusSignal.argumentMap, stimulusSignal.targetAgents)
            else:
                report.filter(stimulusSignal.argumentMap)
            
            #Normalize the agent sets
            if len(report.buckets) > 1:
                report.normalize(stimulusSignal.argumentMap)

            #Now Resolve them
            report.resolve(stimulusSignal.argumentMap)        
            #stimulusID, stimulusMeme, agentSet, resolvedDescriptor, isDeferred = False, anchors = [], dependentConditions = None):
            try:
                for indexKey in sorted(report.descriptorIDs.keys()):
                    queueList = broadcasterRegistrar.getBroadcastQueue(report.descriptorIDs[indexKey]) 
                    stimulusProfile = report.buckets[indexKey]
                    
                    #If there are recipients, build the report object and send it to the broadcasters 
                    if len(stimulusProfile.agentSet) > 0:
                        memePath = Graph.api.getEntityMemeType(stimulusProfile.stimulusID)
                        stimulusReport = StimulusReport(stimulusProfile.stimulusID, 
                                                               memePath, 
                                                               stimulusProfile.agentSet, 
                                                               stimulusProfile.resolvedDescriptor, 
                                                               stimulusProfile.isDeferred, 
                                                               stimulusProfile.anchors, 
                                                               stimulusProfile.dependentConditions)                        
                        for broadcastQueueID in queueList:
                            broadcasterRegistrar.broadcasterIndex[broadcastQueueID].put(stimulusReport)
                            
                            #Debug
                            #theMsg = "Queue %s length = %s, last value %s" %(broadcastQueueID, broadcasterRegistrar.broadcasterIndex[broadcastQueueID].qsize(), stimulusProfile.resolvedDescriptor)
                            #Graph.logQ.put( [logType , logLevel.WARNING, method , theMsg])
            except Exceptions.NoSuchBroadcasterError as e:
                memePath = Graph.api.getEntityMemeType(stimulusSignal.stimulusID)
                errorMsg = "Stimulus %s has no broadcaster.  Traceback = %s" %(memePath, e)
                Graph.logQ.put( [logType , logLevel.ERROR, method , errorMsg])
            except Exceptions.NullBroadcasterIDError as e:
                memePath = Graph.api.getEntityMemeType(stimulusSignal.stimulusID)
                errorMsg = "Stimulus %s has no broadcaster.  Traceback = %s" %(memePath, e)
                Graph.logQ.put( [logType , logLevel.ERROR, method , errorMsg])
            except Exception as e:
                pass

        except Exception as e:
            stimulusSignalMeme = "unknown"
            try:
                stimulusSignalMeme = Graph.api.getEntityMemeType(stimulusSignal.stimulusID)
            except: pass
            errorMessage = "Error processing stimulus %s for agentlist %s.  Traceback = %s" %(stimulusSignalMeme, stimulusSignal.targetAgents, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMessage])


    
    """
    def execute(self):
        ''' 
            Adds an XML-RPC version of the script API to Angela.  
            The methods of the class API are currently is just a copy of the Python 
            module in the same package.  Later on, we should perhaps think of a way 
                to make all of the methods in API dynamically added (as callable 
                objects?) so that this file does not require dual maintenance with 
                Python.py 
        '''
        method = self.className + '.' + os.path.splitext(os.path.basename(__file__))[0] + '.' + 'execute'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
        try:
            self.server = xmlrpc.server.SimpleXMLRPCServer(("localhost", self.portID))
            self.server.register_function(self.getStimulus, 'getStimulus')
            if self.exposeSIQToAPI == 1:
                self.server.register_function(self.getStimulus, 'putStimulus')
            
            #Go into the main listener loop
            Graph.logQ.put( [logType , logLevel.ADMIN , method , "Main process plugin thread %s is listening an an XML RPC server on port %s" %(self.pluginName, self.portID)])
            self.server.serve_forever()
        except Exception as e:
            Graph.logQ.put( [logType , logLevel.ERROR , method , "Main process plugin thread % unable to start!!!  Traceback = %s" %(self.pluginName, e)])
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    """


    def indexStimuli(self):
        methodName = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'indexStimuli'
        
        
        startTime = time.time()
        nTh = 1
        
        numberOfStimuli = stimulusIndexerQ.qsize()

        Graph.logQ.put( [logType , logLevel.INFO , methodName, "Descriptor (broadcaster) Indexer - Found %s descriptors to index" %(numberOfStimuli)])
        while self.startupIndexingFinished == False:
            try:
                stimulusToBeIndexed = stimulusIndexerQ.get_nowait()
                try:
                    broadcasterRegistrar.indexDescriptor(stimulusToBeIndexed)
                    nTh = nTh + 1
                except Exception as e:
                    stimulusMeme = Graph.api.getEntityMetaMemeType(stimulusToBeIndexed)
                    Graph.logQ.put( [logType , logLevel.ERROR , methodName, "Descriptor (broadcaster) Indexer - Problem indexing stimulus %s.  Traceback = %s" %(stimulusMeme, e)])
            except queue.Empty:
                self.startupIndexingFinished = True
                endTime = time.time()
                deltaT = endTime - startTime
                Graph.logQ.put( [logType , logLevel.INFO , methodName, "Descriptor (broadcaster) Indexer - Finished initial loading from engine stimulus indexer queue"])
                Graph.logQ.put( [logType , logLevel.INFO , methodName, "Descriptor (broadcaster) Indexer - Indexed %s descriptors in %s seconds" %(nTh, deltaT)])
            except Exception as e:
                self.startupIndexingFinished = True
                Graph.logQ.put( [logType , logLevel.ERROR , methodName, "Descriptor (broadcaster) Indexer - Unknown Error.  Traceback = %s" %e])
                self._stopevent.wait(self._sleepperiod)
            

    def join(self):
        """
        Stop the thread
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'join'
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "......Stimulus Engine shut down"])
        self.stoprequest.set()
        super(StimulusEngine, self).join(0.5)
        
        
class ConditionProcessor(object):
    """
        A helper class, packaging the methods needed to set up a map-reduce test of a condition set
        
        The following information is presumed to be in the rtParams of and stimulus signal
            rtParams["_intentsity_actionID_local"] = action.instanceID  (might be there)
            rtParams["_intentsity_processorID"] = self.queueID          (might be there.  probably irrelevant for stimuli)
            rtParams["actionID"] = action.uuid                      (might be there)
            rtParams["subjectID"] = subjectID                       (might be there.  the actor if the stimulus is related to an action)
            rtParams["controllerID"] = controllerID                 (might be there.  the original controller issuing the command if it was due to an action)
            rtParams["objectID"] = objectList                       (might be there.  The original action object list)

            we'll be adding the following:
            rtParams["agentID"]                                      (might be there.  If the stimulus is associated with an agent)
            rtParams[targetID] = targetList                          (might be there.  If there are specified targets
    """
    className = "ConditionProcessor"
    
    def mapFunctionCondition(self, agentID, argumentMap):
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'mapFunctionCondition'
        
        actionID = None
        controllerID = None
        conditionID = None
        
        try:
            conditionID = argumentMap["conditionID"]
        except Exception as e:
            errorMsg = "Conditional Stimulus with undeclared condition on agent %s.  Traceback = %s" %(agentID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
        try: actionID = argumentMap["actionID"]
        except: pass
        
        try: controllerID = argumentMap["controllerID"]
        except: pass
        try:
            localResult = Graph.api.evaluateEntity(conditionID, argumentMap, actionID, agentID)
            
            returnVal = None
            if localResult == True:
                returnVal = agentID
            return returnVal  
        except Exception as e:
            errorMsg = "Unknown error testing individual condition %s on agent %s.  Traceback = %s" %(argumentMap["conditionID"], agentID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def checkCondition(self, conditionID, stimulusID, argumentMap, excludeSet = None, subjectIDList = []):
        '''This method selects all agents with a view on the stimulus' page that the
            Can also be given a specific list of agents to test for
        ''' 
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'checkCondition'
        
        
        agentSet = self.selectAgents(stimulusID, excludeSet, subjectIDList)
        okAgents = []
        
        try:
            localParams = copy.deepcopy(argumentMap)
            localParams["conditionID"] = conditionID
            localParams["api"] = Graph.api
            okAgents = Graph.api.map(self.mapFunctionCondition, list(agentSet), localParams)
        except Exception as e:
            conditionMeme = "unknown"
            stimulusMeme = "unknown"
            try:
                conditionMeme = Graph.api.getEntityMemeType(conditionID)
                stimulusMeme = Graph.api.getEntityMemeType(stimulusID)
            except: pass
            errorMsg = "Unknown error testing %s agents in scope for conditions %s on stimulus %s.  Traceback = %s" %(len(okAgents), conditionMeme, stimulusMeme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return set([])
        #Python's map/reduce functionality sometimes turns empty lists into None values. Remove them 
        try: okAgents.remove(None)
        except Exception as e: 
            pass
        return set(okAgents)
        
        
    # objects
    def selectAgents(self, stimulusID, excludeSet = None, subjectIDList = []):
        """
            Select all agents with a view of the scope of the stimulus
        """
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' + self.className + '.' + 'selectAgents'
        global stimulusAPI
        
        subjectIDSet = set([])
        if len(subjectIDList) > 0: subjectIDSet = set(subjectIDList)
        if excludeSet is None: excludeSet = set([])
        agentSet = set([])
        
        try:
            viewList = stimulusAPI.getAgentsWithViewOfStimulusScope(stimulusID)
            
            if len(subjectIDList) > 0:
                #We made the stimulus request with a specific list of agents in mind.  make sure they can see the page
                agentViewSet = set(viewList)
                agentSet = subjectIDSet.intersection(agentViewSet)
                
            else:
                agentSet = set(viewList)
            agentSet.difference_update(excludeSet)
            return agentSet
        except Exceptions.ScriptError as e:
            Graph.logQ.put( [logType , logLevel.WARNING , method , e])
        except Exception as e:
            errorMsg = "Unknown error selecting observer agents for stimulus %s.  rtParams = %s Traceback = %s" %(stimulusID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return set([])
    # /objects

######################
# / Stimulus Engine
######################



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
        self.api = Graph.api.getAPI()
        self.logQ = queue.Queue()
        self.aQ = queue.Queue() # action queue
        self.siQ = queue.Queue()
        self.basePort = None
        
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
        
        #A hook for adding loosely coupled plugins
        self.plugins = {}

    def log(self, originURI, origin, message, llevel = 3, lType = 1):
        Graph.logQ.put( [lType , llevel , origin , message])

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
        
    def setBasePort(self, basePort):
        self.basePort = basePort
        
    
    def start(self, startWithStandardRepo = True, resetDatabase = False):
        '''
            processName = process attribute value from Logging.Logger in AngelaMasterConfiguration.xml.
                The process name must be one of the ones defined in the configuration file
            manualAutoVal = an optional boolean (True or False) overriding the validateOnLoad setting in 
                AngelaMasterConfiguration.xml.  If this is not given, or is not boolean, the engine will
                use the setting defined in the configuration file
        '''
        
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.start'
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
        #print(("queues = %s" %self.engineQueues.keys()))
        
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
        Graph.startDB(self.additionalRepos, self.persistenceType, self.persistenceArg, True, resetDatabase, False, validateOnLoad)
        
        #/Start Graphyne
                
        #Initialize Other Plugins
        PluginFacade.initPlugins(self.plugins)
                
        #Yeah baby!  Start dem services!
        #rtParams[u"responseQueue"]
        self.rtParams['processName'] = self.processName
        self.rtParams['engineService'] = True
        self.rtParams['siQ'] = self.siQ
        self.rtParams['aQ'] = self.aQ
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
        actions = self.api.getEntitiesByMetaMemeType("Action.Action")
        for actionID in actions:
            actionIndexerQ.put(actionID)
            
        desriptors = self.api.getEntitiesByMetaMemeType("Stimulus.Descriptor")
        for desriptorID in desriptors:
            stimulusIndexerQ.put(desriptorID)
        Graph.logQ.put( [logType , logLevel.INFO , method ,"Finished initial loading of Action and Stimulus Indexers"])
         
        
        self.serverState = self.startupState.STARTING_SERVICES
        #Now we can start the service plugins
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "starting engine services"])
        self.actionEngine = ActionEngine()
        self.stimulusEngine = StimulusEngine()
        
        self.actionEngine.initialize(None, {'heatbeatTick' : 1}, self.rtParams)
        self.actionEngine.start()
        
        self.stimulusEngine.initialize(None, {'heatbeatTick' : 1}, self.rtParams)
        self.stimulusEngine.start()
        
        print("starting engine services")
        for plugin in PluginFacade.engineServices:
            engineService = plugin['module']
            self.rtParams['moduleName'] = plugin['moduleName']
            dtParams = plugin['params']
            try:
                tmpClass = getattr(engineService, 'Plugin')
                service = tmpClass()
                #apiCopy = copy.deepcopy(api)
                service.initialize(Graph.api, dtParams, self.rtParams)
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
        try:
            del self.rtParams['moduleName']
        except KeyError: 
            pass
        
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
        method = os.path.splitext(os.path.basename(__file__))[0] + '.' +  self.className + '.shutdown'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Engine Shutdown Started."])
        print("Finished waiting.  Shutting down service plugins.")
        try:
            self.stimulusEngine.join()
        except AttributeError:
            pass
        try:
            self.actionEngine.join()
        except AttributeError:
            pass
        try:
            for service in self.services:
                print("stopping %s thread ID %s %s" %(service.__class__, service._name, service.name))
                try:
                    service.join()
                    service.killServers()
                    service.join()
                except Exception as e:
                    print(( 'Exception while waiting for service thread to shut down. Traceback = %s' %(e)))
        except AttributeError:
            pass        
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


def runscript():
    PluginFacade.utilities
                
