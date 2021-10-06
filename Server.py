'''
Created on June 13, 2018

@author: David Stocker
'''

from bottle import route, run, request, template, abort, static_file, response
import json
import time
import os
import sys
import threading
import queue
import uuid
from os.path import expanduser
from . import Engine
from . import Exceptions
import argparse
        
basePort = 8080

class IntentTagSchema(object):  
    """
        A small helper class for determining what tags and interfaces an intent requires
    """ 
    tags = {}
    
    
    def __init__(self, intentName):
        self.tags = ""
        self.requiredInterfaces = []  #Any tags that
        self.intentName = intentName
        
    def addTag(self, tagName, tagCardinality):
        try:
            testVal = self.tags[tagName]
            
            #If no KeyError exception was thrown, then we have an existing tag and must update it
            tagCardinality = tagCardinality + testVal
            self.tags[tagName] = tagCardinality
        except KeyError:
            self.tags[tagName] = tagCardinality
        except Exception as e:
            raise e
        
        
        
class EventTagSchema(object):  
    """
        A small helper class for determining what tags and interfaces an event requires
    """ 
    
    def __init__(self, eventName):
        self.tags = ""
        self.requiredInterfaces = []  #Any tags that
        self.eventName = eventName
        
    def addTag(self, tagName, tagCardinality):
        try:
            testVal = self.tags[tagName]
            
            #If no KeyError exception was thrown, then we have an existing tag and must update it
            tagCardinality = tagCardinality + testVal
            self.tags[tagName] = tagCardinality
        except KeyError:
            self.tags[tagName] = tagCardinality
        except Exception as e:
            raise e
        
        

class EngineStatus(object):
    def __init__(self, start = 0):
        self.lock = threading.Lock()
        self.serverOn = False
        self.busy = False
        self.alerts = None
    def busyOn(self):
        self.lock.acquire()
        try:
            self.busy = True
        finally:
            self.lock.release()   
    def busyOff(self):
        self.lock.acquire()
        try:
            self.busy = False
        finally:
            self.lock.release()  
    def setAlert(self, alertMessage):
        self.lock.acquire()
        try:
            self.alerts = alertMessage
        finally:
            self.lock.release()  
    def clearAlert(self):
        self.lock.acquire()
        try:
            self.alerts = None
        finally:
            self.lock.release() 
    def toggleOn(self):
        if self.busy == True:
            raise AttributeError("Intentsity status change blocked, because busy flag is set!")
        else:
            self.lock.acquire()
            try:
                self.serverOn = True
            finally:
                self.busy = False
                self.lock.release()
    def toggleOff(self):
        if self.busy == True:
            raise AttributeError("Intentsity status change blocked, because busy flag is set!")
        else:
            self.lock.acquire()
            try:
                self.serverOn = False
            finally:
                self.busy = False
                self.lock.release()
                    

rmlEngine = Engine.Engine()
engineStatus = EngineStatus()
engineStartQueue = queue.Queue()
ationInsertionTypes = Engine.ActionInsertionType()

class EngineStarter(threading.Thread):
    '''
        A little helper class that lets up delegate the start operations on the Intentsity engine to a separate thread and return the REST call right away.
    '''


    def run(self):
        try:
            global engineStatus
            global basePort
            if (engineStatus.busy == False) and (engineStatus.serverOn == False):
                engineStatus.busyOn()
                engineStatus.clearAlert()
                global engineStartQueue
                startParams = engineStartQueue.get_nowait()
                rmlEngine.setPersistence(startParams[0], startParams[1])   
                rmlEngine.setBasePort(basePort)
                    
                #let url handler return 
                engineStartQueue.put_nowait([200, "Starting..."])
                
                try:
                    rmlEngine.start() 
                    engineStatus.busyOff()
                    engineStatus.toggleOn()
                except Exception as unusedE:
                    engineStatus.busyOff()
                    engineStatus.toggleOff()
                    
                    fullerror = sys.exc_info()
                    errorID = str(fullerror[0])
                    errorMsg = str(fullerror[1])
                    alertMessage = "%s, %s" %(errorID, errorMsg)
                    rmlEngine.startupState.FAILED_TO_START
                    engineStatus.setAlert(alertMessage)
            elif (engineStatus.serverOn == True) and ((engineStatus.busy == True)):
                engineStartQueue.put([202, "Command ignored.  Server currently shutting down"])
            elif engineStatus.serverOn == False:
                engineStartQueue.put([202, "Command ignored.  Server in busy state"])
            else:
                engineStartQueue.put([202, "Command ignored.  Server already in startup"]) 
        except Exception as unusedE:
            engineStatus.busyOff()
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            alertMessage = "%s, %s" %(errorID, errorMsg)
            engineStartQueue.push([500, alertMessage])
        

    
    
################################
##  Non Routed helper methods
################################



#this method does not have a url handler.  the addDataMolecule and addServiceMolecule handlers act as wrappers for this method
def verifyURLDefinitions(rawRequest):
    """
        A method for sanity checking url definition json payloads.  The addURLDefinitionGet and addURLDefinitionPost 
            handlers use this method this method to ensure that these payloads are property formed.
    """
    try:
        rHandlerParameters = None
        rReturnParameters = None
        rPostParameters = None
        
        validTypes = ["Str", 
                    "Int", 
                    "Num", 
                    "StrList", 
                    "IntList", 
                    "NumList", 
                    "StrKeyValuePairList", 
                    "IntKeyValuePairList", 
                    "IntKeyValuePairList"]
        
        # Begin checking data consistence, before creating entity
        # return parameters
        hasReturnParameters = False
        try:
            returnParameters = rawRequest['returnParameters']
            hasReturnParameters = True
        except:
            pass
        #post parameters
        hasPostParams = False
        try:
            postParameters = rawRequest['postParameters']
            hasPostParams = True
        except:
            pass
        #post parameters
        hasHandlerParams = False
        try:
            handlerParameters = rawRequest['handlerParameters']
            hasHandlerParams = True
        except:
            pass

        
        if hasReturnParameters == True:
            #if we have return parameters, then the each parameter must have a name, type and enumeration (even if the enumeration is empty)
            try:
                try:
                    returnParameterTypes = rawRequest['returnParameterTypes']
                    for returnParameterType in returnParameterTypes:
                        if returnParameterType not in validTypes:
                            errorMsg = "%s not one of valid returnParameterTypes values %s" %(returnParameterType, validTypes)
                            raise Exceptions.MismatchedPOSTParameterDeclarationError(errorMsg)
                except Exceptions.MismatchedPOSTParameterDeclarationError as e:
                    raise e
                except Exception as e:
                    pass        
                try:
                    returnParameterDescriptions = rawRequest['returnParameterDescriptions']
                except:
                    pass
        
                try:
                    #First assert that all three branches are filled
                    unusedTest = returnParameters
                    unusedTest = returnParameterTypes
                    unusedTest = returnParameterDescriptions
                except NameError as e:
                    
                    errorMsg = "Mismatched return Parameter Declaration Error:  If declaring a REST endpoint return interface, then the lists parameters, their types and descriptions must match."
                    errorMsg = "%s Missing at least one of 'returnParameters', returnParameterTypes' or 'returnParameterDescriptions'!"  %(errorMsg)
                    raise Exceptions.MissingPOSTParameterDeclarationError(errorMsg)   
                
                lp = len(returnParameters)
                lpt = len(returnParameterTypes)
                lpd = len(returnParameterDescriptions)
                if (lp != lpt) or (lp != lpd):
                    errorMsg = "Mismatched rest Parameter Declaration Error:  If declaring a REST endpoint with a return interface, then the lists parameters, their types and descriptions must match."
                    errorMsg = "%s postParameters length = %s, postParameterTypes length = %s, , postParameterDescriptions length = %s "  %(errorMsg, lp, lpt, lpd)
                    raise Exceptions.MismatchedPOSTParameterDeclarationError()
                else:
                    rReturnParameters = {"parameters" : returnParameters, "types" : returnParameterTypes, "descriptions" : returnParameterDescriptions}
            except Exceptions.MissingPOSTParameterDeclarationError as e:
                raise e
            except Exceptions.MismatchedPOSTParameterDeclarationError:
                raise e
            
        if hasPostParams == True:
            #if we have post parameters, then the each parameter must have a name, type and enumeration (even if the enumeration is empty)
            try:
                try:
                    postParameterTypes = rawRequest['postParameterTypes']
                    for postParameterType in postParameterTypes:
                        if postParameterType not in validTypes:
                            errorMsg = "%s not one of valid postParameterTypes values %s" %(postParameterType, validTypes)
                            raise Exceptions.MismatchedPOSTParameterDeclarationError(errorMsg)
                except Exceptions.MismatchedPOSTParameterDeclarationError as e:
                    raise e
                except Exception as e:
                    raise e        
                try:
                    postParameterDescriptions = rawRequest['postParameterDescriptions']
                except:
                    pass
        
                try:
                    #First assert that all three branches are filled
                    unusedTest = postParameters
                    unusedTest = postParameterTypes
                    unusedTest = postParameterDescriptions
                except NameError as e:
                    
                    errorMsg = "Mismatched POST Parameter Declaration Error:  If declaring a REST endpoint with a POST handler, then the lists parameters, their types and descriptions must match."
                    errorMsg = "%s Missing at least one of 'postParameters', postParameterTypes' or 'postParameterDescriptions'!"  %(errorMsg)
                    raise Exceptions.MissingPOSTParameterDeclarationError(errorMsg)   
                
                lp = len(postParameters)
                lpt = len(postParameterTypes)
                lpd = len(postParameterDescriptions)
                if (lp != lpt) or (lp != lpd):
                    errorMsg = "Mismatched POST Parameter Declaration Error:  If declaring a REST endpoint with a POST handler, then the lists parameters, their types and descriptions must match."
                    errorMsg = "%s postParameters length = %s, postParameterTypes length = %s, , postParameterDescriptions length = %s "  %(errorMsg, lp, lpt, lpd)
                    raise Exceptions.MismatchedPOSTParameterDeclarationError()
                else:
                    rPostParameters = {"parameters" : postParameters, "types" : postParameterTypes, "descriptions" : postParameterDescriptions}
            except Exceptions.MissingPOSTParameterDeclarationError as e:
                raise e
            except Exceptions.MismatchedPOSTParameterDeclarationError:
                raise e
            
        if hasHandlerParams == True:
            #if we have hasHandlerParams parameters, then the each parameter must have a name, and enumeration (even if the enumeration is empty)
            #  Handler parameters are stacked on the end of the url.
            #    e.g.  if we had a base url of '/foo/bar' and handlerParameters was ['first', 'second']
            #    The handler would be '/foo/bar/<first>/<second>
            try:      
                try:
                    handlerParameterDescriptions = rawRequest['handlerParameterDescriptions']
                except:
                    pass
        
                try:
                    #First assert that all three branches are filled
                    unusedTest = handlerParameters
                    unusedTest = handlerParameterDescriptions
                except NameError as e:
                    errorMsg = "Mismatched return Parameter Declaration Error:  If declaring a REST endpoint with a 'clean' url, then the lists parameters, their and descriptions must match."
                    errorMsg = "%s Missing at least one of 'handlerParameters' or 'handlerParameterDescriptions'!"  %(errorMsg)
                    raise Exceptions.MissingPOSTParameterDeclarationError(errorMsg)   
                
                lp = len(handlerParameters)
                lpd = len(handlerParameterDescriptions)
                if lp != lpd:
                    errorMsg = "Mismatched rest Parameter Declaration Error:  If declaring a REST endpoint with a return interface, then the lists parameters, their types and descriptions must match."
                    errorMsg = "%s handlerParameters length = %s, handlerParameterDescriptions length = %s "  %(errorMsg, lp, lpd)
                    raise Exceptions.MismatchedPOSTParameterDeclarationError()
                else:
                    rHandlerParameters = {"parameters" : handlerParameters, "descriptions" : handlerParameterDescriptions}
            except Exceptions.MissingPOSTParameterDeclarationError as e:
                raise e
            except Exceptions.MismatchedPOSTParameterDeclarationError:
                raise e
    
        return (rHandlerParameters, rReturnParameters, rPostParameters)
    
    except Exceptions.MissingPOSTParameterDeclarationError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Incomplete callback URL parameter definition.  %s" %(errorMsg)
        raise Exception(returnStr)
    except Exceptions.MismatchedPOSTParameterDeclarationError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Inconsistent callback URL parameter definition.  %s" %(errorMsg)
        raise Exception(returnStr)        
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Problematic  URL parameter definition.  %s, %s" %(errorID, errorMsg)
        raise Exception(returnStr)



