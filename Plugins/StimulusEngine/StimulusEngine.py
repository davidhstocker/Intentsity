import threading
from ... import Engine
import Graphyne.Graph as Graph
import queue
import time

from ... import Exceptions as EngineExceptions
from ... import Exceptions



#import Condition
#import ConditionArgument
#import Controller


moduleName = 'StimulusEngine'
logType = Graph.logTypes.CONTENT
logLevel = Graph.LogLevel()
graphAPI = None


class StimulusAPI(object):
    
    '''
    def getAllAgentsInAgentScope(self, agentID):
        """
            Returns all agents in the same scope as the supplied agent
        """
        global graphAPI
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
        
       
    def getAllLandmarksInAgentScope(self, agentID):
        """
            Returns all landmarks (of other agents) in the same scope as the supplied agent
        """
        global graphAPI
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark"
        ownLandmarks = graphAPI.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
    
    
    
    def getAllAgentsInSpecifiedPage(self, pageUUID):
        """
            Returns agents with a scope on the supplied page
        """
        global graphAPI
        scopePath = "Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = graphAPI.getLinkCounterpartsByType(pageUUID, scopePath, None)
        return peers
    '''

        
        
    
    def getAllAgentsWithViewOfSpecifiedPage(self, pageUUID):
        """
            Returns agents with a view on the supplied page
        """
        global graphAPI
        scopePath = "Agent.View::Agent.Landmark::Agent.Agent"
        peers = graphAPI.getLinkCounterpartsByType(pageUUID, scopePath, None)
        return peers
        
    
    
    def getAgentsWithViewOfStimulusScope(self, stimulusID):
        #Given a stimulus, find all agents that are linked to the scope of the stimulus
            
        global graphAPI
              
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
        global graphAPI
        scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
     
     
        
    
    def getAllLandmarksInAgentView(self, agentID):
        """
            Get all landmarks (of other agents) that have active scope in the view of the supplied agent
        """
        global graphAPI
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark"
        ownLandmarks = graphAPI.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
            
            
    
    def getAllAgentsWithAgentView(self, agentID):
        """
            Get all agents with an active view of the scope of the supplied agent
        """
        global graphAPI
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark::Agent.Agent"
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
    
        
    
    def getAllLandmarksWithAgentView(self, agentID):
        """
            Get all landmarks of other agents, where those agents have an active view of the scope of the supplied agent.
        """
        global graphAPI
        ownLandmarkPath = "Agent.Landmark"
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark"
        ownLandmarks = graphAPI.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        for ownLandmark in ownLandmarks:
            peers.remove(ownLandmark)
        return peers
     
     
    
    def getAgentView(self, agentID):
        """
            Return the pages on the supplied agent's current view.
        """
        scopePath = "Agent.Landmark::Agent.View::Agent.Page"
        viewedPages = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        return viewedPages   
        
        
    
    def getAgentScope(self, agentID):
        """
            Return the pages on the supplied agent's current scope.
        """
        scopePath = "Agent.Landmark::Agent.Scope::Agent.Page"
        peers = graphAPI.getLinkCounterpartsByType(agentID, scopePath, None)
        return peers
    '''    
        
    
    def getStimulusScope(self, stimulusID):
        """
            Return the pages on the supplied stimulus' current scope.
        """
        global graphAPI
        stimulusChoicePath = "Stimulus.StimulusChoice"
        conditionalStimulusPath = "Stimulus.ConditionalStimulus"
        stimulusPath = "Stimulus.Stimulus"
        
        metamemeType = graphAPI.getEntityMetaMemeType(stimulusID)
    
        try:
            ''' Three params: entity, metaMemePath, linkType'''
            pageIDList = []
            if metamemeType.count(stimulusChoicePath) > 0:
                localPageIDList = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                pageIDList.extend(localPageIDList)    
            elif metamemeType.count(conditionalStimulusPath) > 0:
                localPageIDListFree = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                localPageIDListAn = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                pageIDList.extend(localPageIDListFree)    
                pageIDList.extend(localPageIDListAn)
            elif metamemeType.count(stimulusPath) > 0:
                localPageIDListFree = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
                localPageIDListAn = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
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
        
        



class StimulusProfile(object):
    """
        This class contains acts as a container for a single stimulus report.  When finished, it contains:
        A stimulus ID
        A list of all agents that need to have this stimulus resolved and rendered
        A list of any render stage conditions that need to be resolved
    """
    className = "StimulusProfile"
    
    def __init__(self, stimulusID, conditionSet = [], anchors = [], isDeferred = False, dependentConditions = None):
        global graphAPI
        self.stimulusID = stimulusID
        self.conditionSet = conditionSet
        self.agentSet = set([])
        self.isDeferred = isDeferred
        self.dependentConditions = dependentConditions
        self.anchors = anchors
        self.stimulusMeme = "(unknown)"
        try: self.stimulusMeme = graphAPI.getEntityMemeType(self.stimulusID)
        except: pass
        
        
    def addAgents(self, agentSet):
        self.agentSet = agentSet
        
    def resolve(self, runtimeVariables):
        method = self.className + '.' + moduleName + '.' + 'resolve'
        global graphAPI
        descriptorPath = "*::Stimulus.Descriptor::*"
        try:
            descriptorIDList = self.getDescriptors() 
            descriptorID = descriptorIDList[0] #Descriptor is a switch and only ever has one child
            self.descriptorID = descriptorID
            self.resolvedDescriptor = graphAPI.evaluateEntity(descriptorID, runtimeVariables)
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
        global graphAPI
        descFreePath = "Stimulus.FreeStimulus::Stimulus.Descriptor"
        descAnchoredMPath = "Stimulus.AnchoredStimulus::Stimulus.Descriptor"   
        freeStimulusDescriptors = graphAPI.getLinkCounterpartsByMetaMemeType(self.stimulusID, descFreePath)
        anchoredStimulusDescriptors = graphAPI.getLinkCounterpartsByMetaMemeType(self.stimulusID, descAnchoredMPath)  
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
        method = self.className + '.' + moduleName + '.' + 'getBucketLists'
        global graphAPI
        orderedBucketList = {}
        
        stimulusChoicePath = "Stimulus.StimulusChoice"
        conditionalStimulusPath = "Stimulus.ConditionalStimulus"
        stimulusPath = "Stimulus.Stimulus"
        conditionPath = "Graphyne.Condition.Condition"  #We'll be using this in multiple places later
        anchorPath = "Stimulus.AnchoredStimulus::Stimulus.Anchor::Stimulus.Stimulus" #This is relative to Stimulus.Stimulus
        metamemeType = graphAPI.getEntityMetaMemeType(conditionalStimulusID)
        
        stimulusProfile = None

        if (metamemeType == stimulusPath):
            #The simplest case.  There are no conditions to worry about
            anchorList = graphAPI.getLinkCounterpartsByMetaMemeType(conditionalStimulusID, anchorPath)
            #script, stimulusID, conditionSet, anchors = [], isDeferred = False, dependentConditions = None
            stimulusProfile = StimulusProfile(conditionalStimulusID, [], anchorList)
            orderedBucketList = {0 : stimulusProfile}         
        elif metamemeType == stimulusChoicePath:
            conditionElements = graphAPI.getLinkCounterpartsByMetaMemeType(conditionalStimulusID, conditionalStimulusPath)
            
            #now, determine the "buckets"
            masterdeferredList = {}
            for conditionElement in conditionElements:
                memeName = graphAPI.getEntityMemeType(conditionElement)
                if memeName in Engine.renderStageStimuli:
                    prio = 0
                    hasPriority = graphAPI.getEntityHasProperty(conditionElement, "Priority")
                    if hasPriority is True:
                        prio = graphAPI.getEntityPropertyValue(conditionElement, "Priority")
                    masterdeferredList[prio, conditionElement]
                    
            #Now, make a second pass, this time looking at everything
            for conditionElement in conditionElements:
                dependentList = []
                prio = 0
                hasPriority = graphAPI.getEntityHasProperty(conditionElement, "Priority")
                if hasPriority is True:
                    prio = graphAPI.getEntityPropertyValue(conditionElement, "Priority")
                for deferredKey in masterdeferredList.keys():
                    if prio < deferredKey:
                        dependentList.append(masterdeferredList[deferredKey])
                        
                stimulusID = graphAPI.getLinkCounterpartsByMetaMemeType(conditionElement, stimulusPath)
                conditionID = graphAPI.getLinkCounterpartsByMetaMemeType(conditionElement, conditionPath)
                anchorList = graphAPI.getLinkCounterpartsByMetaMemeType(stimulusID, anchorPath)
                        
                memeName = graphAPI.getEntityMemeType(conditionElement)
                if memeName in Engine.renderStageStimuli:
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
        method = moduleName + '.' + self.className + '.' + 'filter'
        global graphAPI
        
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
                    
                    #conditionResults = script.map(self.mapFunctionConditions, conditions, argumentMap)
                    #conditionsTrue = True
                    #if False in conditionResults:
                        #conditionsTrue = False
                    #return conditionsTrue
                except Exception as e:
                    conditionMeme = "unknown"
                    stimulusMeme = "unknown"
                    try:
                        conditionMeme = graphAPI.getEntityMemeType(stimulusProfile.conditionSet)
                        stimulusMeme = graphAPI.getEntityMemeType(stimulusProfile.stimulusID)
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
        method = moduleName + '.' + self.className + '.' + 'normalize'
        global graphAPI
        
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
                        stimulusMeme = graphAPI.getEntityMemeType(stimulusProfile.stimulusID)
                        errorMsg = "Can't disentangle lower prio conditional stimulus %s agent set from higher prio agent set.  Traceback = %s" %(stimulusMeme,e)
                        Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
            except Exception as e:
                errorMsg = ""
                try:
                    remaining = len(flowControlList)
                    stimulusProfile = self.buckets[indexKey]
                    stimulusMeme = graphAPI.getEntityMemeType(stimulusProfile.stimulusID)
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





class Plugin(Engine.ServicePlugin):
    className = "Plugin"
    portID = 1049
    exposeSIQToAPI = 0 #This is normally not used; only to test if the sIQ is functioning properly.  It presents a security risk otherwise
    
    def initialize(self, scriptAPI, dtParams = None, rtParams = None):
        method = self.className + '.' + moduleName + '.' + 'initialize'
        global graphAPI
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            #use the instance of the graphyne API, which was already initialized by the main Engine module.
            graphAPI = scriptAPI
            
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , u"Design Time Parameters = %s" %(dtParams)])
            self._sleepperiod = 0.03    
            self._stopevent = threading.Event()
            self.startupIndexingFinished = False
            threading.Thread.__init__(self, name = rtParams['moduleName'])
        except Exception as e:
            errorMsg = "Fatal Error while starting Stimulus Engine. Traceback = %s" %e
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        
        
        
    def run(self):
        method = moduleName + '.' + self.className + '.' + 'run'
 
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Stimulus Engine waiting for initial loading of templates and entities to finish before it can start"])
        while Graph.readyToServe == False:
            time.sleep(5.0)
            Graph.logQ.put( [logType , logLevel.DEBUG , moduleName + '.' + self.className + '.' + 'run' , "...Stimulus Engine waiting for initial loading of templates and entities to finish"])
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run' , "Templates and Entities are ready.  Stimulus Engine Registrar may now be started"])
       
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Stimulus Engine Starting"])
        while not self.stoprequest.isSet():
            
            try:
                if self.startupIndexingFinished == False:
                    self.indexStimuli()
                    self.startupIndexingFinished = True
                else:
                    try:
                        '''Pop the oldest stimulus from the siq. It comes as a Engine.StimulusMessage,
                            which consists of a stimulusID, rtparams (as argumentMap) and agent list
                        '''
                        
                        stimulusSignal = Engine.siQ.get_nowait()                       
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
        
            stimulusSignal (an Engine.StimulusMessage) has the following attributes
            stimulusID - should always be present.  We have a problem if it is not
            targetAgents - this list might be empty.  Throw an exception if it is not a list
        '''
        method = self.className + '.' + moduleName + '.' + 'processStimulus'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        global graphAPI
        
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
                    queueList = Engine.broadcasterRegistrar.getBroadcastQueue(report.descriptorIDs[indexKey]) 
                    stimulusProfile = report.buckets[indexKey]
                    
                    #If there are recipients, build the report object and send it to the broadcasters 
                    if len(stimulusProfile.agentSet) > 0:
                        memePath = graphAPI.getEntityMemeType(stimulusProfile.stimulusID)
                        stimulusReport = Engine.StimulusReport(stimulusProfile.stimulusID, 
                                                               memePath, 
                                                               stimulusProfile.agentSet, 
                                                               stimulusProfile.resolvedDescriptor, 
                                                               stimulusProfile.isDeferred, 
                                                               stimulusProfile.anchors, 
                                                               stimulusProfile.dependentConditions)                        
                        for broadcastQueueID in queueList:
                            Engine.broadcasterRegistrar.broadcasterIndex[broadcastQueueID].put(stimulusReport)
                            
                            #Debug
                            #theMsg = "Queue %s length = %s, last value %s" %(broadcastQueueID, Engine.broadcasterRegistrar.broadcasterIndex[broadcastQueueID].qsize(), stimulusProfile.resolvedDescriptor)
                            #Graph.logQ.put( [logType , logLevel.WARNING, method , theMsg])
            except EngineExceptions.NoSuchBroadcasterError as e:
                memePath = graphAPI.getEntityMemeType(stimulusSignal.stimulusID)
                errorMsg = "Stimulus %s has no broadcaster.  Traceback = %s" %(memePath, e)
                Graph.logQ.put( [logType , logLevel.ERROR, method , errorMsg])
            except EngineExceptions.NullBroadcasterIDError as e:
                memePath = graphAPI.getEntityMemeType(stimulusSignal.stimulusID)
                errorMsg = "Stimulus %s has no broadcaster.  Traceback = %s" %(memePath, e)
                Graph.logQ.put( [logType , logLevel.ERROR, method , errorMsg])
            except Exception as e:
                pass

        except Exception as e:
            stimulusSignalMeme = "unknown"
            try:
                stimulusSignalMeme = graphAPI.getEntityMemeType(stimulusSignal.stimulusID)
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
        method = self.className + '.' + moduleName + '.' + 'execute'
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
        methodName = moduleName + '.' + self.className + '.' + 'indexStimuli'
        global graphAPI
        
        startTime = time.time()
        nTh = 1
        
        numberOfStimuli = Engine.stimulusIndexerQ.qsize()

        Graph.logQ.put( [logType , logLevel.INFO , methodName, "Descriptor (broadcaster) Indexer - Found %s descriptors to index" %(numberOfStimuli)])
        while self.startupIndexingFinished == False:
            try:
                stimulusToBeIndexed = Engine.stimulusIndexerQ.get_nowait()
                try:
                    Engine.broadcasterRegistrar.indexDescriptor(stimulusToBeIndexed)
                    nTh = nTh + 1
                except Exception as e:
                    stimulusMeme = graphAPI.getEntityMetaMemeType(stimulusToBeIndexed)
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
        method = moduleName + '.' + self.className + '.' + 'join'
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "......Stimulus Engine shut down"])
        self.stoprequest.set()
        super(Plugin, self).join(0.5)
        
        
    
    
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
        method = moduleName + '.' + self.className + '.' + 'mapFunctionCondition'
        
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
            script = argumentMap["api"]
            localResult = script.evaluateEntity(conditionID, argumentMap, actionID, agentID)
            
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
        method = moduleName + '.' + self.className + '.' + 'checkCondition'
        global graphAPI
        
        agentSet = self.selectAgents(stimulusID, excludeSet, subjectIDList)
        okAgents = []
        
        try:
            import copy
            localParams = copy.deepcopy(argumentMap)
            localParams["conditionID"] = conditionID
            localParams["api"] = graphAPI
            okAgents = graphAPI.map(self.mapFunctionCondition, list(agentSet), localParams)
        except Exception as e:
            conditionMeme = "unknown"
            stimulusMeme = "unknown"
            try:
                conditionMeme = graphAPI.getEntityMemeType(conditionID)
                stimulusMeme = graphAPI.getEntityMemeType(stimulusID)
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
        method = moduleName + '.' + self.className + '.' + 'selectAgents'
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


def usage():
    print(__doc__)

    
def main():
    pass


if __name__ == "__main__":
    pass