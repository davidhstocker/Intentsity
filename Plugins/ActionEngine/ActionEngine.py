'''
Created on June 13, 2018

@author: David Stocker
'''

import threading
import copy
import queue
import time
import sys
#from collections import deque

import Graphyne.Graph as Graph
from ... import Engine
from ... import Exceptions
from . import Action

#remote debugger support for pydev
#import pydevd


class WorkerTerminationRequestStep(object):
    START = 0
    ROLLBACK = 1
    COMMIT = 2
    
    
class WorkerTerminationVerificationMessage(object):
    COMMIT = 0
    ROLLBACK = 1
    ERROR = 2
    
    
    
#globals
moduleName = 'ActionEngine.ActionEngine'
logType = Graph.logTypes.CONTENT
logLevel = Graph.LogLevel()
terminationSteps = WorkerTerminationRequestStep()
terminationVerificationMsg = WorkerTerminationVerificationMessage()
actionInsertionTypes = Engine.ActionInsertionType()






class Plugin(Engine.ServicePlugin):
    className = "Plugin"

    def initialize(self, script, dtParams = None, rtParams = None):
        # This method overrides the initialize from the parent class.
        method = moduleName + '.' + self.className + '.' + 'initialize'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        try:
            indexerapi = copy.deepcopy(script)
            
            self.script = script
            self.actionIndex = {}
            self.indexer = ActionIndexer(indexerapi, self.actionIndex)
            self.commQueue = queue.Queue()
            self.workerQueues = {}
            self.depricatedWorkerQueues = {}
            self._stopevent = threading.Event()
            self._sleepperiod = 0.03
            threading.Thread.__init__(self, name = rtParams['moduleName'])
        except Exception as e:
            errorMsg = "Fatal Error while starting Action Engine. Traceback = %s" %e
            Graph.logQ.put( [logType , logLevel.ERROR , method , errorMsg])
        
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
        

    def run(self):
        #method = moduleName + '.' + self.className + '.' + 'run'
        #try:
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Engine waiting for initial loading of templates and entities to finish before it can start the registrar"])
        while Graph.readyToServe == False:
            time.sleep(5.0)
            Graph.logQ.put( [logType , logLevel.DEBUG , moduleName + '.' + self.className + '.' + 'run' , "...Action Engine waiting for initial loading of templates and entities to finish"])
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run' , "Templates and Entities are ready.  action indexer may now be started"])
                
        self.indexer.start()
        
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Engine waiting for action indexer to be finished before starting to serve actions"])
        while self.indexer.startupStateActionsFinished == False:
            time.sleep(10.0)
            Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "...Action Engine waiting for action indexer to be finish starting"])
        
        for actionToBeInflatedKey in self.actionIndex:
            actionToBeInflated = self.actionIndex[actionToBeInflatedKey]
            actionToBeInflated.inflateMembers(self.script)
        Engine.startupStateActionEngineFinished = True
        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run' , "Action Indexer is ready.  Action Engine started"])
               
        #while not self._stopevent.isSet(  ):
        while not self.stoprequest.isSet():
            try:
                #actionInvoc = Engine.stagingQ.get_nowait()
                actionInvoc = Engine.aQ.get_nowait()
                
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
        method = moduleName + '.' + self.className + '.' + 'brokerAction'
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
                Engine.securityLogQ.put(securityMessage)
            except Exception as e:
                errorMsg = "unknown error during action copy and instance ID refresh. Traceback = %s" %e
                Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
                raise e
            
            #actionInvocation = Engine.ActionRequest(actionInvReq.actionMeme, actionInvReq.insertionType, actionInvReq.rtParams, actionInvReq.subjectID, actionInvReq.objectID, actionInvReq.controllerID)
            
            #Add the master landmark infromation
            masterLandmarkEntity = self.script.getEntity(actionInvocation.action.masterLandmark)
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
                    workerapi = copy.deepcopy(self.script)
                    worker = WorkerThread(workerapi, actionInvocation.masterLandmarkUUID, self.commQueue, self.actionIndex)
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
        method = moduleName + '.' + self.className + '.' + 'manageWorkers'
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
                                workerapi = copy.deepcopy(self.script)
                                newWorker = WorkerThread(workerapi, worker.queueID, self.commQueue, self.actionIndex)
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
        method = moduleName + '.' + self.className + '.' + 'join'
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
        super(Plugin, self).join(0.5)







