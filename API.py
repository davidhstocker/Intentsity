#!/usr/bin/env python2
"""Angela RML Interpreter - Core Server Module (abstract)
Created by the project angela team
    http://sourceforge.net/projects/projectangela/
    http://www.projectangela.org"""
    
__license__ = "GPL"
__version__ = "$Revision: 0.1 $"
__author__ = 'David Stocker'


import Graphyne.Graph as Graph
from . import Exceptions

api = Graph.api
api.initialize()

# Monkey patching function, as defined by Guido van Rossum on the Python-Dev mailing list
#https://mail.python.org/pipermail/python-dev/2008-January/076194.html
def monkeyPatch(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator

@monkeyPatch(Graph.api)
def getAllAgentsInAgentScope(agentID):
    """
        Returns all agents in the same scope as the supplied agent
    """
    scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    return peers
    
@monkeyPatch(Graph.api)    
def getAllLandmarksInAgentScope(agentID):
    """
        Returns all landmarks (of other agents) in the same scope as the supplied agent
    """
    ownLandmarkPath = "Agent.Landmark"
    scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.Scope::Agent.Landmark"
    ownLandmarks = api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    for ownLandmark in ownLandmarks:
        peers.remove(ownLandmark)
    return peers


@monkeyPatch(Graph.api)
def getAllAgentsInSpecifiedPage(pageUUID):
    """
        Returns agents with a scope on the supplied page
    """
    scopePath = "Agent.Scope::Agent.Landmark::Agent.Agent"
    peers = api.getLinkCounterpartsByType(pageUUID, scopePath, None)
    return peers
    
    
@monkeyPatch(Graph.api)
def getAllAgentsWithViewOfSpecifiedPage(pageUUID):
    """
        Returns agents with a view on the supplied page
    """
    scopePath = "Agent.View::Agent.Landmark::Agent.Agent"
    peers = api.getLinkCounterpartsByType(pageUUID, scopePath, None)
    return peers
    
    
        
@monkeyPatch(Graph.api)
def getAllAgentsInAgentView(agentID):
    """
        Get all agents that have active scope in the view of the supplied agent
    """
    scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark::Agent.Agent"
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    return peers
 
 
    
@monkeyPatch(Graph.api)
def getAllLandmarksInAgentView(agentID):
    """
        Get all landmarks (of other agents) that have active scope in the view of the supplied agent
    """
    ownLandmarkPath = "Agent.Landmark"
    scopePath = "Agent.Landmark::Agent.View::Agent.Page::Agent.Scope::Agent.Landmark"
    ownLandmarks = api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    for ownLandmark in ownLandmarks:
        peers.remove(ownLandmark)
    return peers
        
        
@monkeyPatch(Graph.api)
def getAllAgentsWithAgentView(agentID):
    """
        Get all agents with an active view of the scope of the supplied agent
    """
    scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark::Agent.Agent"
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    return peers

    
@monkeyPatch(Graph.api)
def getAllLandmarksWithAgentView(agentID):
    """
        Get all landmarks of other agents, where those agents have an active view of the scope of the supplied agent.
    """
    ownLandmarkPath = "Agent.Landmark"
    scopePath = "Agent.Landmark::Agent.Scope::Agent.Page::Agent.View::Agent.Landmark"
    ownLandmarks = api.getLinkCounterpartsByType(agentID, ownLandmarkPath, None)
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    for ownLandmark in ownLandmarks:
        peers.remove(ownLandmark)
    return peers
 
 
@monkeyPatch(Graph.api)
def getAgentView(agentID):
    """
        Return the pages on the supplied agent's current view.
    """
    scopePath = "Agent.Landmark::Agent.View::Agent.Page"
    viewedPages = api.getLinkCounterpartsByType(agentID, scopePath, None)
    return viewedPages   
    
    
@monkeyPatch(Graph.api) 
def getAgentScope(agentID):
    """
        Return the pages on the supplied agent's current scope.
    """
    scopePath = "Agent.Landmark::Agent.Scope::Agent.Page"
    peers = api.getLinkCounterpartsByType(agentID, scopePath, None)
    return peers
    
    
@monkeyPatch(Graph.api) 
def getStimulusScope(stimulusID):
    """
        Return the pages on the supplied stimulus' current scope.
    """
    stimulusChoicePath = "Stimulus.StimulusChoice"
    conditionalStimulusPath = "Stimulus.ConditionalStimulus"
    stimulusPath = "Stimulus.Stimulus"
    
    metamemeType = api.getEntityMetaMemeType(stimulusID)

    try:
        ''' Three params: entity, metaMemePath, linkType'''
        pageIDList = []
        if metamemeType.count(stimulusChoicePath) > 0:
            localPageIDList = api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.StimulusScope::Agent.Scope::Agent.Page")
            pageIDList.extend(localPageIDList)    
        elif metamemeType.count(conditionalStimulusPath) > 0:
            localPageIDListFree = api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
            localPageIDListAn = api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.Stimulus::Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
            pageIDList.extend(localPageIDListFree)    
            pageIDList.extend(localPageIDListAn)
        elif metamemeType.count(stimulusPath) > 0:
            localPageIDListFree = api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.FreeStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
            localPageIDListAn = api.getLinkCounterpartsByMetaMemeType(stimulusID, "Stimulus.AnchoredStimulus::Stimulus.StimulusScope::Agent.Scope::Agent.Page")
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
    


@monkeyPatch(Graph.api) 
def oc(stimulusID):
    """
        Return the agents with view of the supplied stimulus' current scope.
    """
    try:
        pageList = api.getStimulusScope(stimulusID)
        agentSet = set([])
        for page in pageList:
            localAgentList = api.getAllAgentsWithViewOfSpecifiedPage(page)
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
    

