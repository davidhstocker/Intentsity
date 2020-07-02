'''
Created on June 13, 2018

@author: David Stocker
'''

import copy
import os
from os.path import expanduser
import sys
import argparse
import re
import codecs
import time
import urllib.request
import urllib.error
import queue
import uuid
from xml.dom import minidom
from time import ctime
import subprocess

from Intentsity import Engine
import Graphyne.Graph as Graph
from Graphyne import Fileutils
from Intentsity import Exceptions

from urllib import parse
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

rmlEngine = Engine.Engine()
responseQueue = queue.Queue()
entityList = []

#Globals
tiogaHome = os.path.dirname(os.path.abspath(__file__))
testDirPath = os.path.join(tiogaHome,"Config", "Test")
configDirPath = os.path.join(tiogaHome, "utils", "Config")  
resultFile = None
moduleName = 'smoketest'     
logType = Graph.logTypes.CONTENT
logLevel = Graph.logLevel


class DBError(ValueError):
    pass



def testEngineRestart(resetDB = False):
    """
        Test shutting down and starting the engine back up
        
        
        If the DB has been reset, then an entity created prior to shutdown should no longer be avaiable
    """
    method = moduleName + '.' + 'testServerAPIAdminStop'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = False

    try:
        #create a generic entity
        testuuid = rmlEngine.api.createEntity()
        
        #Shut down and start with the reset option set to True
        rmlEngine.shutdown()
        rmlEngine.start(True, resetDB)
        time.sleep(300.0)
        
        try:
            #this SHOULD fail.  The engine has been stopped and its 
            unusedTestEntity = rmlEngine.api.getEntity(testuuid)
            testResult = True
        except Exception as unusedE:
            unusedCatchme = ""
    except Exception as unusedE:
        unusedCatchme = ""
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    expectedResult = True
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str(expectedResult)
    results = [1, "Restart", testResult, expectedResult, ""]
    resultSet.append(results)
    return resultSet

    
    
def testActionQueue(resultFile, rawDataFile, parentAction = False, port = None):
    """
        This test method is a bit different than the ones before.  Previously, either one testfile was used, or none at all.
        Each line of the raw data file contains a list of actions.  These actions are sent to the queue in order of their
        appearance.  The results file also contains a list action meme paths.  These are the responses, in the order that
        they are expected.  The presence of choreographies, throws and catches will determine how much the results list looks
        like the raw data list.
        This has two:
            The results file - The pattern of the results file is:
                firstActionResponse, secondActionResponse, ...
            The raw data file - the pattern of this file is:
                agentID, firstAction, secondAction, ...
        If parentAction is True, then look for the parent action of the current keyframe (the executable on the action 
            is attached to the child keyframe)
                
        If port is left as None, then the action will be posted directly to the aQ.  Otherwise, it will go 
            via the simple xml-rpc action server.  The value for port is the port that the simple xml-rpc 
            server is listening on 
    """
    method = moduleName + '.' + 'testActionQueue'
       
    results = []
    resultSet = []
        
    #try:
    resultFileName = os.path.join(testDirPath, resultFile)
    resReadLoc = codecs.open(resultFileName, "r", "utf-8")
    resAllLines = resReadLoc.readlines()
    resReadLoc.close
    rawFileName = os.path.join(testDirPath, rawDataFile)
    rawReadLoc = codecs.open(rawFileName, "r", "utf-8")
    rawAllLines = rawReadLoc.readlines()
    rawReadLoc.close
    n = 0
    
    global rmlEngine
    for eachReadLine in resAllLines:
        try:
            rawLine = rawAllLines[n]
        except IndexError:
            break
        errata = []
        n = n+1
        testResult = []
        
        unicodeReadLine = str(eachReadLine)
        stringArray = []
        if unicodeReadLine != "***":
            stringArray = str.split(unicodeReadLine)
        
        unicodeRawReadLine = str(rawLine)
        stringRawArray = str.split(unicodeRawReadLine)

        try:
            #create an agent to use as the test agent
            agentMeme = stringRawArray.pop(0)
            agentID = None
            try:
                agentID = rmlEngine.api.createEntityFromMeme(agentMeme)
            except:
                #creating the agent failed because the agent mem does not exist.
                #There are test cases specifically geared toward trying to assign action to non-existant agents
                #simply make a fake uuid
                agentID = uuid.uuid4()
                            
            #create a queue
            resultQueue = queue.Queue()
            
            #Each test run shoudl use a unique controller ID, so that we're not mixing action commands from different test runs.
            controllerID = uuid.uuid4()
            
            rtparams = {}
            rtparams["controllerID"] = None
            rtparams["subjectID"] = agentID
            rtparams["objectID"] = agentID
            rtparams["_intentsity_actionEngineModTest_responseQueue"] = resultQueue
            rtparams["parentAction"] = parentAction
            rtparams["agentMeme"] = stringRawArray

            actionInsertionTypes = Engine.ActionInsertionType()
            
            for actionCommand in stringRawArray:
                actionInvocation = Engine.ActionRequest(actionCommand, actionInsertionTypes.APPEND, rtparams, agentID, agentID, controllerID)
                rmlEngine.aQ.put(actionInvocation)
                
            time.sleep(15.0)
            try:
                while True:
                    #returnQueue.put([memeID, instanceID, workerThread, currTime])
                    result = resultQueue.get_nowait()
                    if len(result) > 0:
                        testResult.append(result[0])
                    else:
                        testResult.append("***")
            except queue.Empty:
                if len(testResult) < 1:
                    #if testresult is emptyand wetime out on the queue, then the result of the action is considered null
                    testResult.append("***")   
                    
            while rmlEngine.aQ.qsize() > 0:
                time.sleep(1)
        except Exception as e:
            errorMsg = ('Error!  Traceback = %s' % (e) )
            errata.append(errorMsg)

        #if testResult is empty, make sure that it has "***"
        if len(testResult) < 1:
            testResult.append("***") 

        testcase = str(stringArray)
        allTrueResult = str(testResult)
        results = [n, stringRawArray, allTrueResult, testcase, errata]
        resultSet.append(results)
        
        Graph.logQ.put( [logType , logLevel.INFO , method , "Finished testcase %s: %s" %(n, actionInvocation.actionMeme.fullTemplatePath)])
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet 




def testActionQueueSingleAgent(resultFile, rawDataFile, agentMeme, parentAction = False, port = None):
    """
        A variant of testActionQueue, where a single agent is used.  The agentID is passed as a parameter
    """
    method = moduleName + '.' + 'testActionQueueSingleAgent'
       
    results = []
    resultSet = []
        
    #try:
    resultFileName = os.path.join(testDirPath, resultFile)
    resReadLoc = codecs.open(resultFileName, "r", "utf-8")
    resAllLines = resReadLoc.readlines()
    resReadLoc.close
    rawFileName = os.path.join(testDirPath, rawDataFile)
    rawReadLoc = codecs.open(rawFileName, "r", "utf-8")
    rawAllLines = rawReadLoc.readlines()
    rawReadLoc.close
    n = 0
    global rmlEngine

    agentID = None
    try:
        agentID = rmlEngine.api.createEntityFromMeme(agentMeme)
    except Exception as e:
        errorMessage = "Unable to create entity from testcase meme %s.  WTraceback = %s" %(agentMeme, e)
        Graph.logQ.put( [logType , logLevel.ERROR , method , errorMessage])
        
    for eachReadLine in resAllLines:
        rawLine = ""
        try:
            rawLine = rawAllLines[n]
        except:
            pass
        errata = []
        n = n+1
        testResult = []
        
        unicodeReadLine = str(eachReadLine)
        stringArray = []
        if unicodeReadLine != "***":
            stringArray = str.split(unicodeReadLine)
        
        unicodeRawReadLine = str(rawLine)
        stringRawArray = str.split(unicodeRawReadLine)

        try:
            #create a queue
            resultQueue = queue.Queue()
            
            rtparams = {}
            rtparams["controllerID"] = None
            rtparams["subjectID"] = agentID
            rtparams["objectID"] = agentID
            rtparams["_intentsity_actionEngineModTest_responseQueue"] = resultQueue
            rtparams["parentAction"] = parentAction

            actionInsertionTypes = Engine.ActionInsertionType()
            
            for actionCommand in stringRawArray:
                actionInvocation = Engine.ActionRequest(rmlEngine.api, actionCommand, actionInsertionTypes.APPEND, rtparams, agentID, agentID, None)
                #debug
                #if actionCommand == u"TestPackageActionEngine.SimpleActions.Action2":
                #    unusedcatch = "me"
                #/debug
                rmlEngine.aQ.put(actionInvocation)
                
            time.sleep(10.0)
            try:
                while True:
                    #returnQueue.put([memeID, instanceID, workerThread, currTime])
                    result = resultQueue.get_nowait()
                    if len(result) > 0:
                        testResult.append(result[0])
                    else:
                        testResult.append("***")
            except queue.Empty:
                if len(testResult) < 1:
                    #if testresult is emptyand wetime out on the queue, then the result of the action is considered null
                    testResult.append("***")   
        except Exception as e:
            errorMsg = ('Error!  Traceback = %s' % (e) )
            errata.append(errorMsg)

        testcase = str(stringArray)
        allTrueResult = str(testResult)
        results = [n, stringRawArray, allTrueResult, testcase, errata]
        resultSet.append(results)
        
        Graph.logQ.put( [logType , logLevel.INFO , method , "Finished testcase %s" %(n)])
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet 



def testActionEngineDynamicLandmarks(rawDataFile, port = None):
    """
        This test method examines the decoratingLandmarks parameter in the Engine.ActionRequest() __init__ method.  This
        parameter is used to pass additional, dynamic required landmarks to an action invocation, that are not defined in
        the action meme itself.  The basic strategy is to:
        1 - create an agent.
        2 - Allocate actions to this subject, some of which should work and some not (because of landmark restrictions on the
            action meme).  This is for calibration, to make sure that decoratingLandmarks don't add any regressions.
        3 - Allocate these same actions again, with a decoratingLandmark that the agent has  (should duplicate the results from 2)
        4 - Repeat, but with a decoratingLandmark that the agent does not have.  Should fail in all trials.
        
        The pattern of the raw data file file is:
            firstActionResponse, secondActionResponse, ...
            The raw data file - the pattern of this file is:
                agentID, actionID, additionalLandmark, True/False

    """
    method = moduleName + '.' + 'testActionEngineDynamicLandmarks'
       
    results = []
    resultSet = []
        
    #try:
    rawFileName = os.path.join(testDirPath, rawDataFile)
    rawReadLoc = codecs.open(rawFileName, "r", "utf-8")
    rawAllLines = rawReadLoc.readlines()
    rawReadLoc.close
    n = 0
    global rmlEngine
        
    for rawLine in rawAllLines:

        errata = []
        n = n+1
        testResult = "False"
        dynamicLandmark = ""
        
        unicodeRawReadLine = str(rawLine)
        stringRawArray = str.split(unicodeRawReadLine)
        actionCommand = stringRawArray[1]
        expectedResult = stringRawArray[3]

        try:
            #create an agent to use as the test agent
            agentMeme = stringRawArray[0]
            agentID = None
            try:
                agentID = rmlEngine.api.createEntityFromMeme(agentMeme)
            except Exception as e:
                raise e
            
            dynamicLandmarkID = []
            if stringRawArray[2] != "***":
                #use createEntityFromMeme to get the uuid of the landmark singleton
                dynamicLandmark = stringRawArray[2]
                dynamicLandmarkID = None
                try:
                    dynamicLandmarkUUID = rmlEngine.api.createEntityFromMeme(dynamicLandmark)
                    dynamicLandmarkID = [dynamicLandmarkUUID]
                except Exception as e:
                    raise e
                
            
            #create a queue
            resultQueue = queue.Queue()
            
            #Each test run shoudl use a unique controller ID, so that we're not mixing action commands from different test runs.
            controllerID = uuid.uuid4()
            
            rtparams = {}
            rtparams["controllerID"] = controllerID
            rtparams["subjectID"] = agentID
            rtparams["objectID"] = agentID
            rtparams["_intentsity_actionEngineModTest_responseQueue"] = resultQueue
            rtparams["parentAction"] = False
            rtparams["agentMeme"] = agentMeme

            actionInsertionTypes = Engine.ActionInsertionType()
            
            actionInvocation = Engine.ActionRequest(rmlEngine.api, actionCommand, actionInsertionTypes.APPEND, rtparams, agentID, agentID, controllerID, dynamicLandmarkID)
            rmlEngine.aQ.put(actionInvocation)
                
            time.sleep(15.0)
            try:
                while True:
                    #returnQueue.put([memeID, instanceID, workerThread, currTime])
                    result = resultQueue.get_nowait()
                    if len(result) > 0:
                        testResult = "True"
                    else:
                        testResult = "False"
            except queue.Empty:
                if len(testResult) < 1:
                    #if testresult is emptyand wetime out on the queue, then the result of the action is considered null
                    testResult = "False"   
                    
            while rmlEngine.aQ.qsize() > 0:
                time.sleep(1)
        except Exception as e:
            errorMsg = ('Error!  Traceback = %s' % (e) )
            errata.append(errorMsg)


        testcase = "%s, %s, %s" %(agentMeme, actionCommand, dynamicLandmark)
        results = [n, testcase, testResult, expectedResult, ""]
        resultSet.append(results)
        
        Graph.logQ.put( [logType , logLevel.INFO , method , "Finished testcase %s: %s" %(n, actionCommand)])
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet 



def testStimulusEngineTrailer():
    """
        Create a trailer request and drop it into the SiQ.  
        Then look in the broadcast queue and wait for the trailer report.
        If it comes before the timeout, then the test is successful 
        
        This method looks directly in the queue registered with the broadcast registrar
    """
    method = moduleName + '.' + 'testStimulusEngineTrailer'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = False
    
    #Let's create a Hello Agent
    agentPath = "AgentTest.HelloAgent"
    agentID = rmlEngine.api.createEntityFromMeme(agentPath)
    
    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)
    
    #Create the message and put it into the SiQ
    try:
        argumentMap = {}
        stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap, [agentID])
        #stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
        Engine.siQ.put(stimulusMessage)
        dummyIgnoreThis = "I'm just here to have a place to put a breakpoint"
    except Exception as e:
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "Error testing trailer.  Traceback = %s" %e])
    
    timeout = 10.0
    time.sleep(timeout)
    try:       
        #stimulusReport = urllib.request.urlopen("http://localhost:8080/test").read()
        
        #Look directly in the SiQ broadcast queue for the "test" broadcaster
        stimulusReport = Engine.broadcasterRegistrar.broadcasterIndex["test"].get_nowait()
        if stimulusReport.stimulusID == stimulusID:
            testResult = True
        else:
            Graph.logQ.put( [logType , logLevel.WARNING , method , "Trailer Stimulus Failed"])
            
        #Clear the queue in preperation for it being used in more tests
        while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
            try:
                unusedReport = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
            except queue.Empty:
                #ok.  Concurrency is being squirrelly.  The queue tests as not empty, but ends up empty.
                #  Let's not burn the world down over this  
                break
    except Exception as e:
        Graph.logQ.put( [logType , logLevel.WARNING , method , "Trailer Stimulus Timed Out."])
        testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testcase = "Trailer Stimulus"
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, ""]
    resultSet.append(results)
    return resultSet



def testStimulusEngineTrailer2(filename):
    """
        Create a set of agents.  
        For each agent/stimuluscombination,
            Create a trailer request and drop it into the SiQ.
        Then look in the broadcast queue:
            Wait for the trailer report (or timeout)
        Then compare the results
    """
    method = moduleName + '.' + 'testStimulusEngineTrailer'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    resultSet =[]
    
    #try:
    testFileName = os.path.join(testDirPath, filename)
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    n = 0

    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)
    
    for eachReadLine in allLines:
        n = n+1
        unicodeReadLine = str(eachReadLine)
        stringArray = str.split(unicodeReadLine)
        agentMemePath = stringArray[0]
        expectedResult = stringArray[1]
        agentID = rmlEngine.api.createEntityFromMeme(agentMemePath)

        testResult = False
        try:
            argumentMap = {}
            stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap, [agentID])
            #stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
            Engine.siQ.put(stimulusMessage)
            dummyIgnoreThis = "I'm just here to have a place to put a breakpoint"
        except Exception as e:
            Graph.logQ.put( [logType , logLevel.DEBUG , method , "Error testing trailer.  Traceback = %s" %e])
        
        timeout = 10.0
        time.sleep(timeout)
        try:
            report = Engine.broadcasterRegistrar.broadcasterIndex["test"].get_nowait()
            testResult = report.resolvedDescriptor
        except Exception as e:
            testResult = "***"
            
        #Clear the queue in preperation for it being used in more tests
        while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
            try:
                unusedReport = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
            except queue.Empty:
                #ok.  Concurrency is being squirrelly.  The queue tests as not empty, but ends up empty.
                #  Let's not burn the world down over this  
                break
            
        testcase = agentMemePath
        results = [n, testcase, testResult, expectedResult, ""]
        resultSet.append(results)
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet



