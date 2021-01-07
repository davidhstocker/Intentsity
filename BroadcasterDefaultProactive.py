'''
Created on Nov 20, 2020

@author: d035331
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
from Intentsity import Engine
from Intentsity import Exceptions
import argparse
        
basePort = 8090


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Intentsity")

    parser.add_argument("-p", "--port", type=int, help="|Int| The port used by the INtentsity Default Broadcaster")
    
    args = parser.parse_args()
    
    if args.port:
        basePort = args.port

    run(host='localhost', port=basePort)
    
    
@route('/')
def server_static():
    return("Intentsity Default Broadcaster Active!")
    
    
@route('/broadcast', method='POST')
def broadcast():
    
    try:
        rawRequest = request.POST.dict
        for rawKey in rawRequest.keys():
            keyVal = rawKey
        jsonPayload = json.loads(keyVal)
        
        
        reciepientOwnerID = None
        reciepientCreatorID = None
        reciepientCreatorCallbackURL = None
        resolvedDescriptor = None
        

        try:
            reciepientOwnerID = jsonPayload["reciepientOwnerID"]
        except (KeyError, Exception) as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on processing json POST parameter 'reciepientOwnerID'.  %s, %s" %(errorID, errorMsg)
            tb = sys.exc_info()[2]
            raise ValueError(responseMessage).with_traceback(tb)
        
        try:
            reciepientCreatorID = jsonPayload["reciepientCreatorID"]
        except (KeyError, Exception) as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on processing json POST parameter 'reciepientCreatorID'.  %s, %s" %(errorID, errorMsg)
            tb = sys.exc_info()[2]
            raise ValueError(responseMessage).with_traceback(tb)
        
        try:
            reciepientCreatorCallbackURL = jsonPayload["reciepientCreatorCallbackURL"]
        except (KeyError, Exception) as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on processing json POST parameter 'reciepientCreatorCallbackURL'.  %s, %s" %(errorID, errorMsg)
            tb = sys.exc_info()[2]
            raise ValueError(responseMessage).with_traceback(tb)
        
        try:
            resolvedDescriptor = jsonPayload["resolvedDescriptor"]
        except (KeyError, Exception) as e:
            fullerror = sys.exc_info()
            errorID = str(fullerror[0])
            errorMsg = str(fullerror[1])
            responseMessage = "Error on processing json POST parameter 'resolvedDescriptor'.  %s, %s" %(errorID, errorMsg)
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