class WorkerThread(threading.Thread):
    className = "WorkerThread"
    
    def __init__(self, script, queueID, commQueue, actionIndex):
        """
            queueID = the uuid of the entity landmark that the queue is associated with.  The workerQueues dictionary object uses
                this value as the key for the worker thread's entry.  The worker needs to track this value because it communicates 
                with the main AE thread via queue object and the UID is used as the identifier.
            commQueue = the queue object that the worker uses to communicate with the main AE thread
            registrarQueryQueue = the queue object that the worker uses to communicate with the action registrar
            actionIndex - a pointer to the main AE actionIndex, so that unpacked child actions in sets can be verified.
        """
        #self.name = "ActionEngineWorkerThread_%s" %queueID
        self.script = script
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
        method = moduleName + '.' + self.className + '.' + 'run'
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
                                1 - Open up the ActionSet, and create a new list of Engine.ActionRequestobjects;one for each keyframe
                                2 - Make sure that they are all head insert.
                                3 - reverse the order of the list (last keyframe in the sequence first.  first keyframe in the sequence last.)
                                4 - In the new order,post these new action requests.
                                5 - Because each has a head revision, they are added to the dQueue in reverse order from how they were posted to the aQ. They are now in the proper order
                        """
                        
                        #first, test the landmarks and and throw the whole choreography out if they don't work out
                        landmarksOK = actionInvocation.action.checkLandmarks(self.script, actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
                        if landmarksOK == True:
                            actionSetKeyframes = []
                            #debug
                            debugMessage = "%s is an ActionSet" %actionInvocation.actionMeme.fullTemplatePath
                            Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                            memenames = []
                            actionSetChildren = self.script.getLinkCounterpartsByMetaMemeType(actionInvocation.action.uuid, "Action.ChoreographyStep", None, False)
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
                                actionSubInvocation = Engine.ActionRequest(taskItem, actionInsertionTypes.HEAD, actionInvocation.rtParams, actionInvocation.subjectID, actionInvocation.objectID, actionInvocation.controllerID, actionInvocation.decoratingLandmarks)
                                actionSetKeyframes.append(actionSubInvocation)
                            
                            #actionSetKeyframes.reverse()
                            for actionSetKeyframe in actionSetKeyframes:
                                #Engine.aQ.put(actionSetKeyframe)
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
                                        Engine.securityLogQ.put(securityMessage)
                                    except Exception as e:
                                        errorMsg = "unknown error during action copy and instance ID refresh. Traceback = %s" %e
                                        Graph.logQ.put( [logType , logLevel.ERROR , method, errorMsg])
                                        raise e
                                    
                                    #Add the master landmark infromation
                                    masterLandmarkEntity = self.script.getEntity(actionSetKeyframe.action.masterLandmark)
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
                #debug
                '''
                debugMessage = "%s is an ActionSet" %actionInvocation.actionMeme
                Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                memenames = []
                actionSetChildren = self.script.getLinkCounterpartsByMetaMemeType(actionInvocation.action.uuid, "Action.ChoreographyStep")
                for actionSetChild in actionSetChildren:
                    try:
                        memeIDofChild = self.script.getEntityMemeType(actionSetChild)
                        memenames.append(memeIDofChild)
                    except:
                        pass
                
                #/debug
                if type(testActionSet) == type(actionInvocation.action):
                    for taskItem in actionInvocation.action.memberList:
                        actionSubInvocation = Engine.ActionRequest(taskItem, actionInsertionTypes.HEAD, actionInvocation.rtParams, actionInvocation.subjectID, actionInvocation.objectID, actionInvocation.controllerID)
                        actionSetKeyframes.append(actionSubInvocation)
                        #debug
                        debugMessage = "posting choreography member %s %s to action queue" %(actionInvocation.actionMeme, actionSubInvocation.actionMeme)
                        Graph.logQ.put( [logType , logLevel.DEBUG , method , debugMessage])
                        #/debug 
                elif type(testKeyFrame) == type(actionInvocation.action):
                    Engine.aQ.put(actionInvocation)
                
                #actionSetKeyframes.reverse()
                for actionSetKeyframe in actionSetKeyframes:
                    Engine.aQ.put(actionSetKeyframe)
                #debug
                '''
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
        method = moduleName + '.' + self.className + '.' + 'catchQueueException'
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
        method = moduleName + '.' + self.className + '.' + 'processKeyFrame'
        try:
            actionInvocation.rtParams["_intentsity_actionID_local"] = actionInvocation.action.instanceID
            actionInvocation.rtParams["_intentsity_processorID"] = self.queueID
            actionInvocation.rtParams["actionID"] = actionInvocation.action.uuid
            actionInvocation.rtParams["subjectID"] = actionInvocation.subjectID 
            actionInvocation.rtParams["controllerID"] = actionInvocation.controllerID
        
            #First check for validity
            landmarksOK = actionInvocation.action.checkLandmarks(self.script, actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
            conditionsOK = actionInvocation.action.checkConditions(self.script, actionInvocation.rtParams)
            if (landmarksOK == False) or (conditionsOK == False):
                errorMsg = ""
                actionMeme = self.script.getEntityMemeType(actionInvocation.rtParams["actionID"])
                subjectMeme = self.script.getEntityMemeType(actionInvocation.rtParams["subjectID"])
                if (landmarksOK == False):
                    #debug
                    landmarksOK = actionInvocation.action.checkLandmarks(self.script, actionInvocation.subjectID, actionInvocation.decoratingLandmarks)
                    #/debug
                    errorMsg = "Landmarks Invalid for action %s by subject %s.  " %(actionMeme, subjectMeme)
                if (conditionsOK == False):
                    errorMsg = "Conditions Invalid for action %s by subject %s.  " %(actionMeme, subjectMeme)
                raise Exceptions.ActionKeyframeExecutionError(errorMsg)
            
            startTime = time.time()
            
            objectList = actionInvocation.action.selectObjects(self.script, actionInvocation.rtParams, actionInvocation.objectID)
            actionInvocation.rtParams["objectID"] = objectList

            actionInvocation.action.changeStates(self.script, actionInvocation.rtParams)
            actionInvocation.action.broadcastStimuli(self.script, actionInvocation.rtParams)
            try:
                #rtParams, subjectID, controllerID, objectIDs
                actionInvocation.action.invoke(self.script, actionInvocation.rtParams)
            except Exception as e:
                errorMsg = "Error while invoking script on keyframe %s on landmark %s.  Subject = %s, object = %s  Traceback = %s" %(actionInvocation.actionMeme, self.queueID, actionInvocation.subjectID, actionInvocation.objectID, e)
                Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
                raise Exceptions.ActionKeyframeExecutionError(e)
                        
            #Now ensure that the action takes the required time
            endTime = time.time()
            duration = endTime - startTime
            #requiredTime = script.evaluateEntity(action.timescale, rtParams, action.uuid, subjectID, controllerID, True)
            requiredTime = 0.0
            cooldown = requiredTime - duration
            if cooldown > 0:
                time.sleep(cooldown) 
        except Exceptions.ActionKeyframeExecutionError as e:
            actionMeme = None
            subjectMeme = None
            objectMeme = None
            try:
                actionMeme = self.script.getEntityMemeType(actionInvocation.rtParams["actionID"])
            except: pass
            try:
                subjectMeme = self.script.getEntityMemeType(actionInvocation.subjectID)
            except: pass
            try:
                objectMeme = self.script.getEntityMemeType(actionInvocation.objectID)
            except: pass
            errorMsg = "Nested Exceptions.ActionKeyframeExecutionError Error while processing keyframe %s on landmark %s.  Subject = %s, object = %s  Traceback = %s" %(actionMeme, self.queueID, subjectMeme, objectMeme, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method , errorMsg])
            raise Exceptions.ActionKeyframeExecutionError(errorMsg) 
        except Exception as e:
            actionMeme = None
            subjectMeme = None
            objectMeme = None
            try:
                actionMeme = self.script.getEntityMemeType(actionInvocation.rtParams["actionID"])
            except: pass
            try:
                subjectMeme = self.script.getEntityMemeType(actionInvocation.subjectID)
            except: pass
            try:
                objectMeme = self.script.getEntityMemeType(actionInvocation.objectID)
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
        method = moduleName + '.' + self.className + '.' + 'shutdown'
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
        method = moduleName + '.' + self.className + '.' + 'awaitVerification'
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
        method = moduleName + '.' + self.className + '.' + 'finalizeShutdown'
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
    
    def __init__(self, script, actionIndex, useActionIndexerQ = True):
        """
            indexOver = a Queue.Queue object: iterate over it in the run loop.  (continual indexing of loaded action singletons)
            indexOver = None.  Index over the Entity repository ( Engine.entityRepository ) once, looking for actions.
        """
        method = moduleName + '.' + self.className + '.' + '__init__'
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
        self.actionIndex = actionIndex
        self.script = script
        self.useActionIndexerQ = useActionIndexerQ
        
        #It may be possible that multiple registrars are in use (such as in module testing)
        #    In those cases, we want to ensure that the registrar will only set Engine.startupStateActionsFinished to true
        #    the first time that we complete indexing of the repo, or run into an empty index queue and not on every loop
        self.startupStateActionsFinished = False
        
        self._stopevent = threading.Event()
        self._sleepperiod = 30.0
        threading.Thread.__init__(self)
        Graph.logQ.put( [logType , logLevel.ADMIN , method , "Action Indexer ready start caching action entities"])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])

        
    def run(self):
        Graph.logQ.put( [logType , logLevel.INFO , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer Starting"])
        startTime = time.time()
        
        #Remote debugging support
        #pydevd.settrace()
        
        if self.useActionIndexerQ == False:
            #index directly off of the entity repository; no later updates
            
            # if we iterate over the repo, there is always the danger of it changing while we work.  let's take a snapshot
            repoEntries = []
            entityList = self.script.getAllEntities()
            for entityID in entityList:
                repoEntries.append(entityID)
            
            numberOfEntities = len(repoEntries)
            Graph.logQ.put( [logType , logLevel.INFO , moduleName + '.' + self.className + '.' + 'run'  , "Indexer has %s entities to check" %numberOfEntities])
            #Now filter this list down to ones with "Action.Action" in their taxonomy
            fullMetamemeTaxonomyEntries = []
            nth = 1
            for entityID in repoEntries:
                try:
                    memeID = self.script.getEntityMemeType(entityID)
                    fullMetamemeTaxonomy = self.script.getTaxonomy(memeID)
                    if "Action.Action" in fullMetamemeTaxonomy:
                        #Engine.actionIndexerQ.put(entityID)
                        fullMetamemeTaxonomyEntries.append(entityID)
                    Graph.logQ.put( [logType , logLevel.INFO , moduleName + '.' + self.className + '.' + 'run'  , "Determined taxonomy on %s of %s entities" %(nth, numberOfEntities)])
                    nth = nth + 1
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , moduleName + '.' + self.className + '.' + 'run'  , "Unknown error indexing action %s.  Traceback = %s" %(entityID, e)])
                  
            #Now index the actions
            numberOfActions = len(fullMetamemeTaxonomyEntries)  
            Graph.logQ.put( [logType , logLevel.INFO , moduleName + '.' + self.className + '.' + 'run'  , "Indexer has %s actions to index" %numberOfActions])      
            jth = 1
            for toBeIndexed in fullMetamemeTaxonomyEntries:
                try:
                    self.indexItem(toBeIndexed)
                    Graph.logQ.put( [logType , logLevel.INFO , moduleName + '.' + self.className + '.' + 'run'  , "Indexed %s of %s actions" %(jth, numberOfActions)])
                    jth = jth + 1
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , moduleName + '.' + self.className + '.' + 'run'  , "Unknown error indexing action %s.  Traceback = %s" %(entityID, e)])

            
            endTime = time.time()
            deltaT = endTime - startTime
            self.startupStateActionsFinished = True
            Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Finished ad hoc load run"])
            Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Indexed %s actions in %s seconds" %(len(fullMetamemeTaxonomyEntries), deltaT)])
            Graph.logQ.put( [logType , logLevel.DEBUG , moduleName + '.' + self.className + '.' + 'run'  , "exiting"])
        else:
            #index off of the chosen queue
            nTh = 0
            finishedInitialIndexing = False
            while self.isAlive():
                try:
                    #toBeLogged = the memeID
                    Graph.logQ.put( [logType , logLevel.DEBUG , moduleName + '.' + self.className + '.' + 'run'  , "Checking Action Indexer Q.  Current number of estimated workitems = %s" %(Engine.actionIndexerQ.qsize())])
                    toBeIndexed = Engine.actionIndexerQ.get_nowait()
                    try:
                        Graph.logQ.put( [logType , logLevel.DEBUG , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer off of the chosen queue - Index %s" %(toBeIndexed)])
                        self.indexItem(toBeIndexed)
                        nTh = nTh + 1
                    except Exception as e:
                        Graph.logQ.put( [logType , logLevel.ERROR , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Problem indexing action %s.  Traceback = %s" %(toBeIndexed, e)])
                except queue.Empty:
                    if finishedInitialIndexing == False:
                        finishedInitialIndexing = True
                        endTime = time.time()
                        deltaT = endTime - startTime
                        self.startupStateActionsFinished = True
                        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Finished initial loading from engine action indexer queue"])
                        Graph.logQ.put( [logType , logLevel.ADMIN , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Indexed %s actions in %s seconds" %(nTh, deltaT)])
                    self._stopevent.wait(self._sleepperiod)
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.ERROR , moduleName + '.' + self.className + '.' + 'run'  , "Action Indexer - Unknown Error.  Traceback = %s" %e])
                    self._stopevent.wait(self._sleepperiod)
                   


    def join(self, timeout = 0.5):
        '''
        Stop the thread
        '''
        try:
            method = moduleName + '.' + self.className + '.' + 'join'
            Graph.logQ.put( [logType , logLevel.ADMIN , method , '......Action Indexer shutting down'])
            self._stopevent.set()
            threading.Thread.join(self, 0.5)
        except Exception as e:
            unusedDebugCatch = e
                    
                    


    def indexItem(self, toBeIndexed):
        method = moduleName + '.' + self.className + '.' + 'indexItem' 
        #toto - revert to .INFO
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"]) 
        try:
            action = Action.getActionIndexItem(self.script, toBeIndexed)
            
            #Actions are initially created with an empty dict for action index.
            #Add the action index to the actions so that they can later run getInflatedMemberList()
            action.actionIndex = self.actionIndex
            
            #Actions are indexed by meme path
            #self.registrar.actionIndex[action.meme] = action
            self.actionIndex[action.meme] = action
            Graph.logQ.put( [logType , logLevel.INFO , method, "Indexed %s to action registrar" %action.meme])
        except Exceptions.ScriptError as e:
            actionMeme = self.script.getEntityMemeType(toBeIndexed)
            errorMsg = "Error indexing action %s %s.  Traceback = %s" %(actionMeme, toBeIndexed, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
            raise e
        except Exception as e:
            actionMeme = self.script.getEntityMemeType(toBeIndexed)
            errorMsg = "Error indexing action %s %s.  Traceback = %s" %(actionMeme, toBeIndexed, e)
            Graph.logQ.put( [logType , logLevel.WARNING , method, errorMsg])
            raise e
        finally:
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
            pass
        
# /Threads


def usage():
    print(__doc__)

    
def main(argv):
    pass
    
    
if __name__ == "__main__":
    pass