#this method does not have a url handler.  the addDataMolecule and addServiceMolecule handlers act as wrappers for this method
def setURLDefinitions(memePath, rHandlerParameters, rReturnParameters, rPostParameters = None):
    """
        This method sets defined the url parameter definitions for the Agent.URLDefinitionMM family of memes.  It can be fired
           on meme creation, or at a later date to reset the meme api
    """
    try:
        '''
        #If we are going to ask for a URL callback, then let's be consistent about its type
        validTypes = [ "urlPOST", "urlGET"]
        if urlType not in validTypes:
            errorMsg = "%s not one of valid types %s" %(urlType, validTypes)
            raise ValueError(errorMsg)
        unusedReturnResults = rmlEngine.api.setEntityPropertyValue(entityUUID, "URLType", urlType)
        '''
        
        'list'
        #set appropriate properties
        global rmlEngine
        if rHandlerParameters is not None:
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "HandlerParameters", rHandlerParameters['parameters'], 'list')
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "HandlerParameterDescriptions", rHandlerParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "HandlerParameters")
            except: 
                pass
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "HandlerParameterDescriptions")
            except: 
                pass            

        
        if rReturnParameters is not None:
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "ReturnParameters", rReturnParameters['parameters'], 'list')
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "ReturnParameterTypes", rReturnParameters['types'], 'list')
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "ReturnParameterDescriptions", rReturnParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "ReturnParameters")
            except: 
                pass
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "ReturnParameterTypes")
            except: 
                pass  
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "ReturnParameterDescriptions")
            except: 
                pass  
            
        if rPostParameters is not None:
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "POSTParameters", rPostParameters['parameters'], 'list')
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "POSTParameterTypes", rPostParameters['types'], 'list')
            unusedReturnResults = rmlEngine.api.sourceMemePropertySet(memePath, "POSTParameterDescriptions", rPostParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "POSTParameters")
            except: 
                pass
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "POSTParameterTypes")
            except: 
                pass  
            try:
                unusedReturnResults = rmlEngine.api.sourceMemePropertyRemove(memePath, "POSTParameterDescriptions")
            except: 
                pass 
            
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Error while populating URL parameter definitions.  %s, %s" %(errorID, errorMsg)
        raise Exception(returnStr)
    


def addMolecule(memeType, moleculeType, technicalName, creatorID, ownerID, rawRequest):
    """
        Adding data and service molecules is essentially the same; with slight changes in terms of which entity types are created and what the error
            message strings look like.  The "addXMolecule" handlers wrap this method
    """
    try:
        global rmlEngine
        newUUID = rmlEngine.api.createEntityFromMeme(memeType)
        #Agent.Molecule is created with the default controller.  Break the link and replace it with the desired controller
        defaultControllerUUID = rmlEngine.api.createEntityFromMeme("Agent.DefaultController")
        unusedReturnResults = rmlEngine.api.removeEntityLink(newUUID, defaultControllerUUID)
        unusedReturnResults = rmlEngine.api.addEntityLink(newUUID, ownerID)
        unusedReturnResults = rmlEngine.api.addEntityLink(newUUID, creatorID)
        unusedReturnResults = rmlEngine.api.setEntityPropertyValue(newUUID, "technicalName", technicalName)
        
        #This property is purely optional and won't affect entity creation    
        try:
            description = rawRequest['description']
            unusedReturnResults = rmlEngine.api.setEntityPropertyValue(newUUID, "description", description)
        except:
            pass
        
        return newUUID
    except Exceptions.MissingPOSTParameterDeclarationError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create %s molecule %s for controller %s.  Incomplete callback URL parameter definition.  %s" %(moleculeType, technicalName, ownerID, errorMsg)
        raise Exception(returnStr)
    except Exceptions.MismatchedPOSTParameterDeclarationError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create %s molecule %s for controller %s.  Inconsistent callback URL parameter definition.  %s" %(moleculeType, technicalName, ownerID, errorMsg)
        raise Exception(returnStr) 
    except Exceptions.InvalidControllerError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create %s molecule %s.  Invalid controller %s" %(moleculeType, technicalName, ownerID)
        raise Exception(returnStr)        
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create %s molecule %s for controller %s.  Inconsistent callback URL parameter definition.  %s, %s" %(moleculeType, technicalName, ownerID, errorID, errorMsg)
        raise Exception(returnStr)



    

@route('/')
def server_static():
    return("Hello!")
    
    
@route('/admin/status', method='GET')
def status():
    global engineStatus
    try:
        if (engineStatus.serverOn == True) and (engineStatus.busy == False) :
            response.status = 200
            returnStr = "Intentsity Engine Status: Ready"
        elif (engineStatus.serverOn == True) and (engineStatus.busy == True) :
            response.status = 503
            returnStr = "Intentsity Engine Status: Shutting Down"
        elif (engineStatus.serverOn == False) and (engineStatus.busy == True) :
            response.status = 503
            returnStr = "Intentsity Engine Status: Starting"
        elif (engineStatus.serverOn == False) and (engineStatus.busy == False) :
            response.status = 503
            returnStr = "Intentsity Engine Status: Not Running"
        response.body = json.dumps({"status": returnStr})
        return response
    except Exception as e:
        response.status = 500
        returnStr = "Intentsity Engine Status: Failed to Start"
        response.body = json.dumps({"status": returnStr})
        return response



@route('/admin/start', method='POST')
def start():
    
    try:
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        validateOnLoad = False
        try:
            validateOnLoad = jsonPayload["validateRepository"]
            if type(validateOnLoad) != type(True):
                errorMsg = "POST call json parameter 'validateRepository' has non-boolean value %s of type %s.  This parameter must be a boolean if present" %(validateOnLoad, type(validateOnLoad))
                raise TypeError(errorMsg)
        except KeyError:
            pass
        except TypeError as e:
            raise e
        except Exception as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on processing json POST parameter 'validateRepository'.  %s, %s" %(errorID, errorMsg)
            tb = sys.exc_info()[2]
            raise ValueError(responseMessage).with_traceback(tb)

        repositories = []
        try:
            #"Config", "Test", "TestRepository"
            repos = jsonPayload["repositories"]
            if type(repos) != type([]):
                errorMsg = "POST call json parameter 'repositories' has non-list value %s of type %s.  Proper format is a list of lists, e.g. [['parentDir', 'childDir', 'grandChildDir', ...], ['parentDir', 'childDir', 'grandChildDir', ...], ...]" %(repos, type(repos))
                raise TypeError(errorMsg)
            for repo in repos:
                if type(repo) != type([]):
                    errorMsg = "POST call json parameter 'repositories' has non-list value %s of type %s in nested list.  Proper format is a list of lists, e.g. [['parentDir', 'childDir', 'grandChildDir', ...], ['parentDir', 'childDir', 'grandChildDir', ...], ...]" %(repo, type(repo))
                    raise TypeError(errorMsg)
                userRoot =  expanduser("~")
                repoLocationSnippet = os.path.join(*repo)
                repoLocation = os.path.join(userRoot, repoLocationSnippet)
                #repoLocation = os.path.join(*repo)
                repositories.append(repoLocation)
        except KeyError:
            pass
        except TypeError as unusedE:
            try:
                fullerror = sys.exc_info()
                errorID = str(fullerror[0])
                errorMsg = str(fullerror[1])
                responseMessage = "%s, %s,  Likely cause is malformed nested 'repositories' parameter %s.  Proper format is a list of lists, e.g. [['parentDir', 'childDir', 'grandChildDir', ...], ['parentDir', 'childDir', 'grandChildDir', ...], ...]" %(errorID, errorMsg, repos)
                raise ValueError(responseMessage)
            except ValueError as e:
                raise e
            except:
                raise e
        except Exception as unusedE:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "%s, %s,  Likely cause is malformed 'repositories' parameter in startup POST url call.  Proper format is a list of lists, e.g. [['parentDir', 'childDir', 'grandChildDir', ...], ['parentDir', 'childDir', 'grandChildDir', ...], ...]" %(errorID, errorMsg)
            raise ValueError(responseMessage)
        
        
        for repoLocation in repositories:
            rmlEngine.addRepo(repoLocation)
        
        persistenceType = None
        try:
            dbSetting = jsonPayload["persistenceType"]
            if (dbSetting is None) or (dbSetting == 'none'):
                pass
            elif (dbSetting == 'sqlite') or (dbSetting == 'mssql') or (dbSetting == 'hana'):
                persistenceType = dbSetting
                print("\n  -- using persistence type %s" %dbSetting)
            else:
                responseMessage = "Invalid persistence type %s!  Permitted valies of --dbtype are 'none', 'sqlite', 'mssql' and 'hana'!  Defaulting to 'none'" %dbSetting
                print(responseMessage)
                raise ValueError(responseMessage)
        except KeyError:
            pass
        except Exception as unusedE:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "%s, %s,  Likely cause is malformed 'persistenceType' parameter in startup POST url call." %(errorID, errorMsg)
            raise ValueError(responseMessage)
                
        dbConnectionString = None
        try:
            try:
                dbConStr = jsonPayload["dbConnectionString"]
            except KeyError: 
                dbConStr = None
            if (dbConStr is None) or (dbConStr == 'none'):
                if persistenceType is None:
                    print("  -- Using in-memory persistence (no connection required)")
                elif persistenceType == 'sqlite':
                    dbConnectionString = 'memory'
                    print("  -- Using sqlite persistence with connection = :memory:")
                else:
                    errorMsg = "  -- Persistence type %s requires a valid database connection.  Please provide a dbConnectionString argument in the POST body!" %persistenceType
                    print(errorMsg)
                    raise ValueError(errorMsg)
            elif dbConStr == 'memory':
                if persistenceType is None:
                    #memory is a valid alternative to none with no persistence
                    print("  -- Using in-memory persistence (no connection required)")
                elif persistenceType == 'sqlite':
                    dbConnectionString = 'memory'
                    print("  -- Using sqlite persistence with connection = :memory:")
                else:
                    errorMsg = "  -- Persistence type %s requires a valid database connection.  Please provide a dbConnectionString argument in the POST body!" %persistenceType
                    print(errorMsg)
                    raise ValueError(errorMsg)
            else:
                dbConnectionString = dbConStr
                if persistenceType == 'sqlite':
                    if dbConnectionString.endswith(".sqlite"):
                        print("  -- Using sqlite persistence with file %s" %dbConnectionString)
                    else:
                        errorMsg = "  -- Using sqlite persistence type with invalid filename %s parameter in dbConnectionString argument in the POST body.  It must end with the .sqlite extension" %dbConnectionString
                        print(errorMsg)
                        raise ValueError(errorMsg)
                else:
                    print("  -- Using persistence type %s with connection = %s" %(persistenceType, dbConnectionString))
        except Exception as unusedE:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "%s, %s,  Likely cause is malformed 'dbConnectionString' parameter in startup POST url call." %(errorID, errorMsg)
            raise ValueError(responseMessage)
        
        """
        rmlEngine.plugins['RegressionTestBroadcaster'] = {'name' : 'RegressionTestBroadcaster',
                                'pluginType' : 'EngineService',
                                'Module' : 'Broadcasters.RegressionTestBroadcaster',
                                'PluginParemeters': {'heatbeatTick' : 1, 'broadcasterID' : 'test'}
                                }
        rmlEngine.broadcasters['test'] = {'memes' : [ 'TestPackageStimulusEngine.SimpleStimuli.Descriptor_Trailer',
                                            'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage',
                                            'TestPackageStimulusEngine.SimpleStimuli.ADescriptor_HelloPage',
                                            'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage2',
                                            'TestPackageStimulusEngine.SimpleStimuli.Descriptor_HelloPage3',
                                            'TestPackageStimulusEngine.SimpleStimuli.Descriptor_MultiPage',
                                            'TestPackageStimulusEngine.SimpleStimuli.Descriptor_AnotherPage',
                                            'TestPackageStimulusEngine.SimpleStimuli.ADescriptor_AnotherPage']}
        """
        
        if (engineStatus.serverOn == True) and (engineStatus.busy == False) :
            response.status = 202
            returnStr = "Engine already running.  Start command ignored"
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.serverOn == True) and (engineStatus.busy == True) :
            response.status = 202
            returnStr = "Engine busy with shutdown.  Start command ignored"
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.serverOn == False) and (engineStatus.busy == True) :
            response.status = 202
            returnStr = "Engine busy with startup.  Start command ignored"
            response.body = json.dumps({"status": returnStr})
            return response
        else:
        
            #Set up the persistence of rmlEngine.  It defaults to no persistence
            global engineStartQueue
            engineStartQueue.put([dbConnectionString, persistenceType])
            starter = EngineStarter()
            starter.run()
            
            time.sleep(3.0)  #Give the EngineStarter instance a couple of seconds to read the queue and respond
            returnParams = engineStartQueue.get_nowait()
                    
            response.status = returnParams[0]
            response.body = json.dumps({"status": returnParams[1]})
        return response
    except json.decoder.JSONDecodeError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start due to malformed json payload in POST body:  %s, %s." %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response
    except ValueError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start:  %s, %s" %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start:  %s, %s" %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response
    
    
    