def testStimulusEngineTrailer3():
    """
        Re-use the agents from the earlier tests  
        Create a trailer request (without an agent) and drop it into the SiQ.
        Then look in the broadcast queue:
        Fetch all of the packets from the queue (there should only be one)
        Then compare the agent IDs with the full agentID list.  
    """
    method = moduleName + '.' + 'testStimulusEngineTrailer'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    resultSet =[]
    
    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)
    
    scopePathToAgent = "Agent.View::Agent.Landmark::Agent.Agent"
    stimulusScope = rmlEngine.api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
    listOfExpectedAgents = []
    for pageInStimulusScope in stimulusScope:
        listOfAgents = rmlEngine.api.getLinkCounterpartsByMetaMemeType(pageInStimulusScope, scopePathToAgent, None)
        listOfExpectedAgents.extend(listOfAgents)
        
    setOfAgents = set(listOfExpectedAgents)
    
    testResult = False
    try:
        argumentMap = {}
        stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
        #stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
        Engine.siQ.put(stimulusMessage)
        dummyIgnoreThis = "I'm just here to have a place to put a breakpoint"
    except Exception as e:
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "Error testing trailer.  Traceback = %s" %e])
    
    timeout = 10.0
    time.sleep(timeout)
    n = 1
    try:
        report = Engine.broadcasterRegistrar.broadcasterIndex["test"].get_nowait()
        testResult = report.agentSet
        
        #nowcompare the returned setwith the expected results
        validResults = setOfAgents.intersection(testResult)
        agentsNotInResult = setOfAgents.difference(testResult)
        unexpectedResults = testResult.difference(setOfAgents)
        
        testResultMessageInBoth = "In both expected and returned set"
        testResultMessageInReturned = "In returned set only"
        testResultMessageInExpected = "In expected set only"
        
        for result in list(validResults):
            agentPath = rmlEngine.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInBoth, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
            
        for result in list(agentsNotInResult):
            agentPath = rmlEngine.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInExpected, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
            
        for result in list(unexpectedResults):
            agentPath = rmlEngine.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInReturned, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
    except Exception as e:
        results = [n, None, "No Presponse", "No Presponse", ""]
        resultSet.append(results)

    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet


def testStimulusEngine1(filenameAgentList, filenameTestcase):
    """
        The first 'serious' test of the stimulus engine.  This testcase checks to see whether a variety of free stimuli
            can make their way through the SE.  The restrictions are that each test is a single stimulus and each is 
            restricted to a single target agent.
    
        Create the usual set of four agents.  
        For each agent/stimuluscombination,
            Create a stimulus request and drop it into the SiQ.
        Then look in the broadcast queue:
            Wait for the trailer report (or timeout)
        Then compare the results (whether the response is the expected one for that stimulus)
    """
    method = moduleName + '.' + 'testStimulusEngine1'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    resultSet =[]
    
    #filenameAgentList has a list of the agents
    testFileNameAL = os.path.join(testDirPath, filenameAgentList)
    readLocAL = codecs.open(testFileNameAL, "r", "utf-8")
    allLinesAL = readLocAL.readlines()
    readLocAL.close
    
    #filenameTestcase has a list of the test cases
    testFileNameT = os.path.join(testDirPath, filenameTestcase)
    readLocT = codecs.open(testFileNameT, "r", "utf-8")
    allLinesT = readLocT.readlines()
    readLocT.close


    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)


    agents = []   
    for eachReadLineAL in allLinesAL:
        unicodeReadLineAL = str(eachReadLineAL)
        stringArrayAL = str.split(unicodeReadLineAL)
        agentMemePath = stringArrayAL[0]  
        agentID = rmlEngine.api.createEntityFromMeme(agentMemePath)
        agents.append(agentID)

    n = 0 
    for eachReadLineT in allLinesT:
        unicodeReadLineT = str(eachReadLineT)
        stringArray = str.split(unicodeReadLineT)
        stimulusMemePath = stringArray[0] 
        stimulusID = rmlEngine.api.createEntityFromMeme(stimulusMemePath)
        
        column = 0   
        for agentID in agents:
            n = n + 1
            column = column + 1
            expectedResult = stringArray[column]
            
            argumentMap = {}
            argumentMap["controllerID"] = None
            stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap, [agentID])
            Engine.siQ.put(stimulusMessage)
      
            timeout = 10.0
            time.sleep(timeout)
            
            resultList = []
            while True:
                testResult = None
                try:
                    report = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
                    testResult = report.resolvedDescriptor
                    resultList.append(testResult)
                    
                    #Clear the queue
                    while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
                        try:
                            unusedReport = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
                        except queue.Empty:
                            #ok.  Concurrency is being squirrelly.  The queue tests as not empty, but ends up empty.
                            #  Let's not burn the world down over this  
                            break
                except Exception as e:
                    break
            if len(resultList) < 1:
                resultList.append("***")
                
                
            testResult = ""
            for result in resultList:
                if (len(resultList) > 1) and (result == "***"):
                    #if we have more than one result, then ignore any *** values that get tacked on when resultQueue is emptied
                    pass
                else:
                    testResult = "%s%s" %(testResult, result)
                
            agentMemePath = rmlEngine.api.getEntityMemeType(agentID)
            testcase = "Stimulus= %s, Agent=%s" %(stimulusMemePath, agentMemePath)
            
            results = [n, testcase, testResult, expectedResult, ""]
            resultSet.append(results)
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet




def testStimulusEngine2(filenameAgentList, filenameTestcase, restrictAgents = True):
    """
        Create the usual set of four agents.  
        For each stimulus
            Create a stimulus request and drop it into the SiQ.
        Then look in the broadcast queue:
            Wait for the trailer report (or timeout)
        Then compare the results:
            When the stimulus engine returns a stimulus report, it includes a set of all agents for which it is relevant.  
            All agents in the test go into one of two buckets (sets), either the set for which no return is expected, 
                or the set for which we expect the stimulus engine to return in the report.  
            Each line in the test definition tells us which "bucket" (rendered descriptror)
            that each agent belongs to.  E.g. if the agent should see 'HelloAgent',then it will
            be in the agent list for the report object that has 'HelloAgent' as the report.resolvedDescriptor
            
        if restrictAgents == True, then the agents defined in filenameAgentList will be the targets.
            otherwise, no targets will be defined and all possible agents will be checked 
    """
    method = moduleName + '.' + 'testStimulusEngine2'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    resultSet =[]
    
    #filenameAgentList has a list of the agents
    testFileNameAL = os.path.join(testDirPath, filenameAgentList)
    readLocAL = codecs.open(testFileNameAL, "r", "utf-8")
    allLinesAL = readLocAL.readlines()
    readLocAL.close
    
    #filenameTestcase has a list of the test cases
    testFileNameT = os.path.join(testDirPath, filenameTestcase)
    readLocT = codecs.open(testFileNameT, "r", "utf-8")
    allLinesT = readLocT.readlines()
    readLocT.close


    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)


    agents = []   
    for eachReadLineAL in allLinesAL:
        unicodeReadLineAL = str(eachReadLineAL)
        stringArrayAL = str.split(unicodeReadLineAL)
        agentMemePath = stringArrayAL[0]  
        agentID = rmlEngine.api.createEntityFromMeme(agentMemePath)
        agents.append(agentID)
        
    '''
        If the stimulus engine never returns anything (because there are no agents for which it is relevant), then we'll
           need a set listing all agents used in the test run.  
    '''
    standingBadResultSet = set(agents)
    
    n = 0 
    for eachReadLineT in allLinesT:
        n = n + 1
        unicodeReadLineT = str(eachReadLineT)
        stringArray = str.split(unicodeReadLineT)
        stimulusMemePath = stringArray[0] 
        stimulusID = rmlEngine.api.createEntityFromMeme(stimulusMemePath)
        
        column = 0
        expectedBuckets = {}
        for agentID in agents:
            column = column + 1
            expectedColumnResult = stringArray[column]    
            if expectedColumnResult in expectedBuckets:
                agentList = expectedBuckets[expectedColumnResult]
                agentList.append(agentID)
                expectedBuckets[expectedColumnResult] = agentList
            else:
                expectedBuckets[expectedColumnResult] = [agentID]
        
        testResult = True
        expectedResult = True
    
        argumentMap = {}
        argumentMap["controllerID"] = None
        if restrictAgents == True:
            stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap, agents)
            Engine.siQ.put(stimulusMessage)
        else:
            stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
            Engine.siQ.put(stimulusMessage)            
  
        timeout = 5.0
        time.sleep(timeout)
        resultList = []
        while True:
            try:
                report = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()

                resultList.append(report)
                
                #Clear the queue
                while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
                    try:
                        unusedReport = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
                    except queue.Empty:
                        #ok.  Concurrency is being squirrelly.  The queue tests as not empty, but ends up empty.
                        #  Let's not burn the world down over this  
                        break
            except Exception as e:
                break
        if len(resultList) < 1:
            #nothing came back from the stimulus engine, but some tests expect this situation.  Create a dummy report
            emptyAgentSet = set([])
            emptyReport = Engine.StimulusReport(None, None, emptyAgentSet, "***", False, [], []) 
            resultList.append(emptyReport)

        notes = ""
        for result in resultList:
            if result is not None:
                
                try:
                    resultDescriptor = result.resolvedDescriptor
                    try:
                        #The agentIDs in expectedBuckets should be a subset of that in the report's agent set
                        myAgentList = expectedBuckets[resultDescriptor]
                        myAgentSet = set(myAgentList)
                        # If the stimulus engine never responded (because none of the agents were supposed to be in a report)
                        #    then result.agentset will be empty.  
                        if standingBadResultSet == myAgentSet:
                            badResultList = expectedBuckets["***"]
                            badResultset = set(badResultList) 
                            if bool(result.agentSet) == True:
                                #if we are expecting an empty result set (that is, the expected bucket for *** matches up with standingBadResultSet,
                                #   then result.agentSet should be empty
                                testResult = False
                                notes = "%s\nAgents with descriptor %s,Should be empty, but contain %s" %(notes, resultDescriptor, list(result.agentSet))
                        elif myAgentSet.issubset(result.agentSet) == False:
                            testResult = False
                            notes = "%s\nAgents with descriptor %s,%snot a subset of %s" %(notes, resultDescriptor, myAgentList, list(result.agentSet))
                        
                        #We must also ensure that the "***" results don't get into another bucket
                        #  If the resultDescriptor was "***" (meaning that we times out waiting for a response from the stimulus engine),
                        #  then we already tested for the 
                        if resultDescriptor != "***":
                            try:
                                badResultList = expectedBuckets["***"]
                                badResultset = set(badResultList)
                                if badResultset.issubset(result.agentSet) == True:
                                    testResult = False
                                    notes = "%s\nAgents with descriptor %s,%snot a subset of %s" %(notes, resultDescriptor, badResultset, list(result.agentSet))
                            except KeyError:
                                # this is ok
                                pass
                            except Exception as e:
                                testResult = False
                                notes = "%s %s" %(notes, e)
                    except KeyError:
                        #not every testcase will have agents for every possible returned descriptor
                        pass
                    except Exception as e:
                        notes = "%s %s" %(notes, e)
                except AttributeError as e:
                    testResult = False
            
        agentMemePath = rmlEngine.api.getEntityMemeType(agentID)
        testcase = "Stimulus= %s" %(stimulusMemePath)
        
        results = [n, testcase, str(testResult), str(expectedResult), notes]
        resultSet.append(results)
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet



def testStimulusEngine(filename):
    """
        Create a set of four agents.  
        For each agent/stimuluscombination,
            Create a stimulus request and drop it into the SiQ. 
            Create a trailer request and drop it into the SiQ.
        Then look in the broadcast queue:
            Wait for the trailer report (or timeout)
        Then compare the pre-trailer report results
    """
    method = moduleName + '.' + 'testStimulusEngineTrailer'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = False
    
    #Let's create a Hello Agent
    agentPath = "AgentTest.HelloAgent"
    agentID = rmlEngine.api.createEntityFromMeme(agentPath)
    
    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = rmlEngine.api.createEntityFromMeme(stimulusTrailerPath)
    
    #Create the message and put it into the SiQ
    #Import here as it causes problems when imported at start of module
    try:
        argumentMap = {}
        argumentMap["controllerID"] = None
        stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap, [agentID])
        #stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
        Engine.siQ.put(stimulusMessage)
        dummyIgnoreThis = "I'm just here to have a place to put a breakpoint"
    except Exception as e:
        Graph.logQ.put( [logType , logLevel.DEBUG , method , "Error testing trailer.  Traceback = %s" %e])
    
    timeout = 10.0
    time.sleep(timeout)
    try:
        report = responseQueue.get_nowait()
        if report.stimulusID == stimulusID:
            testResult = True
        else:
            Graph.logQ.put( [logType , logLevel.WARNING , method , "Trailer Stimulus Failed"])
    except Exception as e:
        Graph.logQ.put( [logType , logLevel.WARNING , method , "Trailer Stimulus Timed Out."])
        testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testcase = "Trailer Stimulus"
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, ""]
    resultSet.append(results)
    return resultSet



def testDescriptorSimpleDirect():
    """
        Runs the I18N descriptor testcases in RMLDescriptor_Simple.atestby directly calling their executors.
    """
    method = moduleName + '.' + 'testDescriptorSimpleDirect'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
    testFileName = os.path.join(testDirPath, "RMLDescriptor_Simple.atest")
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    resultSet = []
    
    n = 0
    for eachReadLine in allLines:
        #resultFile.writelines('Readline = %s' %eachReadLine)
        n = n+1
        splitTestData = re.split('\|', eachReadLine)
        stringArray = str.split(splitTestData[0])
        expectedResult = str.rstrip(splitTestData[1])
        expectedResult = str.lstrip(expectedResult)

        #Build up the argument map
        #All arguments are optional in this test:  3/2, 5/4 and 7/6 all contain optional argument/vlaue pairs
        testArgumentMap = {}
        try:
            testArgumentMap = {stringArray[3] : stringArray[2]}
        except:
            pass
        try:
            testArgumentMap[stringArray[5]] = stringArray[4]
        except:
            pass
        try:
            testArgumentMap[stringArray[7]] = stringArray[6]
        except:
            pass    
        
        removeMe = 'XXX'
        try:
            del testArgumentMap[removeMe]
        except: pass 
        
        testArgumentMap["language"] = stringArray[1]
        testArgumentMap["controllerID"] = None
    
        # stringArray[0] should contain the UUID of the token 
        #tokenUUID = uuid.UUID(stringArray[0])
        
        #resultText = RMLText.descriptorCatalog.getText(tokenUUID, stringArray[1], testArgumentMap)
        try:
            stimulusID = stringArray[0]
            agentID = rmlEngine.api.createEntityFromMeme(stimulusID)
            #debug
            unusedLetsLookAt = Graph.templateRepository.templates
            #if n == 51:
            #    pass
            #print(letsLookAt)
            #/debug
            testResult = rmlEngine.api.evaluateEntity(agentID, testArgumentMap, None, [agentID], None, False)
            results = [n, stimulusID, testResult, expectedResult, ""]
            resultSet.append(results)
        except Exception:
            fullerror = sys.exc_info()
            errorMsg = str(fullerror[1])
            Graph.logQ.put( [logType , logLevel.ERROR , method , "Error testing testDescriptorSimpleDirect.  Traceback = %s" %errorMsg])
    return resultSet




def testDescriptorSimpleViaSIQ():
    method = moduleName + '.' + 'testDescriptorSimpleViaSIQ'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
    testFileName = os.path.join(testDirPath, "RMLDescriptor_Simple.atest")
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    resultSet = []
    
    n = 0
    for eachReadLine in allLines:
        #resultFile.writelines('Readline = %s' %eachReadLine)
        n = n+1
        splitTestData = re.split('\|', eachReadLine)
        stringArray = str.split(splitTestData[0])
        expectedResult = str.rstrip(splitTestData[1])
        expectedResult = str.lstrip(expectedResult)

        #Build up the argument map
        #All arguments are optional in this test:  3/2, 5/4 and 7/6 all contain optional argument/vlaue pairs
        testArgumentMap = {}
        try:
            testArgumentMap = {stringArray[3] : stringArray[2]}
        except:
            pass
        try:
            testArgumentMap[stringArray[5]] = stringArray[4]
        except:
            pass
        try:
            testArgumentMap[stringArray[7]] = stringArray[6]
        except:
            pass    
        
        removeMe = 'XXX'
        try:
            del testArgumentMap[removeMe]
        except: pass 
        
        testArgumentMap["language"] = stringArray[1]
    
        # stringArray[0] should contain the UUID of the token 
        #tokenUUID = uuid.UUID(stringArray[0])
        
        #resultText = RMLText.descriptorCatalog.getText(tokenUUID, stringArray[1], testArgumentMap)
        try:
            stimulusID = stringArray[0]
            agentID = rmlEngine.api.createEntityFromMeme(stimulusID)
            stimulusMessage = Engine.StimulusMessage(stimulusID, testArgumentMap, [agentID])
            #stimulusMessage = Engine.StimulusMessage(stimulusID, argumentMap)
            Engine.siQ.put(stimulusMessage)
            
            timeout = 10.0
            time.sleep(timeout)
            resultList = getResponseFromStimulusEngine()
            testResult = resultList[0]
            results = [1, stimulusID, testResult, expectedResult, ""]
            resultSet.append(results)
        except Exception as e:
            Graph.logQ.put( [logType , logLevel.DEBUG , method , "Error testing trailer.  Traceback = %s" %e])
    return resultSet



""" This is not actually aone of the API test methods, but merely a check that the two servers are up
    serverURL is the server hosting Intentsity
    callbackTestServerURL =  the dummy callback harness for Intentsity to intercat with.  It mimics a data provider and stimulus recipient
"""

