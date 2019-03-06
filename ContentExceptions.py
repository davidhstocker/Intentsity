'''
Created on June 13, 2018

@author: David Stocker
'''

#classes

class EmptyFileError(ValueError):
    '''File contains no data  '''
    pass


class UndefinedPersistenceError(ValueError):
    ''' No persistence has been defined '''
    pass

class PersistenceQueryError(ValueError):
    ''' Invalid Relational Query to persistence '''
    pass

class EnhancementError(ValueError):
    pass


class XMLSchemavalidationError(ValueError):
    pass


class UndefinedValueListError(ValueError):
    pass

class DuplicateValueListError(ValueError):
    pass

class UndefinedOperatorError(ValueError):
    pass

class DisallowedCloneError(ValueError):
    pass


class UndefinedUUIDError(ValueError):
    pass

class TemplatePathError(ValueError):
    pass

class DuplicateConditionError(ValueError):
    pass

class MalformedConditionError(ValueError):
    ''' A condition is somehow malformed and can not be processed'''
    pass

class MalformedArgumentPathError(ValueError):
    '''Parsing a conditional argument path via regular expressions yields a zero length array.  
        This means that the argument path does not follow the xPath style  '''
    pass

class MismatchedArgumentPathError(ValueError):
    '''Walking down an agent's attributes using th3e argumen path yields an error.
        This indicated that the agent does not have the desired arguent path available '''
    pass

class MissingArgumentError(ValueError):
    '''A conditional that requires argument X has been called without that argument  '''
    pass

class MissingAgentPathError(ValueError):
    '''A conditional that requires an agent with an attribute at path X has been called without that agent/attribute  combo'''
    pass

class MissingAgentError(ValueError):
    '''A conditional that requires a reference agent has been called without one'''
    pass

class MissingTokenError(ValueError):
    ''' A conditional is somehow malformed and can not be processed'''
    pass

class UnknownConditionalError(ValueError):
    ''' Unknown conditional %s requested from catalog '''
    pass

class ChannelError(ValueError):
    ''' A stimulus is uses an undefined channeland can not be processed - or the channel is malformed'''
    pass

class DuplicateChannelError(ValueError):
    ''' The channel already exists'''
    pass

class DuplicateSubscription(ValueError):
    ''' already subscribed to the object '''
    pass

class DisallowedDescriptorType(ValueError):
    ''' Used for controllers that try  to subscribe to a descriptor that they can't handle, or are not allowed to have '''
    pass

class DisallowedChannelChange(ValueError):
    ''' The method is not allowed on this particuler channel type '''
    pass

class ControllerUpdateError(ValueError):
    ''' The controller is invalid'''
    pass

class InvalidControllerError(ValueError):
    ''' The controller is invalid'''
    pass

class DuplicateControllerError(ValueError):
    ''' The controller is invalid'''
    pass

class PassiveControllerActivationError(ValueError):
    ''' Strictly passive (mayBeActive == False) controllers may not be activated'''
    pass

class MismatchedStimulusDestination(ValueError):
    """A stimulus is given a set of controllers as the destination, but the stimulus has an agent oriented distribution model"""
    pass

class NullDisplacement(ValueError):
    """A displacement can't be determined; usually because the two locations are not in the same zone"""
    pass

class DurationModelError(ValueError):
    """A generic problem with a duration model"""
    pass

class MemePropertyValidationError(ValueError):
    """A meme has an invalid property"""
    pass

class MemePropertyValueError(ValueError):
    """A meme has a property with an invalid value"""
    pass

class MemePropertyValueTypeError(ValueError):
    """A meme's property has been asked to assign a value of the wrong type"""
    pass

class MemePropertyValueOutOfBoundsError(ValueError):
    """A meme property with constrained bounds has been asked to assign a value outside those bounds"""
    pass

class MemeMembershipValidationError(ValueError):
    """A meme has an invalid member"""
    pass

class NonInstantiatedSingletonError(ValueError):
    """This error should only occur if the meme is a singleton, but no entity has been instantiated.  It means that there
    is a technical problem with the meme loader in that it did not instantiate singleton memes"""
    pass

class MemeMemberCardinalityError(ValueError):
    """A meme's membership roll violates the cardinality rules of its parent metameme"""
    pass

class EntityPropertyValueTypeError(ValueError):
    """An entity's property has been asked to assign a value of the wrong type"""
    pass

class EntityPropertyDuplicateError(ValueError):
    """An entity's property has been asked to assign a value of the wrong type"""
    pass

class EntityPropertyValueOutOfBoundsError(ValueError):
    """An entity property with constrained bounds has been asked to assign a value outside those bounds"""
    pass

class EntityMemberDuplicateError(ValueError):
    """An entity may not have a unique member more than 1x"""
    pass

class EntityMemberMissingError(ValueError):
    """An entity may not have a unique member more than 1x"""
    pass

class ScriptError(ValueError):
    """A script error"""
    pass

class GeneratorError(ValueError):
    """General error for random numbers """
    pass


class StateEventScriptInitError(ValueError):
    """An error initializing a state event script"""
    pass

class SourceMemeManipulationError(ValueError):
    """An error in manipulating a source meme"""
    pass

class TagError(ValueError):
    pass

class EntityMaxXOffsetExceeded(ValueError):
    """ An offset element's 'x' is greater than the 'x' value of the agent's OffsetMax"""
    pass

class EntityMaxYOffsetExceeded(ValueError):
    """ An offset element's 'y' is greater than the 'y' value of the agent's OffsetMax"""
    pass

class EntityMaxZOffsetExceeded(ValueError):
    """ An offset element's 'z' is greater than the 'z' value of the agent's OffsetMax"""
    pass

class EntityMinXOffsetExceeded(ValueError):
    """ An offset element's 'x' is greater than the 'x' value of the agent's OffsetMin"""
    pass

class EntityMinYOffsetExceeded(ValueError):
    """ An offset element's 'y' is greater than the 'y' value of the agent's OffsetMin"""
    pass

class EntityMinZOffsetExceeded(ValueError):
    """ An offset element's 'z' is greater than the 'z' value of the agent's OffsetMin"""
    pass

class EntityMaxXAngleExceeded(ValueError):
    """ An offset element's 'x' is greater than the 'x' value of the agent's OffsetMax"""
    pass

class EntityMaxYAngleExceeded(ValueError):
    """ An offset element's 'y' is greater than the 'y' value of the agent's OffsetMax"""
    pass

class EntityMaxZAngleExceeded(ValueError):
    """ An offset element's 'z' is greater than the 'z' value of the agent's OffsetMax"""
    pass

class EntityMinXAngleExceeded(ValueError):
    """ An offset element's 'x' is greater than the 'x' value of the agent's OffsetMin"""
    pass

class EntityMinYAngleExceeded(ValueError):
    """ An offset element's 'y' is greater than the 'y' value of the agent's OffsetMin"""
    pass

class EntityMinZAngleExceeded(ValueError):
    """ An offset element's 'z' is greater than the 'z' value of the agent's OffsetMin"""
    pass

class InvalidStimulusProcessingType(ValueError):
    ''' The Stimulus Engine may only take the types TiogaSchema.ConditionalStimulus and 
        Stimulus.StimulusChoice.  Everything else throws an exception'''
    pass

    