@route('/admin/stop', method='GET')
def stopServer():
    global rmlEngine
    global engineStatus
    try:
        if (engineStatus.busy == False) and (engineStatus.serverOn == True):
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine.shutdown()
            rmlEngine = Engine.Engine()
            returnStr = "Stopped..."
            response.status = 200
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.busy == True) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server in bootstrap.  Please wait until running before stopping or call /admin/forcestop API handler"
            response.status = 202
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.busy == False) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server was not started."
            response.status = 202
            response.body = json.dumps({"status": returnStr})
            return response
        else:
            #This really should not happen, unless we've been careful  about the busy state handling.
            returnStr = "Command ignored.  Server in busy state"
            response.status = 202
            response.body = json.dumps({"status": returnStr})
            return response
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to stop Intentsity engine.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response
    
    
    
@route('/admin/forcestop')
def forceStopServer():
    global rmlEngine
    global engineStatus
    try:
        if (engineStatus.busy == False) and (engineStatus.serverOn == True):
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Stopped..."
            response.status = 200
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.busy == True) and (engineStatus.serverOn == False):
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Force stopped server in bootstrap..."
            response.status = 200
            response.body = json.dumps({"status": returnStr})
            return response
        elif (engineStatus.busy == False) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server was not started."
            response.status = 202
            response.body = json.dumps({"status": returnStr})
            return response
        else:
            #This really should not happen, unless we've been careful  about the busy state handling.
            #  But this gives us a rock crusher workaround for hung state servers
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Force stopped server in unknown busy state..."
            response.status = 200
            response.body = json.dumps({"status": returnStr})
            return response
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to stop Intentsity engine.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response
    
    
@route('/admin/registerOwner', method='POST')
def registerOwner():
    global rmlEngine
    global engineStatus
    try:
        
        rawRequest = request.POST.dict 
        
        dataCCallbackURL = None
        try:
            dataCCallbackURL = rawRequest["stimulusCallbackURL"]
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        cCallbackFormat = "RawJSON"
        try:
            dataCCallbackURL = rawRequest["stimulusCallbackURL"]
            cCallbackFormat = rawRequest["stimulusPreferredFormat"]
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        newUUID = rmlEngine.api.createEntityFromMeme("Agent.Controller")
        
        if dataCCallbackURL is not None:
            rmlEngine.api.addEntityStringProperty(newUUID, "stimulusCallbackURL", dataCCallbackURL)
        
        response.body = json.dumps({"ownerUUID": newUUID})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Controller Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/registerCreator', method='POST')
def registerCreator():
    
    try:
        
        rawRequest = request.POST.dict 
        
        try:
            dataCCallbackURL = rawRequest["dataCallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Creator entity has no data callback url (dataCallbackURL) POST request parameter.  Entity not created")
        except Exception as e:
            raise e
        
        try:
            stimulusCCallbackURL = rawRequest["stimulusCallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Creator entity has no data callback url (stimulusCallbackURL) POST request parameter.  Entity not created")
        except Exception as e:
            raise e
        
        newUUID = rmlEngine.api.createEntityFromMeme("Agent.Creator")
        
        response.body = json.dumps({"ownerUUID": newUUID})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Creator Entity.  %s, %s" %(errorID, errorMsg)
        response.body = json.dumps({"status": returnStr})
        response.status = 500
        return response
    
    