def testServerAPIServerUp(serverURL = None, callbackTestServerURL = None):
    """
        Check to see that the server status works.
        This test stops a currently running server
        Test Cases:
            testcase = "simplestop"
            expectedResult = [200]
            #Should ale=ways return 503, because the server has not yet started
            
            testcase = "already stopping"
            expectedResult = [202, 200]
            #Might return 200, depending on how quickly the server stops.  Otherwise, 202
    """
    method = moduleName + '.' + 'testServerAPIAdminStop'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    if (serverURL is None) or (callbackTestServerURL is None):
        testResult = False
    else:
        statusSURL = serverURL + "/"
        statusCURL = callbackTestServerURL + "/"
        
        try:
            #urllib GET request
            statusRequest = urllib.request.urlopen(statusSURL)  
            unusedStartupStatus = statusRequest.code
        except urllib.error.URLError as e:
            testResult = False
            print ("Intentsity server at %s is not available.  Skipping API tests" %statusSURL)
        except Exception as e:
            raise e
        
        try:
            #urllib GET request
            statusRequest = urllib.request.urlopen(statusCURL)  
            unusedStartupStatus = statusRequest.code
        except urllib.error.URLError as e:
            testResult = False
            print ("Test Callback server at %s is not available.  Skipping API tests" %statusCURL)
        except Exception as e:
            raise e
    return testResult





def testServerAPIAdminStartup(expectedCode, serverURL = None, dbConnectionString = None, persistenceType = None, repoLocations = [[]],  validate = False):
    """
        Start the server up, with the applied options.  Check to see that it has successfully started.
        validateRepository
        repositories
        persistenceType
        dbConnectionString
        sqlite
    """
    method = moduleName + '.' + 'testServerAPIAdminStartup'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    requestURL = serverURL + "/admin/start"
    serverStartupStatus = None
    
    if expectedCode != 503:
        #test invalid parameter in validate repository
        # should return a 500 error and not start
        postFieldsDict1 = {"validateRepository" : "Notavalue"}
        try:
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            response1 = urlopen(request).read().decode('utf8')
            responseStr1= json.loads(response1)
            #We should get an exception on the request, so we should not reach here
            testResult = False
            serverStartupStatus = 500
        except Exception as e:
            if e.code != 500:
                #The server SHOULD return a 500 error
                testResult = False
            serverStartupStatus = e.code
                  
        #test invalid parameter in validate repository
        # should return a 500 error and not start
        postFieldsDict2 = {"validateRepository" : False, "repositories" : "notalist"}
        try:
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict2), encoding='utf-8'))
            response2 = urlopen(request).read().decode('utf8')
            responseStr2= json.loads(response2)
            #We should get an exception on the request, so we should not reach here
            testResult = False
            serverStartupStatus = 500
        except Exception as e:
            if e.code != 500:
                #The server SHOULD return a 500 error when repositories does not contain a nested list
                testResult = False
            serverStartupStatus = e.code
        
        
        #test invalid parameter in repositories.  Should be nested list
        # should return a 500 error and not start
        postFieldsDict3 = {"validateRepository" : False, "repositories" : ["notalist"]}
        try:
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict3), encoding='utf-8'))
            response3 = urlopen(request).read().decode('utf8')
            responseStr3= json.loads(response3)
            #We should get an exception on the request, so we should not reach here
            testResult = False
            serverStartupStatus = 500
        except Exception as e:
            if e.code != 500:
                #The server SHOULD return a 400 error when repositories does not contain a nested list
                testResult = False 
            serverStartupStatus = e.code
        
        #This should work, provided that the command line arguments are valid
        postFieldsDict5 = {"validateRepository" : validate, "repositories" : repoLocations, "dbConnectionString" : dbConnectionString, "persistenceType" : persistenceType}
        try:
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict5), encoding='utf-8'))
            response5 = urlopen(request).read().decode('utf8')
            serverStartupStatus = 200
        except Exception as e:
            testResult = False
            serverStartupStatus = 500
    else:
        #This should work, provided that the command line arguments are valid
        postFieldsDict5 = {"validateRepository" : validate, "repositories" : repoLocations, "dbConnectionString" : dbConnectionString, "persistenceType" : persistenceType}
        try:
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict5), encoding='utf-8'))
            response5 = urlopen(request).read().decode('utf8')
            serverStartupStatus = 202
        except Exception as e:
            if e.code != 503:
                testResult = False
            serverStartupStatus = 500
    
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testcase = "API - /admin/start"
    testResult = str(testResult)
    expectedResult = str('True')
    expectedCodeS = convertIntListToString(expectedCode)
    statusString = "Expected Status: %s, Status: %s" %(expectedCodeS, serverStartupStatus)
    results = [1, testcase, testResult, expectedResult, [statusString]]
    resultSet.append(results)
    return resultSet



def testServerAPIAdminStatus(testcase, expectedCode, waitforSuccess, serverURL = None):
    """
        Check to see that the server status works.
        This test runs in a few places, to probe the status at different points in the server life cycle
        Test Cases:
            testcase = "prestart"
            expectedResult = [503]
            waitforSuccess = False
            #Should ale=ways return 503, because the server has not yet started
            
            testcase = "startup"
            expectedResult = [503, 200]
            waitforSuccess = True
            #Might initially return 503, depending on how quickly the server starts.  Should eventually return 200
    """
    method = moduleName + '.' + 'testServerAPIAdminStatus'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    serverStartupStatus = None
    statusURL = serverURL + "/admin/status"
    try:
        #urllib GET request
        statusRequest = urllib.request.urlopen(statusURL)  
        serverStartupStatus = statusRequest.code
    except urllib.error.URLError as e:
        serverStartupStatus = int(sys.exc_info()[1].code)
        if serverStartupStatus not in expectedCode:
            testResult = False
    except Exception as e:
        if e.code not in expectedCode:
            testResult = False   
        elif e.code == 500:
            testResult = False
            
            
    try:
        if testResult != False:
            timeoutVal = 300 #Five minutes
            currTime = 0
            if waitforSuccess == True:
                #At this point, we need to wait for the server to be fully up before continuing
                while serverStartupStatus != 200:
                    try:
                        #urllib GET request
                        statusRequest = urllib.request.urlopen(statusURL)  
                        serverStartupStatus = statusRequest.code
                    except Exception as e:
                        if currTime > timeoutVal:
                            #We have reached timeout and the server is not started
                            raise e
                        if e.code == 503:
                            time.sleep(10.0) 
                            currTime = currTime + 10  
                        elif e.code == 500:
                            raise e
    except Exception as e:
        testResult = False
    
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    expectedCodeS = convertIntListToString(expectedCode)
    statusString = "Expected Status: %s, Status: %s" %(expectedCodeS, serverStartupStatus)
    results = [1, testcase, testResult, expectedResult, [statusString]]
    resultSet.append(results)
    return resultSet



def testServerAPIAdminStop(testcase, expectedCode, serverURL = None):
    """
        Check to see that the server status works.
        This test stops a currently running server
        Test Cases:
            testcase = "simplestop"
            expectedResult = [200]
            #Should ale=ways return 503, because the server has not yet started
            
            testcase = "already stopping"
            expectedResult = [202, 200]
            #Might return 200, depending on how quickly the server stops.  Otherwise, 202
    """
    method = moduleName + '.' + 'testServerAPIAdminStop'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    serverStartupStatus = None
    statusURL = serverURL + "/admin/stop"
    try:
        #urllib GET request
        statusRequest = urllib.request.urlopen(statusURL)  
        serverStartupStatus = statusRequest.code
    except urllib.error.URLError as e:
        testResult = False
        serverStartupStatus = e.reason
    except Exception as e:
        if e.code not in expectedCode:
            testResult = False   
        elif e.code == 500:
            testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    expectedCodeS = convertIntListToString(expectedCode)
    statusString = "Expected Status: %s, Status: %s" %(expectedCodeS, serverStartupStatus)
    results = [1, testcase, testResult, expectedResult, [statusString]]
    resultSet.append(results)
    return resultSet



