import copy
import uuid
import sys

import Graphyne.Graph as Graph
from ... import Engine
from ... import Exceptions

#remote debugger support for pydev
#import pydevd
    

#globals
moduleName = 'ActionEngine.Action'
logType = Graph.logTypes.CONTENT
logLevel = Graph.LogLevel()
actionInsertionTypes = Engine.ActionInsertionType()
api = None


class Action(object):
    className = 'Action'
    actionIndex = {}  # parameter is the action engine's action index and is used later to inflate member lists
    
    def initialize(self, script, uuid, actionID):
        method = moduleName + '.' + self.className + '.' + 'initialize'
        """
            uuid = the uuid of the child action element (KeyFrame, Catch, Throw, etc.)
            actionID = the uuid of the parent Action element
        """
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.uuid = uuid
            self.meme = script.getEntityMemeType(actionID)
            self.actionID = actionID
            self.instanceID = None
        except Exception as e:
            errorMsg = "Unknown error initializing action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        
        
    def refreshInstanceID(self):
        """
            Actions are singletons and self.uuid points back to the uuid of the memetic entity in the entity repository.
            Actions are initialized as singletons for performance reasons (to frontload the initialization overhead to server startup)
            and because actions of a given type are fungible.  However, we still want to have each instance of an action to have a 
            unique tracking ID for the lag-log's action life cycle tracking.
            
            Calling this method will generate a new UUID
        """
        method = moduleName + '.' + self.className + '.' + 'refreshInstanceID'
        try:
            self.instanceID = uuid.uuid1()
        except Exception as e:
            errorMsg = "Unknown error refreshing instance UUID on action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
            
    def getInflatedMemberList(self, unusedScript):
        method = moduleName + '.' + self.className + '.' + 'getInflatedMemberList'
        try:
            return [self.meme]
        except:
            errorMsg = "Can't run getInflatedMemberList() on initialized action"
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])   
            return []  
        
        
    def inflateMembers(self, script):
        #this method is only relevant for sets
        pass       
    
    
            
    def addLandMarks(self, script):
        """
            Find all of the landmarks attached to the keyframe
        """
        method = moduleName + '.' + self.className + '.' + 'addLandMarks'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            
            # The template paths of the various types of landmarks
            #lmExPath = "Action.RequiredLandmarks::Action.RequiredlandmarksExclusive::Action.RequiredLandmark::Agent.Landmark"
            #lmMPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
            #lmNoExPath = "Action.RequiredLandmarks::Action.RequiredLandmark::Agent.Landmark"
            
            lmExPath = "**::Action.RequiredlandmarksExclusive::Action.RequiredLandmark::Agent.Landmark"
            lmMPath = "**::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
            lmNoExPath = "**::Action.RequiredLandmark::Agent.Landmark"
            
            # Get the actual uuids of the various landmarks
            self.landmarksNonExclusive = script.getLinkCounterpartsByMetaMemeType(self.uuid, lmNoExPath, None, True)
            self.landmarksExclusive = script.getLinkCounterpartsByMetaMemeType(self.uuid, lmExPath, None, True)
            masterLandmarkList = script.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath, None, True)
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
                    masterLandmarkList = script.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath)
                    self.masterLandmark = masterLandmarkList[0]
                except Exception as e:
                    errorMsg = "Action %s has no master landmark defined" %self.meme
                    raise Exceptions.MemeMembershipValidationError(errorMsg)
            except Exceptions.MemeMembershipValidationError as e:
                raise e
            except Exception as e:
                masterLandmarkList = script.getLinkCounterpartsByMetaMemeType(self.uuid, lmMPath)
                errorMsg = "Action %s has no master landmark defined" %self.meme
                raise Exceptions.MemeMembershipValidationError(errorMsg)
            
            #Remote Debugger
            #pydevd.settrace()
            
            #self.landmarkTransforms = []
            reqLMRootPath = "**::Action.RequiredLandmark"
            reqLMPath = "Agent.Landmark"
            #reqLMTransformPath = "Action.LandmarkTransform"
            reqLMRoots = script.getLinkCounterpartsByMetaMemeType(self.uuid, reqLMRootPath)
            for reqLMRoot in reqLMRoots:
                reqLMs = script.getLinkCounterpartsByMetaMemeType(reqLMRoot, reqLMPath)
                #reqLMTransforms = script.getLinkCounterpartsByMetaMemeType(reqLMRoot, reqLMTransformPath)
                # Action.LandmarkTransform is optional, but a transform element only makes sense if one exists
                '''
                if len(reqLMTransforms) > 0:
                    #Agent.Offset
                    deltaX = None
                    deltaY = None
                    deltaZ = None
                    offsetDelta = script.getLinkCounterpartsByMetaMemeType(reqLMTransforms[0], "Agent.Offset")
                    if len(offsetDelta) > 0:
                        deltaX = script.getEntityPropertyValue(offsetDelta[0], "x")
                        deltaY = script.getEntityPropertyValue(offsetDelta[0], "y")
                        deltaZ = script.getEntityPropertyValue(offsetDelta[0], "z")
                        
                    #Agent.EuerAngles
                    rotationX = None
                    rotationY = None
                    rotationZ = None
                    euerAngles = script.getLinkCounterpartsByMetaMemeType(reqLMTransforms[0], "Agent.EuerAngles")
                    if len(euerAngles) > 0:
                        rotationXList = script.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationX")
                        rotationYList = script.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationY")
                        rotationZList = script.getLinkCounterpartsByMetaMemeType(euerAngles[0], "Agent.RotationZ")
                        rotationX = script.getEntityPropertyValue(rotationXList[0], "Angle")
                        rotationY = script.getEntityPropertyValue(rotationYList[0], "Angle")
                        rotationZ = script.getEntityPropertyValue(rotationZList[0], "Angle")
                        
                    transformDict = {"deltaX" : deltaX, "deltaY" : deltaY, "deltaZ" : deltaZ, "rotationX" : rotationX, "rotationY" : rotationY, "rotationZ" : rotationZ}
                    self.landmarkTransforms.append([reqLMs[0], transformDict])
                '''
        except Exceptions.MemeMembershipValidationError as e:
            Graph.logQ.put( [logType , logLevel.WARNING , method , e])
        except Exception as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            #tb = sys.exc_info()[2]
            errorMsg = "Error adding landmarks to keyframe object of action %s.  Traceback = %s, %s" %(self.meme, errorID, errorMsg)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
            
            
            
    def checkLandmarks(self, script, agentUUID, additionalLandmarks = []):
        method = moduleName + '.' + self.className + '.' + 'checkLandmarks'
        """
            additionalLandmarks allows us to pass an arbitrary set of landmark UUIDs at runtime, as an additional check
        """
        allTrue = False
        try:
            exTrue = self.checkExLists(script, agentUUID)
            nonExTrue = script.map(self.mapFunctionLandmarks, self.landmarksNonExclusive, agentUUID)
            masterTrue = script.map(self.mapFunctionLandmarks, [self.masterLandmark], agentUUID)
            allLandmarks = []
            allLandmarks.extend(exTrue)
            allLandmarks.extend(nonExTrue)
            allLandmarks.extend(masterTrue)
            
            if len(additionalLandmarks) > 0:
                #additionalLandmarks lists contain only UUIDs and not traverse paths, so we don't know the exact traverse paths to search.  Simply 
                #    ensure that additionalLandmarks landmarks are in the same cluster.  This is useful for decorated landmarks in action requests.  
                clustermembers = []
                cluster = script.getCluster(agentUUID)
                for clusterMember in cluster['nodes']:
                    #dict: {'metaMeme': 'Agent.View', 'meme': 'Agent.DefaultView', 'id': '008e23c0-e0e0-11e8-885b-720005fb5740'}
                    clustermembers.append(clusterMember['meme'])
                    
                additionalLandmarkMemes = []
                for additionalLandmark in additionalLandmarks:
                    landmarkMeme = script.getEntityMemeType(additionalLandmark)
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
    
    def checkExLists(self, script, agentUUID):
        method = moduleName + '.' + self.className + '.' + 'checkExLists'
        try:
            exTrue = script.map(self.mapFunctionLandmarks, self.landmarksExclusive, agentUUID)
            return exTrue
        except Exception as e:
            errorMsg = "Unknown error checking exclusive landmarks for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
        
        
    def mapFunctionLandmarks(self, landMarkID, agentUUID):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionLandmarks'
        try:
            api = Graph.api.getAPI()
            landMarkPath = api.getEntityMemeType(landMarkID)
            localResult = api.getHasCounterpartsByType(agentUUID, landMarkPath)
            return localResult 
        except Exception as e:
            errorMsg = "Unknown error mapping landmark %s for keyframe object of action %s.  Traceback = %s" %(landMarkPath, self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False   
        
        
        
    def bootstrap(self):
        pass
    
        
        
        
class ConditionalAction(object):
    className = 'ConditionalAction'
    
    def addConditions(self, script):
        method = moduleName + '.' + self.className + '.' + 'addConditions'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.conditions = []
            """ Adds conditions to those actions (KeyFrame, Throw) that require them  """
            conditionPath = "Graphyne.Condition.Condition"
            conditionElements = script.getLinkCounterpartsByMetaMemeType(self.uuid, conditionPath)
            for conditionElement in conditionElements:
                Graph.logQ.put( [logType , logLevel.DEBUG , method , "adding condition %s to action %s" %(conditionElement, self.uuid)])
                self.conditions.append(conditionElement)
        except Exception as e:
            actionID = None
            try: actionID = self.meme
            except: pass
            errorMsg = "Unknown error adding conditions to action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
            
        
    def mapFunctionConditions(self, script, conditionUUID, argumentMap):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionConditions'
        try:
            localResult = script.evaluateEntity(conditionUUID, argumentMap, argumentMap["actionID"], argumentMap["subjectID"], argumentMap["controllerID"])
            return localResult  
        except Exception as e:
            actionID = None
            try: actionID = self.meme
            except: pass
            errorMsg = "Unknown error testing individual condition on action %s.  Traceback = %s" %(actionID, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def checkConditions(self, script, argumentMap):
        method = moduleName + '.' + self.className + '.' + 'checkConditions'
        try:
            conditionResults = script.map(self.mapFunctionConditions, self.conditions, argumentMap)
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
    
    def bootstrap(self, script):
        method = moduleName + '.' + self.className + '.' + 'bootstrap'
        try:
            self.memberList = []
            self.packedMemberList = []
            self.addLandMarks(script)
            actionSetChildren = script.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.ChoreographyStep")
            tempPrio = {}
            try: #lv2
                for actionSetChild in actionSetChildren:
                    priority = script.getEntityPropertyValue(actionSetChild, "Priority")
                    action = script.getLinkCounterpartsByMetaMemeType(actionSetChild, "Action.Action")
                    tempPrio[priority] = action[0]#there should only be one action counterpart per ChoreographyStep
                    
                try: #lv3
                    implicitCatch = script.getEntityPropertyValue(self.uuid, "ImplicitCatch")
                    if implicitCatch == True:
                        #If implicitCatch is true, then create a Action.DefaultCatch 
                        #    and append it to self.packedMemberList before adding any other members
                        landmarkPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
                        landmarkID = script.getLinkCounterpartsByMetaMemeType(self.uuid, landmarkPath)
                        defaultCatchID = script.getEntityPropertyValue(landmarkID[0], 'DefaultCatch')
                        defaultCatchUUID = uuid.UUID(defaultCatchID)
                        defaultCatchMeme = script.getEntityMemeType(defaultCatchUUID)
                        self.packedMemberList.append(defaultCatchMeme)
                except Exception as e:
                    #level 3
                    pass
                try: #lv4
                    prioList = sorted(tempPrio.keys())
                    for prio in prioList:
                        sortedMemberUUID = tempPrio[prio]
                        sortedMember = script.getEntityMemeType(sortedMemberUUID)
                        #debug
                        #errorMsg = "Entity meme %s uuid = %s" %(sortedMemberUUID, tempPrio[prio])
                        #Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
                        #/debug
                        self.packedMemberList.append(sortedMember)
                except Exception as e:
                    errorMsg = "Unknown error setting up ChoreographyStep members on action %s.Traceback = %s" %(self.meme, e)
                    sortedMember = script.getEntityMemeType(sortedMemberUUID)
                    Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            except Exception as e:
                #level 2
                pass
        except Exception as e:
            errorMsg = "Unknown error bootstrapping choreography %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            #debug
            try:
                self.addLandMarks(script)
                actionSetChildren = script.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.ChoreographyStep")
                tempPrio = {}
                for actionSetChild in actionSetChildren:
                    priority = script.getEntityPropertyValue(actionSetChild, "Priority")
                    action = script.getLinkCounterpartsByMetaMemeType(actionSetChild, "Action.Action")
                    tempPrio[priority] = action
                    
                implicitCatch = script.getEntityPropertyValue(self.uuid, "ImplicitCatch")
                if implicitCatch == True:
                    #If implicitCatch is true, then create a Action.DefaultCatch 
                    #    and append it to self.packedMemberList before adding any other members
                    landmarkPath = "Action.RequiredLandmarks::Action.MasterLandmark::Action.RequiredLandmark::Agent.Landmark"
                    landmarkID = script.getLinkCounterpartsByMetaMemeType(self.uuid, landmarkPath)
                    defaultCatchID = script.getEntityPropertyValue(landmarkID[0], 'DefaultCatch')
                    defaultCatchUUID = uuid.UUID(defaultCatchID)
                    defaultCatchMeme = script.getEntityMemeType(defaultCatchUUID)
                    self.packedMemberList.append(defaultCatchMeme)
                prioList = sorted(tempPrio)
                for prio in prioList:
                    sortedMemberUUID = uuid.UUID(tempPrio[prio])
                    sortedMember = script.getEntityMemeType(sortedMemberUUID)
                    self.packedMemberList.append(sortedMember)
            except:
                pass
        
      
            
    def getInflatedMemberList(self, script):
        method = moduleName + '.' + self.className + '.' + 'getInflatedMemberList'
        returnList = []
        for taskItem in self.packedMemberList:
            #First, assert that we even have this action indexed
            try:
                assert taskItem in self.actionIndex
                memberEntity = self.actionIndex[taskItem]
                memberEntityMembers = memberEntity.getInflatedMemberList(script)
                returnList.extend(memberEntityMembers)
            except AssertionError:
                errorMessage = "Action set %s has member %s, which is not indexed in action engine" %(self.meme, taskItem)
                Graph.logQ.put( [logType , logLevel.ERROR , method , errorMessage])
        #debug
        #debugMessage = "Action set %s has the following members: %s" %(self.meme, returnList)
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
        #/debug
        return returnList
    
    
    
    def inflateMembers(self, script):
        inflatedmemberList = self.getInflatedMemberList(script) 
        self.memberList = inflatedmemberList


    
class KeyFrame(Action, ConditionalAction):
    className = 'KeyFrame'
    
    def bootstrap(self, script):
        self.addLandMarks(script)
        self.addConditions(script)
        self.addObjectSelectionConditions(script)
        self.addStateChanges(script)
        self.addStimuli(script)
        self.addControllers(script)
        self.addRestrictedView(script)
        self.addTimescale(script)
        
    
        
    def addObjectSelectionConditions(self, script):
        method = moduleName + '.' + self.className + '.' + 'addObjectSelectionConditions'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            conditionPath = "Action.ObjectSelectionCondition::Graphyne.Condition.Condition"
            self.objectSelectionConditions = script.getLinkCounterpartsByMetaMemeType(self.uuid, conditionPath)
        except Exception as e:
            errorMsg = "Unknown error adding object selection conditions to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])

        
        
    def addStateChanges(self, script):  
        method = moduleName + '.' + self.className + '.' + 'addStateChanges'
        #Action.StateChangeSet
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.stateChangesSimple = [] 
            self.stateChangesJoin = [] 
            self.stateChangesBreak = []
            self.stateChangeSuccessor = []
            
            stateChangeElements = script.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.StateChangeSet")
            if len(stateChangeElements) > 0:
                #StateChangeSet is a switch and will have one of the following children:
                #    SimpleStateChange, LinkJoin, LinkBreak or SuccessorAction
                scElements = script.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.SimpleStateChange")
                ljElements = script.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.LinkJoin")
                lbElements = script.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.LinkBreak")
                saElements = script.getLinkCounterpartsByMetaMemeType(stateChangeElements[0], "Action.SuccessorAction")
                
                for scElement in scElements:
                    #SimpleStateChange have two mandatory elements, a Change and a State, the latter of which extends Intentsity.Condition.AgentAttributeArgument
                    changeElements = script.getLinkCounterpartsByMetaMemeType(scElement, "Action.Change")
                    conditionIDs = script.getLinkCounterpartsByMetaMemeType(scElement, "Graphyne.Condition.Condition")
                    
                    stateElements = script.getLinkCounterpartsByMetaMemeType(scElement, "Action.State")
                    statePath = script.getEntityPropertyValue(stateElements[0], "SubjectArgumentPath")
                    
                    conditionalStimuli = self.getConditionalStimuli(script, scElement)
                    stateChange = StateChangeSimple(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(changeElements[0], statePath)
                    self.stateChangesSimple.append(stateChange)
                    
                for ljElement in ljElements:
                    conditionIDs = script.getLinkCounterpartsByMetaMemeType(ljElement, "Graphyne.Condition.Condition")
                    subjectPath = script.getEntityPropertyValue(ljElement, "SubjectArgumentPath")
                    objectPath = script.getEntityPropertyValue(ljElement, "ObjectArgumentPath")
                    linkTypeStr = script.getEntityPropertyValue(ljElement, "LinkType")
                    
                    linkType = 0
                    if linkTypeStr == "SubAtomic":
                        linkType = 1
                    conditionalStimuli = self.getConditionalStimuli(script, ljElement)
                    stateChange = StateChangeJoin(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(subjectPath, objectPath, linkType)
                    self.stateChangesJoin.append(stateChange)
                    
                for lbElement in lbElements:
                    conditionIDs = script.getLinkCounterpartsByMetaMemeType(lbElement, "Graphyne.Condition.Condition")
                    subjectPath = script.getEntityPropertyValue(lbElement, "SubjectArgumentPath")
                    objectPath = script.getEntityPropertyValue(lbElement, "ObjectArgumentPath")
                    conditionalStimuli = self.getConditionalStimuli(script, lbElement)
                    stateChange = StateChangeBreak(conditionIDs[0], conditionalStimuli)
                    stateChange.prime(subjectPath, objectPath)
                    self.stateChangesBreak.append(stateChange)
                    
                for saElement in saElements:
                    conditionIDs = script.getLinkCounterpartsByMetaMemeType(saElement, "Graphyne.Condition.Condition")
                    priority = script.getEntityPropertyValue(conditionIDs[0], "priority")
                    followOnActions = script.getLinkCounterpartsByMetaMemeType(saElement, "Action.Action")
                    insertionTypeStr = script.getEntityPropertyValue(saElement, "InsertionType")
                    
                    insertionType = actionInsertionTypes.APPEND
                    if insertionTypeStr == "Head":
                        linkType = 1
                    elif insertionTypeStr == "HeadClear":
                        linkType = 2
                    conditionalStimuli = self.getConditionalStimuli(script, saElement)
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

        
        
    def addStimuli(self, script):
        method = moduleName + '.' + self.className + '.' + 'addStimuli'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        #Stimulus.ConditionalStimulus
        try:
            self.conditionalStimuli = self.getConditionalStimuli(script, self.uuid)
        except Exception as e:
            errorMsg = "Unknown error adding stimuli information to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
        

    def getConditionalStimuli(self, script, rootNodeID):
        """
        Keyframes may link to ConditionalStimulus elements directly, or indirectly via StateChange.  
            Also, general keyframe conditional stimuli are stored directly on the keyframe, while
            those associated with a state change belong to the state change and are only added 
            self.conditionalStimuli immediately prior to stimuli distribution, which follows state changes.
        """
        method = moduleName + '.' + self.className + '.' + 'getConditionalStimuli'
        try:
            #Stimulus.StimulusChoice
            conditionalStimuli = []
            conditionalStimuli = script.getLinkCounterpartsByMetaMemeType(rootNodeID, "Stimulus.StimulusChoice")
            return conditionalStimuli
        except Exception as e:
            errorMsg = "Unknown error getting conditional stimuli for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return []
    
    
    def addRequiredCondition(self):
        #toto
        pass
        
        
    def addControllers(self, script):
        #Todo
        method = moduleName + '.' + self.className + '.' + 'addControllers'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            controllerBlacklist = None
            controllerWhitelist = None
            self.controllerBlacklist = controllerBlacklist
            self.controllerWhitelist = controllerWhitelist
        except Exception as e:
            errorMsg = "Unknown error adding controllers to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        
        
    def addTimescale(self, script):
        method = moduleName + '.' + self.className + '.' + 'addTimescale'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.timescale = None
            timescaleElem = script.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.Timescale")
            if len(timescaleElem) > 1:
                self.timescale = timescaleElem[0]
        except Exception as e:
            errorMsg = "Unknown error adding tiimescale to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            
            
    def addRestrictedView(self, script):
        method = moduleName + '.' + self.className + '.' + 'addRestrictedView'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            self.view = None
            viewElem = script.getLinkCounterpartsByMetaMemeType(self.uuid, "Action.View::Agent.Page")
            if len(viewElem) > 1:
                self.view = viewElem[0]
        except Exception as e:
            errorMsg = "Unknown error adding view to keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        

        
    def mapFunctionObjects(self, script, objectID, rtParams):
        #We'll be adding objectID, passing on to script.map and really don't need any concurrency nonsense
        #    Hence the deepcopy
        method = moduleName + '.' + self.className + '.' + 'mapFunctionObjects'
        try:
            argumentMap = {}
            try:
                #If _intentsity_actionEngineModTest_responseQueue is a key in rtParams, then we are running in test mode.
                #    The key in question holds a queue object for the test action script.  Queue objects can't be copied!
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
            conditionResultSet = script.map(self.mapFunctionConditions, self.childConditions, argumentMap)
            if False not in conditionResultSet:
                localResult = objectID
            return localResult    
        except Exception as e:
            errorMsg = "Unknown error mapping objects for keyframe object of action %s.  rtparams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return None
    
    
    def mapFunctionCheckEulerTransforms(self, landmarkTransform):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionCheckEulerTransforms'
        try:
            transformDict = landmarkTransform[1]
            transformResult = self.checkEulerAngles(landmarkTransform[0], transformDict["rotationX"], transformDict["rotationY"], transformDict["rotationZ"])
            return transformResult
        except Exception as e:
            errorMsg = "Unknown error mapping euler transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def mapFunctionCheckDeltaTransforms(self, landmarkTransform):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionCheckDeltaTransforms'
        try:
            transformDict = landmarkTransform[1]
            transformResult = self.checkDeltas(landmarkTransform[0], transformDict["deltaX"], transformDict["deltaY"], transformDict["deltaZ"])
            return transformResult
        except Exception as e:
            errorMsg = "Unknown error mapping transform deltas for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return False
    
    
    def mapFunctionStateChangesInner(self, script, stateChange, argumentMap):
        #self.conditionID = conditionID
        #self.stateChangeStimuli = stateChangeStimuli
        method = moduleName + '.' + self.className + '.' + 'mapFunctionStateChangesInner'
        try:
            conditionResult = script.evaluateEntity(stateChange.conditionID, argumentMap, argumentMap["actionID"], argumentMap["subjectID"], argumentMap["controllerID"])
            if conditionResult == True:
                stateChange.execute(argumentMap["subjectID"], argumentMap["objectID"])
                self.conditionalStimuli.extend(stateChange.stateChangeStimuli)
        except Exception as e:
            errorMsg = "Unknown error mapping state change for keyframe object of action %s.  argumentMap = %s Traceback = %s" %(self.meme, argumentMap, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return None
            
    
    def mapFunctionStateChangesOuter(self, objectID, rtParams):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionStateChangesOuter'
        try:
            argumentMap = {}
            try:
                #If _intentsity_actionEngineModTest_responseQueue is a key in rtParams, then we are running in test mode.
                #    The key in question holds a queue object for the test action script.  Queue objects can't be copied!
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
            unusedReturn = self.script.map(self.mapFunctionStateChangesInner, self.stateChangesBreak, argumentMap)
            unusedReturn = self.script.map(self.mapFunctionStateChangesInner, self.stateChangesJoin, argumentMap)
            unusedReturn = self.script.map(self.mapFunctionStateChangesInner, self.stateChangesSimple, argumentMap)
            unusedReturn = self.script.map(self.mapFunctionStateChangesInner, self.stateChangeSuccessor, argumentMap)
        except copy.Error as e:
            #Logged as error instead of warning because an uncopyable paramater payload from a client may be indicative of an attempted attack.
            errorMsg = "Unable to map state change for keyframe object of action %s because runtime parameters contains an uncopyable object!  rtParams = %s" %(self.meme, rtParams)
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        except Exception as e:
            errorMsg = "Unknown error mapping state change for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return None
    
    
    def mapFunctionSetEulerTransforms(self, script, landmarkTransform):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionSetEulerTransforms'
        try:
            transformDict = landmarkTransform[1]
            landmarkID = landmarkTransform[0]
            eulerElem = script.getLinkCounterpartsByMetaMemeType(landmarkID, "Agent.Offset::Agent.EuerAngles")
            if len(eulerElem) > 0:
                eulerXElem = script.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                eulerYElem = script.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                eulerZElem = script.getLinkCounterpartsByMetaMemeType(eulerElem, "Agent.RotationX")
                unusedEulerX = script.setEntityPropertyValue(eulerXElem[0], "Angle", transformDict["rotationX"])
                unusedEulerY = script.setEntityPropertyValue(eulerYElem[0], "Angle", transformDict["rotationY"])
                unusedEulerZ = script.setEntityPropertyValue(eulerZElem[0], "Angle", transformDict["rotationZ"])
        except Exception as e:
            errorMsg = "Unknown error mapping euler transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return True
    
    
    def mapFunctionSetDeltaTransforms(self, script, landmarkTransform):
        method = moduleName + '.' + self.className + '.' + 'mapFunctionSetDeltaTransforms'
        try:
            transformDict = landmarkTransform[1]
            landmarkID = landmarkTransform[0]
            offsetElem = script.getLinkCounterpartsByMetaMemeType(landmarkID, "Agent.Offset")
            if len(offsetElem) > 0:
                unusedDeltaX = script.setEntityPropertyValue(offsetElem[0], "x", transformDict["deltaX"])
                unusedDeltaY = script.setEntityPropertyValue(offsetElem[0], "y", transformDict["deltaY"])
                unusedDeltaZ = script.setEntityPropertyValue(offsetElem[0], "z", transformDict["deltaZ"])
        except Exception as e:
            errorMsg = "Unknown error mapping delta transforms for keyframe object of action %s.  landmarkTransform = %s Traceback = %s" %(self.meme, landmarkTransform[1], e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        finally: return True
        
    # /Landmarks
 
    
    # objects
    def selectObjects(self, script, rtParams, objectID = None):
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
        method = moduleName + '.' + self.className + '.' + 'selectObjects'
        try:
            if self.view is not None:
                #Use 'action perspective' view
                if (len(self.objectSelectionConditions) < 1) and (objectID is None):
                    viewList = script.getAllAgentsInSpecifiedPage(self.view)
                    return viewList
                elif (len(self.objectSelectionConditions) < 1) and (objectID is not None):
                    viewList = script.getAllAgentsInSpecifiedPage(self.view)
                    if objectID in viewList:
                        return [objectID]
                    else:
                        return []
                else:
                    intersectedObjects = script.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = script.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    return viewList
            else:
                #Use 'subject perspective' view
                if (len(self.objectSelectionConditions) < 1) and (objectID is None):
                    return []
                elif (len(self.objectSelectionConditions) < 1) and (objectID is not None):
                    return [objectID]
                elif objectID is not None:
                    intersectedObjects = script.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = script.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    if objectID not in viewList:
                        viewList.append(objectID)
                    return viewList
                else:
                    intersectedObjects = script.getAllAgentsInAgentView(rtParams["subjectID"])
                    viewList = script.map(self.mapFunctionObjects, intersectedObjects, rtParams)
                    viewList.remove(None)
                    return viewList
        except Exception as e:
            errorMsg = "Unknown error selecting object entities for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            return []
    # /objects
    
    
    # State Changes
    def changeStates(self, script, rtParams):
        method = moduleName + '.' + self.className + '.' + 'changeStates'
        try:
            self.script = script
            stateChangeStimuli = script.map(self.mapFunctionStateChangesOuter, rtParams["objectID"], rtParams)
            self.conditionalStimuli.extend(stateChangeStimuli)
        except Exception as e:
            errorMsg = "Unknown error changing states for keyframe object of action %s.  rtParams = %s Traceback = %s" %(self.meme, rtParams, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
    #/ State Changes
    

    
    
    # Stimuli
    def broadcastStimuli(self, script, rtParams):
        method = moduleName + '.' + self.className + '.' + 'broadcastStimuli'
        try:
            for conditionalStimulus in self.conditionalStimuli:
                if conditionalStimulus is not None:
                    stimulusMessage = None
                    #Engine.StimulusMessage def __init__(self, stimulusID, argumentMap, targetAgents = []):
                    if ("stimuliRecipients" in rtParams) == True:
                        targets = rtParams["stimuliRecipients"]
                        stimulusMessage = Engine.StimulusMessage(conditionalStimulus, rtParams, targets)
                    else:
                        stimulusMessage = Engine.StimulusMessage(conditionalStimulus, rtParams, [])
                    Engine.siQ.put(stimulusMessage)
        except Exception as e:
            errorMsg = "Unknown error broadcasting stimuli for keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])


    def invoke(self, script, rtParams):
        method = moduleName + '.' + self.className + '.' + 'invoke'
        try:
            #todo - refactor script.evaluateEntity to add objects
            script.evaluateEntity(self.uuid, rtParams, rtParams['actionID'], rtParams['subjectID'], rtParams['objectID'])
        except Exception as e:
            errorMsg = "Unknown error invoking keyframe object of action %s.  Traceback = %s" %(self.meme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
        



class Catch(Action, ConditionalAction):
    className = 'Catch'
    
    def bootstrap(self, script):
        self.addConditions(script)
        self.addLandMarks(script)




class Throw(Action, ConditionalAction):
    className = 'Throw'
    def bootstrap(self, script):
        self.addConditions(script)
        self.addLandMarks(script)



class StateChange(object):
    def __init__(self, conditionID, stateChangeStimuli = []):
        self.conditionID = conditionID
        self.stateChangeStimuli = stateChangeStimuli
                
       
class StateChangeBreak(StateChange):
    def prime(self, subjectPath, objectPath):
        self.subjectPath = subjectPath
        self.objectPath = objectPath    
    
    def execute(self, script, subjectID, objectID):
        script.removeEntityLink(subjectID, objectID)
        self
        
        
class StateChangeJoin(StateChange):
    def prime(self, subjectPath, objectPath, linkType):
        self.linkType = linkType
        self.subjectPath = subjectPath
        self.objectPath = objectPath
    
    def execute(self, script, subjectID, objectID):
        subjectMountPoint = script.getLinkCounterpartsByMetaMemeType(subjectID, self.subjectPath)
        objectMountPoint = script.getLinkCounterpartsByMetaMemeType(subjectID, self.objectPath)
        script.addEntityLink(subjectMountPoint[0], objectMountPoint[0], {}, self.linkType)
        
        
class StateChangeSimple(StateChange):
    def prime(self, changeID, path):
        #channgeID is the uuid of the relevant Numeric.Function entity
        #stateID is the path to be changed
        self.changeID = changeID 
        self.path = path
        
    def execute(self, script, subjectID, objectID):
        delta = script.evaluateEntity(self.changeID)
        oldPropValue = script.getEntityPropertyValue(objectID, self.path)
        newPropValue = oldPropValue + delta
        script.setEntityPropertyValue(objectID, self.path, newPropValue) 
    

    
class StateChangeSuccessorAction(StateChange):
    def prime(self, actionID, insertionType, priority):
        self.actionID = actionID 
        self.insertionType = insertionType
        self.priority = priority
        
    def execute(self, subjectID, objectID):
        #todo -
        actionInvoc = {"actionID" : self.actionID, "subjectID" : subjectID, "objectID" : objectID, "controllerID" : None, "insertionType" : self.insertionType, "rtparams" : {}}
        Engine.aQ.put(actionInvoc) 
        
        
#globals



def getActionIndexItem(script, toBeIndexed):
    method = moduleName + '.' + 'getActionIndexItem'
    Graph.logQ.put( [logType , logLevel.DEBUG ,  method, " - entering"])
    
    try:
        actionMemes = []
        action = None
        
        actionMemes = script.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Throw")
        if len(actionMemes) > 0:
            memeName = script.getEntityMemeType(toBeIndexed)
            Graph.logQ.put( [logType , logLevel.DEBUG ,  method, "Action %s is a Throw" %memeName])
            try:
                action = Throw()
                action.initialize(script, actionMemes[0], toBeIndexed)
            except Exception as e:
                actionMeme = None
                try: actionMeme = actionMemes[0]
                except: pass
                errorMsg = "Member Action.Throw entity %s is invalid" %actionMeme
                raise Exceptions.TemplatePathError(errorMsg)
        else:
            actionMemes = script.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Catch")
            if len(actionMemes) > 0:
                Graph.logQ.put( [logType , logLevel.DEBUG ,  method, "Action %s is a Catch" %toBeIndexed])
                try:
                    action = Catch()
                    action.initialize(script, actionMemes[0], toBeIndexed)
                except Exception as e:
                    actionMeme = None
                    try: actionMeme = actionMemes[0]
                    except: pass
                    errorMsg = "Member Action.Catch entity %s is invalid" %actionMeme
                    raise Exceptions.TemplatePathError(errorMsg)
            else:
                memeName = Graph.api.getEntityMemeType(toBeIndexed)
                actionMemes = script.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.Choreography")
                if len(actionMemes) > 0:
                    Graph.logQ.put( [logType , logLevel.DEBUG ,  method, "Action %s is a Choreography" %memeName])
                    try:
                        action = ActionSet()
                        action.initialize(script, actionMemes[0], toBeIndexed)
                    except Exception as e:
                        actionMeme = None
                        try: actionMeme = actionMemes[0]
                        except: pass
                        errorMsg = "Member Action.Choreography entity %s is invalid" %actionMeme
                        raise Exceptions.TemplatePathError(errorMsg)
                else:
                    actionMemes = script.getLinkCounterpartsByMetaMemeType(toBeIndexed, "Action.KeyFrame")
                    if len(actionMemes) > 0:
                        Graph.logQ.put( [logType , logLevel.DEBUG ,  method, "Action %s is a KeyFrame" %memeName])
                        try:
                            action = KeyFrame()
                            action.initialize(script, actionMemes[0], toBeIndexed)
                        except Exception as e:
                            actionMeme = None
                            try: actionMeme = actionMemes[0]
                            except: pass
                            errorMsg = "Member Action.KeyFrame entity %s is invalid" %actionMeme
                            raise Exceptions.TemplatePathError(errorMsg)
                    else:
                        linkOverview = script.getEntityCounterparts(toBeIndexed)
                        errorMsg = "Action %s has no valid child type.  Link overview = %s" %(memeName, linkOverview)
                        Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
        #now finish creating the action object
        action.bootstrap(script)
        Graph.logQ.put( [logType , logLevel.DEBUG , method, "Bootstrapped %s %s" %(type(action), action.meme)])
        Graph.logQ.put( [logType , logLevel.DEBUG ,  method, " - exiting"])
        return action
    except Exceptions.ScriptError as e:
        actionMeme = script.getEntityMemeType(toBeIndexed)
        errorMsg = "Error in method while creating action index item %s.  Traceback = %s" %(actionMeme, e)
        Graph.logQ.put( [logType , logLevel.WARNING ,  method, errorMsg])
        raise e        
    except Exception as e:
        actionMeme = script.getEntityMemeType(toBeIndexed)
        errorMsg = "Error creating action index item %s.  Traceback = %s" %(actionMeme, e)
        Graph.logQ.put( [logType , logLevel.WARNING ,  method, errorMsg])
        raise e

        



def usage():
    print(__doc__)

    
def main(argv):
    pass
    
    
if __name__ == "__main__":
    pass