@route('/admin/registerListener', method='POST')
def registerListener():
    global rmlEngine
    global engineStatus
    try:
        
        rawRequest = request.POST.dict 
        
        try:
            creatorUUID = rawRequest["creatorUUID"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Cannot register listener without a valid creatorUUID parameter.  Listener not registered")
        except Exception as e:
            raise e
        
        try:
            controllerUUID = rawRequest["controllerUUID"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Cannot register listener without a valid controllerUUID parameter.  Listener not registered")
        except Exception as e:
            raise e
        
        memeTypeCreator = rmlEngine.api.getEntityMemeType(creatorUUID)
        memeTypeController = rmlEngine.api.getEntityMemeType(controllerUUID)
        
        if memeTypeCreator != "Agent.Creator":
            raise Exceptions.InvalidControllerError("creatorUUID %s refers to entity of meme type %.  creatorUUID should be a valid Agent.Creator")
        if memeTypeController != "Agent.Controller":
            raise Exceptions.InvalidControllerError("controllerUUID %s refers to entity of meme type %.  controllerUUID should be a valid Agent.Controller")
        
        response.body = json.dumps({"status": "ok"})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to register listener.  %s, %s" %(errorID, errorMsg)
        response.body = json.dumps({"status": returnStr})
        response.status = 500
        return response
    
    
    
@route('/engine/log', method='POST')
def log():
    global rmlEngine
    
    try:
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            origin = jsonPayload["origin"]
        except KeyError:
            origin = "anonomyous"
            
        originURI = request.remote_addr
            
        llevel = 3   
        try:
            llevelString = jsonPayload["logLevel"].upper()
            if llevelString == "ERROR": llevel = 0
            elif llevelString == "WARNING": llevel = 1
            elif llevelString == "ADMIN": llevel = 2
            elif llevelString == "INFO": llevel = 3
            elif llevelString == "DEBUG": llevel = 4
        except KeyError:
            origin = request.remote_addr
            
        lType = 1   
        try:
            lType = int(jsonPayload["logType"])
            if lType > 1 or lType < 0:
                lType = 1
        except KeyError:
            pass
         
        try:
            message = jsonPayload["message"]
        except KeyError as e:
            raise e   
        
        rmlEngine.log(originURI, origin, message, llevel, lType)    
        response.body = json.dumps({"status": "Message posted to queue"})                
        response.status = 200
        return response        
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Error while logging.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        response.body = json.dumps({"status": returnStr})
        return response


###############################
##  Main Engine 
###############################

@route('/postaction', method='POST')
def postAction():
    """  A generic action invocation """
    global rmlEngine
    try:
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            actionID = jsonPayload["actionID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'actionID'"
            raise Exceptions.MissingActionError(errorMsg)

        try:
            ownerID = jsonPayload["ownerID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'ownerID'"
            raise Exceptions.InvalidControllerError()
        
        try:
            subjectID = jsonPayload["subjectID"]
        except KeyError:
            subjectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
        
        try:
            
            insertionModeText = jsonPayload["insertionMode"]
            if insertionModeText == 'head_clear':
                insertionMode = ationInsertionTypes.HEAD_CLEAR
            elif insertionModeText == 'head':
                insertionMode = ationInsertionTypes.HEAD
            elif insertionModeText == 'append':
                insertionMode = ationInsertionTypes.APPEND
            else:
                errorMsg = "Invalid insertionMode parameter.  Valid values are 'head', 'head_clear' and 'append'" %insertionModeText
                raise Exceptions.InsertionModeError()
        except KeyError:
            insertionMode = ationInsertionTypes.HEAD_CLEAR

        try:
            rtparams = jsonPayload["actionParams"]
        except KeyError:
            rtparams = {}        
        
        actionInvocation = Engine.ActionRequest(actionID, insertionMode, rtparams, subjectID, objectID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        response.body = json.dumps({"status": "Action Posted"})
        response.status = 200
        return response
    except Exceptions.InvalidControllerError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response  
    except Exceptions.MissingActionError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response       
    except Exception as unusedE: 

        #When this exception happens, the actionID variable won't be in scope, 
        #  But we can expect that actionID is available, or a MissingActionError would have been thrown.
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        actionID = jsonPayload["actionID"]

        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action %s.  %s, %s" %(actionID, errorID, errorMsg)
        response.status = 500
        return response



@route('/poststimulus', method='POST')
def postStimulus():
    """  A generic stimulus invocation """
    global rmlEngine
    try:
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            actionID = jsonPayload["actionID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'actionID'"
            raise Exceptions.MissingActionError(errorMsg)

        try:
            ownerID = jsonPayload["ownerID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'ownerID'"
            raise Exceptions.InvalidControllerError()
        
        try:
            subjectID = jsonPayload["subjectID"]
        except KeyError:
            subjectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
        
        try:
            
            insertionModeText = jsonPayload["insertionMode"]
            if insertionModeText == 'head_clear':
                insertionMode = ationInsertionTypes.HEAD_CLEAR
            elif insertionModeText == 'head':
                insertionMode = ationInsertionTypes.HEAD
            elif insertionModeText == 'append':
                insertionMode = ationInsertionTypes.APPEND
            else:
                errorMsg = "Invalid insertionMode parameter.  Valid values are 'head', 'head_clear' and 'append'" %insertionModeText
                raise Exceptions.InsertionModeError()
        except KeyError:
            insertionMode = ationInsertionTypes.HEAD_CLEAR

        try:
            rtparams = jsonPayload["actionParams"]
        except KeyError:
            rtparams = {}        
        
        actionInvocation = Engine.ActionRequest(actionID, insertionMode, rtparams, subjectID, objectID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        response.body = json.dumps({"status": "Stimulus Posted"})
        response.status = 200
        return response
    except Exceptions.InvalidControllerError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response  
    except Exceptions.MissingActionError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response       
    except Exception as unusedE: 

        #When this exception happens, the actionID variable won't be in scope, 
        #  But we can expect that actionID is available, or a MissingActionError would have been thrown.
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        actionID = jsonPayload["actionID"]

        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action %s.  %s, %s" %(actionID, errorID, errorMsg)
        response.status = 500
        return response
    
    
@route('/collectmessages', method='POST')
def collectMessages():
    """  A generic stimulus invocation """
    global rmlEngine
    try:
        stimuli = []
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        try:
            actionID = jsonPayload["actionID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'actionID'"
            raise Exceptions.MissingActionError(errorMsg)

        try:
            ownerID = jsonPayload["ownerID"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'ownerID'"
            raise Exceptions.InvalidControllerError()
        
        try:
            subjectID = jsonPayload["subjectID"]
        except KeyError:
            subjectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
            
        try:
            objectID = jsonPayload["objectID"]
        except KeyError:
            objectID = ownerID
        
        try:
            
            insertionModeText = jsonPayload["insertionMode"]
            if insertionModeText == 'head_clear':
                insertionMode = ationInsertionTypes.HEAD_CLEAR
            elif insertionModeText == 'head':
                insertionMode = ationInsertionTypes.HEAD
            elif insertionModeText == 'append':
                insertionMode = ationInsertionTypes.APPEND
            else:
                errorMsg = "Invalid insertionMode parameter.  Valid values are 'head', 'head_clear' and 'append'" %insertionModeText
                raise Exceptions.InsertionModeError()
        except KeyError:
            insertionMode = ationInsertionTypes.HEAD_CLEAR

        try:
            rtparams = jsonPayload["actionParams"]
        except KeyError:
            rtparams = {}        
        
        actionInvocation = Engine.ActionRequest(actionID, insertionMode, rtparams, subjectID, objectID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        response.body = json.dumps({"status": stimuli})
        response.status = 200
        return response
    except Exceptions.InvalidControllerError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response  
    except Exceptions.MissingActionError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return response       
    except Exception as unusedE: 

        #When this exception happens, the actionID variable won't be in scope, 
        #  But we can expect that actionID is available, or a MissingActionError would have been thrown.
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        actionID = jsonPayload["actionID"]

        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to post action %s.  %s, %s" %(actionID, errorID, errorMsg)
        response.status = 500
        return response
    

##########################
##  Modeling (Generic)
##########################
    
#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/createEntityFromMeme/<memePath>', method='GET')
def createEntityFromMeme(memePath):
    
    try:
        newUUID = rmlEngine.api.createEntityFromMeme(memePath)
        uuidAsStr = "%s" %(newUUID)
        
        response.status = 200
        response.body = json.dumps({"entityUUID": uuidAsStr})
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to create new %s Entity.  %s, %s" %(memePath, errorID, errorMsg)
        response.status = 500
        return response
    
    
#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/createEntity', method='GET')
def createEntity():
    
    try:
        newUUID = rmlEngine.api.createEntity()
        uuidAsStr = "%s" %(newUUID)
        
        response.status = 200
        response.body = json.dumps({"entityUUID": uuidAsStr})
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to create new generic Entity %s.  %s, %s" %(newUUID, errorID, errorMsg)
        response.status = 500
        return response
    



@route('/modeling/getEntityMemeType/<entityUUID>', method='GET')
def getEntityMemeType(entityUUID):
    
    try:
        memeType = rmlEngine.api.getEntityMemeType(uuid.UUID(entityUUID))
        
        response.body = json.dumps({"entityUUID": entityUUID, "memeType": memeType})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to get meme type of Entity %s.  %s, %s" %(entityUUID, errorID, errorMsg)
        response.status = 500
        return response
    
    
    
@route('/modeling/getEntityMetaMemeType/<entityUUID>', method='GET')
def getEntityMetaMemeType(entityUUID):
    
    try:
        metaMemeType = rmlEngine.api.getEntityMetaMemeType(uuid.UUID(entityUUID))
        
        response.body = json.dumps({"entityUUID": entityUUID, "mmetaMmeType": metaMemeType})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to get meme type of Entity %s.  %s, %s" %(entityUUID, errorID, errorMsg)
        response.status = 500
        return response
    
    
@route('/modeling/getEntitiesByMemeType/<memePath>', method='GET')
def getEntitiesByMemeType(memePath):
    
    try:
        entityUUIDList = rmlEngine.api.getEntitiesByMemeType(memePath)
        
        entityList = []
        for entityUUID in entityUUIDList:
            entityID = str(entityUUID)
            entityList.append(entityID)
        
        response.body = json.dumps({"memeType": memePath, "entityIDList": entityList})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to find entitities of type %s.  %s, %s" %(memePath, errorID, errorMsg)
        response.status = 500
        return response
    
    
@route('/modeling/getEntitiesByMetaMemeType/<metaMemePath>', method='GET')
def getEntitiesByMetaMemeType(metaMemePath):
    
    try:
        entityUUIDList = rmlEngine.api.getEntitiesByMetaMemeType(metaMemePath)
        
        entityList = []
        for entityUUID in entityUUIDList:
            entityID = str(entityUUID)
            entityList.append(entityID)
        
        response.body = json.dumps({"metaMemeType": metaMemePath, "entityIDList": entityList})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Failed to find entitities of metameme type %s.  %s, %s" %(metaMemePath, errorID, errorMsg)
        response.status = 500
        return response



@route('/modeling/addEntityLink', method='POST')
def addEntityLink():
    
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            sourceEntityID = jsonPayload["sourceEntityID"]
            sourceEntityUUID = uuid.UUID(sourceEntityID)
        except KeyError:
            errorMsg = "Missing required JSON parameter 'sourceEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            targetEntityID = jsonPayload["targetEntityID"]
            targetEntityUUID = uuid.UUID(targetEntityID)
        except KeyError:
            errorMsg = "Missing required JSON parameter 'targetEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        linkAttributes = {}
        try:
            linkAttributes = jsonPayload["linkAttributes"]
        except KeyError:
            #This parameter is optional
            pass 
        
        linkType = 0
        try:
            linkType = int(jsonPayload["linkType"])
        except KeyError:
            #This parameter is optional
            pass 
    
        returnResults = rmlEngine.api.addEntityLink(sourceEntityUUID, targetEntityUUID, linkAttributes, linkType)
        response.body = json.dumps({"sourceEntityUUID": sourceEntityID, "targetEntityID": targetEntityID, "status": "sucsess"})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to link Entity %s to %s, % %s" %(sourceEntityID, targetEntityID, errorID, errorMsg)
        response.body = json.dumps({"sourceEntityUUID": sourceEntityID, "targetEntityID": targetEntityID, "linkAttributes" : linkAttributes, "linkType" : linkType, "status": "failure", "message" : returnStr})
        response.status = 500
        return response
        
    
        
    
@route('/modeling/removeEntityLink/<sourceEntityID>/<targetEntityID>', method='GET')
def removeEntityLink(sourceEntityID, targetEntityID):
    
    try:
        sourceEntityUUID = uuid.UUID(sourceEntityID)
        targetEntityUUID = uuid.UUID(targetEntityID)
        returnResults = rmlEngine.api.removeEntityLink(sourceEntityUUID, targetEntityUUID)
        response.body = json.dumps({"sourceEntityUUID": sourceEntityID, "targetEntityID": targetEntityID, "status": "sucsess"})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to remove link from Entity %s to %s, % %s" %(sourceEntityID, targetEntityID, errorID, errorMsg)
        response.status = 500
        return returnStr



@route('/modeling/getAreEntitiesLinked/<sourceEntityID>/<targetEntityID>', method='GET')
def getAreEntitiesLinked(sourceEntityID, targetEntityID):
    
    try:
        sourceEntityUUID = uuid.UUID(sourceEntityID)
        targetEntityUUID = uuid.UUID(targetEntityID)
        areLinked = rmlEngine.api.getAreEntitiesLinked(sourceEntityUUID, targetEntityUUID)
        areLinkedS = str(areLinked)
        response.body = json.dumps({"sourceEntityUUID": sourceEntityID, "targetEntityID": targetEntityID, "linkExists": areLinkedS})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to remove link from Entity %s to %s, % %s" %(sourceEntityID, targetEntityID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
    


@route('/modeling/getEntityHasProperty/<entityID>/<propName>', method='GET')
def getEntityHasProperty(entityID, propName):
    
    try:
        global rmlEngine
        entityUUID = uuid.UUID(entityID)
        propValue = rmlEngine.api.getEntityHasProperty(entityUUID, propName)
        propValueS = str(propValue)
        response.body = json.dumps({"entityID": entityID, "propertyName": propName, "present" : propValueS})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to set property %s to %s on Entity %s, % %s" %(propName, propValue, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
        

@route('/modeling/getEntityPropertyValue/<entityID>/<propName>', method='GET')
def getEntityPropertyValue(entityID, propName):
    
    try:
        global rmlEngine
        entityUUID = uuid.UUID(entityID)
        propValue = rmlEngine.api.getEntityPropertyValue(entityUUID, propName)
        response.body = json.dumps({"entityID": entityID, "propertyName": propName, "propertyValue" : propValue})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to set property %s to %s on Entity %s, % %s" %(propName, propValue, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr

    
    
@route('/modeling/setEntityPropertyValue', method='POST')
def setEntityPropertyValue():
    
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["entityID"]
            try:
                entityUUID = uuid.UUID(entityID)
            except ValueError as e:
                catchme = ""
        except KeyError:
            errorMsg = "Missing required JSON parameter 'entityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            propName = jsonPayload["propName"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'propName'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            propValue = jsonPayload["propValue"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'propValue'"
            raise Exceptions.MissingActionError(errorMsg)
    
        returnResults = rmlEngine.api.setEntityPropertyValue(entityUUID, propName, propValue)
        response.body = json.dumps({"entityID": entityID, "propertyName": propName, "propertyValue": propValue})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to set property %s to %s on Entity %s, % %s" %(propName, propValue, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr
        
        
@route('/modeling/query', method='POST')
def getLinkCounterpartsByType():
    #entityUUID, memePath, linkType = None, isMeme = True, fastSearch = False
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["originEntityID"]
            try:
                entityUUID = uuid.UUID(entityID)
            except ValueError as e:
                catchme = ""
        except KeyError:
            errorMsg = "Missing required JSON parameter 'originEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            memePath = jsonPayload["query"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'query'"
            raise Exceptions.MissingActionError(errorMsg)
        
        linkType = None
        try:
            linkType = jsonPayload["linkType"]
            if int(linkType) not in [0, 1]:
                errorMessage = "Optional JSON parameter 'linkType' of invalid value.  Only 0 and 1 are valid.  Recieved %s" %(linkType)
                raise ValueError(errorMessage)
        except KeyError as e:
            #Optional
            pass
        except ValueError as e:
            raise e
        except Exception as e:
            raise e
        
        fastSearch = False
        '''
        try:
            fastSearch = jsonPayload["fastSearch"]
            if int(linkType) not in [0, 1]:
                errorMessage = "Optional JSON parameter 'fastSearch' of invalid value.  Only True and False are valid.  Recieved %s" %(fastSearch)
                raise ValueError(errorMessage)
        except ValueError as e:
            raise e
        except Exception as e:
            #Optional
            pass
        '''
    
        entityUUIDList = rmlEngine.api.getLinkCounterpartsByType(entityUUID, memePath, linkType, fastSearch)
        entityList = []
        for selectionUUID in entityUUIDList:
            selectionID = str(selectionUUID)
            entityList.append(selectionID)
        response.body = json.dumps({"entityIDList": entityList})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        response.body = "Graph traverse query %s from entity %s failed.  %s, %s %s" %(memePath, entityUUID, entityID, errorID, errorMsg)
        response.status = 500
        return response




@route('/modeling/querym', method='POST')
def getLinkCounterpartsByMetaMemeType():
    #entityUUID, memePath, linkType = None, isMeme = True, fastSearch = False
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["originEntityID"]
            try:
                entityUUID = uuid.UUID(entityID)
            except ValueError as e:
                catchme = ""
        except KeyError:
            errorMsg = "Missing required JSON parameter 'originEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            memePath = jsonPayload["query"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'query'"
            raise Exceptions.MissingActionError(errorMsg)
        
        linkType = None
        try:
            linkType = jsonPayload["linkType"]
            if int(linkType) not in [0, 1]:
                errorMessage = "Optional JSON parameter 'linkType' of invalid value.  Only 0 and 1 are valid.  Recieved %s" %(linkType)
                raise ValueError(errorMessage)
        except ValueError as e:
            raise e
        except Exception as e:
            #Optional
            pass
    
        entityUUIDList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(entityUUID, memePath, linkType, False)
        entityList = []
        for selectionUUID in entityUUIDList:
            selectionID = str(selectionUUID)
            entityList.append(selectionID)
        response.body = json.dumps({"entityIDList": entityList})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Graph traverse query %s from entity %s failed.  %s, %s %s" %(memePath, entityUUID, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr        
    
    
    
@route('/modeling/getTraverseReport', method='POST')
def getTraverseReport():
    #entityUUID, memePath, linkType = None, isMeme = True, fastSearch = False
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["originEntityID"]
            try:
                entityUUID = uuid.UUID(entityID)
            except ValueError as e:
                catchme = ""
        except KeyError:
            errorMsg = "Missing required JSON parameter 'originEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            memePath = jsonPayload["query"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'query'"
            raise Exceptions.MissingActionError(errorMsg)
        
        linkType = 0
        try:
            linkType = jsonPayload["linkType"]
            if int(linkType) not in [0, 1, 2]:
                errorMessage = "Optional JSON parameter 'linkType' of invalid value.  Only 0 and 1 are valid.  Recieved %s" %(linkType)
                raise ValueError(errorMessage)
            if linkType == 2: linkType = None
        except ValueError as e:
            raise e
        except Exception as e:
            #Optional
            pass

    
        #traverseReport = rmlEngine.api.getTraverseReportJSON(entityUUID, memePath, True, linkType)
        traverseReport = rmlEngine.api.getTraverseReport(entityUUID, memePath, True, linkType)
        response.body = json.dumps(traverseReport)
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Graph traverse query %s from entity %s failed.  %s, %s %s" %(memePath, entityUUID, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr  
    
    
    
@route('/modeling/getTraverseReportByMetaMemes', method='POST')
def getTraverseReportByMetaMemes():
    #entityUUID, memePath, linkType = None, isMeme = True, fastSearch = False
    try:
        global rmlEngine
        
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["originEntityID"]
            try:
                entityUUID = uuid.UUID(entityID)
            except ValueError as e:
                catchme = ""
        except KeyError:
            errorMsg = "Missing required JSON parameter 'originEntityID'"
            raise Exceptions.MissingActionError(errorMsg)
        
        try:
            memePath = jsonPayload["query"]
        except KeyError:
            errorMsg = "Missing required JSON parameter 'query'"
            raise Exceptions.MissingActionError(errorMsg)
        
        linkType = None
        try:
            linkType = jsonPayload["linkType"]
            if int(linkType) not in [0, 1]:
                errorMessage = "Optional JSON parameter 'linkType' of invalid value.  Only 0 and 1 are valid.  Recieved %s" %(linkType)
                raise ValueError(errorMessage)
        except ValueError as e:
            raise e
        except Exception as e:
            #Optional
            pass

    
        traverseReport = rmlEngine.api.getTraverseReportJSON(entityUUID, memePath, False, linkType)
        response.body = json.dumps(traverseReport)
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Graph traverse query %s from entity %s failed.  %s, %s %s" %(memePath, entityUUID, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr       




#####################################
##  Modeling (Intentsity)
#####################################


#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/addCreator', method='GET')
def addCreator():
    
    try:
        global rmlEngine
        newUUID = rmlEngine.api.createEntityFromMeme("Agent.Creator")
        uuidAsStr = "%s" %(newUUID)
        
        response.status = 200
        response.body = json.dumps({"entityUUID": uuidAsStr})
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Owner Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
@route('/modeling/registerCreatorDataCallbackURL', method='POST')
def registerCreatorDataCallbackURL():
    """
        params:
            creatorID 
            dataCallbackURL
    """ 
    try:
        global rmlEngine
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        #ownerID
        try:
            creatorID = jsonPayload["creatorID"]
            creatorUUID = uuid.UUID(creatorID)
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("creatorID parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            ownerEntityType = rmlEngine.api.getEntityMemeType(creatorUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("creatorID parameter value %s does not exist." %creatorID)
        
        if ownerEntityType != "Agent.Creator":
            raise Exceptions.TemplatePathError("creatorID parameter value %s does not refer to a valid data creator" %creatorID)

        #stimulusCallbackURL
        try:
            dataCallbackURL = jsonPayload["dataCallbackURL"]
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("dataCallbackURL parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            rmlEngine.api.setEntityPropertyValue(creatorUUID, "dataCallbackURL", dataCallbackURL)
        except Exception as e:
            raise Exceptions.MismatchedPOSTParametersError("Error while assigning stimulusCallbackURL value %s to entity %s " %(dataCallbackURL, creatorID))

        
        returnStr = "Assigned dataCallbackURL %s to owner %s " %(dataCallbackURL, creatorID)
        response.body = json.dumps({"status": returnStr})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to assign dataCallbackURL to  new Agent.Creator Entity.  %s, %s" %(errorID, errorMsg)
        response.body = json.dumps({"status": returnStr})
        response.status = 500
        return response
    
    
    
@route('/modeling/registerCreatorStimulusCallbackURL', method='POST')
def registerCreatorStimulusCallbackURL():
    """
        params:
            creatorID 
            stimulusCallbackURL
    """    
    try:
        global rmlEngine
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        #ownerID
        try:
            creatorID = jsonPayload["creatorID"]
            creatorUUID = uuid.UUID(creatorID)
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("creatorID parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            ownerEntityType = rmlEngine.api.getEntityMemeType(creatorUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("creatorID parameter value %s does not exist." %creatorID)
        
        if ownerEntityType != "Agent.Creator":
            raise Exceptions.TemplatePathError("creatorID parameter value %s does not refer to a valid data creator" %creatorID)
                
        
        #stimulusCallbackURL
        try:
            stimulusCallbackURL = jsonPayload["stimulusCallbackURL"]
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("stimulusCallbackURL parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            rmlEngine.api.setEntityPropertyValue(creatorUUID, "stimulusCallbackURL", stimulusCallbackURL)
        except Exception as e:
            raise Exceptions.MismatchedPOSTParametersError("Error while assigning stimulusCallbackURL value %s to entity %s " %(stimulusCallbackURL, creatorID))

        returnStr = "Assigned stimulusCallbackURL %s to owner %s " %(stimulusCallbackURL, creatorID)
        response.body = json.dumps({"status": returnStr})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to assign dataCallbackURL to  new Agent.Creator Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
        


#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/addOwner', method='GET')
def addOwner():
    
    try:
        global rmlEngine
        newUUID = rmlEngine.api.createEntityFromMeme("Agent.Owner")
        uuidAsStr = "%s" %(newUUID)
        
        response.status = 200
        response.body = json.dumps({"entityUUID": uuidAsStr})
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Owner Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
    
#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/registerOwnerCallbackURL', method='POST')
def registerOwnerCallbackURL():
    """
        params:
            ownerID 
            stimulusCallbackURL
    """
    
    try:
        global rmlEngine
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        #ownerID
        try:
            ownerID = jsonPayload["ownerID"]
            ownerUUID = uuid.UUID(ownerID)
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("ownerID parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            ownerEntityType = rmlEngine.api.getEntityMemeType(ownerUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %ownerID)
        
        if ownerEntityType != "Agent.Owner":
            raise Exceptions.TemplatePathError("ownerID parameter value %s does not refer to a valid data owner" %ownerID)
        
        
        #stimulusCallbackURL
        try:
            stimulusCallbackURL = jsonPayload["stimulusCallbackURL"]
        except KeyError:
            raise Exceptions.MissingPOSTArgumentError("stimulusCallbackURL parameter missing from POST request.")
        except Exception as e:
            raise e
        
        try:
            rmlEngine.api.setEntityPropertyValue(ownerUUID, "stimulusCallbackURL", stimulusCallbackURL)
        except Exception as e:
            raise Exceptions.MismatchedPOSTParametersError("Error while assigning stimulusCallbackURL value %s to entity %s " %(stimulusCallbackURL, ownerID))

        
        returnStr = "Assigned stimulusCallbackURL %s to owner %s " %(stimulusCallbackURL, ownerID)
        response.body = json.dumps({"status": returnStr})
        response.status = 200
        return response
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Owner Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    

@route('/admin/broadcastersubscribe', method='POST')
def broadcasterSubscribe():
    """
        params:
            ownerID 
            stimulusCallbackURL
    """   
    try:
        rawRequest = request.POST.dict 
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["entityID"]
            entityUUID = uuid.UUID(entityID)
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Request has no valid entityID post patameter")
        except Exception as e:
            raise e
        
        try:
            entityType = rmlEngine.api.getEntityMemeType(entityUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %entityID)
        
        if (entityType != "Agent.Owner") and (entityType != "Agent.Creator"):
            raise Exceptions.TemplatePathError("entityID parameter value %s refers to an entity of type %s.  Only data owners and data creators (Agent.Owner and Agent.Creator) may subscribe to broadbasters" %(entityID, entityType))
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Data Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.Molecule", "data", technicalName, creatorID, ownerID, rawRequest)    
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)    
        returnStr = "%s" %newUUID
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg     
    
    
    
    
@route('/admin/broadcasterunsubscribe', method='POST')
def broadcasterUnSubscribe():
    """
        params:
            ownerID 
            stimulusCallbackURL
    """   
    try:
        rawRequest = request.POST.dict 
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["entityID"]
            entityUUID = uuid.UUID(entityID)
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Request has no valid entityID post patameter")
        except Exception as e:
            raise e
        
        try:
            entityType = rmlEngine.api.getEntityMemeType(entityUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %entityID)
        
        if (entityType != "Agent.Owner") and (entityType != "Agent.Creator"):
            raise Exceptions.TemplatePathError("entityID parameter value %s refers to an entity of type %s.  Only data owners and data creators (Agent.Owner and Agent.Creator) may subscribe to broadbasters" %(entityID, entityType))
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Data Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.Molecule", "data", technicalName, creatorID, ownerID, rawRequest)    
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)    
        returnStr = "%s" %newUUID
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg    
    
    
    
@route('/admin/broadcastercatalog', method='POST')
def broadcasterCatalog():
    """
        params:
            ownerID 
            stimulusCallbackURL
    """   
    try:
        rawRequest = request.POST.dict 
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        try:
            entityID = jsonPayload["entityID"]
            entityUUID = uuid.UUID(entityID)
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Request has no valid entityID post patameter")
        except Exception as e:
            raise e
        
        try:
            entityType = rmlEngine.api.getEntityMemeType(entityUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %entityID)
        
        if (entityType != "Agent.Owner") and (entityType != "Agent.Creator"):
            raise Exceptions.TemplatePathError("entityID parameter value %s refers to an entity of type %s.  Only data owners and data creators (Agent.Owner and Agent.Creator) may subscribe to broadbasters" %(entityID, entityType))
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Data Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.Molecule", "data", technicalName, creatorID, ownerID, rawRequest)    
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)    
        returnStr = "%s" %newUUID
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg    

    
    

@route('/modeling/addDataMolecule/<technicalName>/<creatorID>/<ownerID>', method='POST')
def addDataMolecule(technicalName, creatorID, ownerID):
    """
        params:
            description 
            urlType (URLType)
            postParameters (POSTParameters)
            postParameterTypes (POSTParameterTypes)
            postParameterDescriptions (POSTParameterDescriptions)
    """    
    try:
        rawRequest = request.POST.dict 
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Data Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.Molecule", "data", technicalName, creatorID, ownerID, rawRequest)    
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)    
        returnStr = "%s" %newUUID
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 



@route('/modeling/addEvent/<moduleName>/<eventName>', method='POST')
def addEvent(moduleName, eventName):
    """
        description - A description of the event to be supported   
        
    """

    try:
        global rmlEngine
        rawRequest = request.POST.dict
        eventCreationReport = rmlEngine.api.sourceMemeCreate(eventName, moduleName, "Agent.EventMM")
        unusedReturn = rmlEngine.api.sourceMemeSetSingleton(eventCreationReport["memeID"], True)
        
        try:
            description = rawRequest["description"]
            unusedReturn = rmlEngine.api.sourceMemePropertySet(eventCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(eventCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(eventCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = rmlEngine.api.sourceMemeCompile(eventCreationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(eventCreationReport["memeID"])
        
        response.body = json.dumps(eventCreationReport) 
        response.status = 200
        return response
    except Exception:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        abort(500, "%s %2" %(errorID, errorMsg))
        
        
    



@route('/modeling/addIntent/<moduleName>/<intentName>', method='POST')
def addIntent(moduleName, intentName):
    """
        description - A description of the intent to be supported  
        
    """
    try:
        global rmlEngine
        rawRequest = request.POST.dict
        intentCreationReport = rmlEngine.api.sourceMemeCreate(intentName, moduleName, "Agent.IntentMM")
        unusedReturn = rmlEngine.api.sourceMemeSetSingleton(intentCreationReport["memeID"], True)
        
        try:
            unusedReturn = rmlEngine.api.sourceMemePropertySet(intentCreationReport["memeID"], "description", rawRequest["description"])
        except:
            pass
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(intentCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(intentCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = rmlEngine.api.sourceMemeCompile(intentCreationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(intentCreationReport["memeID"])
        
        response.body = json.dumps(intentCreationReport)  
        response.status = 200
        return response
    except Exception:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        abort(500, "%s %2" %(errorID, errorMsg))
        


@route('/modeling/addIntentMolecule/<technicalName>/<creatorID>/<ownerID>', method='POST')
def addIntentMolecule(technicalName, creatorID, ownerID):
    """
        params:
            description 
            urlType (URLType)
            postParameters (POSTParameters)
            postParameterTypes (POSTParameterTypes)
            postParameterDescriptions (POSTParameterDescriptions)
    """  
      
    try:
        rawRequest = request.POST.dict 
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Intent Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.IntentMolecule", "intent", technicalName, creatorID, ownerID, rawRequest)   
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)  
        response.body = json.dumps({"entityUUID": newUUID})   
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    
    

        
        
        
        
@route('/modeling/addMolecueNode/<technicalName>/<moleculeID>', method='GET')
def addMolecueNode(technicalName, moleculeID):
    """
        params:
            description 
            urlType (URLType)
            postParameters (POSTParameters)
            postParameterTypes (POSTParameterTypes)
            postParameterDescriptions (POSTParameterDescriptions)
    """    
    try:
        newUUID = rmlEngine.api.createEntityFromMeme("Agent.MoleculeNode")
        unusedReturnResults = rmlEngine.api.addEntityLink(moleculeID, newUUID)
        unusedReturnResults = rmlEngine.api.setEntityPropertyValue(newUUID, "technicalName", technicalName)       
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    
    
@route('/modeling/addPage/<moduleName>/<memeName>', method='GET')
def addPage(moduleName, memeName):
    try:
        creationReport = rmlEngine.api.sourceMemeCreate(memeName, moduleName, "Agent.Page")
        unusedReturn = rmlEngine.api.sourceMemeSetSingleton(creationReport["memeID"], True)
        unusedReturn = rmlEngine.api.sourceMemeCompile(creationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(creationReport["memeID"])
        
        response.body = json.dumps(creationReport) 
        response.status = 200
        return response     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    
    
@route('/modeling/addScope/<moduleName>/<memeName>', method='POST')
def addScope(moduleName, memeName):
    '''
        pages - the list of page memes that this 
    '''
    try:
        rawRequest = request.POST.dict
        #First make sure that the pases are valid
        pages = []
        try:
            pages = rawRequest['pages']
        except:
            pass
        try:
            for pageMeme in pages:
                unusedReturn = rmlEngine.api.createEntityFromMeme(pageMeme)
        except Exception as ex:
            fullerror = sys.exc_info()
            errorMsg = str(fullerror[1])
            tb = sys.exc_info()[2]
            raise Exceptions.POSTArgumentError(ex).with_traceback(tb)
        
        creationReport = rmlEngine.api.sourceMemeCreate(memeName, moduleName, "Agent.Scope")
        unusedReturn = rmlEngine.api.sourceMemeSetSingleton(creationReport["memeID"], True)
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(creationReport["memeID"], "Agent.DefaultPage", 1)
        
        for pageMeme in pages:
            unusedReturn = rmlEngine.api.sourceMemeMemberAdd(creationReport["memeID"], pageMeme, 1)
        
        unusedReturn = rmlEngine.api.sourceMemeCompile(creationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(creationReport["memeID"])
        
        response.body = json.dumps(creationReport) 
        response.status = 200
        return response     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
        



@route('/modeling/addServiceMolecule/<technicalName>/<creatorID>/<ownerID>', method='POST')
def addServiceMolecule(technicalName, creatorID, ownerID):
    """
        params:
            description 
            urlType (URLType)
            postParameters (POSTParameters)
            postParameterTypes (POSTParameterTypes)
            postParameterDescriptions (POSTParameterDescriptions)
    """    
    try:
        rawRequest = request.POST.dict
        
        try:
            callbackURL = rawRequest["CallbackURL"]
        except KeyError:
            raise Exceptions.MismatchedPOSTParametersError("Intent Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e       
         
        newUUID = addMolecule("Agent.ServiceMolecule", "service", technicalName, creatorID, ownerID, rawRequest) 
        unusedPropertySetResults = rmlEngine.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)       
        response.body = json.dumps({"entityUUID": newUUID})
        response.status = 200
        return response       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    


@route('/modeling/addTag/<moduleName>/<tagName>', method='POST')
def addTag(moduleName, tagName):
    """
        description - description of the tag  
        
    """

    try:
        rawRequest = request.POST.dict 
        
        try:
            description = rawRequest["description"]
            tagCreationReport = rmlEngine.api.sourceMemeCreate(tagName, moduleName, "Agent.TagMM")
            unusedReturn = rmlEngine.api.sourceMemeSetSingleton(tagCreationReport["memeID"], True)
            unusedReturn = rmlEngine.api.sourceMemePropertySet(tagCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        try:
            parentTag = rawRequest["parentTag"]
            tagCreationReport = rmlEngine.api.sourceMemeCreate(tagName, moduleName, "Agent.TagMM")
            unusedReturn = rmlEngine.api.sourceMemeSetSingleton(tagCreationReport["memeID"], True)
            unusedReturn = rmlEngine.api.sourceMemePropertySet(tagCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(tagCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = rmlEngine.api.sourceMemeMemberAdd(tagCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = rmlEngine.api.sourceMemeCompile(tagCreationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(tagCreationReport["memeID"])
        
        response.body = json.dumps(tagCreationReport)  
        response.status = 200
        return response
    except Exception:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        abort(500, "%s %2" %(errorID, errorMsg))
        
        
 




@route('/modeling/getAvailableIntents/<moleculeID>', method='GET')
def getMoleculeTags(moleculeID):
    '''
        Get the tags attached to this molecule
    '''
    try:
        returnList = []
        tagList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(moleculeID, '*::Agent.TagMM')
        for tagID in tagList:
            tagMM = rmlEngine.api.getEntityMemeType(tagID)
            returnList.append(tagMM)
        
        returnJSON = json.loads(returnList)
        
        response.body = json.dumps(returnJSON) 
        response.status = 200
        return response     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg  
    



@route('/modeling/getIntentCatalog', method='GET')
def getIntentCatalog():
    '''
        Get all intents and their descriptions
    '''
    try:
        
        intentEntityList =rmlEngine.api.getEntitiesByMetaMemeType("Agent.IntentMM")
        intentMemeDict = {}
        for intentEntityID in intentEntityList:
            entityMemetype =rmlEngine.api.getEntityMemeType(intentEntityID)
            entityDescription =rmlEngine.api.getEntityPropertyValue(intentEntityID, "description")
            intentMemeDict[entityMemetype] = {"intentID" : intentEntityID, "intentDescription" : entityDescription}
        returnJSON = json.loads(intentMemeDict)
        
        response.body = json.dumps(returnJSON) 
        response.status = 200
        return response     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg    
    
    

    
@route('/modeling/getAvailableIntents/<moleculeID>', method='GET')
def getAvailableIntents(moleculeID):
    '''
        Get all intents that are available to the current data molecule
        
        Algorithm:
        First, get any service molecules with a valid traverse path from the data molecule.
        Starting at the data molecule, that is: Agent.MoleculeNode::*::Agent.MoleculeNode::Agent.ServiceMolecule
        
        Also, get its tags, via metameme traverse: Agent.Landmark::Agent.TagMM 
        
        For each service molecule:
        Get its required tags, via metameme traverse: Agent.Landmark::Agent.TagMM
        If all of the intent service tags are in the data molecule tags, we are good.
        
         
    '''
    try:
        availableIntents = {}
        serviceMoleculeList =rmlEngine.api.getLinkCounterpartsByType(moleculeID, "Agent.MoleculeNode::*::Agent.MoleculeNode::Agent.ServiceMolecule")
        dataMoleculeTagList =rmlEngine.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.Landmark::Agent.TagMM")
        dataMoleculeTagSet = set(dataMoleculeTagList)
        for serviceMoleculeID in serviceMoleculeList:
            serviceMolecule =rmlEngine.api.getEntityMemeType(serviceMoleculeID)
            serviceMoleculeTagList =rmlEngine.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, "Agent.Landmark::Agent.TagMM")
            serviceMoleculeTagSet = set(serviceMoleculeTagList)
            if serviceMoleculeTagSet.issubset(dataMoleculeTagSet):
                connectedIntentList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.IntentMM')
                for connectedIntentID in connectedIntentList:
                    intentMeme =rmlEngine.api.getEntityMemeType(connectedIntentID)
                    intentDescription =rmlEngine.api.getEntityPropertyValue(connectedIntentID, "description")
                    try:
                        unusedIntentMemeDict = availableIntents[intentMeme]
                        availableIntents[intentMeme][serviceMolecule] = {"intentID" : connectedIntentID, "intentDescription" : intentDescription}
                    except KeyError:
                        availableIntents[intentMeme] = {serviceMolecule : {"intentID" : connectedIntentID, "intentDescription" : intentDescription}}

        returnJSON = json.loads(availableIntents)
        
        response.body = json.dumps(returnJSON)  
        response.status = 200
        return response     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg    
    
    
    
@route('/modeling/getTagCatalog', method='GET')
def getTagCatalog():
    '''
        Get all available tags as a JSON, including the data type and URLDefinition meme if appropriate
    '''
    try:
        returnDict = {}
        tagList = rmlEngine.api.getEntitiesByMetaMemeType('Agent.TagMM')
        for tagID in tagList:
            tagMM = rmlEngine.api.getEntityMemeType(tagID)
            dataType = rmlEngine.api.getEntityPropertyValue(tagID, "DataType")
            if dataType in ["urlPOST", "urlGET"]:
                fullDefPath = rmlEngine.api.getEntityPropertyValue(tagID, "URLDefinitionPath")
                splitDefPath = fullDefPath.split("::")
                dataTypeDict = {"DataType" : dataType, "URLDefinitionMeme" : splitDefPath[1]}
            else:
                dataTypeDict = {"DataType" : dataType}
            returnDict[tagMM] = dataTypeDict

        returnJSON = json.loads(returnDict)
        
        response.body = json.dumps(returnJSON)  
        response.status = 200
        return response    
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg   
    
    
    
@route('/modeling/getTagList', method='GET')
def getTagList():
    '''
        Get all available tags, with just the Meme names
    '''
    try:
        returnList = []
        tagList = rmlEngine.api.getEntitiesByMetaMemeType('Agent.TagMM')
        for tagID in tagList:
            tagMM = rmlEngine.api.getEntityMemeType(tagID)
            returnList.append(tagMM)
        
        returnJSON = json.loads(returnList)
        
        response.body = json.dumps(returnJSON)  
        response.status = 200
        return response    
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg  
    
    
    
@route('/modeling/offerIntentService/<intentServiceMoleculeID>/<intent>', method='GET')
def offerIntentService(intentServiceMoleculeID, intent):
    '''
        Declare that an intent service can support an intent.. Only one intent can be supported at a time
    '''
    try:
        #First, check to see that the desired Intent exists.
        intentEntityID = None
        try:
            intentEntityID = rmlEngine.api.createEntityFromMeme(intent)
            intentEntityType = rmlEngine.api.getEntityMetaMemeType(intentEntityID)
            if intentEntityType != 'Agent.IntentMM':
                errorMessage = "%s is not an intent" %intent
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid Intent %s" %intent
            raise Exceptions.IntentError(errorMessage)
        
        #And only intent service molecules can support intents.
        try:
            intentMoleculeType = rmlEngine.api.getEntityMemeType(intentServiceMoleculeID)
            if intentMoleculeType != 'Agent.IntentMolecule':
                errorMessage = "%s is not an intent service molecule." %intentServiceMoleculeID
                raise Exceptions.IntentServiceMoleculeError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid Intent %s" %intent
            raise Exceptions.IntentError(errorMessage)
        
        #Next, check to see that we don't already support an intent.  If we do, that support will have to be revoked first.
        existingIntentList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(intentServiceMoleculeID, 'Agent.IntentMM')
        if len(existingIntentList) > 0:
            existingMemeType = rmlEngine.api.getEntityMemeType(existingIntentList[0])
            errorMessage = "Intent Service molecule %s already supports intent %s.  Support for %s can't be declared unless prior support is revoked" %(intentServiceMoleculeID, existingMemeType, intent)
            raise Exceptions.RedundantIntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = rmlEngine.api.addEntityLink(intentServiceMoleculeID, intentEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        response.body = json.dumps(returnResultsJson)
        response.status = 200
        return response
   
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
@route('/modeling/revokeIntentService/<intentServiceMoleculeID>', method='GET')
def revokeIntentService(intentServiceMoleculeID):
    '''
        Remove any intent servicing form an intent service entity
    '''
    try:
        intentMoleculeType = rmlEngine.api.getEntityMemeType(intentServiceMoleculeID)
        if intentMoleculeType != 'Agent.IntentMolecule':
            errorMessage = "%s is not an intent service molecule." %intentServiceMoleculeID
            raise Exceptions.IntentServiceMoleculeError(errorMessage)
        
        #Next, check to see that we don't already support an intent.  If we do, that support will have to be revoked first.
        existingIntentList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(intentServiceMoleculeID, 'Agent.IntentMM')
        if len(existingIntentList) < 1:
            returnResults = "Intent Service molecule %s has no declared intents" %(intentServiceMoleculeID)
            raise Exceptions.IntentError(errorMessage)
        else:
            for existingIntentID in existingIntentList:
                returnResults = rmlEngine.api.removeEntityLink(intentServiceMoleculeID, existingIntentID)
 
        returnResultsJson = json.dumps(returnResults)
        
        response.body = json.dumps(returnResultsJson)
        response.status = 200
        return response
   
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
      
    


@route('/modeling/addProperty/<moduleName>/<propertyName>', method='POST')
def addProperty(moduleName, propertyName):
    """
        description - description of the property  
        
    """

    try:
        rawRequest = request.POST.dict 
        
        try:
            dataType = rawRequest["dataType"]
            validTypes = ["Str", 
                    "Int", 
                    "Num", 
                    "StrList", 
                    "IntList", 
                    "NumList", 
                    "StrKeyValuePairList", 
                    "IntKeyValuePairList", 
                    "IntKeyValuePairList"] 
            if dataType not in validTypes:
                raise Exceptions.UndefinedValueListError("Property %s has data type %s") %(propertyName, dataType)
            tagCreationReport = rmlEngine.api.sourceMemeCreate(propertyName, moduleName, "Agent.RESTPropertyMM")
            unusedReturn = rmlEngine.api.sourceMemeSetSingleton(tagCreationReport["memeID"], True)
            unusedReturn = rmlEngine.api.sourceMemePropertySet(tagCreationReport["memeID"], "dataType", dataType)
        except KeyError as e:
            raise Exceptions.POSTArgumentError("Property %s needs a data type") %propertyName
        except Exception as e:
            raise e
        
        try:
            description = rawRequest["description"]
            unusedReturn = rmlEngine.api.sourceMemePropertySet(tagCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        unusedReturn = rmlEngine.api.sourceMemeCompile(tagCreationReport["memeID"], False)
        unusedReturn = rmlEngine.api.createEntityFromMeme(tagCreationReport["memeID"])
        
        returnStr = "%s" %tagCreationReport["memeID"]  
        response.status = 200
        return returnStr
    except Exception:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        abort(500, "%s %2" %(errorID, errorMsg))
        
        
        
        
@route('/modeling/getPropertyCatalog', method='GET')
def getPropertyCatalog():
    '''
        Get all properties, with just the Meme names
    '''
    try:
        
        propertyEntityList =rmlEngine.api.getEntitiesByMetaMemeType("Agent.RESTPropertyMM")
        propertyMemeDict = {}
        for propertyEntityID in propertyEntityList:
            entityMemetype = rmlEngine.api.getEntityMemeType(propertyEntityID)
            entityDescription = rmlEngine.api.getEntityPropertyValue(propertyEntityID, "description")
            propertyMemeDict[entityMemetype] = {"propertyID" : propertyEntityID, "propertyDescription" : entityDescription}
        returnJSON = json.loads(propertyMemeDict)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    
    

@route('/modeling/getPropertyList', method='GET')
def getPropertyList():
    '''
        Get all available tags, with just the Meme names
    '''
    try:
        returnList = []
        propertyEntityList = rmlEngine.api.getEntitiesByMetaMemeType('Agent.RESTPropertyMM')
        for propertyEntityID in propertyEntityList:
            entityMemetype = rmlEngine.api.getEntityMemeType(propertyEntityID)
            returnList.append(entityMemetype)
        
        returnJSON = json.loads(returnList)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr    
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
    
@route('/modeling/assignTagProperty/<tagName>/<propertyName>', method='GET')
def assignTagProperty(tagName, propertyName):
    '''
        Assign a property to a tag
    '''
    try:
        #First, check to see that the desired tag exists.
        tagEntityID = None
        try:
            tagEntityID = rmlEngine.api.createEntityFromMeme(tagName)
            tagEntityType = rmlEngine.api.getEntityMetaMemeType(tagEntityID)
            if tagEntityType != 'Agent.TagMM':
                errorMessage = "%s is not a tag" %tagName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %tagName
            raise Exceptions.IntentError(errorMessage)
        
        #First, check to see that the desired property name exists.
        propertyEntityID = None
        try:
            propertyEntityID = rmlEngine.api.createEntityFromMeme(propertyName)
            propertyEntityType = rmlEngine.api.getEntityMetaMemeType(propertyEntityID)
            if propertyEntityType != 'Agent.RESTPropertyMM':
                errorMessage = "%s is not a property" %propertyName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %propertyName
            raise Exceptions.IntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = rmlEngine.api.addEntityLink(tagEntityID, propertyEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr   
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
    
@route('/modeling/removeTagProperty/<tagName>/<propertyName>', method='GET')
def removeTagProperty(tagName, propertyName):
    '''
        Assign a property to a tag
    '''
    try:
        #First, check to see that the desired tag exists.
        tagEntityID = None
        try:
            tagEntityID = rmlEngine.api.createEntityFromMeme(tagName)
            tagEntityType = rmlEngine.api.getEntityMetaMemeType(tagEntityID)
            if tagEntityType != 'Agent.TagMM':
                errorMessage = "%s is not a tag" %tagName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %tagName
            raise Exceptions.IntentError(errorMessage)
        
        #First, check to see that the desired property name exists.
        propertyEntityID = None
        try:
            propertyEntityID = rmlEngine.api.createEntityFromMeme(propertyName)
            propertyEntityType = rmlEngine.api.getEntityMetaMemeType(propertyEntityID)
            if propertyEntityType != 'Agent.RESTPropertyMM':
                errorMessage = "%s is not a property" %propertyName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %propertyName
            raise Exceptions.IntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = rmlEngine.api.addEntityLink(tagEntityID, propertyEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr   
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
@route('/modeling/getMoleculeAPIDefinition/<moleculeID>', method='GET')
def getMoleculeAPIDefinition(moleculeID):
    '''
        Get the full list of properties that a data molecule can be queried about.       
    '''
    try:
        availableAPIProperties = {}
        propertyEntityList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.MoleculeNodeMM::Agent.TagMM::Agent.RESTPropertyMM")
        for propertyEntityID in propertyEntityList:
            entityMemetype = rmlEngine.api.getEntityMemeType(propertyEntityID)
            entityDescription = rmlEngine.api.getEntityPropertyValue(propertyEntityID, "description")
            availableAPIProperties[entityMemetype] = {"propertyID" : propertyEntityID, "propertyDescription" : entityDescription}
        returnJSON = json.loads(availableAPIProperties)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
    
    
    
@route('/modeling/declareEvent/<moleculeID>/<eventName>', method='GET')
def declareEvent(moleculeID, eventName):
    '''
        Get the full list of properties that a data molecule can be queried about.       
    '''
    try:

        eventEntityList = rmlEngine.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
         
        moleculeMemetype = rmlEngine.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
            
        returnResults = rmlEngine.api.addEntityLink(moleculeID, eventEntityList[0])
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %returnResultsJson  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 
    
    
    
    
@route('/modeling/disableEvent/<moleculeID>/<eventName>', method='GET')
def disableEvent(moleculeID, eventName):
    '''
        Get the full list of properties that a data molecule can be queried about.       
    '''
    try:

        eventEntityList = rmlEngine.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
        else:
            eventMM = rmlEngine.api.getEntityMetaMemeType(eventEntityList[0])
            if eventMM != "Agent.EventMM":
                raise Exceptions.MissingAgentError("The event parameter %s refers to an entity of metameme type is of type %s.  It should be of type Agent.EventMM") %(eventName, eventMM)

         
        moleculeMemetype = rmlEngine.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
            
        returnResults = rmlEngine.api.removeEntityLink(moleculeID, eventEntityList[0])
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %returnResultsJson  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 


    
    
    
    
@route('/modeling/attachEventListener/<moleculeID>/<eventName>', method='GET')
def attachEventListener(moleculeID, eventName):
    '''
        Get the full list of properties that a data molecule can be queried about.       
    '''
    try:

        eventEntityList = rmlEngine.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
        else:
            eventMM = rmlEngine.api.getEntityMetaMemeType(eventEntityList[0])
            if eventMM != "Agent.EventMM":
                raise Exceptions.MissingAgentError("The event parameter %s refers to an entity of metameme type is of type %s.  It should be of type Agent.EventMM") %(eventName, eventMM)
         
        moleculeMemetype = rmlEngine.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.ServiceMolecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.ServiceMolecule") %(moleculeID, moleculeMemetype)
        
        
            
        returnResults = rmlEngine.api.addEntityLink(moleculeID, eventEntityList[0])
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %returnResultsJson  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 




@route('/modeling/getEventListeners/<moleculeID>', method='GET')
def getEventListeners(moleculeID):
    '''
        Get the full catalog of the services that are listening to the current molecule's events.       
    '''
    try:
        moleculeMemetype = rmlEngine.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
        
        availableEventListeners = {}
        serviceMoleculeList = rmlEngine.api.getLinkCounterpartsByType(moleculeID, "Agent.MoleculeNode::*::Agent.MoleculeNode::Agent.ServiceMolecule")
        dataMoleculeTagList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.Landmark::Agent.TagMM")
        dataMoleculeTagSet = set(dataMoleculeTagList)
        for serviceMoleculeID in serviceMoleculeList:
            serviceMoleculeTagList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, "Agent.Landmark::Agent.TagMM")
            serviceMoleculeTagSet = set(serviceMoleculeTagList)
            if serviceMoleculeTagSet.issubset(dataMoleculeTagSet):
                connectedEventList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.EventMM')
                for connectedEventID in connectedEventList:
                    connectedDataList = rmlEngine.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.Molecule') 
                    if moleculeID in connectedDataList:
                        eventMeme = rmlEngine.api.getEntityMemeType(connectedEventID)
                        eventDescription = rmlEngine.api.getEntityPropertyValue(serviceMoleculeID, "description")
                        eventTechnicalName = rmlEngine.api.getEntityPropertyValue(serviceMoleculeID, "technicalName")
                        try:
                            unusedIntentMemeDict = availableEventListeners[eventMeme]
                            availableEventListeners[eventMeme][eventTechnicalName] = {"eventDescription" : eventDescription}
                        except KeyError:
                            availableEventListeners[eventMeme] = {eventTechnicalName : {"eventDescription" : eventDescription}}
        returnResultsJson = json.dumps(availableEventListeners)
        
        returnStr = "%s" %returnResultsJson  
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg 


    


#####################################
##  Runtime Intentsity Actions
#####################################

@route('/action', method='POST')
def action(ownerID, subjectID, nodeID):
    """  
        A Trigger an event 
        Fires an Intentsity.Event action, with the 
    """
    global rmlEngine
    try:
        rawRequest = request.POST.dict
        actionID = rawRequest["actionID"]
        ownerID = rawRequest["ownerID"]
        objectID = rawRequest["creatorID"]
        subjectID = rawRequest["moleculeID"]
        
        rtparams = []
        try:
            rtparams = rawRequest["parameters"]
        except: pass
        
        intentID = None
        try:
            intentID = rawRequest["intentID"]
            rtparams["intentID"] = intentID
        except: pass
        
        eventMoleculeNodes = []
        try:
            eventMoleculeNodes = rawRequest["eventMoleculeNodes"]
            rtparams["eventMoleculeNodes"] = eventMoleculeNodes
        except: pass
        
        
        #test that the entities exist
        unusedSubjectTemplate = rmlEngine.api.getEntityMemeType(subjectID)
        unusedControllerTemplate = rmlEngine.api.getEntityMemeType(ownerID)
        unusedNodeTemplate = rmlEngine.api.getEntityMemeType(nodeID)
        
        actionID = "Intentsity.Event"
        ownerID = ownerID
        subjectID = subjectID
        objectID = None
        rtparams = {'nodeID' : nodeID} 
        
        #get any tags attached to the node

        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, subjectID, objectID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        returnStr = "Action posted"
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action %s.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr

    
@route('/fireevent/<ownerID>/<subjectID>/<nodeID>', method='GET')
def fireevent(ownerID, subjectID, nodeID):
    """  
        A Trigger an event 
        Fires an Intentsity.Event action, with the 
    """
    global rmlEngine
    try:
        #test that the entities exist
        unusedSubjectTemplate = rmlEngine.api.getEntityMemeType(subjectID)
        unusedControllerTemplate = rmlEngine.api.getEntityMemeType(ownerID)
        unusedNodeTemplate = rmlEngine.api.getEntityMemeType(nodeID)
        
        actionID = "Intentsity.Event"
        ownerID = ownerID
        subjectID = subjectID
        objectID = None
        rtparams = {'nodeID' : nodeID} 
        
        #get any tags attached to the node

        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, subjectID, objectID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        returnStr = "Action posted"
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action %s.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
@route('/invokeintent/<moleculeID>/<intentID>', method='GET')
def invokeintent(moleculeID, intentID):
    """  A Trigger an intent.  moleculeID is calling molecule. intentID is the registered intent """
    
    try:
        global rmlEngine
        actionID = "Intentsity.Intent"
        ownerID = None
        rtparams = {} 
        
        #test that the entities exist
        unusedEntityTemplateS = rmlEngine.api.getEntityMemeType(moleculeID)
        unusedEntityTemplateS = rmlEngine.api.getEntityMemeType(intentID)
        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, moleculeID, intentID, ownerID)
        rmlEngine.aQ.put(actionInvocation)
        
        returnStr = "Action posted"
        response.status = 200
        return returnStr     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action %s.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
@route('/stimuli/<ownerID>', method='GET')
def getStimulusReports(ownerID):
    """  Collect current items in a particular broadcast queue """
    
    try:
        try:
            ownerUUID = uuid.UUID(ownerID)
        except Exception as e:
            raise e
        
        try:
            ownerEntityType = rmlEngine.api.getEntityMemeType(ownerUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %ownerID)
        
        try:
            ownerEntityType = rmlEngine.api.getEntityMemeType(ownerUUID)
        except Exception as e:
            raise Exceptions.NoSuchEntityError("ownerID parameter value %s does not exist." %ownerID)
        
        if ownerEntityType != "Agent.Owner":
            raise Exceptions.TemplatePathError("ownerID parameter value %s does not refer to a valid data owner" %ownerID)
        
        if ownerUUID not in Engine.broadcasterRegistrar.broadcasterIndex:
            errorMsg = "No broadcast queue assigned for data owner %s" %ownerID
            raise Exceptions.NoSuchBroadcasterError(errorMsg)
        else:
            #pop the report from myQueue and fire self.onStimulusReport()
            reportList = []
            while not Engine.broadcasterRegistrar.broadcasterIndex[broadcasterID].empty():
                try:
                    stimulusReport = Engine.broadcasterRegistrar.broadcasterIndex[broadcasterID].get_nowait()
                    reportList.append(stimulusReport)
                except queue.Empty:
                    #ok.  Concurrency is being squirrelly.  The queue testes as not empty, but ends up empty.
                    #  Let's not burn the world down over this  
                    break
            response.status = 200
            return json.dumps(reportList)     
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to retrieve stimuli %s.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    

    
    

    
        
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Intentsity")

    parser.add_argument("-p", "--port", type=int, help="|Int| The start of the port range for Intentsity")
    
    args = parser.parse_args()
    
    if args.port:
        basePort = args.port

    run(host='localhost', port=basePort)