def testServerAPICreateEntityFromMeme(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath>
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(createEntityURL)  
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Create entity and retrieve type", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet



def testServerAPIGetEntityMemeType(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Given the UUID returned from the first cvall, request its type via /modeling/getEntityMemeType/<entityUUID>
        3 - the returned type should be the same as the original memePath
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(createEntityURL)  
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    createResponseJsonB = createResponse.read()
    entityUUIDJson = json.loads(createResponseJsonB)
    getEntityMemeTypeURL = serverURL + "/modeling/getEntityMemeType/%s" %entityUUIDJson["entityUUID"]
    try:
        #urllib GET request
        getTypeResponse = urllib.request.urlopen(getEntityMemeTypeURL)  
        getTypeResponseJsonB = getTypeResponse.read()
        getTypeResponseJson = json.loads(getTypeResponseJsonB)
        entityType = getTypeResponseJson["memeType"]
        if entityType != memePath:
            testResult = False
            notes = "Meme type returned = %s.  Should be %s" %(entityType, memePath)
    except Exception as e:
        testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Create entity and retrieve type", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet


def testServerAPIGetEntityMetaMemeType(serverURL = None, memePath = "Graphyne.Generic", metaMemePath = "Graphyne.GenericMetaMeme"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Given the UUID returned from the first cvall, request its type via /modeling/getEntityMemeType/<entityUUID>
        3 - the returned type should be the same as the original memePath
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(createEntityURL)  
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    createResponseJsonB = createResponse.read()
    entityUUIDJson = json.loads(createResponseJsonB)
    getEntityMetaMemeTypeURL = serverURL + "/modeling/getEntityMetaMemeType/%s" %entityUUIDJson["entityUUID"]
    try:
        #urllib GET request
        getTypeResponse = urllib.request.urlopen(getEntityMetaMemeTypeURL)  
        getTypeResponseJsonB = getTypeResponse.read()
        getTypeResponseJson = json.loads(getTypeResponseJsonB)
        entityType = getTypeResponseJson["mmetaMmeType"]
        if entityType != metaMemePath:
            testResult = False
            notes = "Meta Meme type returned = %s.  Should be %s" %(entityType, metaMemePath)
    except Exception as e:
        testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Create entity and retrieve type", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet



def testServerAPIGetEntitiesByMemeType(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/getEntitiesByMemeType/<memePath>
        1 - Create an entity, using /modeling/createEntityFromMeme/
        2 - Get the entities of that type, using /modeling/getEntitiesByMemeType
        3 - Make sure that the entity created in step 1 is in the list.
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/getEntitiesByMemeType/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    getEntityURL = serverURL + "/modeling/getEntitiesByMemeType/%s" %memePath
    notes = ""
    entityID = None
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(createEntityURL)  
        createResponseJsonB = createResponse.read()
        entityUUIDJson = json.loads(createResponseJsonB)
        entityID = entityUUIDJson["entityUUID"]
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        notes = e.reason
        
    if testResult != False:
        try:
            #urllib GET request
            getResponse = urllib.request.urlopen(getEntityURL)  
            getResponseJsonB = getResponse.read()
            getUUIDJson = json.loads(getResponseJsonB)
            entityIDList = getUUIDJson["entityIDList"]
            if entityID not in entityIDList:
                entityIDListS = ", ".join(entityIDList)
                notes = "Entity %s was %s" %(entityID, entityIDListS)
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Check to see if entity is in list of type", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet




def testServerAPIGetEntitiesByMetaMemeType(serverURL = None, memePath = "Graphyne.Generic", metaMemePath = "Graphyne.GenericMetaMeme"):
    """
        Tests the /modeling/getEntitiesByMetaMemeType/<memePath>
        1 - Create an entity, using /modeling/createEntityFromMeme/
        2 - Get the entities of that type, using /modeling/getEntitiesByMetaMemeType
        3 - Make sure that the entity created in step 1 is in the list.
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/getEntitiesByMetaMemeType/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    getEntityURL = serverURL + "/modeling/getEntitiesByMetaMemeType/%s" %metaMemePath
    notes = ""
    entityID = None
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(createEntityURL)  
        createResponseJsonB = createResponse.read()
        entityUUIDJson = json.loads(createResponseJsonB)
        entityID = entityUUIDJson["entityUUID"]
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        notes = e.reason
        
    if testResult != False:
        try:
            #urllib GET request
            getResponse = urllib.request.urlopen(getEntityURL)  
            getResponseJsonB = getResponse.read()
            getUUIDJson = json.loads(getResponseJsonB)
            entityIDList = getUUIDJson["entityIDList"]
            if entityID not in entityIDList:
                entityIDListS = ", ".join(entityIDList)
                notes = "Entity %s was %s" %(entityID, entityIDListS)
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Check to see if entity is in list of type", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet





def testServerAPIAddEntityLink(serverURL = None, memePath = "Graphyne.Generic", linkAttributes = {}, linkType = 1):
    """
        Tests the /modeling/addEntityLink REST API call
        1 - Create two entities of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Link them via via /modeling/addEntityLink
        3 - Should not cause any errors.  We'll check to see if they are actually linked via another test
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #create two generic entities
        createResponse1 = urllib.request.urlopen(createEntityURL)  
        createResponse2 = urllib.request.urlopen(createEntityURL)
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    createResponseJson1B = createResponse1.read()
    createResponseJson2B = createResponse2.read()
    entityUUID1Json = json.loads(createResponseJson1B)
    entityUUID2Json = json.loads(createResponseJson2B)
    
    if testResult != False:
        #Link the two
        postFieldsDict1 = {
                            "sourceEntityID" : entityUUID1Json["entityUUID"],
                            "targetEntityID" : entityUUID2Json["entityUUID"],
                            "linkAttributes" : linkAttributes,
                            "linkType" : linkType
                        }
    
        requestURL = serverURL + "/modeling/addEntityLink"
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            response1 = urlopen(request).read().decode('utf8')
            responseStr1= json.loads(response1)
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, "Link Entities", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet


def testServerAPIGetAreEntitiesLinked(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create two entities of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Link them via via /modeling/getEntityMemeType/<entityUUID>
        3 - Check to see that they are linked via /modeling/getAreEntitiesLinked
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #create two generic entities
        createResponse1 = urllib.request.urlopen(createEntityURL)  
        createResponse2 = urllib.request.urlopen(createEntityURL)
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    createResponseJson1B = createResponse1.read()
    createResponseJson2B = createResponse2.read()
    entityUUID1Json = json.loads(createResponseJson1B)
    entityUUID2Json = json.loads(createResponseJson2B)
    
    
    if testResult != False:
        #Link the two
        postFieldsDict1 = {
                            "sourceEntityID" : entityUUID1Json["entityUUID"],
                            "targetEntityID" : entityUUID2Json["entityUUID"]
                        }
    
        requestURL = serverURL + "/modeling/addEntityLink"
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            unusedResponse = urlopen(request).read().decode('utf8')
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
     
    if testResult != False:   
        #Link the two
        getLinkedURL = serverURL + "/modeling/getAreEntitiesLinked/%s/%s" %(entityUUID1Json["entityUUID"], entityUUID2Json["entityUUID"])
        try:
            #urllib GET request
            getLinkedResponse = urllib.request.urlopen(getLinkedURL)  
            getLinkedResponseJsonB = getLinkedResponse.read()
            getLinkedResponseJson = json.loads(getLinkedResponseJsonB)
            linkExists = getLinkedResponseJson["linkExists"]
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    try:
        testResult = linkExists
    except:
        testResult = "No value returned"
    expectedResult = str(True)
    results = [1, "Unlink Entities", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet




def testServerAPIRemoveEntityLink(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create two entities of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Link them via via /modeling/getEntityMemeType/<entityUUID>
        3 - Check to see if they are linked via /modeling/getAreEntitiesLinked.  (should be True)
        4 - Remove the link via /modeling/removeEntityLink/
        5 - Check again to see if they are linked via /modeling/getAreEntitiesLinked.  (should be False)
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/createEntityFromMeme/<memePath>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    notes = ""
    try:
        #create two generic entities
        createResponse1 = urllib.request.urlopen(createEntityURL)  
        createResponse2 = urllib.request.urlopen(createEntityURL)
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    createResponseJson1B = createResponse1.read()
    createResponseJson2B = createResponse2.read()
    entityUUID1Json = json.loads(createResponseJson1B)
    entityUUID2Json = json.loads(createResponseJson2B)
    
    
    if testResult != False:
        #Link the two
        postFieldsDict1 = {
                            "sourceEntityID" : entityUUID1Json["entityUUID"],
                            "targetEntityID" : entityUUID2Json["entityUUID"]
                        }
    
        requestURL = serverURL + "/modeling/addEntityLink"
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            unusedResponse = urlopen(request).read().decode('utf8')
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    #first check to see that they are linked.  Should be True
    getLinkedURL = serverURL + "/modeling/getAreEntitiesLinked/%s/%s" %(entityUUID1Json["entityUUID"], entityUUID2Json["entityUUID"])       
    if testResult != False:   
        try:
            #urllib GET request
            getLinkedResponse = urllib.request.urlopen(getLinkedURL)  
            getLinkedResponseJsonB = getLinkedResponse.read()
            getLinkedResponseJson = json.loads(getLinkedResponseJsonB)
            linkExists = getLinkedResponseJson["linkExists"]
            
            if linkExists == str(False):
                #This should be true.  If False, we have a problem
                testResult = False
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
     
    #Now unlink them
    if testResult != False:   
        #Link the two
        removeEntityMemeTypeURL = serverURL + "/modeling/removeEntityLink/%s/%s" %(entityUUID1Json["entityUUID"], entityUUID2Json["entityUUID"])
        try:
            #urllib GET request
            unusedRemovalResult = urllib.request.urlopen(removeEntityMemeTypeURL)  
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
            
    #Now check again to see if they are linked.  Should be False
    getLinkedURL = serverURL + "/modeling/getAreEntitiesLinked/%s/%s" %(entityUUID1Json["entityUUID"], entityUUID2Json["entityUUID"])       
    if testResult != False:   
        try:
            #urllib GET request
            getLinkedResponse = urllib.request.urlopen(getLinkedURL)  
            getLinkedResponseJsonB = getLinkedResponse.read()
            getLinkedResponseJson = json.loads(getLinkedResponseJsonB)
            linkExists = getLinkedResponseJson["linkExists"]
            
            if linkExists == str(True):
                #This should be False this time.  If True, then /modeling/removeEntityLink/ failed
                testResult = False
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str(True)
    results = [1, "Unlink Entities", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet


def testServerAPIGetLinkCounterpartsByType(serverURL = None, fName = "Entity_Phase7.atest"):
    ''' This is a modified version of testEntityPhase7() from Graphyne's Smoketest.py.
        Instead of direct API access, it uses the server REST API
        Create entities from the meme in the first two colums.
        Add a link between the two at the location on entity in from column 3.
        Check and see if each is a counterpart as seen from the other using the addresses in columns 4&5 (CheckPath & Backpath)
            & the filter.  
        
        The filter must be the same as the type of link (or None)
        The check location must be the same as the added loation.
        
        Note!  Most operations are not exhausively tested for different internal permutations and we just trust that Graphyne works.
          What is different here is that we still expect Graphyne to act as it should, but we need to make sure that the traverse path
          queries reach Graphyne intact.
    '''
    results = []
    lresultSet = []
        
    #try:
    testFileName = os.path.join(testDirPath, fName)
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    n = 0
    
    for eachReadLine in allLines:
        errata = []
        n = n+1
        stringArray = str.split(eachReadLine)

        testResult = False
        try:
            createEntityURL0 = serverURL + "/modeling/createEntityFromMeme/%s" %stringArray[0]
            createEntityURL1 = serverURL + "/modeling/createEntityFromMeme/%s" %stringArray[1]
            queryURL = serverURL + "/modeling/query"
            attachURL = serverURL + "/modeling/addEntityLink"
            
            #entityID0 = Graph.api.createEntityFromMeme(stringArray[0])
            #entityID1 = Graph.api.createEntityFromMeme(stringArray[1])
            
            createResponse0 = urllib.request.urlopen(createEntityURL0)
            createResponseJson0B = createResponse0.read()
            entityUUID0Json = json.loads(createResponseJson0B)
            entityID0 = entityUUID0Json["entityUUID"]
            
            createResponse1 = urllib.request.urlopen(createEntityURL1)
            createResponseJson1B = createResponse1.read()
            entityUUID1Json = json.loads(createResponseJson1B)
            entityID1 = entityUUID1Json["entityUUID"]
            
            #Attach entityID1 at the mount point specified in stringArray[2]
            if stringArray[2] != "X":
                postFieldsDictAttachQuery = {
                                    "originEntityID" : entityID0,
                                    "query" : stringArray[2]
                                }
                request = Request(url=queryURL, data=bytes(json.dumps(postFieldsDictAttachQuery), encoding='utf-8'))
                attachPointResponse = urlopen(request).read().decode('utf8')
                try:
                    attachPointResponseJson = json.loads(attachPointResponse)
                except:
                    attachPointResponseJsonB = attachPointResponse.read()
                    attachPointResponseJson = json.loads(attachPointResponseJsonB)
                mountPoints = attachPointResponseJson["entityIDList"]
                #mountPoints = api.getLinkCounterpartsByType(entityID0, stringArray[2], 0)
                                
                unusedMountPointsOverview = {}
                for mountPoint in mountPoints:
                    postFieldsDictAttach = {
                                        "sourceEntityID" : mountPoint,
                                        "targetEntityID" : entityID1,
                                        "query" : stringArray[2],
                                        "linkType" : int(stringArray[5])
                                        }
                    request = Request(url=attachURL, data=bytes(json.dumps(postFieldsDictAttach), encoding='utf-8'))
                    unusedAttachPointResponse = urlopen(request).read().decode('utf8')
            else:
                raise ValueError("Testcase with invalid attachment point")
              
            backTrackCorrect = False
            linkType = None
            if stringArray[6] != "X":
                linkType = int(stringArray[6])
            
            #see if we can get from entityID0 to entityID1 via stringArray[3]
            addLocationCorrect = False
            if linkType is not None:
                postFieldsDictForwardQuery = {
                                        "originEntityID" : entityID0,
                                        "query" : stringArray[3],
                                        "linkType" : int(stringArray[6])
                                    }
            else:
                postFieldsDictForwardQuery = {
                                        "originEntityID" : entityID0,
                                        "query" : stringArray[3]
                                    }
            request = Request(url=queryURL, data=bytes(json.dumps(postFieldsDictForwardQuery), encoding='utf-8'))
            forwardQueryResponse = urlopen(request).read().decode('utf8')
            try:
                forwardQueryResponseJson = json.loads(forwardQueryResponse)
            except:
                forwardQueryResponseJsonB = forwardQueryResponse.read()
                forwardQueryResponseJson = json.loads(forwardQueryResponseJsonB)          
            addLocationList = forwardQueryResponseJson["entityIDList"]
            if len(addLocationList) > 0:
                addLocationCorrect = True
                
            #see if we can get from entityID1 to entityID0 via stringArray[4]
            backTrackCorrect = False
            if linkType is not None:
                postFieldsDictBacktrackQuery = {
                                        "originEntityID" : entityID1,
                                        "query" : stringArray[4],
                                        "linkType" : int(stringArray[6])
                                    }
            else:
                postFieldsDictBacktrackQuery = {
                                        "originEntityID" : entityID1,
                                        "query" : stringArray[4]
                                    }
            request = Request(url=queryURL, data=bytes(json.dumps(postFieldsDictBacktrackQuery), encoding='utf-8'))
            backtrackQueryResponse = urlopen(request).read().decode('utf8')
            try:
                backtrackQueryResponseJson = json.loads(backtrackQueryResponse)
            except:
                backtrackQueryResponseJsonB = backtrackQueryResponse.read()
                backtrackQueryResponseJson = json.loads(backtrackQueryResponseJsonB)
            backTrackLocationList = backtrackQueryResponseJson["entityIDList"]
            if len(backTrackLocationList) > 0:
                backTrackCorrect = True
            
            if (backTrackCorrect == True) and (addLocationCorrect == True):
                testResult = True
                
        except Exception as e:
            errorMsg = ('Error!  Traceback = %s' % (e) )
            errata.append(errorMsg)

        testcase = str(stringArray[0])
        allTrueResult = str(testResult).upper() 
        expectedResult = stringArray[7]
        results = [n, testcase, allTrueResult, expectedResult, errata]
        lresultSet.append(results)

    return lresultSet


def testServerAPIGetLinkCounterpartsByMetaMemeType(serverURL = None, fName = "LinkCounterpartsByMetaMemeType.atest"):
    ''' Repeat testServerAPIGetLinkCounterpartsByType(), but traversing with metameme paths, instead of meme paths.
        LinkCounterpartsByMetaMemeType.atest differs from TestEntityPhase7.atest only in that cols D and E use metameme paths.
    
        Create entities from the meme in the first two colums.
        Add a link between the two at the location on entity in from column 3.
        Check and see if each is a counterpart as seen from the other using the addresses in columns 4&5 (CheckPath & Backpath)
            & the filter.  
        
        The filter must be the same as the type of link (or None)
        The check location must be the same as the added loation.
    '''
    results = []
    lresultSet = []
        
    #try:
    testFileName = os.path.join(testDirPath, fName)
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    n = 0
    
    for eachReadLine in allLines:
        errata = []
        n = n+1
        stringArray = str.split(eachReadLine)

        testResult = False
        try:
            createEntityURL0 = serverURL + "/modeling/createEntityFromMeme/%s" %stringArray[0]
            createEntityURL1 = serverURL + "/modeling/createEntityFromMeme/%s" %stringArray[1]
            queryURL = serverURL + "/modeling/query"
            querymURL = serverURL + "/modeling/querym"
            attachURL = serverURL + "/modeling/addEntityLink"
            
            #entityID0 = Graph.api.createEntityFromMeme(stringArray[0])
            #entityID1 = Graph.api.createEntityFromMeme(stringArray[1])
            
            createResponse0 = urllib.request.urlopen(createEntityURL0)
            createResponseJson0B = createResponse0.read()
            entityUUID0Json = json.loads(createResponseJson0B)
            entityID0 = entityUUID0Json["entityUUID"]
            
            createResponse1 = urllib.request.urlopen(createEntityURL1)
            createResponseJson1B = createResponse1.read()
            entityUUID1Json = json.loads(createResponseJson1B)
            entityID1 = entityUUID1Json["entityUUID"]
            
            #Attach entityID1 at the mount point specified in stringArray[2]
            if stringArray[2] != "X":
                postFieldsDictAttachQuery = {
                                    "originEntityID" : entityID0,
                                    "query" : stringArray[2]
                                }
                request = Request(url=queryURL, data=bytes(json.dumps(postFieldsDictAttachQuery), encoding='utf-8'))
                attachPointResponse = urlopen(request).read().decode('utf8')
                try:
                    attachPointResponseJson = json.loads(attachPointResponse)
                except:
                    attachPointResponseJsonB = attachPointResponse.read()
                    attachPointResponseJson = json.loads(attachPointResponseJsonB)
                mountPoints = attachPointResponseJson["entityIDList"]
                #mountPoints = api.getLinkCounterpartsByType(entityID0, stringArray[2], 0)
                                
                unusedMountPointsOverview = {}
                for mountPoint in mountPoints:
                    postFieldsDictAttach = {
                                        "sourceEntityID" : mountPoint,
                                        "targetEntityID" : entityID1,
                                        "query" : stringArray[2],
                                        "linkType" : int(stringArray[5])
                                        }
                    request = Request(url=attachURL, data=bytes(json.dumps(postFieldsDictAttach), encoding='utf-8'))
                    unusedAttachPointResponse = urlopen(request).read().decode('utf8')
            else:
                raise ValueError("Testcase with invalid attachment point")
              
            backTrackCorrect = False
            linkType = None
            if stringArray[6] != "X":
                linkType = int(stringArray[6])
            
            #see if we can get from entityID0 to entityID1 via stringArray[3]
            addLocationCorrect = False
            if linkType is not None:
                postFieldsDictForwardQuery = {
                                        "originEntityID" : entityID0,
                                        "query" : stringArray[3],
                                        "linkType" : int(stringArray[6])
                                    }
            else:
                postFieldsDictForwardQuery = {
                                        "originEntityID" : entityID0,
                                        "query" : stringArray[3]
                                    }
            request = Request(url=querymURL, data=bytes(json.dumps(postFieldsDictForwardQuery), encoding='utf-8'))
            forwardQueryResponse = urlopen(request).read().decode('utf8')
            try:
                forwardQueryResponseJson = json.loads(forwardQueryResponse)
            except:
                forwardQueryResponseJsonB = forwardQueryResponse.read()
                forwardQueryResponseJson = json.loads(forwardQueryResponseJsonB)          
            addLocationList = forwardQueryResponseJson["entityIDList"]
            if len(addLocationList) > 0:
                addLocationCorrect = True
                
            #see if we can get from entityID1 to entityID0 via stringArray[4]
            backTrackCorrect = False
            if linkType is not None:
                postFieldsDictBacktrackQuery = {
                                        "originEntityID" : entityID1,
                                        "query" : stringArray[4],
                                        "linkType" : int(stringArray[6])
                                    }
            else:
                postFieldsDictBacktrackQuery = {
                                        "originEntityID" : entityID1,
                                        "query" : stringArray[4]
                                    }
            request = Request(url=querymURL, data=bytes(json.dumps(postFieldsDictBacktrackQuery), encoding='utf-8'))
            backtrackQueryResponse = urlopen(request).read().decode('utf8')
            try:
                backtrackQueryResponseJson = json.loads(backtrackQueryResponse)
            except:
                backtrackQueryResponseJsonB = backtrackQueryResponse.read()
                backtrackQueryResponseJson = json.loads(backtrackQueryResponseJsonB)
            backTrackLocationList = backtrackQueryResponseJson["entityIDList"]
            if len(backTrackLocationList) > 0:
                backTrackCorrect = True
            
            if (backTrackCorrect == True) and (addLocationCorrect == True):
                testResult = True
                
        except Exception as e:
            errorMsg = ('Error!  Traceback = %s' % (e) )
            errata.append(errorMsg)

        testcase = str(stringArray[0])
        allTrueResult = str(testResult).upper() 
        expectedResult = stringArray[7]
        results = [n, testcase, allTrueResult, expectedResult, errata]
        lresultSet.append(results)

    return lresultSet



def testServerAPIAEntityPropertiesAdd(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Add a string property 'Hello World'
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/setEntityPropertyValue/<entityID>/<propName>/<propValue>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    notes = ""
    
    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    try:
        #create two generic entities
        createResponse = urllib.request.urlopen(createEntityURL)  
        createResponseJson = createResponse.read()
        entityUUIDJson = json.loads(createResponseJson)
        entityID = entityUUIDJson["entityUUID"]
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
    
    if testResult != False:   
        #Set a property
        originalPropValue = "Hello World"
        postFieldsDict = {"entityID" : entityID, "propName" : "Hello", "propValue" : originalPropValue}
        try:
            #urllib POST request
            requestURL = serverURL + "/modeling/setEntityPropertyValue"
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict), encoding='utf-8'))
            responseM = urlopen(request).read().decode('utf8')
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    resultSet = []
    testResult = str(testResult)
    expectedResult = str(True)
    results = [1, "Entity Properties", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet


def testServerAPIAEntityPropertiesRead(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Add a string property 'Hello World'
        3 - Check for that property
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/setEntityPropertyValue/<entityID>/<propName>/<propValue>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    notes = ""

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    try:
        #create two generic entities
        createResponse = urllib.request.urlopen(createEntityURL)  
        createResponseJson = createResponse.read()
        entityUUIDJson = json.loads(createResponseJson)
        entityID = entityUUIDJson["entityUUID"] 
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    if testResult != False:
        #Set a property
        originalPropValue = "Hello World"
        postFieldsDict = {"entityID" : entityID, "propName" : "Hello", "propValue" : originalPropValue}
        try:
            #urllib POST request
            requestURL = serverURL + "/modeling/setEntityPropertyValue"
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict), encoding='utf-8'))
            responseM = urlopen(request).read().decode('utf8')
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    if testResult != False:
        try:
            #Now read that same property    
            getPropURL = serverURL + "/modeling/getEntityPropertyValue/%s/%s" %(entityID, "Hello")
            readResponse = urllib.request.urlopen(getPropURL) 
            readResponseJsonB = readResponse.read()
            readResponseJson = json.loads(readResponseJsonB)
            propValue = readResponseJson["propertyValue"] 
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    if testResult != False:    
        if propValue != originalPropValue:
            testResult = False
    
    resultSet = []
    try:
        testResult = propValue
    except: 
        testResult = "No result returned"
    expectedResult = originalPropValue
    results = [1, "Entity Properties", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet


def testServerAPIAEntityPropertiesPresent(serverURL = None, memePath = "Graphyne.Generic"):
    """
        Tests the /modeling/createEntityFromMeme/<memePath> and /modeling/getEntityMemeType/<entityUUID> REST API calls
        1 - Create an entity of meme type memePath using /modeling/createEntityFromMeme/<memePath>
        2 - Add a string property 'Hello World'
        3 - Check for that property
    """
    #"NumericValue.nv_intValue_3"
    
    method = moduleName + '.' + '/modeling/setEntityPropertyValue/<entityID>/<propName>/<propValue>'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    notes = ""

    createEntityURL = serverURL + "/modeling/createEntityFromMeme/%s" %memePath
    try:
        #create two generic entities
        createResponse = urllib.request.urlopen(createEntityURL)  
        createResponseJson = createResponse.read()
        entityUUIDJson = json.loads(createResponseJson)
        entityID = entityUUIDJson["entityUUID"] 
    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
    except Exception as e:
        testResult = False
        
    if testResult != False:
        #Set a property
        originalPropValue = "Hello World"
        postFieldsDict = {"entityID" : entityID, "propName" : "Hello", "propValue" : originalPropValue}
        try:
            #urllib POST request
            requestURL = serverURL + "/modeling/setEntityPropertyValue"
            request = Request(url=requestURL, data=bytes(json.dumps(postFieldsDict), encoding='utf-8'))
            responseM = urlopen(request).read().decode('utf8')
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    if testResult != False:
        try:
            #Now read that same property    
            getPropURL = serverURL + "/modeling/getEntityHasProperty/%s/%s" %(entityID, "Hello")
            readResponse = urllib.request.urlopen(getPropURL) 
            readResponseJsonB = readResponse.read()
            readResponseJson = json.loads(readResponseJsonB)
            propValue = readResponseJson["present"] 
        except urllib.error.URLError as e:
            testResult = False
            notes = e.reason
        except Exception as e:
            testResult = False
    
    if testResult != False:    
        if propValue != originalPropValue:
            testResult = False
    
    resultSet = []
    try:
        testResult = propValue
    except: 
        testResult = "No result returned"
    expectedResult = str(True)
    results = [1, "Entity Properties", testResult, expectedResult, [notes]]
    resultSet.append(results)
    return resultSet



def testServerAPIGetClusterMembers(serverURL):
    """
        Test Getting Cluster Members.
        Create 6 entities of type Graphyne.Generic.  
        Chain four of them together: E1 >> E2 >> E3 >> E4
        Connect E4 to a singleton, Action.Event
        Connect E5 to Action.Event
        Connect E3 to E6 via a subatomic link
        
        Check that we can traverse from E1 to E5.
        Get the cluseter member list of E3 with linktype = None.  It should include E2, E3, E4, E6
        Get the cluseter member list of E3 with linktype = 0.  It should include E2, E3, E4
        Get the cluseter member list of E3 with linktype = 1.  It should include E6
        Get the cluseter member list of E5.  It should be empty
        
        memeStructure = script.getClusterMembers(conditionContainer, 1, False)
        
        
    """
    method = moduleName + '.' + 'testGetClusterMembers'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])

    resultSet = []
    errata = []
    testResult = "True"
    expectedResult = "True"
    errorMsg = ""
    
    #Create 5 entities of type Graphyne.Generic and get the Examples.MemeA4 singleton as well.  
    #Chain them together: E1 >> E2 >> E3 >> E4 >> Examples.MemeA4 << E5
    try:
        createEntityURLGeneric = serverURL + "/modeling/createEntity" 
        createEntityURLSingleton = serverURL + "/modeling/createEntityFromMeme/Action.Event"
        addEntityLinkURL = serverURL + "/modeling/addEntityLink"   

        #Create Entities
        createResponse1 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson1B = createResponse1.read()
        entityUUID1Json = json.loads(createResponseJson1B)
        testEntityID1 = entityUUID1Json["entityUUID"]
        
        createResponse2 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson2B = createResponse2.read()
        entityUUID2Json = json.loads(createResponseJson2B)
        testEntityID2 = entityUUID2Json["entityUUID"]
        
        createResponse3 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson3B = createResponse3.read()
        entityUUID3Json = json.loads(createResponseJson3B)
        testEntityID3 = entityUUID3Json["entityUUID"]
        
        createResponse4 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson4B = createResponse4.read()
        entityUUID4Json = json.loads(createResponseJson4B)
        testEntityID4 = entityUUID4Json["entityUUID"]
        
        createResponse5 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson5B = createResponse5.read()
        entityUUID5Json = json.loads(createResponseJson5B)
        testEntityID5 = entityUUID5Json["entityUUID"]
        
        createResponse6 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson6B = createResponse6.read()
        entityUUID6Json = json.loads(createResponseJson6B)
        testEntityID6 = entityUUID6Json["entityUUID"]
        
        createResponse6 = urllib.request.urlopen(createEntityURLGeneric)
        createResponseJson6B = createResponse6.read()
        entityUUID6Json = json.loads(createResponseJson6B)
        testEntityID6 = entityUUID6Json["entityUUID"]
        
        createResponseS = urllib.request.urlopen(createEntityURLSingleton)
        createResponseJsonSB = createResponseS.read()
        entityUUIDSJson = json.loads(createResponseJsonSB)
        theSingleton = entityUUIDSJson["entityUUID"]
         

        #Graph.api.addEntityLink(testEntityID1, testEntityID2)
        postFieldsDict1 = {"sourceEntityID" : testEntityID1, "targetEntityID" : testEntityID2 }
        postFieldsDict2 = {"sourceEntityID" : testEntityID2, "targetEntityID" : testEntityID3 }
        postFieldsDict3 = {"sourceEntityID" : testEntityID3, "targetEntityID" : testEntityID4 }
        postFieldsDict4 = {"sourceEntityID" : testEntityID3, "targetEntityID" : testEntityID6, "linkAttributes": {}, "linkType" : 1 }
        postFieldsDict5 = {"sourceEntityID" : testEntityID4, "targetEntityID" : theSingleton }
        postFieldsDict6 = {"sourceEntityID" : testEntityID5, "targetEntityID" : theSingleton }
   
        #urllib POST request
        request1 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
        response1 = urlopen(request1).read().decode('utf8')
        responseStr1= json.loads(response1)
        if responseStr1["status"] != "sucsess": raise ValueError("Unable to join entities")
        
        request2 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict2), encoding='utf-8'))
        response2 = urlopen(request2).read().decode('utf8')
        responseStr2= json.loads(response2)
        if responseStr2["status"] != "sucsess": raise ValueError("Unable to join entities")
        
        request3 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict3), encoding='utf-8'))
        response3 = urlopen(request3).read().decode('utf8')
        responseStr3= json.loads(response3)
        if responseStr3["status"] != "sucsess": raise ValueError("Unable to join entities")
        
        request4 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict4), encoding='utf-8'))
        response4 = urlopen(request4).read().decode('utf8')
        responseStr4= json.loads(response4)
        if responseStr4["status"] != "sucsess": raise ValueError("Unable to join entities")

        request5 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict5), encoding='utf-8'))
        response5 = urlopen(request5).read().decode('utf8')
        responseStr5= json.loads(response5)
        if responseStr5["status"] != "sucsess": raise ValueError("Unable to join entities")
        
        request6 = Request(url=addEntityLinkURL, data=bytes(json.dumps(postFieldsDict6), encoding='utf-8'))
        response6 = urlopen(request6).read().decode('utf8')
        responseStr6= json.loads(response6)
        if responseStr6["status"] != "sucsess": raise ValueError("Unable to join entities")
            

    except urllib.error.URLError as e:
        testResult = False
        notes = e.reason
        errorMsg = ('Error creating entities!  Traceback = %s' % (notes) )
    except Exception as e:
        testResult = "False"
        errorMsg = ('Error creating entities!  Traceback = %s' % (e) )
        errata.append(errorMsg)

    #Navitate to end of chain and back
    try:
        queryURL = serverURL + "/modeling/query"
        queryDict15 = {"originEntityID": testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Action.Event::Graphyne.Generic"}
        #queryDict15 = {"originEntityID": testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic"}
        
        requestQuery15 = Request(url=queryURL, data=bytes(json.dumps(queryDict15), encoding='utf-8'))
        response15 = urlopen(requestQuery15).read().decode('utf8')
        responseStr15= json.loads(response15)
        entutyUUID15 = responseStr15["entityIDList"][0]
        
        queryDict51 = {"originEntityID": entutyUUID15, "query" : "Action.Event::Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Graphyne.Generic"}
        requestQuery51 = Request(url=queryURL, data=bytes(json.dumps(queryDict51), encoding='utf-8'))
        response51 = urlopen(requestQuery51).read().decode('utf8')
        responseStr51= json.loads(response51)
        entutyUUID51 = responseStr51["entityIDList"][0]
        
        if (entutyUUID15 != testEntityID5) or (entutyUUID51 != testEntityID1): 
            testResult = "False"
            errorMsg = ('%sShould be able to navigate full chain and back before measuring cluster membership, but could not!\n')
    except Exception as e:
        testResult = "False"
        errorMsg = ('Error measuring cluster membership!  Traceback = %s' % (e) )
        errata.append(errorMsg)
      
    #From E3, atomic
    try:
        """ 
        Chain four of them together: E1 >> E2 >> E3 >> E4
        Connect E4 to a singleton, Action.Event
        Connect E5 to Action.Event
        Connect E3 to E6 via a subatomic link
        """
        
        traverseReeportURL = serverURL + "/modeling/getTraverseReport"
        
        #Traverses from E1 to Action.Event.
        #We can see E5 and E6
        traverseDictE1toAction = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Action.Event"}
        requestQueryE1toAction = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toAction), encoding='utf-8'))
        responseE1toAction = urlopen(requestQueryE1toAction).read().decode('utf8')
        responseStrE1toAction = json.loads(responseE1toAction)
        
        #Traverses from E1 to E3.
        #We can see Action.Event and E6
        traverseDictE1toE3 = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic"}
        requestQueryE1toE3 = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toE3), encoding='utf-8'))
        responseE1toE3 = urlopen(requestQueryE1toE3).read().decode('utf8')
        responseStrE1toE3 = json.loads(responseE1toE3)
        
        #Traverses from E1 to E3.
        #We can see Action.Event and E6
        traverseDictE1toE3_2 = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic", "linkType" :  2}
        requestQueryE1toE3_2 = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toE3_2), encoding='utf-8'))
        responseE1toE3_2 = urlopen(requestQueryE1toE3_2).read().decode('utf8')
        responseStrE1toE3_2 = json.loads(responseE1toE3_2)
         
        #Traverses from E1 to both E5
        #We can see everything
        traverseDictE1toEnd_2 = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Action.Event::Graphyne.Generic", "linkType" :  2}
        requestQueryE1toEnd_2 = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toEnd_2), encoding='utf-8'))
        responseE1toEnd_2 = urlopen(requestQueryE1toEnd_2).read().decode('utf8')
        responseStrE1toEnd_2 = json.loads(responseE1toEnd_2)
        
        #Traverses from E1 to both E5
        #We can Action.Event, but not E6, because its link is subatomic and the default linkType is atomic
        traverseDictE1toEnd = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Action.Event::Graphyne.Generic"}
        requestQueryE1toEnd = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toEnd), encoding='utf-8'))
        responseE1toEnd = urlopen(requestQueryE1toEnd).read().decode('utf8')
        responseStrE1toEnd = json.loads(responseE1toEnd)
        
        #Traverses from E1 to E3
        #We can Action.Event, but not E6, because its link is subatomic
        traverseDictE1toEnd_0 = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic", "linkType" :  0}
        requestQueryE1toEnd_0 = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toEnd_0), encoding='utf-8'))
        responseE1toEnd_0 = urlopen(requestQueryE1toEnd_0).read().decode('utf8')
        responseStrE1toEnd_0 = json.loads(responseE1toEnd_0)
        
        #Traverses from E1 to E5, but fails, because it is looking for subatomic links.  
        #Only E1 should be in the result set
        traverseDictE1toEnd_1 = {"originEntityID" : testEntityID1, "query" : "Graphyne.Generic::Graphyne.Generic::Graphyne.Generic::Action.Event::Graphyne.Generic", "linkType" : 1}
        requestQueryE1toEnd_1 = Request(url=traverseReeportURL, data=bytes(json.dumps(traverseDictE1toEnd_1), encoding='utf-8'))
        responseE1toEnd_1 = urlopen(requestQueryE1toEnd_1).read().decode('utf8')
        responseStrE1toEnd_1 = json.loads(responseE1toEnd_1)
        
        
        sanityCheck = [
                        {"query" : traverseDictE1toAction["query"], "traverse" : responseStrE1toAction, "expectedResults" : {theSingleton : True, testEntityID5 : True, testEntityID6 : False}},
                        {"query" : traverseDictE1toE3["query"], "traverse" : responseStrE1toE3, "expectedResults" : {theSingleton : True, testEntityID5 : False, testEntityID6 : False}},
                        {"query" : traverseDictE1toE3_2["query"], "traverse" : responseStrE1toE3_2, "expectedResults" : {theSingleton : True, testEntityID5 : False, testEntityID6 : True}},
                        {"query" : traverseDictE1toEnd["query"], "traverse" : responseStrE1toEnd, "expectedResults" : {theSingleton : True, testEntityID5 : True, testEntityID6 : False}},
                        {"query" : traverseDictE1toEnd_0["query"], "traverse" : responseStrE1toEnd_0, "expectedResults" : {theSingleton : True, testEntityID5 : False, testEntityID6 : False}},
                        {"query" : traverseDictE1toEnd_1["query"], "traverse" : responseStrE1toEnd_1, "expectedResults" : {theSingleton : False, testEntityID5 : False, testEntityID6 : False}},
                        {"query" : traverseDictE1toEnd_2["query"], "traverse" : responseStrE1toEnd_2, "expectedResults" : {theSingleton : True, testEntityID5 : True, testEntityID6 : True}}
                    ]
        for sanityTestCase in sanityCheck:
            for checkNode in sanityTestCase["expectedResults"]:
                if sanityTestCase["expectedResults"][checkNode] == False:
                    for node in sanityTestCase["traverse"]["nodes"]:
                        if checkNode == node["id"]:
                            testResult = "False"
                            errorMsg = ('Error in traverse report for %s!  Node found, which should not have been present' %traverseDictE1toAction["query"])
                            errata.append(errorMsg)
                else:
                    found = False
                    for node in sanityTestCase["traverse"]["nodes"]:
                        if checkNode == node["id"]:
                            found = True
                    if found == False:
                        testResult = "False"
                        errorMsg = ('Error in traverse report for %s!  Node not found, which should have been present' %sanityTestCase["query"])
                        errata.append(errorMsg)
        
    except Exception as e:
        testResult = "False"
        errorMsg = ('Getting traverse reports!  Traceback = %s' % (e) )
        errata.append(errorMsg)
        
    testcase = "getTraverseReport()"
    
    results = [1, testcase, testResult, expectedResult, errata]
    resultSet.append(results)
    
    Graph.logQ.put( [logType , logLevel.INFO , method , "Finished testcase %s" %(1)])
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return resultSet


