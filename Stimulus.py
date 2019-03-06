'''
Created on June 13, 2018

@author: David Stocker
'''
import Graphyne.Graph as Graph
import Graphyne.Scripting
import Graphyne.Exceptions as ContentExceptions
import threading
import re

#remote debugger support for pydev
#import pydevd

#Globals
module = "Stimulus"


class Text(threading.Thread):
    entityLock = threading.RLock()
    
    def __init__(self, descriptorEntityUUID):
        self.descriptorEntityUUID = descriptorEntityUUID
        
    def execute(self, entityID, params):   
        """
        This class does not extend Graphyne.Scripting.StateEventScript, but it is installed as the evaluate event 
        script in the evaluate event of a Text element.  Therefore, it patterns itself after 
        Graphyne.Scripting.StateEventScript and follows its  execute() method parameter usage.

        """       
        try:
            contentPropertyName = "Content"
            contentPropertyValue = Graph.api.getEntityPropertyValue(self.descriptorEntityUUID, contentPropertyName)
            return contentPropertyValue
        except ContentExceptions as e:
            raise ContentExceptions.ScriptError(e)



class InitText(Graphyne.Scripting.StateEventScript):
    """ The Descriptor class is a switch and thusly does not have direct access to any state event scripts,
         so we use the 'instantiation by proxy' pattern.  See the InitStimulus class for details
         
        Normally, a descriptor (the metamemes that are children of TiogaSchema.Stimuluis.Descriptor) have complex,
            heavywieght, resolver scripts.  A good example being Stimulus.InternationalizedDescriptor.  
            Such descriptors will build executors and install them as callable objects onto parent Descriptor 
            entity.  
        If the descriptor type in question is one with simple evaluation needs, it may not need a complex pre-
            calculation and purely runtime resolution is sufficient.  A good example is Stimulus.Text.
            The resolver for this metameme (see the execute() method the Text class in this module) simply returns
            the contents of the Content property.  For such types of descriptors, we can make a standardized handler
            available.
        This is installed as executor on the parent TiogaSchema.Stimuluis.Descriptor entity and essentially acts as a
            wrapper for the child entity's executor.  Note that the child must in turn  have a Child State event 
            script for the evaluation event for this to work. 
    """
        
    def execute(self, descriptorUUID, unusedParams):
        # Determine the parent descriptor UUID (descriptorContainerUUID)
        descriptorContainerUUID = None
        descriptorContainerUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(descriptorUUID, "Stimulus.Descriptor", 0)
        for descriptorContainerEntry in descriptorContainerUUIDSet:
            descriptorContainerUUID = descriptorContainerEntry

        if descriptorContainerUUID is None:
            descriptorEntityMemeType = Graph.api.getEntityMemeType(descriptorUUID)
            warningMsg = "Descriptor Meme %s has no parent Stimulus.Descriptor assigned." %descriptorEntityMemeType
            Graph.api.writeError(warningMsg)
        else:
            descriptorContainerMemeType = Graph.api.getEntityMemeType(descriptorContainerUUID)
            descriptorContainerMetaMemeType = Graph.api.getEntityMetaMemeType(descriptorContainerUUID)
            try:
                text = Text(descriptorUUID)
                Graph.api.installPythonExecutor(descriptorContainerUUID, text)
                descriptorContainerMemeType = Graph.api.getEntityMemeType(descriptorContainerUUID)
                logStatement = "Added executor object to %s descriptor %s" %(descriptorContainerMetaMemeType, descriptorContainerMemeType)
                Graph.api.writeLog(logStatement)
            except ContentExceptions.ScriptError as e:
                descriptorEntityMemeType = Graph.api.getEntityMemeType(descriptorUUID)
                errorMsg = "%s has no evaluate state event script!  Aborting initialization of parent descriptor %s" %(descriptorEntityMemeType, descriptorContainerMemeType)
                Graph.api.writeError(errorMsg)
                raise ContentExceptions.StateEventScriptInitError(e)
            except Exception as e:
                descriptorEntityMemeType = Graph.api.getEntityMemeType(descriptorUUID)
                errorMsg = "Unknown error while executing init script of %s and installing executor on parent descriptor %s" %(descriptorEntityMemeType, descriptorContainerMemeType)
                Graph.api.writeError(errorMsg)
                raise ContentExceptions.StateEventScriptInitError(e)                

        '''
        actionID = None
        try: actionID = runtimeVariables["actionID"]
        except: pass
        
        subjectID = None
        try: subjectID = runtimeVariables["subjectID"]
        except: pass
        
        controllerID = None
        try: controllerID = runtimeVariables["controllerID"]
        except: pass
        
        resolvedStimulus = Graph.api.evaluateEntity(self.descriptorUUID, runtimeVariables, actionID, subjectID, controllerID)
        return resolvedStimulus
        '''




