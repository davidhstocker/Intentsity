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
import queue
import uuid
from xml.dom import minidom
from time import ctime

from Intentsity import Engine
import Graphyne.Graph as Graph
from Graphyne import Fileutils
from Intentsity import Exceptions


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



def testToken():
    method = moduleName + '.' + 'testToken'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
    testFileName = os.path.join(testDirPath, "Token.atest")
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    
    n = 0
    for eachReadLine in allLines:
        n = n+1
        splitTestData = re.split('\|', eachReadLine)
        stringArray = str.split(splitTestData[0])
        expectedResult = str.rstrip(splitTestData[1])
        expectedResult = str.lstrip(expectedResult)

        #Build up the argument map
        #colums after 3 can me repeated in pairs.  5/4 and 7/6 can also contain argument/vlaue pairs
        testArgumentMap = {stringArray[3] : stringArray[2]}
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
    
        # stringArray[0] should contain the UUID of the token 
        #tokenUUID = uuid.UUID(stringArray[0])
        tokenToTest = Graph.templateRepository.templates[stringArray[0]]
        resultText = tokenToTest.getText(stringArray[1], testArgumentMap)
        #resultText = Text.tokenCatalog.getTokenText(tokenUUID, stringArray[1], testArgumentMap)
        resultText = resultText.lstrip()
        resultText = resultText.rstrip()
        
        testcase = stringArray[0]
        if len(stringArray[0]) < 52:
            itr = 52 - len(stringArray[0])
            for unusedI in range(0, itr):
                testcase = testcase + '-'

        resultDisplay = '%s :: %s' % (resultText, expectedResult)
        if resultText != expectedResult:
            printLine = 'Test %s - %s  --FAILURE-- %s' %(n, testcase, resultDisplay)
        else:
            printLine = 'Test %s - %s  ----------- %s' %(n, testcase, resultDisplay)
            
        #print(resultText)
        resultFile.writelines('%s\n' % (printLine) )
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    
    
