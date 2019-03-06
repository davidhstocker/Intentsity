'''
Created on June 13, 2018

@author: David Stocker
'''

import Graphyne.Graph as Graph
import Graphyne.Scripting
from TiogaSchema import TiogaContentExceptions

class InitLandmark(Graphyne.Scripting.StateEventScript):
    
    def execute(self, landmarkEntityUUID, unusedParams):
        """ Default catch and throw are universal actions; meaning that they are linked to every landmark in existence.  
            Memetics does not understand the concept of the universal landmarks and requires explicit linking.  Because 
            of this, we need to dynamically link them.  

            When the default catch and throw actions are instantiated, they are built against the dummyLandmark.
            This method links the default catch and throw to another landmark, so that it can now access these 
            'universal' actions.  
        
            Create new DefaultCatch and DefaultThrow entities.  Sever their connection with dummyLandmark
            and replace the link with the landmark at landmarkEntityUUID.  Then update the landmark entity
            defaultCatch and defaultThrow entries.
        """
        try:
            #Agent.DummyLandmark is a singleton, so we are really just getting its UUID.
            selfType = Graph.api.getEntityMemeType(landmarkEntityUUID)
            if selfType != "Agent.DummyLandmark":
                defaultCatchActionID = Graph.api.createEntityFromMeme("Action.DefaultCatchAction")
                defaultThrowActionID = Graph.api.createEntityFromMeme("Action.DefaultThrowAction")
                defaultCatchID = Graph.api.createEntityFromMeme("Action.DefaultCatch")
                defaultThrowID = Graph.api.createEntityFromMeme("Action.DefaultThrow")
                
                #Add these two new entries to the Landmark
                hasDefaultCatch = Graph.api.getEntityHasProperty(landmarkEntityUUID, 'DefaultCatch')
                if hasDefaultCatch == False:
                    Graph.api.addEntityStringProperty(landmarkEntityUUID, 'DefaultCatch', str(defaultCatchActionID))
                hasDefaultThrow = Graph.api.getEntityHasProperty(landmarkEntityUUID, 'DefaultThrow')
                if hasDefaultThrow == False:
                    Graph.api.addEntityStringProperty(landmarkEntityUUID, 'DefaultThrow', str(defaultThrowActionID))
                
                #  Since Agent.DummyLandmark is a singleton, then we should suppress init to prevent 
                #  an endless loop of initialization
                dummyLandmark = Graph.api.createEntityFromMeme("Agent.DummyLandmark", None, None, None, True)
                defReqLandmarkPath = "Action.DefaultRequiredLandmarks::Action.DefaultMasterLandmark::Action.DefaultRequiredLandmark"
                        
                #sever the connection between the new DefaultCatch and Agent.DummyLandmark
                #   Replace it with one to landmarkEntity
                catchDefReqLandmark = Graph.api.getLinkCounterpartsByType(defaultCatchID, defReqLandmarkPath)
                Graph.api.removeEntityLink(catchDefReqLandmark[0], dummyLandmark)
                Graph.api.addEntityLink(catchDefReqLandmark[0], landmarkEntityUUID)
                
                #Do the same for the throw
                throwDefReqLandmark = Graph.api.getLinkCounterpartsByType(defaultThrowID, defReqLandmarkPath)
                Graph.api.removeEntityLink(throwDefReqLandmark[0], dummyLandmark)
                Graph.api.addEntityLink(throwDefReqLandmark[0], landmarkEntityUUID)  
        except Exception as e:
            landmarkID = None
            try:
                landmarkID = Graph.api.getEntityMemeType(landmarkEntityUUID)
            except: pass
            errorMsg = "Encountered problem trying to run initialization script for landmark %s of type %s.  Traceback = %s" %(landmarkEntityUUID, landmarkID, e)
            raise TiogaContentExceptions.ScriptError(errorMsg)     