class SimpleArgument(object):
    '''A very simple class for managing simple arguments of conditions '''
    className = "SimpleArgument"
    
    def initArgument(self, argument):
        self.argument = argument 
        self.isSimple = True
        self.isAAA = False

        
    def getArgumentValue(self, argMap):
        returnVal = None
        try:
            returnVal = argMap[self.argument] 
        except: 
            pass
        return returnVal


    def testMapforArgument(self, argMap):
        returnVal = False
        try:
            hasReturnVal = argMap[self.argument]
            if hasReturnVal is not None: returnVal = True
        except: 
            pass 
        return returnVal      


    def getRequiredArgumentList(self):
        return [self.argument]

    
    def getRequiredAgentPathList(self):
        return []
    


class ComplexTokenObject(object):
    ''' A container object that acts as a proxy executor for a Stimulus.ConditionalDescriptor, 
        even though it is not actually installed on one.
        '''
    className = 'ComplexToken'
    
    def __init__(self, conditionalDescriptorUUID):
        method = module + '.' +  self.className + '.__init__'
        Graph.api.writeLog("Entering %s" %method)
        
        #First, get the uuid of the ConditionalDescriptor's linked condition
        self.conditionUUID = None
        conditionUUIDDet = Graph.api.getLinkCounterpartsByMetaMemeType(conditionalDescriptorUUID, "Graphyne.Condition.Condition", 1)
        for conditionUUID in conditionUUIDDet:
            #There should be only one entry
            self.conditionUUID = conditionUUID
        
        #Now do the same with the linked descriptor
        self.descriptorUUID = None
        descriptorUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(conditionalDescriptorUUID, "Stimulus.Descriptor", 1)
        for descriptorUUID in descriptorUUIDSet:
            #There should be only one entry
            self.descriptorUUID = descriptorUUID
        Graph.api.writeLog("Exiting %s" %method)
        
    def testConditionalDescriptor(self, rtParams, actionID = None, subjectID = None, controllerID = None):
        #entityUUID, runtimeVariables, ActionID = None, Subject = None, Controller = None, supressInit = False
        #debug
        #cdMemeType = Graph.api.getEntityMemeType(self.conditionUUID)
        #dMemeType = Graph.api.getEntityMemeType(self.descriptorUUID)
        #/debug
        try:
            result = Graph.api.evaluateEntity(self.conditionUUID, rtParams, actionID, subjectID, controllerID, True)
            return result
        except Exception as e:
            dummyVariable = e #debug aid
            return False
        
    
    def getConditionalDescriptor(self, rtParams, actionID = None, subjectID = None, controllerID = None):
        try:
            result = Graph.api.evaluateEntity(self.descriptorUUID, rtParams, actionID, subjectID, controllerID, True)
            return result
        except Exception as e:
            dummyVariable = e #debug aid
            return 'INVALID_DESCRIPTOR'