def testServerAPIAddOwner(serverURL):
    """
        Create an owner and listen for a 200 response
        Note the UUID
    """
    method = moduleName + '.' + 'testServerAPIAddOwner'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    serverStartupStatus = None
    statusURL = serverURL + "/modeling/addOwner"
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(statusURL)  
        serverStartupStatus = createResponse.code
    except Exception as e:
        testResult = False
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        serverStartupStatus = "Error in request invocation  %s, %s" %(errorID, errorMsg)
            
    #Make sure that there is a response, with an entityUUID
    if testResult == True:
        try:
            createResponseJsonB = createResponse.read()
            ownerUUIDJson = json.loads(createResponseJsonB)
            if "entityUUID" not in ownerUUIDJson.keys():
                testResult = False
                serverStartupStatus = "Response code 200, but entityUUID not in response"
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            serverStartupStatus = "Response code 200, but error encountered while processing response  %s, %s" %(errorID, errorMsg)
     
    # make sure that entity is for an Agent.Owner   
    if testResult == True:
        getEntityMemeTypeURL = serverURL + "/modeling/getEntityMemeType/%s" %ownerUUIDJson["entityUUID"]
        try:
            #urllib GET request
            getTypeResponse = urllib.request.urlopen(getEntityMemeTypeURL)  
            getTypeResponseJsonB = getTypeResponse.read()
            getTypeResponseJson = json.loads(getTypeResponseJsonB)
            entityType = getTypeResponseJson["memeType"]
            if entityType != "Agent.Owner":
                testResult = False
                serverStartupStatus = "Meme type returned = %s.  Should be Agent.Owner" %(entityType)
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            serverStartupStatus = "Owner creation Response code 200 and entityUUID returned, but error encountered while verifying entity meme type: %s, %s" %(errorID, errorMsg)
    
        
    if testResult == True:
        statusString = "Successfully created and verified Agent.Owner" 
    else:
        statusString = "Failure!: %s" %(serverStartupStatus)
        
            
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    testcase = "API - /modeling/addOwner"
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, [statusString]]
    resultSet.append(results)
    return resultSet




def testServerAPIOwnerCallbackURL(serverURL, callbackTestServerURL):
    """
        Create an owner
        Add a callback url for that owner
    """
    method = moduleName + '.' + 'testServerAPIOwnerCallbackURL'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    creationURL = serverURL + "/modeling/addOwner"
    registerURL = serverURL + "/modeling/registerOwnerCallbackURL"
    callbackURL = callbackTestServerURL + "/stimuluscallback"
    
    
    registerStatus = ""
    
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(creationURL)  
    except Exception as e:
        testResult = False
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        registerStatus = "%s. Error in request invocation  %s, %s" %(registerStatus, errorID, errorMsg)
            
    #Make sure that there is a response, with an entityUUID
    if testResult == True:
        try:
            createResponseJsonB = createResponse.read()
            ownerUUIDJson = json.loads(createResponseJsonB)
            if "entityUUID" not in ownerUUIDJson.keys():
                testResult = False
                registerStatus = "%s.  Response code 200, but entityUUID not in response" %registerStatus
            else:
                entityID = ownerUUIDJson["entityUUID"]
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s.  Response code 200, but error encountered while processing response  %s, %s" %(registerStatus, errorID, errorMsg)


    #Now add the url
    if testResult == True:
        postFieldsDict1 = {
                            "ownerID" : entityID,
                            "stimulusCallbackURL" : callbackURL
                        }
    
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=registerURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            response1 = urlopen(request).read().decode('utf8')
            responseStr1= json.loads(response1)
            registerStatus = "%s.  All Good" %registerStatus
        except urllib.error.URLError as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s.  urllib.error.URLError while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s, Problem while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
      
    #Lastly, test it      
    if testResult != False:
        try:
            #Now read that same property    
            getPropURL = serverURL + "/modeling/getEntityPropertyValue/%s/%s" %(entityID, "stimulusCallbackURL")
            readResponse = urllib.request.urlopen(getPropURL) 
            readResponseJsonB = readResponse.read()
            readResponseJson = json.loads(readResponseJsonB)
            if callbackURL != readResponseJson["propertyValue"] :
                testResult = False
                registerStatus = "%s.  No reported errors while adding stimulusCallbackURL, but property can't be retrieved" %registerStatus               
        except urllib.error.URLError as e:
            testResult = False
            registerStatus = "%s.  No reported errors while adding stimulusCallbackURL, but property can't be retrieved.  Error message = %s" %(registerStatus, e.reason)
        except Exception as e:
            testResult = False
            
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testcase = "API - /admin/start"
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, [registerStatus]]
    resultSet.append(results)
    return resultSet




