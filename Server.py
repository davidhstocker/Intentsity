'''
Created on June 13, 2018

@author: David Stocker
'''

########  Generated Imports - Do not edit  ####################
from bottle import route, run, request, template, abort, static_file, response
import json
import time
import os
import sys
import threading
import queue
from os.path import expanduser
from Intentsity import Engine
from Intentsity import Exceptions
import Graphyne.Graph as Graph
        



class IntentTagSchema(object):  
    """
        A small helper class for determining what tags and interfaces an intent requires
    """ 
    tags = {}
    requiredInterfaces = []  #Any tags that
    
    def __init__(self, intentName):
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
    tags = {}
    requiredInterfaces = []  #Any tags that
    
    def __init__(self, eventName):
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
            if (engineStatus.busy == False) and (engineStatus.serverOn == False):
                engineStatus.busyOn()
                engineStatus.clearAlert()
                global engineStartQueue
                startParams = engineStartQueue.get_nowait()
                rmlEngine.setPersistence(startParams[0], startParams[1])   
                    
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
            elif engineStatus.serverOn == False:
                engineStartQueue.push([202, "Command ignored.  Server already running"])
            elif engineStatus.serverOn == False:
                engineStartQueue.push([202, "Command ignored.  Server in busy state"])
            else:
                engineStartQueue.push([202, "Command ignored.  Server already in startup"]) 
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
        unusedReturnResults = Engine.Graph.api.setEntityPropertyValue(entityUUID, "URLType", urlType)
        '''
        
        'list'
        #set appropriate properties
        if rHandlerParameters is not None:
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "HandlerParameters", rHandlerParameters['parameters'], 'list')
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "HandlerParameterDescriptions", rHandlerParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "HandlerParameters")
            except: 
                pass
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "HandlerParameterDescriptions")
            except: 
                pass            

        
        if rReturnParameters is not None:
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "ReturnParameters", rReturnParameters['parameters'], 'list')
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "ReturnParameterTypes", rReturnParameters['types'], 'list')
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "ReturnParameterDescriptions", rReturnParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "ReturnParameters")
            except: 
                pass
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "ReturnParameterTypes")
            except: 
                pass  
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "ReturnParameterDescriptions")
            except: 
                pass  
            
        if rPostParameters is not None:
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "POSTParameters", rPostParameters['parameters'], 'list')
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "POSTParameterTypes", rPostParameters['types'], 'list')
            unusedReturnResults = Engine.Graph.api.sourceMemePropertySet(memePath, "POSTParameterDescriptions", rPostParameters['descriptions'], 'list')
        else:
            #Remove these properties if they are in the meme.  
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "POSTParameters")
            except: 
                pass
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "POSTParameterTypes")
            except: 
                pass  
            try:
                unusedReturnResults = Engine.Graph.api.sourceMemePropertyRemove(memePath, "POSTParameterDescriptions")
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
        newUUID = Engine.Graph.api.createEntityFromMeme(memeType)
        
        #Agent.Molecule is created with the default controller.  Break the link and replace it with the desired controller
        defaultControllerUUID = Engine.Graph.api.createEntityFromMeme("Agent.DefaultController")
        unusedReturnResults = Engine.Graph.api.removeEntityLink(newUUID, defaultControllerUUID)
        unusedReturnResults = Engine.Graph.api.addEntityLink(newUUID, ownerID)
        unusedReturnResults = Engine.Graph.api.addEntityLink(newUUID, creatorID)
        unusedReturnResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "technicalName", technicalName)
        
        #This property is purely optional and won't affect entity creation    
        try:
            description = rawRequest['description']
            unusedReturnResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "description", description)
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
        if engineStatus.serverOn == True:
            response.status = 200
            returnStr = "Intentsity Engine Status: Ready"
        else:
            response.status = 503
            returnStr = "Intentsity Engine Status: Starting"
        return returnStr
    except Exception as e:
        response.status = 500
        returnStr = "Intentsity Engine Status: Failed to Start"
        return returnStr



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
        
        #Set up the persistence of rmlEngine.  It defaults to no persistence
        global engineStartQueue
        engineStartQueue.put([dbConnectionString, persistenceType])
        starter = EngineStarter()
        starter.run()
        
        time.sleep(3.0)  #Give the EngineStarter instance a couple of seconds to read the queue and respond
        returnParams = engineStartQueue.get_nowait()
                
        response.status = returnParams[0]
        return(returnParams[1])
    except json.decoder.JSONDecodeError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start due to malformed json payload in POST body:  %s, %s." %(errorID, errorMsg)
        response.status = 400
        return returnStr
    except ValueError as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start:  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return returnStr
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Intentsity failed to start:  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
    
@route('/admin/stop')
def stopServer():
    global rmlEngine
    global engineStatus
    try:
        if (engineStatus.busy == False) and (engineStatus.serverOn == True):
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Stopped..."
            response.status = 200
            return returnStr
        elif (engineStatus.busy == True) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server in bootstrap.  Please wait until running before stopping or call /admin/forcestop API handler"
            response.status = 202
            return returnStr
        elif (engineStatus.busy == False) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server was not started."
            response.status = 202
            return returnStr
        else:
            #This really should not happen, unless we've been careful  about the busy state handling.
            returnStr = "Command ignored.  Server in busy state"
            response.status = 202
            return returnStr
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to stop Intentsity engine.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
    
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
            return returnStr
        elif (engineStatus.busy == True) and (engineStatus.serverOn == False):
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Force stopped server in bootstrap..."
            response.status = 200
            return returnStr
        elif (engineStatus.busy == False) and (engineStatus.serverOn == False):
            returnStr = "Command ignored.  Server was not started."
            response.status = 202
            return returnStr
        else:
            #This really should not happen, unless we've been careful  about the busy state handling.
            #  But this gives us a rock crusher workaround for hung state servers
            engineStatus.toggleOff()
            engineStatus.clearAlert()
            rmlEngine = Engine.Engine()
            returnStr = "Force stopped server in unknown busy state..."
            response.status = 200
            return returnStr
    except Exception as unusedE:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to stop Intentsity engine.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr


###############################
##  Main Engine 
###############################

@route('/postaction', method='POST')
def postAction():
    """  A generic action invocation """
    
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
        Engine.aQ.put(actionInvocation)
        
        returnStr = "Action posted"
        response.status = 200
        return returnStr
    except Exceptions.InvalidControllerError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return returnStr  
    except Exceptions.MissingActionError:
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action.  %s, %s" %(errorID, errorMsg)
        response.status = 400
        return returnStr       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to post action %s.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr


##########################
##  Modeling (Generic)
##########################
    
@route('/modeling/addEntityLink/<sourceEntityID>/<targetEntityID>', method='GET')
def addEntityLink(sourceEntityID, targetEntityID):
    
    try:
        returnResults = Engine.Graph.api.addEntityLink(sourceEntityID, targetEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to link Entity %s to %s, % %s" %(sourceEntityID, targetEntityID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/createEntityFromMeme/<memePath>', method='GET')
def createEntityFromMeme(memePath):
    
    try:
        newUUID = Engine.Graph.api.createEntityFromMeme(memePath)
        
        returnStr = "%s" %(newUUID)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new %s Entity %s.  %s, %s" %(memePath, newUUID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
        
    
@route('/modeling/getClusterJSON/<entityUUID>', method='GET')
def getClusterJSON(entityUUID):
    
    try:
        newUUID = Engine.Graph.api.getClusterJSON(entityUUID)
        
        returnStr = "%s" %(newUUID)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to get cluster of Entity %s.  %s, %s" %(entityUUID, errorID, errorMsg)
        response.status = 500
        return returnStr



@route('/modeling/getEntityMemeType/<entityUUID>', method='GET')
def getEntityMemeType(entityUUID):
    
    try:
        newUUID = Engine.Graph.api.getEntityMemeType(entityUUID)
        
        returnStr = "%s" %(newUUID)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to get meme type of Entity %s.  %s, %s" %(entityUUID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
        
    
@route('/modeling/removeEntityLink/<sourceEntityID>/<targetEntityID>', method='GET')
def removeEntityLink(sourceEntityID, targetEntityID):
    
    try:
        returnResults = Engine.Graph.api.removeEntityLink(sourceEntityID, targetEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to remove link from Entity %s to %s, % %s" %(sourceEntityID, targetEntityID, errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
    
@route('/modeling/setEntityPropertyValue/<entityID>/<propName>/<propValue>', method='GET')
def setEntityPropertyValue(entityID, propName, propValue):
    
    try:
        returnResults = Engine.Graph.api.setEntityPropertyValue(entityID, propName, propValue)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to set property %s to %s on Entity %s, % %s" %(propName, propValue, entityID, errorID, errorMsg)
        response.status = 500
        return returnStr
        



#####################################
##  Modeling (Intentsity)
#####################################


#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/addCreator', method='POST')
def addCreator():
    
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
        
        newUUID = Engine.Graph.api.createEntityFromMeme("Agent.Creator")
        
        returnStr = "%s" %(newUUID)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Creator Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    


#Graph Methods - These handlers expose the Graphyene API via REST
@route('/modeling/addOwner', method='GET')
def addOwner():
    
    try:
        newUUID = Engine.Graph.api.createEntityFromMeme("Agent.Owner")
        
        returnStr = "%s" %(newUUID)
        response.status = 200
        return returnStr
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorID = str(fullerror[0])
        errorMsg = str(fullerror[1])
        returnStr = "Failed to create new Agent.Owner Entity.  %s, %s" %(errorID, errorMsg)
        response.status = 500
        return returnStr
    
    
    

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
            raise Exceptions.MismatchedPOSTParametersError("Intent Modlecule has no url.  Molecule not created")
        except Exception as e:
            raise e
        
        newUUID = addMolecule("Agent.Molecule", "data", technicalName, creatorID, ownerID, rawRequest)    
        unusedPropertySetResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)    
        returnStr = "%s" %newUUID
        response.status = 200
        return returnStr       
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
        rawRequest = request.POST.dict
        eventCreationReport = Engine.Graph.api.sourceMemeCreate(eventName, moduleName, "Agent.EventMM")
        unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(eventCreationReport["memeID"], True)
        
        try:
            description = rawRequest["description"]
            unusedReturn = Engine.Graph.api.sourceMemePropertySet(eventCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(eventCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(eventCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = Engine.Graph.api.sourceMemeCompile(eventCreationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(eventCreationReport["memeID"])
        
        returnStr = "%s" %eventCreationReport["memeID"]  
        response.status = 200
        return returnStr
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
        rawRequest = request.POST.dict
        intentCreationReport = Engine.Graph.api.sourceMemeCreate(intentName, moduleName, "Agent.IntentMM")
        unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(intentCreationReport["memeID"], True)
        
        try:
            unusedReturn = Engine.Graph.api.sourceMemePropertySet(intentCreationReport["memeID"], "description", rawRequest["description"])
        except:
            pass
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(intentCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(intentCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = Engine.Graph.api.sourceMemeCompile(intentCreationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(intentCreationReport["memeID"])
        
        returnStr = "%s" %intentCreationReport["memeID"]  
        response.status = 200
        return returnStr
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
        unusedPropertySetResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)     
        returnStr = "%s" %newUUID
        response.status = 200
        return returnStr       
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
        newUUID = Engine.Graph.api.createEntityFromMeme("Agent.MoleculeNode")
        unusedReturnResults = Engine.Graph.api.addEntityLink(moleculeID, newUUID)
        unusedReturnResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "technicalName", technicalName)       
        returnStr = "%s" %newUUID
        response.status = 200
        return returnStr       
    except Exception as unusedE: 
        fullerror = sys.exc_info()
        errorMsg = str(fullerror[1])
        response.status = 500
        return errorMsg
    
    
    
@route('/modeling/addPage/<moduleName>/<memeName>', method='GET')
def addPage(moduleName, memeName):
    try:
        creationReport = Engine.Graph.api.sourceMemeCreate(memeName, moduleName, "Agent.Page")
        unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(creationReport["memeID"], True)
        unusedReturn = Engine.Graph.api.sourceMemeCompile(creationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(creationReport["memeID"])
        
        returnStr = "%s" %creationReport["memeID"]  
        response.status = 200
        return returnStr     
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
                unusedReturn = Engine.Graph.api.createEntityFromMeme(pageMeme)
        except Exception as ex:
            fullerror = sys.exc_info()
            errorMsg = str(fullerror[1])
            tb = sys.exc_info()[2]
            raise Exceptions.POSTArgumentError(ex).with_traceback(tb)
        
        creationReport = Engine.Graph.api.sourceMemeCreate(memeName, moduleName, "Agent.Scope")
        unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(creationReport["memeID"], True)
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(creationReport["memeID"], "Agent.DefaultPage", 1)
        
        for pageMeme in pages:
            unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(creationReport["memeID"], pageMeme, 1)
        
        unusedReturn = Engine.Graph.api.sourceMemeCompile(creationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(creationReport["memeID"])
        
        returnStr = "%s" %creationReport["memeID"]  
        response.status = 200
        return returnStr     
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
        unusedPropertySetResults = Engine.Graph.api.setEntityPropertyValue(newUUID, "CallbackURL", callbackURL)       
        returnStr = "%s" %newUUID
        response.status = 200
        return returnStr       
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
            tagCreationReport = Engine.Graph.api.sourceMemeCreate(tagName, moduleName, "Agent.TagMM")
            unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(tagCreationReport["memeID"], True)
            unusedReturn = Engine.Graph.api.sourceMemePropertySet(tagCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        #scope - for now, we'll just take the default.  Strictly speaking, there should be rights management to scopes and views
        #    Future development
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(tagCreationReport["memeID"], "Agent.DefaultScope", 1)
        unusedReturn = Engine.Graph.api.sourceMemeMemberAdd(tagCreationReport["memeID"], "Agent.DefaultView", 1)
        
        unusedReturn = Engine.Graph.api.sourceMemeCompile(tagCreationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(tagCreationReport["memeID"])
        
        returnStr = "%s" %tagCreationReport["memeID"]  
        response.status = 200
        return returnStr
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
        tagList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(moleculeID, '*::Agent.TagMM')
        for tagID in tagList:
            tagMM = Engine.Graph.api.getEntityMemeType(tagID)
            returnList.append(tagMM)
        
        returnJSON = json.loads(returnList)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr     
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
        
        intentEntityList = Graph.api.getEntitiesByMetaMemeType("Agent.IntentMM")
        intentMemeDict = {}
        for intentEntityID in intentEntityList:
            entityMemetype = Graph.api.getEntityMemeType(intentEntityID)
            entityDescription = Graph.api.getEntityPropertyValue(intentEntityID, "description")
            intentMemeDict[entityMemetype] = {"intentID" : intentEntityID, "intentDescription" : entityDescription}
        returnJSON = json.loads(intentMemeDict)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr     
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
        serviceMoleculeList = Graph.api.getLinkCounterpartsByType(moleculeID, "Agent.MoleculeNode::*::Agent.MoleculeNode::Agent.ServiceMolecule")
        dataMoleculeTagList = Graph.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.Landmark::Agent.TagMM")
        dataMoleculeTagSet = set(dataMoleculeTagList)
        for serviceMoleculeID in serviceMoleculeList:
            serviceMolecule = Graph.api.getEntityMemeType(serviceMoleculeID)
            serviceMoleculeTagList = Graph.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, "Agent.Landmark::Agent.TagMM")
            serviceMoleculeTagSet = set(serviceMoleculeTagList)
            if serviceMoleculeTagSet.issubset(dataMoleculeTagSet):
                connectedIntentList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.IntentMM')
                for connectedIntentID in connectedIntentList:
                    intentMeme = Graph.api.getEntityMemeType(connectedIntentID)
                    intentDescription = Graph.api.getEntityPropertyValue(connectedIntentID, "description")
                    try:
                        unusedIntentMemeDict = availableIntents[intentMeme]
                        availableIntents[intentMeme][serviceMolecule] = {"intentID" : connectedIntentID, "intentDescription" : intentDescription}
                    except KeyError:
                        availableIntents[intentMeme] = {serviceMolecule : {"intentID" : connectedIntentID, "intentDescription" : intentDescription}}

        returnJSON = json.loads(availableIntents)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr     
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
        tagList = Engine.Graph.api.getEntitiesByMetaMemeType('Agent.TagMM')
        for tagID in tagList:
            tagMM = Engine.Graph.api.getEntityMemeType(tagID)
            dataType = Engine.Graph.api.getEntityPropertyValue(tagID, "DataType")
            if dataType in ["urlPOST", "urlGET"]:
                fullDefPath = Engine.Graph.api.getEntityPropertyValue(tagID, "URLDefinitionPath")
                splitDefPath = fullDefPath.split("::")
                dataTypeDict = {"DataType" : dataType, "URLDefinitionMeme" : splitDefPath[1]}
            else:
                dataTypeDict = {"DataType" : dataType}
            returnDict[tagMM] = dataTypeDict

        returnJSON = json.loads(returnDict)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr    
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
        tagList = Engine.Graph.api.getEntitiesByMetaMemeType('Agent.TagMM')
        for tagID in tagList:
            tagMM = Engine.Graph.api.getEntityMemeType(tagID)
            returnList.append(tagMM)
        
        returnJSON = json.loads(returnList)
        
        returnStr = "%s" %returnJSON  
        response.status = 200
        return returnStr    
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
            intentEntityID = Engine.Graph.api.createEntityFromMeme(intent)
            intentEntityType = Engine.Graph.api.getEntityMetaMemeType(intentEntityID)
            if intentEntityType != 'Agent.IntentMM':
                errorMessage = "%s is not an intent" %intent
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid Intent %s" %intent
            raise Exceptions.IntentError(errorMessage)
        
        #And only intent service molecules can support intents.
        try:
            intentMoleculeType = Engine.Graph.api.getEntityMemeType(intentServiceMoleculeID)
            if intentMoleculeType != 'Agent.IntentMolecule':
                errorMessage = "%s is not an intent service molecule." %intentServiceMoleculeID
                raise Exceptions.IntentServiceMoleculeError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid Intent %s" %intent
            raise Exceptions.IntentError(errorMessage)
        
        #Next, check to see that we don't already support an intent.  If we do, that support will have to be revoked first.
        existingIntentList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(intentServiceMoleculeID, 'Agent.IntentMM')
        if len(existingIntentList) > 0:
            existingMemeType = Engine.Graph.api.getEntityMemeType(existingIntentList[0])
            errorMessage = "Intent Service molecule %s already supports intent %s.  Support for %s can't be declared unless prior support is revoked" %(intentServiceMoleculeID, existingMemeType, intent)
            raise Exceptions.RedundantIntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = Engine.Graph.api.addEntityLink(intentServiceMoleculeID, intentEntityID)
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr
   
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
        intentMoleculeType = Engine.Graph.api.getEntityMemeType(intentServiceMoleculeID)
        if intentMoleculeType != 'Agent.IntentMolecule':
            errorMessage = "%s is not an intent service molecule." %intentServiceMoleculeID
            raise Exceptions.IntentServiceMoleculeError(errorMessage)
        
        #Next, check to see that we don't already support an intent.  If we do, that support will have to be revoked first.
        existingIntentList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(intentServiceMoleculeID, 'Agent.IntentMM')
        if len(existingIntentList) < 1:
            returnResults = "Intent Service molecule %s has no declared intents" %(intentServiceMoleculeID)
            raise Exceptions.IntentError(errorMessage)
        else:
            for existingIntentID in existingIntentList:
                returnResults = Engine.Graph.api.removeEntityLink(intentServiceMoleculeID, existingIntentID)
 
        returnResultsJson = json.dumps(returnResults)
        
        returnStr = "%s" %(returnResultsJson)
        response.status = 200
        return returnStr
   
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
            tagCreationReport = Engine.Graph.api.sourceMemeCreate(propertyName, moduleName, "Agent.RESTPropertyMM")
            unusedReturn = Engine.Graph.api.sourceMemeSetSingleton(tagCreationReport["memeID"], True)
            unusedReturn = Engine.Graph.api.sourceMemePropertySet(tagCreationReport["memeID"], "dataType", dataType)
        except KeyError as e:
            raise Exceptions.POSTArgumentError("Property %s needs a data type") %propertyName
        except Exception as e:
            raise e
        
        try:
            description = rawRequest["description"]
            unusedReturn = Engine.Graph.api.sourceMemePropertySet(tagCreationReport["memeID"], "description", description)
        except KeyError:
            pass
        except Exception as e:
            raise e
        
        unusedReturn = Engine.Graph.api.sourceMemeCompile(tagCreationReport["memeID"], False)
        unusedReturn = Engine.Graph.api.createEntityFromMeme(tagCreationReport["memeID"])
        
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
        
        propertyEntityList = Graph.api.getEntitiesByMetaMemeType("Agent.RESTPropertyMM")
        propertyMemeDict = {}
        for propertyEntityID in propertyEntityList:
            entityMemetype = Graph.api.getEntityMemeType(propertyEntityID)
            entityDescription = Graph.api.getEntityPropertyValue(propertyEntityID, "description")
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
        propertyEntityList = Engine.Graph.api.getEntitiesByMetaMemeType('Agent.RESTPropertyMM')
        for propertyEntityID in propertyEntityList:
            entityMemetype = Graph.api.getEntityMemeType(propertyEntityID)
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
            tagEntityID = Engine.Graph.api.createEntityFromMeme(tagName)
            tagEntityType = Engine.Graph.api.getEntityMetaMemeType(tagEntityID)
            if tagEntityType != 'Agent.TagMM':
                errorMessage = "%s is not a tag" %tagName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %tagName
            raise Exceptions.IntentError(errorMessage)
        
        #First, check to see that the desired property name exists.
        propertyEntityID = None
        try:
            propertyEntityID = Engine.Graph.api.createEntityFromMeme(propertyName)
            propertyEntityType = Engine.Graph.api.getEntityMetaMemeType(propertyEntityID)
            if propertyEntityType != 'Agent.RESTPropertyMM':
                errorMessage = "%s is not a property" %propertyName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %propertyName
            raise Exceptions.IntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = Engine.Graph.api.addEntityLink(tagEntityID, propertyEntityID)
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
            tagEntityID = Engine.Graph.api.createEntityFromMeme(tagName)
            tagEntityType = Engine.Graph.api.getEntityMetaMemeType(tagEntityID)
            if tagEntityType != 'Agent.TagMM':
                errorMessage = "%s is not a tag" %tagName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %tagName
            raise Exceptions.IntentError(errorMessage)
        
        #First, check to see that the desired property name exists.
        propertyEntityID = None
        try:
            propertyEntityID = Engine.Graph.api.createEntityFromMeme(propertyName)
            propertyEntityType = Engine.Graph.api.getEntityMetaMemeType(propertyEntityID)
            if propertyEntityType != 'Agent.RESTPropertyMM':
                errorMessage = "%s is not a property" %propertyName
                raise Exceptions.IntentError(errorMessage)                
        except Exceptions.ScriptError:
            errorMessage = "Invalid tag %s" %propertyName
            raise Exceptions.IntentError(errorMessage)
        
        #Still here and not thrown any exceptions?  Ok, we can assign attach the service to the intent
        returnResults = Engine.Graph.api.addEntityLink(tagEntityID, propertyEntityID)
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
        propertyEntityList = Graph.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.MoleculeNodeMM::Agent.TagMM::Agent.RESTPropertyMM")
        for propertyEntityID in propertyEntityList:
            entityMemetype = Graph.api.getEntityMemeType(propertyEntityID)
            entityDescription = Graph.api.getEntityPropertyValue(propertyEntityID, "description")
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

        eventEntityList = Engine.Graph.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
         
        moleculeMemetype = Graph.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
            
        returnResults = Engine.Graph.api.addEntityLink(moleculeID, eventEntityList[0])
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

        eventEntityList = Engine.Graph.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
        else:
            eventMM = Engine.Graph.api.getEntityMetaMemeType(eventEntityList[0])
            if eventMM != "Agent.EventMM":
                raise Exceptions.MissingAgentError("The event parameter %s refers to an entity of metameme type is of type %s.  It should be of type Agent.EventMM") %(eventName, eventMM)

         
        moleculeMemetype = Graph.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
            
        returnResults = Engine.Graph.api.removeEntityLink(moleculeID, eventEntityList[0])
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

        eventEntityList = Engine.Graph.api.getEntitiesByMemeType(eventName)
        if len(eventEntityList) < 1:
            raise Exceptions.NoSuchEntityError("No such event %s") %eventName
        else:
            eventMM = Engine.Graph.api.getEntityMetaMemeType(eventEntityList[0])
            if eventMM != "Agent.EventMM":
                raise Exceptions.MissingAgentError("The event parameter %s refers to an entity of metameme type is of type %s.  It should be of type Agent.EventMM") %(eventName, eventMM)
         
        moleculeMemetype = Graph.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.ServiceMolecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.ServiceMolecule") %(moleculeID, moleculeMemetype)
        
        
            
        returnResults = Engine.Graph.api.addEntityLink(moleculeID, eventEntityList[0])
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
        moleculeMemetype = Graph.api.getEntityMemeType(moleculeID)
        if moleculeMemetype != "Agent.Molecule":
            raise Exceptions.MissingAgentError("Entity %s is of type %s.  It shoulf be of type Agent.Molecule") %(moleculeID, moleculeMemetype)
        
        availableEventListeners = {}
        serviceMoleculeList = Graph.api.getLinkCounterpartsByType(moleculeID, "Agent.MoleculeNode::*::Agent.MoleculeNode::Agent.ServiceMolecule")
        dataMoleculeTagList = Graph.api.getLinkCounterpartsByMetaMemeType(moleculeID, "Agent.Landmark::Agent.TagMM")
        dataMoleculeTagSet = set(dataMoleculeTagList)
        for serviceMoleculeID in serviceMoleculeList:
            serviceMoleculeTagList = Graph.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, "Agent.Landmark::Agent.TagMM")
            serviceMoleculeTagSet = set(serviceMoleculeTagList)
            if serviceMoleculeTagSet.issubset(dataMoleculeTagSet):
                connectedEventList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.EventMM')
                for connectedEventID in connectedEventList:
                    connectedDataList = Engine.Graph.api.getLinkCounterpartsByMetaMemeType(serviceMoleculeID, 'Agent.Molecule') 
                    if moleculeID in connectedDataList:
                        eventMeme = Graph.api.getEntityMemeType(connectedEventID)
                        eventDescription = Graph.api.getEntityPropertyValue(serviceMoleculeID, "description")
                        eventTechnicalName = Graph.api.getEntityPropertyValue(serviceMoleculeID, "technicalName")
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
        unusedSubjectTemplate = Engine.api.getEntityMemeType(subjectID)
        unusedControllerTemplate = Engine.api.getEntityMemeType(ownerID)
        unusedNodeTemplate = Engine.api.getEntityMemeType(nodeID)
        
        actionID = "Intentsity.Event"
        ownerID = ownerID
        subjectID = subjectID
        objectID = None
        rtparams = {'nodeID' : nodeID} 
        
        #get any tags attached to the node

        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, subjectID, objectID, ownerID)
        Engine.aQ.put(actionInvocation)
        
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
    
    try:
        #test that the entities exist
        unusedSubjectTemplate = Engine.api.getEntityMemeType(subjectID)
        unusedControllerTemplate = Engine.api.getEntityMemeType(ownerID)
        unusedNodeTemplate = Engine.api.getEntityMemeType(nodeID)
        
        actionID = "Intentsity.Event"
        ownerID = ownerID
        subjectID = subjectID
        objectID = None
        rtparams = {'nodeID' : nodeID} 
        
        #get any tags attached to the node

        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, subjectID, objectID, ownerID)
        Engine.aQ.put(actionInvocation)
        
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
        actionID = "Intentsity.Intent"
        ownerID = None
        rtparams = {} 
        
        #test that the entities exist
        unusedEntityTemplateS = Engine.api.getEntityMemeType(moleculeID)
        unusedEntityTemplateS = Engine.api.getEntityMemeType(intentID)
        
        actionInvocation = Engine.ActionRequest(actionID, ationInsertionTypes.APPEND, rtparams, moleculeID, intentID, ownerID)
        Engine.aQ.put(actionInvocation)
        
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
    
    
@route('/stimuli/<broadcasterID>', method='GET')
def getStimulusReports(broadcasterID):
    """  Collect current items in a particular broadcast queue """
    
    try:
        if broadcasterID not in Engine.broadcasterRegistrar.broadcasterIndex:
            errorMsg = "No such broadcast queue %s" %broadcasterID
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
    run(host='localhost', port=8080)