class ComplexToken(threading.Thread):
    ''' A container object for referencing and evaluating internationalzed descriptors'''
    className = 'ComplexToken'
    entityLock = threading.RLock()
    
    def __init__(self, cdCheckList, defaultDescriptor):
        method = module + '.' +  self.className + '.__init__'
        Graph.api.writeLog("Entering %s" %method)
        self.cdCheckList = cdCheckList
        self.defaultDescriptor = defaultDescriptor
        Graph.api.writeLog("Exiting %s" %method)
        


    def getText(self, rtParams, actionID = None, subjectID = None, controllerID = None):
        ''' a retreiver for the text of an i18n descriptor from tha catalog  '''
        method = module + '.' +  self.className + '.getText'
        
        #sort through the conditions to find the first true value
        chosenDescriptor = None
        keepIterating = True
        chosenConditionKey = None
        for variantKey in self.cdCheckList:
            try:
                testResult = False
                Graph.api.writeDebug( '%s Testing condition %s' %(method, variantKey))
                #uuidVariantKey = uuid.UUID(variantKey)
                conditionalDescriptor = self.cdCheckList[variantKey]
                isTrue = conditionalDescriptor.testConditionalDescriptor(rtParams[1], actionID, subjectID, controllerID)
                if isTrue == True:
                    chosenDescriptor = conditionalDescriptor.getConditionalDescriptor(rtParams[1], actionID, subjectID, controllerID)
                    testResult = True
                Graph.api.writeDebug( '%s Condition %s test result = %s' % (method, variantKey, testResult))
                if (testResult == True) and (keepIterating == True):
                    chosenConditionKey = variantKey
                    keepIterating = False
                    break
            except Exception as e:
                lengthOfChecklist = len(self.cdCheckList)
                errorMsg = "Error evaluating conditional descriptor %s out of %s.  Traceback = %s" %(variantKey, lengthOfChecklist, e)
                raise Exception(errorMsg)
 
        #Now determine the descriptor associated with the condition
        Graph.api.writeDebug( '%s Chosen Condition = %s' %(method, chosenConditionKey))
        descriptor = None
        if chosenDescriptor is None:
            descriptor = self.defaultDescriptor
            try:
                descriptor = Graph.api.evaluateEntity(self.defaultDescriptor, rtParams[1], actionID, subjectID, controllerID, True)
            except:
                descriptor =  'INVALID_DESCRIPTOR'
        else:
            descriptor = chosenDescriptor
        Graph.api.writeDebug( '%s Counterpart Descriptor = %s' %(method, descriptor))
 
        return descriptor