def testServerAPIAddCreator(serverURL):
    """
        Create a creator and listen for a 200 response
        Note the UUID
    """
    method = moduleName + '.' + 'testServerAPIAddCreator'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    serverStartupStatus = None
    statusURL = serverURL + "/modeling/addCreator"
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(statusURL)  
        serverStartupStatus = createResponse.code
    except Exception as e:
        testResult = False
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        serverStartupStatus = "Error in request invocation  %s, %s" %(errorID, errorMsg)
            
    #Make sure that there is a response, with an entityUUID
    if testResult == True:
        try:
            createResponseJsonB = createResponse.read()
            ownerUUIDJson = json.loads(createResponseJsonB)
            if "entityUUID" not in ownerUUIDJson.keys():
                testResult = False
                serverStartupStatus = "Response code 200, but entityUUID not in response"
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            serverStartupStatus = "Response code 200, but error encountered while processing response  %s, %s" %(errorID, errorMsg)
     
    # make sure that entity is for an Agent.Owner   
    if testResult == True:
        getEntityMemeTypeURL = serverURL + "/modeling/getEntityMemeType/%s" %ownerUUIDJson["entityUUID"]
        try:
            #urllib GET request
            getTypeResponse = urllib.request.urlopen(getEntityMemeTypeURL)  
            getTypeResponseJsonB = getTypeResponse.read()
            getTypeResponseJson = json.loads(getTypeResponseJsonB)
            entityType = getTypeResponseJson["memeType"]
            if entityType != "Agent.Creator":
                testResult = False
                serverStartupStatus = "Meme type returned = %s.  Should be Agent.Owner" %(entityType)
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            serverStartupStatus = "Owner creation Response code 200 and entityUUID returned, but error encountered while verifying entity meme type: %s, %s" %(errorID, errorMsg)
    
        
    if testResult == True:
        statusString = "Successfully created and verified Agent.Creator" 
    else:
        statusString = "Failure!: %s" %(serverStartupStatus)
        
            
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    testcase = "API - /modeling/addCreator"
    resultSet = []
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, [statusString]]
    resultSet.append(results)
    return resultSet




def testServerAPICreatorCallbackURLs(serverURL, callbackTestServerURL):
    """
        Create an owner
        Add a callback url for that owner
    """
    method = moduleName + '.' + 'testServerAPIOwnerCallbackURL'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    testResult = True
    
    creationURL = serverURL + "/modeling/addCreator"
    registerDURL = serverURL + "/modeling/registerCreatorDataCallbackURL"
    registerSURL = serverURL + "/modeling/registerCreatorStimulusCallbackURL"
    callbackURLS = callbackTestServerURL + "/stimuluscallback"
    callbackURLD = callbackTestServerURL + "/datacallback"
    
    
    registerStatus = ""
    
    try:
        #urllib GET request
        createResponse = urllib.request.urlopen(creationURL)  
    except Exception as e:
        testResult = False
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        registerStatus = "%s. Error in request invocation  %s, %s" %(registerStatus, errorID, errorMsg)
            
    #Make sure that there is a response, with an entityUUID
    if testResult == True:
        try:
            createResponseJsonB = createResponse.read()
            creatorUUIDJson = json.loads(createResponseJsonB)
            if "entityUUID" not in creatorUUIDJson.keys():
                testResult = False
                registerStatus = "%s.  Response code 200, but entityUUID not in response" %registerStatus
            else:
                entityID = creatorUUIDJson["entityUUID"]
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s.  Response code 200, but error encountered while processing response  %s, %s" %(registerStatus, errorID, errorMsg)


    #Now add the urls
    if testResult == True:
        postFieldsDict1 = {
                            "creatorID" : entityID,
                            "stimulusCallbackURL" : callbackURLS
                        }
    
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=registerSURL, data=bytes(json.dumps(postFieldsDict1), encoding='utf-8'))
            response1 = urlopen(request).read().decode('utf8')
            responseStr1= json.loads(response1)
            registerStatus = "%s.  All Good" %registerStatus
        except urllib.error.URLError as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s.  urllib.error.URLError while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s, Problem while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
            
    if testResult == True:
        postFieldsDict2 = {
                            "creatorID" : entityID,
                            "dataCallbackURL" : callbackURLD
                        }
    
        try:
            #urllib GET request
            #entityMemeType = urllib.request.urlopen(createEntityMemeTypeURL)  
            
            #urllib POST request
            request = Request(url=registerDURL, data=bytes(json.dumps(postFieldsDict2), encoding='utf-8'))
            response1 = urlopen(request).read().decode('utf8')
            responseStr1= json.loads(response1)
            registerStatus = "%s.  All Good" %registerStatus
        except urllib.error.URLError as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s.  urllib.error.URLError while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
        except Exception as e:
            testResult = False
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            registerStatus = "%s, Problem while adding stimulusCallbackURL to Agent.Owner : %s, %s" %(registerStatus, errorID, errorMsg)
      
    #Lastly, test them      
    if testResult != False:
        try:
            #Now read that same property    
            getPropURL = serverURL + "/modeling/getEntityPropertyValue/%s/%s" %(entityID, "stimulusCallbackURL")
            readResponse = urllib.request.urlopen(getPropURL) 
            readResponseJsonB = readResponse.read()
            readResponseJson = json.loads(readResponseJsonB)
            if callbackURLS != readResponseJson["propertyValue"] :
                testResult = False
                registerStatus = "%s.  No reported errors while adding stimulusCallbackURL, but property can't be retrieved" %registerStatus               
        except urllib.error.URLError as e:
            testResult = False
            registerStatus = "%s.  No reported errors while adding stimulusCallbackURL, but property can't be retrieved.  Error message = %s" %(registerStatus, e.reason)
        except Exception as e:
            testResult = False
            
    if testResult != False:
        try:
            #Now read that same property    
            getPropURL = serverURL + "/modeling/getEntityPropertyValue/%s/%s" %(entityID, "dataCallbackURL")
            readResponse = urllib.request.urlopen(getPropURL) 
            readResponseJsonB = readResponse.read()
            readResponseJson = json.loads(readResponseJsonB)
            if callbackURLD != readResponseJson["propertyValue"] :
                testResult = False
                registerStatus = "%s.  No reported errors while adding dataCallbackURL, but property can't be retrieved" %registerStatus               
        except urllib.error.URLError as e:
            testResult = False
            registerStatus = "%s.  No reported errors while adding dataCallbackURL, but property can't be retrieved.  Error message = %s" %(registerStatus, e.reason)
        except Exception as e:
            testResult = False
            
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    resultSet = []
    testcase = "API - /admin/start"
    testResult = str(testResult)
    expectedResult = str('True')
    results = [1, testcase, testResult, expectedResult, [registerStatus]]
    resultSet.append(results)
    return resultSet







def getResponseFromStimulusEngine(returnWholeReport = False):
    global Engine
    queueResults = []
    if not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
        while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
            report = None
            testResult = None
            try:
                report = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
                testResult = report.resolvedDescriptor
                if returnWholeReport == True:
                    #return the whole of every report
                    queueResults.append(report)
                else:
                    #just return a list of resolved descriptors
                    queueResults.append(testResult)
                
                #Clear the queue
                while not Engine.broadcasterRegistrar.broadcasterIndex['test'].empty():
                    try:
                        unusedReport = Engine.broadcasterRegistrar.broadcasterIndex['test'].get_nowait()
                    except queue.Empty:
                        #ok.  Concurrency is being squirrelly.  The queue tests as not empty, but ends up empty.
                        #  Let's not burn the world down over this  
                        break
            except Exception as e:
                break
    else:
        queueResults.append("***")
    return queueResults



def convertIntListToString(intList):
    returnString = "["
    nnTh = 0
    if type(intList) == type([]):
        for intVal in intList:
            if nnTh > 0:
                returnString = "%s, %s" %(returnString, intVal)
            else:
                returnString = "%s%s" %(returnString, intVal)
            nnTh = nnTh +1
    else:
        returnString = "%s%s" %(returnString, intList)
    returnString = "%s]" %(returnString)
    return returnString



def getResultPercentage(resultSet):
    #results = [n, testcase, allTrueResult, expectedResult, errata]
    totalTests = len(resultSet)
    if totalTests == 0:
        return 0
    else:
        partialResult = 0
        if totalTests > 0:
            for test in resultSet:
                try:
                    if test[2].upper() == test[3].upper():
                        partialResult = partialResult + 1
                except Exception as e:
                    print(e)
        pp = partialResult/totalTests
        resultPercentage = pp * 100
        return int(resultPercentage)



def usage():
    print(__doc__)

    
def runTests(testPrefix):
    
    method = moduleName + '.' + 'main'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])

    global rmlEngine
    # a helper item for debugging whther or not a particular entity is in the repo
    debugHelperIDs = rmlEngine.api.getAllEntities()
    for debugHelperID in debugHelperIDs:
        debugHelperMemeType = rmlEngine.api.getEntityMemeType(debugHelperID)
        entityList.append([str(debugHelperID), debugHelperMemeType])

    #test
    #start with the graphDB smoke tests
    resultSet = []

    """
    #First Action Queue Test
    print("Action Engine (Action Queue)")
    testSetData = testActionQueue("AESerialization_Output.atest", "AESerialization_Input.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Action Queue)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, single agent
    #Dealing with 'ad hoc sets'; i.e. rapid flows of incoming action invocations.  Comprehensive testing on a single agent
    print("Action Engine (Ad Hoc Set, Single Agent)")
    testSetData = testActionQueueSingleAgent("AdHocSetOutput_SingleAgent.atest", "AdHocSetSource_SingleAgent.atest", "AgentTest.Agent12", True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Ad Hoc Set, Single Agent)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, multi-agent
    #Dealing with 'ad hoc sets'; i.e. rapid flows of incoming action invocations.  Comprehensive testing on multiple agents
    print("Action Engine (Ad Hoc Set, multi-Agent)")
    testSetData = testActionQueue("AdHocSetOutput_MultiAgent.atest", "AdHocSetSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Ad Hoc Set, multi-Agent)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  
    #End non choreographed action tests
    

    #Action Engine - Choreography, multi-agent
    #A test set for choreographies alone.
    print("Action Engine (Single Set, multi-Agent)")
    testSetData = testActionQueue("ChoreoSingleOutput_MultiAgent.atest", "ChoreoSingleSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Mixed Set, multi-Agent)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  

    
    #Action Engine - Choreography, multi-agent
    #A test set for choreographies with nested child coreographies
    print("Action Engine (Nested Set, multi-Agent)")
    testSetData = testActionQueue("ChoreoOutput_MultiAgent.atest", "ChoreoSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Mixed Set Choreography, multi-Agent)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, single agent
    #Dealing with 'ad hoc sets' composed of individual actions and choreographies.  Mimics full blown usage by a single user
    #testSetData = testActionQueueSingleAgent("MixedOutput_SingleAgent.atest", "MixedSource_SingleAgent.atest", u"AgentTest.Agent12", True)
    #testSetPercentage = getResultPercentage(testSetData)
    #testcaseName = "%s - Action Engine (Ad Hoc Set, Single Agent)" %testPrefix
    #resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  

    #Dynamic, Ad-Hoc Required Landmarks
    print("Action Engine (Dynamic, Ad-Hoc Required Landmarks)")
    testSetData = testActionEngineDynamicLandmarks("AEDynamicLandmarks.atest")
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Action Engine (Dynamic, Ad-Hoc Required Landmarks)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  
    """

    
    #Try to simply get a stimulus trailer through the stimulus engine
    print("Stimulus Engine (Trailer Pass Through)")
    testSetData = testStimulusEngineTrailer()
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Trailer Pass Through)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  
    
    """
    #Now try it with a variety of different agent configurations
    print("Stimulus Engine (Trailer with different Agent Views)")
    testSetData = testStimulusEngineTrailer2('testStimulusEngineTrailerII.atest')
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Trailer with different Agent Views)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)]) 
     
    #Now try it with no targetagent
    print("Stimulus Engine (Trailer with no target agents)")
    testSetData = testStimulusEngineTrailer3()
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Trailer with no target agents)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])
    
    #Check to see if conditional stimuli are processed
    print("Stimulus Engine (Single Free Stimuli)")
    testSetData = testStimulusEngine1('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest')
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Trailer with no target agents)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])
    
    
    #Now check to see holisiically is the right stimuli go to the right agents
    print("Stimulus Engine (Conditional Stimuli, restricted agents)")
    testSetData = testStimulusEngine2('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest', True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Conditional Stimuli, restricted agents)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])
    
    #Now try it with no targetagent
    print("Stimulus Engine (Conditional Stimuli, all agents)")
    testSetData = testStimulusEngine2('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest', False)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Stimulus Engine (Conditional Stimuli, all agents)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])


    #testDescriptorSimple
    #Now do the internationalized descriptor
    testSetData = testDescriptorSimpleDirect()
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Internationalized Descriptor" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])
    
    """
        
    return resultSet




def runRestartTests(testPrefix = "Restart"):
    
    method = moduleName + '.' + 'main'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])

    global rmlEngine
    # a helper item for debugging whther or not a particular entity is in the repo
    debugHelperIDs = rmlEngine.api.getAllEntities()
    for debugHelperID in debugHelperIDs:
        debugHelperMemeType = rmlEngine.api.getEntityMemeType(debugHelperID)
        entityList.append([str(debugHelperID), debugHelperMemeType])

    #test
    #start with the graphDB smoke tests
    resultSet = []
    
    #Testing Restart
    print("Engine Restart (No Reset)")
    testSetData = testEngineRestart()
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Engine Restart (No Reset)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])    
    
    print("Engine Restart (Reset)")
    testSetData = testEngineRestart(True)
    testSetPercentage = getResultPercentage(testSetData)
    testcaseName = "%s - Engine Restart (Reset)" %testPrefix
    resultSet.append([testcaseName, testSetPercentage, copy.deepcopy(testSetData)])  
        
    return resultSet

    
    
    
    
