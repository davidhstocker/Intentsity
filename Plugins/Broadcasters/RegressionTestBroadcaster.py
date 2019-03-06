#!/usr/bin/env python2
"""Angela RML Interpreter - Core Logging Module
Created by the project angela team
    http://sourceforge.net/projects/projectangela/
    http://www.projectangela.org"""
    
__license__ = "GPL"
__version__ = "$Revision: 0.1 $"
__author__ = 'David Stocker'



from bottle import route, run, request, template, abort
import json
import queue
import sys

import Graphyne.Graph as Graph
from ... import Engine

responseQueue = queue.Queue()


@route('/')
def index():
    global responseQueue
    try:
        returnVal = responseQueue.get_nowait()
        return returnVal
    except queue.Empty:
        return None
    
        


class Plugin(Engine.Broadcaster):
    ''' 
        A test broadcaster.  Relatively Simple.    
        It polls its 
    '''
    className = 'Plugin'
    responseQueue = None
    myQueue = None
    broadcasterID = None
        
    def onAfterInitialize(self, adminParams = None, engineParams = None):
        noadminParamsMessage = "Regression test Broadcaster requires a rtparams dict, with a 'port' key, in order to start the broadcaster REST API"
        if adminParams is None:
            errMessage = "%s  No adminParams supplied" %noadminParamsMessage
            raise KeyError(errMessage)
            raise TypeError(errMessage)
        else:
            try:
                serverPort = adminParams["port"]
                run(host='localhost', port=serverPort)
            except KeyError:
                errMessage = "%s  rtparams supplied, but no 'port' key present" %noadminParamsMessage
                raise KeyError(errMessage)
            except Exception as e:
                fullerror = sys.exc_info()
                errorID = str(fullerror[0])
                errorMsg = str(fullerror[1])
                responseMessage = "Error on starting regression test broadcaster %s.  %s, %s" %(self.broadcasterID, errorID, errorMsg)
                tb = sys.exc_info()[2]
                raise ValueError(responseMessage).with_traceback(tb)
         
        
    
    def onStimulusReport(self, stimulusReport):
        global responseQueue
        responseQueue.put_nowait(stimulusReport)
    




#Globals
moduleName = 'RegressionTestBroadcaster' 
logType = Graph.logTypes.CONTENT
logLevel = Graph.LogLevel()  

