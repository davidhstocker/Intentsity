
# Creator Element Life Cycle

Before any data or service molecules can be created, there needs to be a creator element in the graph, which they can be associated with.  The creator is the controller element associated with managing the molecule, from a technical perspective.  Generally speaking, creator molecules are associated with application developers; either for the application that creates the data, or the app that provides the service.  

A single creator can manage several data or service molecules at once.

## Creator Creation

Creator molecules are created with the [/modeling/addcreator][1] REST endpoint.  This is a POST method and has two parameters, **dataCallbackURL** and **stimulusCallbackURL**.  Both are required and both should be be POST method handlers.  The app developer is responsible for creating, hosting and maintaining these endpoints.

### dataCallbackURL

dataCallbackURL is called whenever data is requested of any molecules managed by the creator.  If there are no data molecules managed by the creator, then it can simply return OK.

### stimulusCallbackURL

This is the url that Intentsity will call whenever there is something going on related to a molecule, where the creator needs to be informed.


## Molecule creation and management

Nothing special happens with the creator during these operations.  


## Event

An Event action has been called and Intentsity has been informed that the data behind a particular data molecule (let’s call it **X**) has been updated.  Intentsity has determined that an event service, **Y** mates to the data molecule.  The following things happen in order:

1. Intentsity calls the data callback URL of X. The parameters are a list all of the data interface parameters that X and Y agreed on.  
2. The callback URL handler of X returns a json, containing these parameters as keys and the values of those parameters as the values.
3. Intentsity calls the stimulus callback URL of Y with a resolved *Stimulus.Event* message as the json body.  It will provide the entirety of the data returned by X’s  data callback URL handler, as well as the UUIDs of the data molecule entity, the data creator and the data owner.  This is the standard Intentsity service request resolved stimulus.
4. The stimulus callback URL of Y should simply return OK.  Intentsity is not expecting a response to stimuli being broadcast.  It should return OK and go about doing its thing in a non blocking way.
5. Whatever processing triggered Y’s stimulus callback URL handler does its thing and is ready to pass the results back to Intentsity, it fires the *EventFinished* action.  
6. Intentsity will call the stimulus callback URL of X with a resolved *Stimulus.EventResponse* message as the json body.   

## Intent

An Intent action has been called and Intentsity has been informed a specific intent service **Y** is being evoked on behalf of data molecule **X**.   The following things happen in order:

1. Intentsity calls the data callback URL of X. The parameters are a list all of the data interface parameters that X and Y agreed on.  
2. The callback URL handler of X returns a json, containing these parameters as keys and the values of those parameters as the values.
3. Intentsity calls the stimulus callback URL of Y with a resolved *Stimulus.Intent* message as the json body.  It will provide the entirety of the data returned by X’s  data callback URL handler, as well as the UUIDs of the data molecule entity, the data creator and the data owner.  This is the standard Intentsity service request resolved stimulus.
4. The stimulus callback URL of Y should simply return OK.  Intentsity is not expecting a response to stimuli being broadcast.  It should return OK and go about doing its thing in a non blocking way.
5. Whatever processing triggered Y’s stimulus callback URL handler does its thing and is ready to pass the results back to Intentsity, it fires the *IntentFinished* action.  
6. Intentsity will call the stimulus callback URL of X with a resolved *Stimulus.IntentResponse* message as the json body.  

You may notice that these two callback orchestration scenarios are nearly identical and differ only in the resolved stimuli being provided to the stimulus callback URLs.  This is by design.  The primary difference is when and how they are triggered.  Intents services are specifically invoked on behalf of the data molecule and event services are passively evoked, meaning that the data molecule app calls the Event action and leaves marshaling the event services to Intentsity.



[1]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addcreator