def runAPITests(testSetID, serverURL = None, dbConnectionString = None, persistenceType = None, repoLocations = [],  validate = False, callbackTestServerURL = None):
    
    method = moduleName + '.' + 'main'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    resultSet = []
    
        
    areServersUp = testServerAPIServerUp(serverURL, callbackTestServerURL)
    if areServersUp == True:
    
        """ Cold Start """
        
        #Check Status before statting for the first time
        testSetDataStatus1 = testServerAPIAdminStatus("prestart", [503], False, serverURL)
        testSetPercentageStatus1 = getResultPercentage(testSetDataStatus1)
        
        #Start the server
        testSetDataStart1 = testServerAPIAdminStartup(200, serverURL, dbConnectionString, persistenceType, repoLocations,  validate) 
        testSetPercentageStart1 = getResultPercentage(testSetDataStart1)
        
        #Make sure that we can ask the current status and that it delivers a proper calue
        testSetDataStatus2 = testServerAPIAdminStatus("startup", [503, 200], True, serverURL)
        testSetPercentageStatus2 = getResultPercentage(testSetDataStatus2)
        
        #The server is running, so this should return 503
        testSetDataStart2 = testServerAPIAdminStartup(503, serverURL, dbConnectionString, persistenceType, repoLocations,  validate) 
        testSetPercentageStart2 = getResultPercentage(testSetDataStart2)
        
        ############
        # Server up.  You can temporarily slip test in here when working the kinks out
        ###########
        #User and application administration
        testSetDataAddOwner = testServerAPIAddOwner(serverURL)
        testSetPercentageddOwner = getResultPercentage(testSetDataAddOwner)
        
        testSetDataAddCreator = testServerAPIAddCreator(serverURL)
        testSetPercentageddCreator = getResultPercentage(testSetDataAddCreator)
        
        testSetDataOwnerCallbackURL = testServerAPIOwnerCallbackURL(serverURL, callbackTestServerURL)
        testSetPercentageOwnerCallbackURL  = getResultPercentage(testSetDataOwnerCallbackURL)
        
        testSetDataCreatorCallbackURL = testServerAPICreatorCallbackURLs(serverURL, callbackTestServerURL)
        testSetPercentageCreatorCallbackURL  = getResultPercentage(testSetDataCreatorCallbackURL)        
        ##########
        #  End new test teething block.  Don't forget to move them out when they test green.
        ##########
        
        #Entity Creation
        testSetDataCreateEntity1 = testServerAPICreateEntityFromMeme(serverURL)
        testSetPercentageCreateEntity1 = getResultPercentage(testSetDataCreateEntity1)
        
        testSetDataGetMemeType = testServerAPIGetEntityMemeType(serverURL)
        testSetPercentageGetMemeType = getResultPercentage(testSetDataGetMemeType)
        
        testSetDataGetMetaMemeType = testServerAPICreateEntityFromMeme(serverURL)
        testSetPercentageGetMetaMemeType = getResultPercentage(testSetDataGetMetaMemeType)
        
        
        #Finding list of entitities in repo, by type
        
        testSetDataFindEntity1 = testServerAPIGetEntitiesByMemeType(serverURL)
        testSetPercentageFindEntity1 = getResultPercentage(testSetDataFindEntity1)
        
        testSetDataFindEntity2 = testServerAPIGetEntitiesByMetaMemeType(serverURL)
        testSetPercentageFindEntity2 = getResultPercentage(testSetDataFindEntity2)
        
        #Add and remove links
        testSetDataEntityLink1 = testServerAPIAddEntityLink(serverURL)
        testSetPercentageEntityLink1 = getResultPercentage(testSetDataEntityLink1)
        
        testSetDataEntityLink5 = testServerAPIGetAreEntitiesLinked(serverURL)
        testSetPercentageEntityLink5 = getResultPercentage(testSetDataEntityLink5)    
        
        testSetDataEntityLink2 = testServerAPIRemoveEntityLink(serverURL)
        testSetPercentageEntityLink2 = getResultPercentage(testSetDataEntityLink2)
        
        testSetDataEntityLink3 = testServerAPIAddEntityLink(serverURL, "Graphyne.Generic", {"hello" : "Hello World"})
        testSetPercentageEntityLink3 = getResultPercentage(testSetDataEntityLink3)  
        
        testSetDataEntityLink4 = testServerAPIAddEntityLink(serverURL, "Graphyne.Generic", {"hello" : "Hello World"}, 0)
        testSetPercentageEntityLink4 = getResultPercentage(testSetDataEntityLink4)  
        
        #Properties
        testSetDataCreateEntityProp1 = testServerAPIAEntityPropertiesAdd(serverURL)
        testSetPercentageCreateEntityProp1 = getResultPercentage(testSetDataCreateEntityProp1)
        
        testSetDataCreateEntityProp2 = testServerAPIAEntityPropertiesRead(serverURL)
        testSetPercentageCreateEntityProp2 = getResultPercentage(testSetDataCreateEntityProp2)
        
        testSetDataCreateEntityProp3 = testServerAPIAEntityPropertiesPresent(serverURL)
        testSetPercentageCreateEntityProp3 = getResultPercentage(testSetDataCreateEntityProp3)
        
        testSetDataQuery1 = testServerAPIGetLinkCounterpartsByType(serverURL)
        testSetPercentageQuery1 = getResultPercentage(testSetDataQuery1)
        
        testSetDataQuery2 = testServerAPIGetLinkCounterpartsByMetaMemeType(serverURL)
        testSetPercentageQuery2 = getResultPercentage(testSetDataQuery2)
        
        # test /modeling/getTraverseReport
        testSetDataGetTraverseReport = testServerAPIGetClusterMembers(serverURL)
        testSetPercentageGetTraverseReport = getResultPercentage(testSetDataGetTraverseReport)
        

        
        
        
        """First Shutdown"""
        
        #Now to stop the server for the first time
        testSetDataStop1 = testServerAPIAdminStop("simplestop", [200], serverURL)
        testSetPercentageStop1 = getResultPercentage(testSetDataStop1)
        #Don't wait around.  Just stop it.
        testSetDataStop2 = testServerAPIAdminStop("already stopping", [202, 200], serverURL)
        testSetPercentageStop2 = getResultPercentage(testSetDataStop2)
        
        """First Restart"""
        #no tests here yet
                
        """Tests Done Collect and return results"""
        #Report on the startup, shutdown and status tests
        resultSet.append([testSetID + " - /admin/start - cold start", testSetPercentageStart1, copy.deepcopy(testSetDataStart1)])
        resultSet.append([testSetID + " - /admin/start - server alread running", testSetPercentageStart2, copy.deepcopy(testSetDataStart2)])
        
        resultSet.append([testSetID + " - /admin/status - prestart", testSetPercentageStatus1, copy.deepcopy(testSetDataStatus1)])
        resultSet.append([testSetID + " - /admin/status - startup", testSetPercentageStatus2, copy.deepcopy(testSetDataStatus2)])
        
        resultSet.append([testSetID + " - /admin/stop - cold start", testSetPercentageStop1, copy.deepcopy(testSetDataStop1)])
        resultSet.append([testSetID + " - /admin/stop - server already stopping", testSetPercentageStop2, copy.deepcopy(testSetDataStop1)])
        
        resultSet.append([testSetID + " - /modeling/createEntityFromMeme/<memePath>", testSetPercentageCreateEntity1, copy.deepcopy(testSetDataCreateEntity1)])
        
        resultSet.append([testSetID + " - /modeling/getEntityMemeType/<entityUUID>", testSetPercentageGetMemeType, copy.deepcopy(testSetDataGetMemeType)])
        resultSet.append([testSetID + " - /modeling/getEntityMetaMemeType/<entityUUID>", testSetPercentageGetMetaMemeType, copy.deepcopy(testSetDataGetMetaMemeType)])
        
        resultSet.append([testSetID + " - /modeling/addEntityLink (no attributes)", testSetPercentageEntityLink1, copy.deepcopy(testSetDataEntityLink1)])
        resultSet.append([testSetID + " - /modeling/addEntityLink (attributes)", testSetPercentageEntityLink3, copy.deepcopy(testSetDataEntityLink3)])
        resultSet.append([testSetID + " - /modeling/addEntityLink (attributes and link type)" , testSetPercentageEntityLink4, copy.deepcopy(testSetDataEntityLink4)])
        
        resultSet.append([testSetID + " - /modeling/getAreEntitiesLinked", testSetPercentageEntityLink5, copy.deepcopy(testSetDataEntityLink5)])
        resultSet.append([testSetID + " - /modeling/removeEntityLink", testSetPercentageEntityLink2, copy.deepcopy(testSetDataEntityLink2)])
        
        resultSet.append([testSetID + " - /modeling/setEntityPropertyValue", testSetPercentageCreateEntityProp1, copy.deepcopy(testSetDataCreateEntityProp1)])
        resultSet.append([testSetID + " - /modeling/getEntityPropertyValue", testSetPercentageCreateEntityProp2, copy.deepcopy(testSetDataCreateEntityProp2)])
        resultSet.append([testSetID + " - /modeling/getEntityHasProperty", testSetPercentageCreateEntityProp3, copy.deepcopy(testSetDataCreateEntityProp3)])
        
        resultSet.append([testSetID + " - /modeling/getEntitiesByMemeType", testSetPercentageFindEntity1, copy.deepcopy(testSetDataFindEntity1)])
        resultSet.append([testSetID + " - /modeling/getEntitiesByMetaMemeType", testSetPercentageFindEntity2, copy.deepcopy(testSetDataFindEntity1)])
        
        resultSet.append([testSetID + " - /modeling/query", testSetPercentageQuery1, copy.deepcopy(testSetDataQuery1)])
        resultSet.append([testSetID + " - /modeling/querym", testSetPercentageQuery2, copy.deepcopy(testSetDataQuery2)])
        
        resultSet.append([testSetID + " - /modeling/getTraverseReport", testSetPercentageGetTraverseReport, copy.deepcopy(testSetDataGetTraverseReport)])
 
        #User and application administration
        resultSet.append([testSetID + " - /modeling/addOwner", testSetPercentageddOwner, copy.deepcopy(testSetDataAddOwner)])
        resultSet.append([testSetID + " - /modeling/addcreator", testSetPercentageddCreator, copy.deepcopy(testSetDataAddCreator)])
        resultSet.append([testSetID + " - /modeling/registerOwnerDataCallbackURL", testSetPercentageOwnerCallbackURL, copy.deepcopy(testSetDataOwnerCallbackURL)])
        resultSet.append([testSetID + " - /modeling/registerCreatorDataCallbackURL", testSetPercentageCreatorCallbackURL, copy.deepcopy(testSetDataCreatorCallbackURL)])       

    

    return resultSet





def publishResults(testReports, css, fileName, titleText, ranUnitTests, ranAPITests):
    #testReport = {"resultSet" : resultSet, "validationTime" : validationTime, "persistence" : persistence.__name__} 
    #resultSet = [u"Condition (Remote Child)", copy.deepcopy(testSetData), testSetPercentage])

    #"Every report repeats exactly the same result sets, so we need only count onece"
    testCaseCount = 0
    exampleTestReport = testReports[0]
    exampleResultSet = exampleTestReport["resultSet"]
    for testScenario in exampleResultSet:
        testCaseCount = testCaseCount + len(testScenario[2])
        
    #Totals for time and number of test cases
    numReports = len(testReports)
    totalTCCount = testCaseCount * numReports
    totalTCTime = 0.0
    for countedTestReport in testReports:
        totalTCTime = totalTCTime + countedTestReport["validationTime"] 
        
    # Create the minidom document
    doc = minidom.Document()
    
    # Create the <html> base element
    html = doc.createElement("html")
    #html.setAttribute("xmlns", "http://www.w3.org/1999/xhtml")
        
    # Create the <head> element
    head = doc.createElement("head")
    style = doc.createElement("style")
    defaultCSS = doc.createTextNode(css)
    style.appendChild(defaultCSS)
    title = doc.createElement("title")
    titleTextNode = doc.createTextNode(titleText)
    title.appendChild(titleTextNode)
    head.appendChild(style)
    head.appendChild(title)
        
    body = doc.createElement("body")
    h1 = doc.createElement("h1")
    h1Text = doc.createTextNode(titleText)
    h1.appendChild(h1Text)
    body.appendChild(h1)
    
    h3Tests1 = doc.createElement("h3")
    h3Tests1Text = doc.createTextNode("Unit Tests Executed:  %s" %(ranUnitTests))
    h3Tests1.appendChild(h3Tests1Text)
    body.appendChild(h3Tests1)
    
    h3Tests2 = doc.createElement("h3")
    h3Tests2Text = doc.createTextNode("API Tests Executed:  %s" %(ranAPITests))
    h3Tests2.appendChild(h3Tests2Text)
    body.appendChild(h3Tests2)
    
    h2 = doc.createElement("h2")
    h2Text = doc.createTextNode("%s regression tests over %s persistence types in in %.1f seconds:  %s" %(totalTCCount, numReports, totalTCTime, ctime()))
    h2.appendChild(h2Text)
    body.appendChild(h2)
    
    
    """
        The Master table wraps all the result sets.
        masterTableHeader contains all of the overview blocks
        masterTableBody contains all of the detail elements
    """  
    masterTable = doc.createElement("table")
    masterTableHeader = doc.createElement("table")
    masterTableBody = doc.createElement("table")
    
    for testReport in testReports:
        masterTableHeaderRow = doc.createElement("tr")
        masterTableBodyRow = doc.createElement("tr")
        
        localValTime = testReport["validationTime"]
        localPersistenceName = testReport["persistence"]
        resultSet = testReport["resultSet"]
        profileName = testReport["profileName"]
    
        #Module Overview
        numberOfColumns = 1
        numberOfModules = len(resultSet)
        if numberOfModules > 6:
            numberOfColumns = 2
        if numberOfModules > 12:
            numberOfColumns = 3
        if numberOfModules > 18:
            numberOfColumns = 4
        if numberOfModules > 24:
            numberOfColumns = 5
        rowsPerColumn = numberOfModules//numberOfColumns + 1
    
        listPosition = 0
        icTable = doc.createElement("table")
        
        icTableHead= doc.createElement("thead")
        icTableHeadText = doc.createTextNode("%s, %s: %.1f seconds" %(profileName, localPersistenceName, localValTime) )
        icTableHead.appendChild(icTableHeadText)
        icTableHead.setAttribute("class", "tableheader")
        icTable.appendChild(icTableHead)
        
        icTableFoot= doc.createElement("tfoot")
        icTableFootText = doc.createTextNode("Problem test case sets are detailed in tables below" )
        icTableFoot.appendChild(icTableFootText)
        icTable.appendChild(icTableFoot)
        
        icTableRow = doc.createElement("tr")
        
        for unusedI in range(0, numberOfColumns):
            bigCell = doc.createElement("td")
            nestedTable = doc.createElement("table")
            
            #Header
            headers = ["", "Tests", "Valid"]
            nestedTableHeaderRow = doc.createElement("tr")
            for headerElement in headers:
                nestedCell = doc.createElement("th")
                nestedCellText = doc.createTextNode("%s" %headerElement)
                nestedCell.appendChild(nestedCellText)
                nestedTableHeaderRow.appendChild(nestedCell)
                #nestedTableHeaderRow.setAttribute("class", "tableHeaderRow")
                nestedTable.appendChild(nestedTableHeaderRow)  
                      
            for dummyJ in range(0, rowsPerColumn):
                currPos = listPosition
                listPosition = listPosition + 1
                if listPosition <= numberOfModules:
                    try:
                        moduleReport = resultSet[currPos]
                        
                        #Write Data Row To Table
                        row = doc.createElement("tr")
                        
                        #Module Name is first cell
                        cell = doc.createElement("td")
                        cellText = doc.createTextNode("%s" %moduleReport[0])
                        hyperlinkNode = doc.createElement("a")
                        hyperlinkNode.setAttribute("href", "#%s%s" %(moduleReport[0], localPersistenceName)) 
                        hyperlinkNode.appendChild(cellText)
                        cell.appendChild(hyperlinkNode)
                        if moduleReport[1] < 100:
                            row.setAttribute("class", "badOverviewRow")
                        else:
                            row.setAttribute("class", "goodOverviewRow")                   
                        row.appendChild(cell) 
    
                        rowData = [len(moduleReport[2]), "%s %%" %moduleReport[1]]
                        for dataEntry in rowData:
                            percentCell = doc.createElement("td")
                            percentCellText = doc.createTextNode("%s" %dataEntry)
                            percentCell.appendChild(percentCellText)
                            row.appendChild(percentCell)
                        nestedTable.appendChild(row)
                    except:
                        pass
                else:
                    row = doc.createElement("tr")
                    cell = doc.createElement("td")
                    cellText = doc.createTextNode("")
                    cell.appendChild(cellText)
                    row.appendChild(cellText)
                    nestedTable.appendChild(row)
            nestedTable.setAttribute("class", "subdivision")
            bigCell.appendChild(nestedTable) 
            
            icTableRow.appendChild(bigCell)
            icTableDiv = doc.createElement("div")
            icTableDiv.setAttribute("class", "vAlignment")
            icTableDiv.appendChild(icTableRow) 
            icTable.appendChild(icTableDiv)
            
        #Add some blank spave before icTable
        frontSpacer = doc.createElement("div")
        frontSpacer.setAttribute("class", "vBlankSpace")
        frontSpacer.appendChild(icTable)
        
        masterTableDiv = doc.createElement("div")
        masterTableDiv.setAttribute("class", "vAlignment")
        masterTableDiv.appendChild(frontSpacer) 
        masterTableHeaderRow.appendChild(masterTableDiv)
        masterTableHeader.appendChild(masterTableHeaderRow)
                
            
        #Individual Data Sets
        for testSet in resultSet:
            
            #first, build up the "outer" table header, which has the header
            idHash = "%s%s" %(testSet[0], localPersistenceName)
            oTable = doc.createElement("table")
            oTable.setAttribute("style", "border-style:solid")
            tableHeader= doc.createElement("thead")
            tableHeaderText = doc.createTextNode("%s (%s)" %(testSet[0], localPersistenceName) )
            tableAnchor = doc.createElement("a")
            tableAnchor.setAttribute("id", idHash)
            tableAnchor.appendChild(tableHeaderText)
            tableHeader.appendChild(tableAnchor)
            tableHeader.setAttribute("class", "tableheader")
            oTable.appendChild(tableHeader)
            oTableRow = doc.createElement("tr")
            oTableContainer = doc.createElement("td")
    
            #Inner Table         
            table = doc.createElement("table")
            headers = ["#", "Test Case", "Result", "Expected Result", "Notes"]
            tableHeaderRow = doc.createElement("tr")
            for headerEntry in headers:
                cell = doc.createElement("th")
                cellText = doc.createTextNode("%s" %headerEntry)
                cell.appendChild(cellText)
                cell.setAttribute("class", "tableHeaderRow")
                tableHeaderRow.appendChild(cell)
            table.appendChild(tableHeaderRow)
            
            for fullTestRow in testSet[2]:
                #fullTestRow = [n, testcase, allTrueResult, expectedResult, errata]
                test = [fullTestRow[0], fullTestRow[1], fullTestRow[2], fullTestRow[3]]
                tableRow = doc.createElement("tr")
                for dataEntry in test:
                    cell = doc.createElement("td")
                    cellText = doc.createTextNode("%s" %dataEntry)
                    cell.appendChild(cellText)
                    cell.setAttribute("class", "detailsCell")
                    tableRow.appendChild(cell)
                    try:
                        if test[2].upper() != test[3].upper():
                            #then mark the whole row as red
                            tableRow.setAttribute("class", "badDRow")
                        else:
                            tableRow.setAttribute("class", "goodDRow")
                    except:
                        cell = doc.createElement("td")
                        cellText = doc.createTextNode("Please check Testcase code: actual test result = %s, expected = %s" %(test[2], test[3]))
                        cell.appendChild(cellText)
                        cell.setAttribute("class", "detailsCell")
                        tableRow.appendChild(cell) 
                        tableRow.setAttribute("class", "badDRow")                   
    
                errataCell = doc.createElement("td")
                if type(fullTestRow[4]) == type([]):
                    filteredErrata = Graph.filterListDuplicates(fullTestRow[4])
                    for bulletpointElement in filteredErrata:
                        
                        paragraph = doc.createElement("p")
                        pText = doc.createTextNode("%s" %bulletpointElement)
                        paragraph.appendChild(pText)
                        errataCell.appendChild(paragraph)
                        tableRow.appendChild(cell)
                else:
                    filteredErrata = Graph.filterListDuplicates(fullTestRow[4])
                    paragraph = doc.createElement("p")
                    pText = doc.createTextNode("%s" %filteredErrata)
                    paragraph.appendChild(pText)
                    #rowValidityCell.appendChild(paragraph)
                    errataCell.appendChild(paragraph)
                tableRow.appendChild(errataCell)
                table.appendChild(tableRow)
            oTableContainer.appendChild(table)
            oTableRow.appendChild(oTableContainer)
            oTable.appendChild(oTableRow)
            
            #Add some blank spave before any tables
            tableSpacer = doc.createElement("div")
            tableSpacer.setAttribute("class", "vBlankSpace")
            tableSpacer.appendChild(oTable)
            
            masterTableDivL = doc.createElement("div")
            masterTableDivL.setAttribute("class", "vAlignment")
            masterTableDivL.appendChild(tableSpacer) 
            masterTableBodyRow.appendChild(masterTableDivL)
            masterTableBody.appendChild(masterTableBodyRow)

    masterTable.appendChild(masterTableHeader)
    masterTable.appendChild(masterTableBody)
    body.appendChild(masterTable)
    html.appendChild(head)
    html.appendChild(body)
    doc.appendChild(html)
        
    fileStream = doc.toprettyxml(indent = "    ")
    logRoot =  expanduser("~")
    logDir = os.path.join(logRoot, "Graphyne")
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    resultFileLoc = os.path.join(logDir, fileName)
    fileObject = open(resultFileLoc, "w", encoding="utf-8")
    fileObject.write(fileStream)
    fileObject.close()