class InternationalizedDescriptor(threading.Thread):
    ''' An InternationalizedDescriptor holds one I18N text string for all defined languages, along with possible adjectives.  
            Initialized with the filename of the descriptor xml, the logger object of the server, the default language of the server and the loglevel.'''
    className = 'InternationalizedDescriptor'
    entityLock = threading.RLock()

    def __init__(self, descriptorEntityUUID, descriptorContainerUUID):
        method = module + '.' +  self.className + '.__init__'
        Graph.api.writeLog("Entering %s" %method)
        self.devLanguage = "en"
        self.descriptor = {}
        self.descriptorEntityUUID = descriptorEntityUUID
        self.descriptorContainerUUID = descriptorContainerUUID
        Graph.api.writeLog("Exiting %s" %method)
        
        
    def execute(self, unusedUUID, rtParams):
        method = module + '.' +  self.className + '.__init__'
        Graph.api.writeLog("Entering %s" %method) 
        internationalizedDescriptor = None   
        actionID = rtParams['actionID']
        subjectID = rtParams['subjectID']
        controllerID = rtParams['runtimeVariables']['controllerID']
        if "language" in rtParams:
            language = rtParams["language"]
            language = language.lower() #force lowercase
            if language in self.descriptor:
                internationalizedDescriptor = self.descriptor[language]
            elif self.devLanguage in self.descriptor:
                internationalizedDescriptor = self.descriptor[language]
            else:
                descriptorEntityMeme = Graph.api.getEntityMemeType(self.descriptorEntityUUID)
                Graph.api.writeError(" %s has no localized descriptor maintained for dev language, %s" %(descriptorEntityMeme, self.devLanguage))
                return "NO_TEXT_MAINTAINED"
        elif self.devLanguage in self.descriptor:
            internationalizedDescriptor = self.descriptor[self.devLanguage]
        else:
            descriptorEntityMeme = Graph.api.getEntityMemeType(self.descriptorEntityUUID)
            Graph.api.writeError(" %s has no localized descriptor maintained for dev language, %s" %(descriptorEntityMeme, self.devLanguage))
            return "NO_TEXT_MAINTAINED"
        
        returnText = Graph.api.evaluateEntity(internationalizedDescriptor, rtParams, actionID, subjectID, controllerID, True)
        return returnText
    


    def assignDevLanguage(self, devLanguage):
        self.devLanguage = devLanguage.lower()

                

    def addDescriptor(self):
        """This method turns a LocalizedDescriptor XML element into a list.  This list is put together serially 
        at runtime to create dynamic text.  Each member of the list may be Unicode text, a UUID, or a 
        SimpleArgument object; each representing a text fragment, a complex token, or a simple token. """
        method = module + '.' +  self.className + '.addDescriptors'
        Graph.api.writeLog("Entering %s" %method)

        try:
            localizedDescriptorUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(self.descriptorEntityUUID, "Stimulus.LocalizedDescriptor", 1)
            for localizedDescriptorUUID in localizedDescriptorUUIDSet:
                language = Graph.api.getEntityPropertyValue(localizedDescriptorUUID, "Language")
                
                #This sets up references to complex tokens
                complexTokenSet = {}
                complexTokenSetUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(localizedDescriptorUUID, "Stimulus.ComplexToken", 1)
                for complexTokenSetUUID in complexTokenSetUUIDSet:
                    cdCheckList = {}
                    tag = Graph.api.getEntityPropertyValue(complexTokenSetUUID, "Anchor")
                    
                    conditionalDescriptortUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(complexTokenSetUUID, "Stimulus.DescriptorToken::Stimulus.ConditionalDescriptor", 1)
                    for conditionalDescriptortUUID in conditionalDescriptortUUIDSet:
                        priority = Graph.api.getEntityPropertyValue(conditionalDescriptortUUID, "Priority")
                        complexTokenObject = ComplexTokenObject(conditionalDescriptortUUID)
                        cdCheckList[priority] = complexTokenObject
                    
                    defaultDescriptor = None    
                    defaultDescriptortUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(complexTokenSetUUID, "Stimulus.DescriptorToken::Stimulus.DefaultDescriptor::Stimulus.Descriptor", 1)
                    for defaultDescriptortUUID in defaultDescriptortUUIDSet:
                        #Should only be one
                        defaultDescriptor = defaultDescriptortUUID
    
                    complexToken = ComplexToken(cdCheckList, defaultDescriptor)    
                    complexTokenSet[tag] = complexToken
    
                simpleTokenSet = {}
                simpleTokenSetUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(localizedDescriptorUUID, "Stimulus.SimpleToken", 1)
                for simpleTokenSetUUID in simpleTokenSetUUIDSet:
                    try:
                        tag = Graph.api.getEntityPropertyValue(simpleTokenSetUUID, "Anchor")
                        argument = Graph.api.getEntityPropertyValue(simpleTokenSetUUID, "Argument")
                        token = SimpleArgument()
                        token.initArgument(argument)
                        simpleTokenSet[tag] = token
                    except Exception as e:
                        #pass    
                        #debug
                        tag = Graph.api.getEntityPropertyValue(simpleTokenSetUUID, "Anchor")
                        argument = Graph.api.getEntityPropertyValue(simpleTokenSetUUID, "Argument")
                        token = SimpleArgument()
                        token.initArgument(argument)
                        simpleTokenSet[tag] = token
                        #/debug 
 
                #Now that we have internailzed the tokens used by the descriptor, we can turn to the text string itself. 
                baseText = Graph.api.getEntityPropertyValue(localizedDescriptorUUID, "Text")  
                tagString = re.compile('\[/?[^\]]+\]')
                tokenList = re.findall( tagString, baseText)
    
                for token in tokenList:
                    #remove the leading and trailing brackets
                    trimmedTokenName = token[1:]
                    trimmedTokenName = trimmedTokenName[:-1]
                    
                    #Now we test to ensure that we we have tokens for all of our anchors
                    #simpleTokenSet contains anchor tags only,this is an easy test
                    if trimmedTokenName not in simpleTokenSet:
                        #complexTokenSet contains a list of UUIDs, we'll need to extract their tokens
                        #these are contained in the keys
                        complexTokenList = []
                        for complexTokenKey in complexTokenSet:
                            complexTokenList.append(complexTokenKey)
                        if trimmedTokenName not in complexTokenList:
                            raise MissingTokenError(trimmedTokenName)
                    
                    # baseText starts out as the original text.  We will be systematically replacing the tokens with
                    #    a standard seperator so that later on we can parse the string based on the location of the tokens.
                    reToken = '\[' + trimmedTokenName + '\]'
                    tokenReplacement = re.compile(reToken)
                    baseText = tokenReplacement.sub( '<>', baseText, count=1)
                
                # Now turn baseText into a list of text fragments, cut at the location of the tokens      
                textList = re.split('<>', baseText)         
                
                # At this point, we should have two lists; a list of text fragments that excludes the tokens (textList)
                #    and a list of the tokens contained in the descriptor (tokenList).  We will now interleave them into 
                #    a single list that will be used at runtime to built the text dynamically.
                # 1 - For each step in textList, we will look for the counterpart in tokenList
                # 2 - That entry in tokenList will be a key to a dict object either in simpleTokenSet or complexTokenSet
                # 3 - Check both dicts for the key and add it if found.  (if it is not found, we will get a key error, 
                #    hence the try/except blocks)
                i=0
                interleavedList = []
                for textFragment in textList:
                    Graph.api.writeDebug( '%s Interleave Step = %s.  textFragment= %s' % (method, i, textFragment))
                    interleavedList.append(textFragment)
                    try:
                        if tokenList[i] is not None:
                            Graph.api.writeDebug( '%s We are within the boundary of the tokenlist.' %method)
                            
                            #Again, leading and trailing brackets must be trimmed
                            tokenToBeTrimmed = tokenList[i]
                            trimmedTokenName = tokenToBeTrimmed[1:]
                            trimmedTokenName = trimmedTokenName[:-1]
    
                            try:
                                addMe = simpleTokenSet[trimmedTokenName]
                                interleavedList.append(addMe)
                                Graph.api.writeDebug( '%s %s is of type = %s' % (method, addMe, type(addMe)))
                                Graph.api.writeDebug( '%s Tag %s is in the simple token set.  argument = %s' % (method, trimmedTokenName, addMe))
                            except: 
                                Graph.api.writeDebug( '%s Nothing for tag %s in the simple token set' %(method, trimmedTokenName))
                            try:
                                addMe = complexTokenSet[trimmedTokenName]
                                interleavedList.append(addMe)
                                Graph.api.writeDebug( '%s %s is of type = %s' % (method, addMe, type(addMe)))
                                Graph.api.writeDebug( '%s Tag %s is in the simple token set.  token ID = %s' % (method, trimmedTokenName, addMe))
                            except:
                                Graph.api.writeDebug( '%s Nothing for tag %s in the complex token set' %(method, trimmedTokenName))
                    except:
                        # don't worry about an exception here.  We'll always overstep tokenList on the last pass.
                        Graph.api.writeDebug( '%s We have gone past the boundary of the tokenlist on pass %s' %(method, (i)))
                    i=i+1
        
                #Graph.api.writeDebug( '%s The interleaved token list is %s' %(method, interleavedList))
    
                #Create a localized descriptor python object and install it on the Localized Descriptor object            
                descriptor = LocalizedDescriptor(interleavedList, language)
                Graph.api.installPythonExecutor(localizedDescriptorUUID, descriptor)

                #now index it                
                self.descriptor[language] = localizedDescriptorUUID
                dummyVariable = "me"
        except Exception as e:
            memeType = Graph.api.getEntityMemeType(self.descriptorContainerUUID)
            errorMsg = "Failed to add executor object to Internationalized Descriptor %s.  Traceback = %s" %(memeType, e)
            Graph.api.writeError(errorMsg)
            #debug
            self.addDescriptor()
            #/debug
        Graph.api.writeLog("Exiting %s" %method)
        