def testDescriptor():
    method = moduleName + '.' + 'testDescriptor'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
        
    testFileName = os.path.join(testDirPath, "Descriptor.atest")
    readLoc = codecs.open(testFileName, "r", "utf-8")
    allLines = readLoc.readlines()
    readLoc.close
    
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
    
        # stringArray[0] should contain the UUID of the token 
        #tokenUUID = uuid.UUID(stringArray[0])
        
        #resultText = Text.descriptorCatalog.getText(tokenUUID, stringArray[1], testArgumentMap)
        try:
            descriptorToTest = Graph.templateRepository.templates[stringArray[0]]
            resultText = descriptorToTest.getText(stringArray[1], testArgumentMap)
            
            resultText = str.rstrip(resultText)
            resultText = str.lstrip(resultText)

            testcase = stringArray[0]
            if len(stringArray[0]) < 52:
                itr = 52 - len(stringArray[0])
                for unusedI in range(0, itr):
                    testcase = testcase + '-'
    
            resultDisplay = '%s :: %s' % (resultText, expectedResult)
            if resultText != expectedResult:
                printLine = 'Test %s - %s  --FAILURE-- %s' %(n, testcase, resultDisplay)
            else:
                printLine = 'Test %s - %s  ----------- %s' %(n, testcase, resultDisplay)
        except:
            resultDisplay = '***** :: %s' % expectedResult
            printLine = 'Test %s - %s  --FAILURE-- %s' %(n, testcase, resultDisplay)
            
        #print(resultText
        resultFile.writelines('%s\n' % (printLine) )
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    
    
    
    
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
                agentID = Graph.api.createEntityFromMeme(agentMeme)
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
                Engine.aQ.put(actionInvocation)
                
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
                    
            while Engine.aQ.qsize() > 0:
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

    agentID = None
    try:
        agentID = Graph.api.createEntityFromMeme(agentMeme)
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
                actionInvocation = Engine.ActionRequest(actionCommand, actionInsertionTypes.APPEND, rtparams, agentID, agentID, None)
                #debug
                #if actionCommand == u"TestPackageActionEngine.SimpleActions.Action2":
                #    unusedcatch = "me"
                #/debug
                Engine.aQ.put(actionInvocation)
                
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
                agentID = Graph.api.createEntityFromMeme(agentMeme)
            except Exception as e:
                raise e
            
            dynamicLandmarkID = []
            if stringRawArray[2] != "***":
                #use createEntityFromMeme to get the uuid of the landmark singleton
                dynamicLandmark = stringRawArray[2]
                dynamicLandmarkID = None
                try:
                    dynamicLandmarkUUID = Graph.api.createEntityFromMeme(dynamicLandmark)
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
            
            actionInvocation = Engine.ActionRequest(actionCommand, actionInsertionTypes.APPEND, rtparams, agentID, agentID, controllerID, dynamicLandmarkID)
            Engine.aQ.put(actionInvocation)
                
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
                    
            while Engine.aQ.qsize() > 0:
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
    agentID = Graph.api.createEntityFromMeme(agentPath)
    
    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)
    
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
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)
    
    for eachReadLine in allLines:
        n = n+1
        unicodeReadLine = str(eachReadLine)
        stringArray = str.split(unicodeReadLine)
        agentMemePath = stringArray[0]
        expectedResult = stringArray[1]
        agentID = Graph.api.createEntityFromMeme(agentMemePath)

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
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)
    setOfAgents = set()
    #listOfAgents =.getAgentsWithViewOfStimulusScope(stimulusID)
    #setOfAgents = set(listOfAgents)
    
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
            agentPath = Graph.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInBoth, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
            
        for result in list(agentsNotInResult):
            agentPath = Graph.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInExpected, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
            
        for result in list(unexpectedResults):
            agentPath = Graph.api.getEntityMemeType(result)
            results = [n, agentPath, testResultMessageInReturned, testResultMessageInBoth, ""]
            resultSet.append(results)
            n = n + 1
    except Exception as e:
        results = [n, None, [], [], ""]
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
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)


    agents = []   
    for eachReadLineAL in allLinesAL:
        unicodeReadLineAL = str(eachReadLineAL)
        stringArrayAL = str.split(unicodeReadLineAL)
        agentMemePath = stringArrayAL[0]  
        agentID = Graph.api.createEntityFromMeme(agentMemePath)
        agents.append(agentID)

    n = 0 
    for eachReadLineT in allLinesT:
        unicodeReadLineT = str(eachReadLineT)
        stringArray = str.split(unicodeReadLineT)
        stimulusMemePath = stringArray[0] 
        stimulusID = Graph.api.createEntityFromMeme(stimulusMemePath)
        
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
                
            agentMemePath = Graph.api.getEntityMemeType(agentID)
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
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)


    agents = []   
    for eachReadLineAL in allLinesAL:
        unicodeReadLineAL = str(eachReadLineAL)
        stringArrayAL = str.split(unicodeReadLineAL)
        agentMemePath = stringArrayAL[0]  
        agentID = Graph.api.createEntityFromMeme(agentMemePath)
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
        stimulusID = Graph.api.createEntityFromMeme(stimulusMemePath)
        
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
            
        agentMemePath = Graph.api.getEntityMemeType(agentID)
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
    agentID = Graph.api.createEntityFromMeme(agentPath)
    
    #Stimuli are singletons, but we still need to aquire the UUID of the trailer
    stimulusTrailerPath = "TestPackageStimulusEngine.SimpleStimuli.Stimulus_Trailer"
    stimulusID = Graph.api.createEntityFromMeme(stimulusTrailerPath)
    
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
            agentID = Graph.api.createEntityFromMeme(stimulusID)
            #debug
            unusedLetsLookAt = Graph.templateRepository.templates
            #if n == 51:
            #    pass
            #print(letsLookAt)
            #/debug
            testResult = Graph.api.evaluateEntity(agentID, testArgumentMap, None, [agentID], None, False)
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
            agentID = Graph.api.createEntityFromMeme(stimulusID)
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

    
def runTests(css):
    
    method = moduleName + '.' + 'main'
    Graph.logQ.put( [logType , logLevel.DEBUG , method , "entering"])
    
    startTime = time.time()
    Graph.logQ.put( [logType , logLevel.ADMIN , method , "Test Suite waiting for Action Engine to complete startup before executing"])
    #while Engine.startupStateActionEngineFinished == False:
    #    time.sleep(5.0)
    endTime = time.time()
    waitTime = endTime - startTime  
    aeNotification = "Action Engine Ready to serve.  It took %s seconds to initialize.  Test Suite may now be started" %waitTime
    Graph.logQ.put( [logType , logLevel.ADMIN , method , aeNotification])
    
    
    # a helper item for debugging whther or not a particular entity is in the repo
    debugHelperIDs = Graph.api.getAllEntities()
    for debugHelperID in debugHelperIDs:
        debugHelperMemeType = Graph.api.getEntityMemeType(debugHelperID)
        entityList.append([str(debugHelperID), debugHelperMemeType])

    #test
    #start with the graphDB smoke tests
    startTime = time.time()
    resultSet = []
    

    #First Action Queue Test
    print("Action Engine (Action Queue)")
    testSetData = testActionQueue("AESerialization_Output.atest", "AESerialization_Input.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Action Queue)", testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, single agent
    #Dealing with 'ad hoc sets'; i.e. rapid flows of incoming action invocations.  Comprehensive testing on a single agent
    print("Action Engine (Ad Hoc Set, Single Agent)")
    testSetData = testActionQueueSingleAgent("AdHocSetOutput_SingleAgent.atest", "AdHocSetSource_SingleAgent.atest", "AgentTest.Agent12", True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Ad Hoc Set, Single Agent)", testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, multi-agent
    #Dealing with 'ad hoc sets'; i.e. rapid flows of incoming action invocations.  Comprehensive testing on multiple agents
    print("Action Engine (Ad Hoc Set, multi-Agent)")
    testSetData = testActionQueue("AdHocSetOutput_MultiAgent.atest", "AdHocSetSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Ad Hoc Set, multi-Agent)", testSetPercentage, copy.deepcopy(testSetData)])  
    #End non choreographed action tests
    

    #Action Engine - Choreography, multi-agent
    #A test set for choreographies alone.
    print("Action Engine (Single Set, multi-Agent)")
    testSetData = testActionQueue("ChoreoSingleOutput_MultiAgent.atest", "ChoreoSingleSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Mixed Set, multi-Agent)", testSetPercentage, copy.deepcopy(testSetData)])  

    
    #Action Engine - Choreography, multi-agent
    #A test set for choreographies with nested child coreographies
    print("Action Engine (Nested Set, multi-Agent)")
    testSetData = testActionQueue("ChoreoOutput_MultiAgent.atest", "ChoreoSource_MultiAgent.atest", True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Mixed Set, multi-Agent)", testSetPercentage, copy.deepcopy(testSetData)])  

    #Action Engine - AdHocSet, single agent
    #Dealing with 'ad hoc sets' composed of individual actions and choreographies.  Mimics full blown usage by a single user
    #testSetData = testActionQueueSingleAgent("MixedOutput_SingleAgent.atest", "MixedSource_SingleAgent.atest", u"AgentTest.Agent12", True)
    #testSetPercentage = getResultPercentage(testSetData)
    #resultSet.append([u"Action Engine (Mixed Set, Single Agent)", testSetPercentage, copy.deepcopy(testSetData)])  

    #Dynamic, Ad-Hoc Required Landmarks
    print("Action Engine (Dynamic, Ad-Hoc Required Landmarks)")
    testSetData = testActionEngineDynamicLandmarks("AEDynamicLandmarks.atest")
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Action Engine (Dynamic, Ad-Hoc Required Landmarks)", testSetPercentage, copy.deepcopy(testSetData)])  


    #Try to simply get a stimulus trailer through the stimulus engine
    print("Stimulus Engine (Trailer Pass Through)")
    testSetData = testStimulusEngineTrailer()
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Stimulus Engine (Trailer Pass Through)", testSetPercentage, copy.deepcopy(testSetData)])  
    
    
    #Now try it with a variety of different agent configurations
    print("Stimulus Engine (Trailer with different Agent Views)")
    testSetData = testStimulusEngineTrailer2('testStimulusEngineTrailerII.atest')
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Stimulus Engine (Trailer with different Agent Views)", testSetPercentage, copy.deepcopy(testSetData)]) 
    
    
    #Now try it with no targetagent
    #print("Stimulus Engine (Trailer with no target agents)")
    #testSetData = testStimulusEngineTrailer3()
    #testSetPercentage = getResultPercentage(testSetData)
    #resultSet.append(["Stimulus Engine (Trailer with no target agents)", testSetPercentage, copy.deepcopy(testSetData)])

    
    #Check to see if conditional stimuli are processed
    print("Stimulus Engine (Single Free Stimuli)")
    testSetData = testStimulusEngine1('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest')
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Stimulus Engine (Single Free Stimuli)", testSetPercentage, copy.deepcopy(testSetData)])
    
    
    #Now check to see holisiically is the right stimuli go to the right agents
    print("Stimulus Engine (Conditional Stimuli, restricted agents)")
    testSetData = testStimulusEngine2('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest', True)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Stimulus Engine (Conditional Stimuli, restricted agents)", testSetPercentage, copy.deepcopy(testSetData)])
    
    #Now try it with no targetagent
    print("Stimulus Engine (Conditional Stimuli, all agents)")
    testSetData = testStimulusEngine2('testStimulusEngineTrailerII.atest', 'testStimulusEngineFree.atest', False)
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Stimulus Engine (Conditional Stimuli, all agents)", testSetPercentage, copy.deepcopy(testSetData)])

    '''
    #testDescriptorSimple
    #Now do the internationalized descriptor
    testSetData = testDescriptorSimpleDirect()
    testSetPercentage = getResultPercentage(testSetData)
    resultSet.append(["Internationalized Descriptor", testSetPercentage, copy.deepcopy(testSetData)])
    '''

    return resultSet
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])