def smokeTestSet(persistence, lLevel, css, profileName, persistenceArg = None, persistenceType = None, createTestDatabase = False, repoLocations = [[]],  validate = False, serverURL = None, unitTests = True, callbackTestServerURL = None):
    '''
    repoLocations = a list of all of the filesystem location that that compose the repository.
    useDeaultSchema.  I True, then load the 'default schema' of Graphyne
    persistenceType = The type of database used by the persistence engine.  This is used to determine which flavor of SQL syntax to use.
        Enumeration of Possible values:
        Default to None, which is no persistence
        "sqlite" - Sqlite3
        "mssql" - Miscrosoft SQL Server
        "hana" - SAP Hana
    persistenceArg = the Module/class supplied to host the entityRepository and LinkRepository.  If default, then use the Graphyne.DatabaseDrivers.NonPersistent module.
        Enumeration of possible values:
        None - May only be used in conjunction with "sqlite" as persistenceType and will throw an InconsistentPersistenceArchitecture otherwise
        "none" - no persistence.  May only be used in conjunction with "sqlite" as persistenceType and will throw an InconsistentPersistenceArchitecture otherwise
        "memory" - Use SQLite in in-memory mode (connection = ":memory:")
        "<valid filename with .sqlite as extension>" - Use SQLite, with that file as the database
        "<filename with .sqlite as extension, but no file>" - Use SQLite and create that file to use as the DB file
        "<anything else>" - Presume that it is a pyodbc connection string and throw a InconsistentPersistenceArchitecture exception if the dbtype is "sqlite".
    createTestDatabase = a flag for creating regression test data.  This flag is only to be used for regression testing the graph and even then, only if the test 
        database does not already exist.
        
        *If persistenceType is None (no persistence, then this is ignored and won't throw any InconsistentPersistenceArchitecture exceptions)
    '''
    global rmlEngine
    print(("\nStarting Graphyne Smoke Test: %s") %(persistenceType))
    print(("...%s: Engine Start") %(persistenceType))
        
    #Graph.startLogger(lLevel, "utf-8", True, persistenceType)

    #Smoketest pecific Engine config
    #Some broadcaster Configuration for testing purposes. ActionEngine and StimulusEngine are in Engine by default, but Smotetest needs RegressionTestBroadcaster
    """
    rmlEngine.plugins['RegressionTestBroadcaster'] = {'name' : 'RegressionTestBroadcaster',
                            'pluginType' : 'EngineService',
                            'Module' : 'Broadcasters.RegressionTestBroadcaster',
                            'PluginParemeters': {'heatbeatTick' : 1, 'broadcasterID' : 'test', 'port' : 8081}
                            }
    """
    rmlEngine.broadcasters['test'] = {'memes' : [ 'TestPackageStimulusEngine.SimpleStimuli.Descriptor_Trailer',
                                        'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage',
                                        'TestPackageStimulusEngine.SimpleStimuli.ADescriptor_HelloPage',
                                        'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage2',
                                        'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage3',
                                        'TestPackageStimulusEngine.SimpleStimuli.Descriptor_MultiPage',
                                        'TestPackageStimulusEngine.SimpleStimuli.Descriptor_AnotherPage',
                                        'TestPackageStimulusEngine.SimpleStimuli.ADescriptor_AnotherPage']}
    
    #Set up the persistence of rmlEngine.  It defaults to no persistence
    rmlEngine.setPersistence(persistenceArg, persistenceType)
    
    #Fill out rmlEngine.rtParams
    rmlEngine.setRuntimeParam("consoleLogLevel", lLevel)
    rmlEngine.setRuntimeParam("responseQueue", responseQueue)
    

    for repo in repoLocations:
        #installFilePath = os.path.dirname(__file__)
        userRoot =  expanduser("~")
        repoLocationSnippet = os.path.join(*repo)
        repoLocation = os.path.join(userRoot, repoLocationSnippet)
        rmlEngine.addRepo(repoLocation)

    #Start a gpaphyne engine in the current process, for the direct control tests
    rmlEngine.validateOnLoad = validate
    rmlEngine.start()
    
    #start server instance in the 
    #subprocess.run('server.py')
    
    time.sleep(300.0)
    print("...Engine Started")
    startTime = time.time()
    
    resultSet = []
    '''
    if serverURL is not None: 
        print("Running Cold Start REST API tests")
        resultSetAPI = runAPITests("API (Cold Start)", serverURL, persistenceArg, persistenceType, repoLocations,  validate) 
        resultSet.extend(resultSetAPI)   
        print("Finished REST API tests")
    '''   
     
    if unitTests == True:
        print("Starting Unit Tests")
        print("Starting Cold Start Unit Tests")
        resultSetUitTests = runTests("Cold Start")
        resultSet.extend(resultSetUitTests)
        print("Finished Cold Start")
        
        print("Starting Reatart Tests")
        resultSetRestartTests = runRestartTests()
        resultSet.extend(resultSetRestartTests)
        print("Finished Reatart Tests")
        
        #Is it really nescessary to restart the engine a third time, after the initial boot up?
        #rmlEngine.shutdown()
        #rmlEngine = Engine.Engine()
        
    if serverURL is not None: 
        print("Running Warm Start REST API tests")
        resultSetAPI = runAPITests("API (Warm Start)", serverURL, persistenceArg, persistenceType, repoLocations,  validate, callbackTestServerURL) 
        resultSet.extend(resultSetAPI)   
        print("Finished REST API tests")
        
        print("Starting Warm Start Unit Tests")
        resultSetUitTestsW = runTests("Warm Start")
        resultSet.extend(resultSetUitTestsW)
        print("Finished Warm Start")
        
        
        
    endTime = time.time()
    validationTime = endTime - startTime
    testReport = {"resultSet" : resultSet, "validationTime" : validationTime, "persistence" : persistence.__name__, "profileName" : profileName}     
    #publishResults(resultSet, validationTime, css)
    
    print(("...%s: Test run finished.  Waiting 30 seconds for log thread to catch up before starting shutdown") %(persistence.__name__))
    time.sleep(30.0)
    
    print(("...%s: Engine Stop") %(persistence.__name__)) 
    #Graph.stopLogger()
    rmlEngine.shutdown()
    print(("...%s: Engine Stopped") %(persistence.__name__))   
    return testReport 




    

    
if __name__ == "__main__":
    print("\nStarting Intentsity Smoke Test")
    print("...Engine Start")
    
    css = Fileutils.defaultCSS()

    parser = argparse.ArgumentParser(description="Intentsity Smoke Test")

    parser.add_argument("-c", "--dbtcon", type=str, help="|String| The database connection string (if a relational DB) or filename (if SQLite).\n    'none' - no persistence.  This is the default value\n    'memory' - Use SQLite in in-memory mode (connection = ':memory:')  None persistence defaults to memory id SQlite is used\n    '<valid filename>' - Use SQLite, with that file as the database\n    <filename with .sqlite as extension, but no file> - Use SQLite and create that file to use as the DB file\n    <anything else> - Presume that it is a pyodbc connection string")
    parser.add_argument("-d", "--dbtype", type=str, help="|String| The database type to be used.  If --dbtype is a relational database, it will also determine which flavor of SQL syntax to use.\n    Possible options are 'none', 'sqlite', 'mssql' and 'hana'.  \n    Default is 'none'")
    parser.add_argument("-i", "--library", type=str, help="|String| Run the unit tests or skip them.  The full suite takes about 4 hours to run, so you may want to skip them if you are only testing the rest API.\n    Options are (in increasing order of verbosity) 'warning', 'info' and 'debug'.  \n    Default is 'warning'")
    parser.add_argument("-l", "--logl", type=str, help="|String| Graphyne's log level during the validation run.  \n    Options are (in increasing order of verbosity) 'warning', 'info' and 'debug'.  \n    Default is 'warning'")
    parser.add_argument("-r", "--repo", nargs='*', type=str, help="|String| One or more repository folders to be tested.  At least two required (Graphyne test repo and Intentsity Test Repo filesystem locations)")
    parser.add_argument("-s", "--server", type=str, help="|String| Whether to test the server REST api, or skip it.  'y' or 'n'.  'y' == Yes, test the  server.  'n' == No, skip it.  If no, then the url parameter is ignored.  defaults to y")
    parser.add_argument("-u", "--url", type=str, help="|String| URL for exterlally launched server.  If none is given, then a server will be started in a subprocess, wuth the url localhost:8080.  Giving a specific url allows you to start the server in a seperate debug session and debug the server side seperately.  If you are simply running unit tests, then you can save yourself the complexity and let smoketest start the serrver on its own.")
    parser.add_argument("-t", "--callback", type=str, help="|String| URL callback test server.  If none is given, then a server will be started in a subprocess, wuth the url localhost:8090.  Giving a specific url allows you to start the server in a seperate debug session and debug the server side seperately.  If you are simply running unit tests, then you can save yourself the complexity and let smoketest start the serrver on its own.")
    parser.add_argument("-v", "--val", type=str, help="|String| Sets validation of the repo.  'y' or 'n', defaults to n")
    parser.add_argument("-x", "--resetdb", type=str, help="|String| Reset the esisting persistence DB  This defaults to true and is only ever relevant when Graphyne is using relational database persistence.")
    
    args = parser.parse_args()
    
    lLevel = Graph.logLevel.WARNING
    if args.logl:
        if args.logl == "info":
            lLevel = Graph.logLevel.INFO
            print("\n  -- log level = 'info'")
        elif args.logl == "debug":
            lLevel = Graph.logLevel.DEBUG
            print("\n  -- log level = 'debug'")
        elif args.logl == "warning":
            pass
        else:
            print("Invalid log level %s!  Permitted valies of --logl are 'warning', 'info' and 'debug'!" %args.logl)
            sys.exit()
            
    useServer = True
    if args.server:
        if (args.server is None) or (args.server == 'none'):
            pass
        elif (args.server == 'y') or (args.server == 'Y'):
            useServer = True
            print("\n  -- Including REST API tests")
        elif (args.server == 'n') or (args.server == 'N'):
            useServer = False
            print("\n  -- Skipping REST API tests")
        else:
            print("Invalid REST API server choice %s!  Permitted valies of --server are 'y', 'Y', 'n' and 'N'!" %args.logl)
            sys.exit() 
            
    unitTests = True
    if args.library:
        if (args.library is None) or (args.library == 'none'):
            pass
        elif (args.library == 'y') or (args.library == 'Y'):
            unitTests = True
            print("\n  -- Including unit tests")
        elif (args.library == 'n') or (args.library == 'N'):
            unitTests = False
            print("\n  -- Skipping unit tests")
        else:
            print("Invalid unit test choice %s!  Permitted valies of --server are 'y', 'Y', 'n' and 'N'!" %args.logl)
            sys.exit() 
    
    serverURL = None
    callbackTestServerURL = None
    
    ranAPITests = False
    if useServer == True:
        serverURL = "http://localhost:8080"
        callbackTestServerURL = "http://localhost:8090"
        if args.url:
            if (args.url is None) or (args.url == 'none'):
                pass
            else:
                serverURL = args.url
                ranAPITests = True
                
            if (args.callback is None) or (args.callback == 'none'):
                pass
            else:
                serverURL = args.callback
                
    callbackTestServerURL = None
    if useServer == True:
        callbackTestServerURL = "http://localhost:8090"
        if args.url:
            if (args.callback is None) or (args.callback == 'none'):
                pass
            else:
                serverURL = args.callback
                ranAPITests = True
    
    validate = False
    if args.val:
        if (args.val is None) or (args.val == 'none'):
            pass
        elif (args.val == 'y') or (args.val == 'Y'):
            validate = True
            print("\n  -- validate repositories")
        elif (args.val == 'n') or (args.val == 'N'):
            validate = False
            print("\n  -- don't validate repositories")
        else:
            print("Invalid validation choice %s!  Permitted valies of --val are 'y', 'Y', 'n' and 'N'!" %args.logl)
            sys.exit()
    
    persistenceType = None
    if args.dbtype:
        if (args.dbtype is None) or (args.dbtype == 'none'):
            pass
        elif (args.dbtype == 'sqlite') or (args.dbtype == 'mssql') or (args.dbtype == 'hana'):
            persistenceType = args.dbtype
            print("\n  -- using persistence type %s" %args.dbtype)
        else:
            print("Invalid persistence type %s!  Permitted valies of --dbtype are 'none', 'sqlite', 'mssql' and 'hana'!" %args.logl)
            sys.exit()
            
    dbConnectionString = None
    if args.dbtcon:
        if (args.dbtcon is None) or (args.dbtcon == 'none'):
            if persistenceType is None:
                print("  -- Using in-memory persistence (no connection required)")
            elif persistenceType == 'sqlite':
                dbConnectionString = 'memory'
                print("  -- Using sqlite persistence with connection = :memory:")
            else:
                print("  -- Persistence type %s requires a valid database connection.  Please provide a --dbtcon argument!" %persistenceType)
                sys.exit()
        elif args.dbtcon == 'memory':
            if persistenceType is None:
                #memory is a valid alternative to none with no persistence
                print("  -- Using in-memory persistence (no connection required)")
            elif persistenceType == 'sqlite':
                dbConnectionString = args.dbtcon
                print("  -- Using sqlite persistence with connection = :memory:")
            else:
                print("  -- Persistence type %s requires a valid database connection.  Please provide a --dbtcon argument!" %persistenceType)
                sys.exit()
        else:
            dbConnectionString = args.dbtcon
            if persistenceType == 'sqlite':
                if dbConnectionString.endswith(".sqlite"):
                    print("  -- Using sqlite persistence with file %s" %dbConnectionString)
                else:
                    print("  -- Using sqlite persistence with invalid filename %s.  It must end with the .sqlite extension" %dbConnectionString)
                    sys.exit()
            else:
                print("  -- Using persistence type %s with connection = %s" %(args.dbtype, args.dbtcon))

    #The relative location of Intentsity's Graphyne repo, relative to this file.  
    testRepoRelLoc = ["Config", "Test", "TestRepository"]
    
    userRoot =  expanduser("~")
    installFilePath = os.path.dirname(__file__)
    installFilePathStub = installFilePath.replace(userRoot, "")
    parsedStub = installFilePathStub.split(os.path.sep)
    try:
        #If installFilePath is longer than userRoot, then there will be a leading file seperator at the start of installFilePathStub
        #  Taking the slice at zero removes this.
        #obviously, if this file is at the user root, then userRoot == installFilePath, there will be no stray file seperator and there will be an exception
        del parsedStub[0]
    except: pass
    parsedStub.extend(testRepoRelLoc)
        
    nRepoCount = 1            
    additionalRepoToTest = [parsedStub]
    if args.repo:
        for additionalRepo in args.repo:
            parsedRepoLoc = additionalRepo.split(os.path.sep)
            additionalRepoToTest.append(parsedRepoLoc)  
            nRepoCount = nRepoCount + 1
            print("  -- repo: %s" %additionalRepo)
    print("  %s repositories (including Memetic core,  repo) are being used" %nRepoCount)

    testReport = {}
    css = Fileutils.defaultCSS()
    
    try:
        if persistenceType is None:
            import Graphyne.DatabaseDrivers.NonPersistent as persistenceModule1
            testReport = smokeTestSet(persistenceModule1, lLevel, css, "No-Persistence", dbConnectionString, persistenceType, True, additionalRepoToTest, validate, serverURL, unitTests, callbackTestServerURL)
        elif ((persistenceType == "sqlite") and (dbConnectionString== "memory")):
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModule2
            testReport = smokeTestSet(persistenceModule2, lLevel, css, "sqllite", dbConnectionString, persistenceType, True, additionalRepoToTest, validate, serverURL, unitTests, callbackTestServerURL)
        elif persistenceType == "sqlite":
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModule4
            testReport = smokeTestSet(persistenceModule4, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate, serverURL, unitTests, callbackTestServerURL)
        else:
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModul3
            testReport = smokeTestSet(persistenceModul3, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate, serverURL, unitTests, callbackTestServerURL)
    except Exception as e:
        import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModul32
        testReport = smokeTestSet(persistenceModul32, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate, serverURL, unitTests, callbackTestServerURL)
    
    titleText = "Intentsity Smoke Test Suite - Results"
    publishResults([testReport], css, "IntentsityTestresult.html", titleText, unitTests, ranAPITests)
    os._exit(0)