class LocalizedDescriptor(threading.Thread):
    ''' A language specific text/adjetive combination for the InternationalizedDescriptor '''
    className = 'LocalizedDescriptor'
    entityLock = threading.RLock()
    
    def __init__(self, fragmentList, language):
        method = module + '.' +  self.className + '.__init__'
        Graph.api.writeLog("Entering %s" %method)
        self.fragmentList = fragmentList
        self.language = language
        Graph.api.writeLog("Exiting %s" %method)

                
    def execute(self, entityID, rtParams):
        """
        This class does not extend Graphyne.Scripting.StateEventScript, but it is installed as the evaluate event 
        script in the evaluate event of a localized descriptor.  Therefore, it patterns itself after 
        Graphyne.Scripting.StateEventScript and follows its  execute() method parameter usage.

        """
        
        method = module + '.' +  self.className + '.execute'
        Graph.api.writeLog("Entering %s" %method)
        
        actionID = rtParams["actionID"]
        subjectID = rtParams["subjectID"]
                                  
        method = module + '.' +  self.className + '.execute'
        Graph.api.writeLog("Entering %s" %method)
        
        returnString = ''
        insertValue = None
        Graph.api.writeDebug( "%s Building text string in language '%s'.  argumentMap = %s" % (method, self.language, rtParams))
        nth=0
        for step in self.fragmentList:
            nth = nth+1
            try:
                #Graph.api.writeDebug( "%s Dynamic String Construction - Step %s, type = %s" % (method, unicode(nth), type(step)))
                if isinstance(step, SimpleArgument):
                    #Graph.api.writeDebug( "%s Step %s is a simple token" %(method, unicode(nth)))
                    insertValue = step.getArgumentValue(rtParams)
                elif isinstance(step, ComplexToken):
                    #Graph.api.writeDebug( "%s Step %s is a complex token" %(method, unicode(nth)))
                    insertValue = step.getText(rtParams, actionID, subjectID)
                else:
                    #Graph.api.writeDebug( "%s Step %s is text" %(method, unicode(nth)))
                    insertValue = step
                
                returnString = returnString + insertValue
                #Graph.api.writeDebug( "%s Text buildup at step %s = %s" % (method, unicode(nth), returnString))
            except Exception as e:
                errorMsg = "%s Error building text at stepat step %s.  Traceback = %s" % (method, str(nth), e)
                Graph.api.writeError(errorMsg)
                try:
                    if isinstance(step, SimpleArgument):
                        insertValue = step.getArgumentValue(rtParams)
                    elif isinstance(step, ComplexToken):
                        insertValue = step.getText(rtParams, actionID, subjectID)
                    else:
                        insertValue = step
                    returnString = returnString + insertValue
                except:
                    pass
            
        Graph.api.writeLog("Exiting %s" %method)
        return returnString        
        

        
        