def publishResults(testReports, css, fileName, titleText):
    #testReport = {"resultSet" : resultSet, "validationTime" : validationTime, "persistence" : persistence.__name__} 
    #resultSet = [u"Condition (Remote Child)", copy.deepcopy(testSetData), testSetPercentage])

    "Every report repeats exactly the same result sets, so we need only count onece"
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
    html.setAttribute("xmlns", "http://www.w3.org/1999/xhtml")
        
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


def smokeTestSet(persistence, lLevel, css, profileName, persistenceArg = None, persistenceType = None, createTestDatabase = False, repoLocations = [],  validate = False):
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
    
    for repoLocation in repoLocations:
        rmlEngine.addRepo(repoLocation)

    rmlEngine.validateOnLoad = validate
    rmlEngine.start()
    
    time.sleep(300.0)
    print("...Engine Started")
    
    startTime = time.time()
    resultSet = runTests(css)    
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
    parser.add_argument("-l", "--logl", type=str, help="|String| Graphyne's log level during the validation run.  \n    Options are (in increasing order of verbosity) 'warning', 'info' and 'debug'.  \n    Default is 'warning'")
    parser.add_argument("-x", "--resetdb", type=str, help="|String| Reset the esisting persistence DB  This defaults to true and is only ever relevant when Graphyne is using relational database persistence.")
    parser.add_argument("-d", "--dbtype", type=str, help="|String| The database type to be used.  If --dbtype is a relational database, it will also determine which flavor of SQL syntax to use.\n    Possible options are 'none', 'sqlite', 'mssql' and 'hana'.  \n    Default is 'none'")
    parser.add_argument("-c", "--dbtcon", type=str, help="|String| The database connection string (if a relational DB) or filename (if SQLite).\n    'none' - no persistence.  This is the default value\n    'memory' - Use SQLite in in-memory mode (connection = ':memory:')  None persistence defaults to memory id SQlite is used\n    '<valid filename>' - Use SQLite, with that file as the database\n    <filename with .sqlite as extension, but no file> - Use SQLite and create that file to use as the DB file\n    <anything else> - Presume that it is a pyodbc connection string")
    parser.add_argument("-r", "--repo", nargs='*', type=str, help="|String| One or more repository folders to be tested.  At least two required (Graphyne test repo and Intentsity Test Repo filesystem locations)")
    parser.add_argument("-v", "--val", type=str, help="|String| Sets validation of the repo.  'y' or 'n', defaults to n")
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
            
    validate = False
    if args.val:
        if (args.val is None) or (args.val == 'none'):
            pass
        elif (args.val == 'y') or (args.dbtype == 'Y'):
            validate = True
            print("\n  -- validate repositories")
        elif (args.val == 'n') or (args.dbtype == 'N'):
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


    installFilePath = os.path.dirname(__file__)
    testRepo = os.path.join(installFilePath, "Config", "Test", "TestRepository")
        
    nRepoCount = 1            
    additionalRepoToTest = [testRepo]
    if args.repo:
        for additionalRepo in args.repo:
            additionalRepoToTest.append(additionalRepo)  
            nRepoCount = nRepoCount + 1
            print("  -- repo: %s" %additionalRepo)
    print("  %s repositories (including Memetic core,  repo) are being used" %nRepoCount)

    testReport = {}
    css = Fileutils.defaultCSS()
    
    try:
        if persistenceType is None:
            import Graphyne.DatabaseDrivers.NonPersistent as persistenceModule1
            testReport = smokeTestSet(persistenceModule1, lLevel, css, "No-Persistence", dbConnectionString, persistenceType, True, additionalRepoToTest, validate)
        elif ((persistenceType == "sqlite") and (dbConnectionString== "memory")):
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModule2
            testReport = smokeTestSet(persistenceModule2, lLevel, css, "sqllite", dbConnectionString, persistenceType, True, additionalRepoToTest, validate)
        elif persistenceType == "sqlite":
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModule4
            testReport = smokeTestSet(persistenceModule4, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate)
        else:
            import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModul3
            testReport = smokeTestSet(persistenceModul3, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate)
    except Exception as e:
        import Graphyne.DatabaseDrivers.RelationalDatabase as persistenceModul32
        testReport = smokeTestSet(persistenceModul32, lLevel, css, "sqllite", dbConnectionString, persistenceType, False, additionalRepoToTest, validate)
    
    titleText = "Intentsity Smoke Test Suite - Results"
    publishResults([testReport], css, "IntentsityTestresult.html", titleText)
    os._exit(0)