class InitInternationalizedDescriptor(Graphyne.Scripting.StateEventScript):
    className = "InitInternationalizedDescriptor"

    def execute(self, descriptorEntityUUID, unusedParams):

        """
        This method uses the 'instantiation by proxy' pattern.  See TiogaSchema.Condition.InitCondition for details. 

        This method is the state event script executed on creation of the Descriptor's child entity; one of the actual descriptor
            entity structure, e.g. InternationalizedDescriptor or Text.  Since this child entity links one and only one Descriptor,  
            it builds the relevant callable object and then installs that as the parent descriptor's executor.  

        descriptorEntityUUID is the uuid of the child internatialized descriptor
        descriptorContainerUUID is the uuid of the parent descriptor
        """        
        #pydev debugger.  Comment out for final checkin
        #pydevd.settrace()
        
        # Determine the parent descriptor UUID (descriptorContainerUUID)
        descriptorEntity = Graph.api.getEntity(descriptorEntityUUID)
        descriptorContainerUUID = None
        descriptorContainerUUIDSet = Graph.api.getLinkCounterpartsByMetaMemeType(descriptorEntityUUID, "Stimulus.Descriptor", 0)
        for descriptorContainerEntry in descriptorContainerUUIDSet:
            descriptorContainerUUID = descriptorContainerEntry

        if descriptorContainerUUID is None:
            warningMsg = "Internationalized Descriptor Meme %s has no parent Stimulus.Descriptor assigned." %descriptorEntity.memePath.fullTemplatePath
            Graph.api.writeError(warningMsg)
        else:
            uuidAsStr = str(descriptorContainerUUID)
            try:
                devLanguage = Graph.api.getEntityPropertyValue(descriptorEntityUUID, "DevLanguage")
                
                internationalizedDescriptor = InternationalizedDescriptor(descriptorEntityUUID, descriptorContainerUUID)
                internationalizedDescriptor.addDescriptor()
                internationalizedDescriptor.assignDevLanguage(devLanguage)
                Graph.api.installPythonExecutor(descriptorContainerUUID, internationalizedDescriptor)
                logStatement = "Added executor object to Internationalized Descriptor %s" %(uuidAsStr)
                Graph.api.writeLog(logStatement)
            except Exception as e:
                errorMsg = "Failed to add executor object to Internationalized Descriptor %s.  Traceback = %s" %(uuidAsStr,e)
                Graph.api.writeError(errorMsg)
                
                
                
class MissingTokenError(ValueError):
    ''' A conditional is somehow malformed and can not be processed'''
    pass


