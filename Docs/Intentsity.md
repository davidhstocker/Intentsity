
Intentsity is an intelligent-agent friendly, smart REST API broker.  It brings together providers of REST APIs (services) and consumers, based on data context.  Instead of having to build support for each type of REST API that you might conceivably want to use, you build support for a single, simple API and let data context do rest of the work.
 
# 10,000-foot View
 
At its core, Intentsity uses a [Graphyne property graph][1] to mediate connections between services and consumers.  It has its own built-in [Memetic][2] schema.  Memetic is the graph language used by Graphyne.  When offering services or data, users define the layout of the data – the metadata - that they have or need and do this in the form of a [cluster][3] of [nodes or entities][4], linked together.   Within the graph, there are [certain singleton elements][5], known as tags.  Tags define the nature of data provided by a consumer or required by a service.  Linking to a common tag represents a compact between the service and consumer, the consumer can provide what the service needs to work.  This shared linking to tags between clusters is used in place of direct REST API linking.

![][image-1]
 
When talking about the specific Graphyne clusters used to define the consumers and services in Intentsity, we call them molecules.  There are three kinds of molecules in Intentsity; data molecules and two kinds of service molecules, event service molecules and intent intent molecules. 
 

# Overview and Walkthrough 

To help explain how Intentsity works, we’ll use an example of a consumer and a service.  Our consumer is the user of a mobile running app.  The app tracks the users heart rate, speed, rate of climb/descent, etc.; all the things that you’d expect such an app to track.   The interesting thing for us is that the app generates data and the user – the consumer – can do things with this data.  The service can take any two lists of numbers and compute the coefficient of correlation.  This might be useful to the user to see how their heart rate is affected by their pace.
 
 
## The Owners
 
Every participant, whether a consumer or service provider, is uniquely identified in the graph as a whole with an owner node.  In this case, we add two nodes to the graph, one for the calculation service and one for the consumer.  These owners are globally unique.  The service owner is a shorthand root node for the service being provided and the consumer owner represents the user.  In memetic, the graph language that Graphyne uses, there is an owner [meme][6], defining a generic owner node.  When an owner is created, an [entity is created form this meme][7]. 

Owner elements are created with [/modeling/addowner][8]

 
## The Creators
 
The app that the user is using to generate the data would get its own node.  This is the creator node.  Its entity is created from the Agent.CreatorNode meme, of Intentsity’s Memetic schema. 

Creator elements are created with [/modeling/addcreator][9]
 
 
## About Owners vs Creators
 
The creator might be distinct from the owner.  The owner is about who or what owns the data or the service.  The creator is about who or what owns the technical access to the data or service.  In our fitness app example, the user is the owner of the data.  The app developer is who builds the connectivity in Intentsity and makes it possible for the user to use Intentsity. 

The creator is responsible for maintaining a pair of callback REST URLs, so that it can be reached by Intentsity in response to events within Intentsity.  It must be able to provide the data that it agreed to provide when linking a data molecule node to a tag.  It must also be able to receive the results produced by a service.
 
 
## Consumer Molecule
 
![][image-2]

There are a few bits of information that we’ll use to build out the consumer molecule.  The app generates a table of data.  Let’s suppose for simplicity that our data table has columns for heart rate and pace; and there is one timestamp per row. 
 
We would then add a table to the graph, represented by an entity.  This table entity is actually a central entity, which every data molecule has.  It is always created form the *Agent.Molecule* meme, of Intentsity’s Memetic schema.  This central entity is linked directly to the creator and owner entities, allowing for single hop graph traverses in either direction.  

A data molecule entity is created with [/modeling/addDataMolecule][10]  It will be linked to the creator and owner when created.
 
Heart rate, pace and timestamp would each get their own entities.  These entities are all created from the *Agent.MoleculeNode* meme, of Intentsity’s Memetic schema.
 
A data molecule node entity is created with [/modeling/addMoleculeNode/][11].  It will automatically be linked to the parent molecule entity.
 
 
## Tags
 
The *Agent.MoleculeNode* entities are all linked to tags.  Tags are singleton memes that act a a control mechanism in Intentsity.  They have three roles. 
 
They are the universal connectors, between data molecules and services. In the language of Graphyne, they act as [singleton bridges][12] between molecules.  Graph traverses specifically designed for a certain pattern 
 
They are how data molecule node entities declare what they are to the world.  This is done by simply linking molecule nodes to tag entities.  This is called ‘tagging’ and the molecule node is said to be ‘tagged’ with a particular tag.
 
They are how service molecules declare what kind of data that they want to the world.
 
In our example data, heart rate app example, heart rate and pace are lists of numbers that can be calculated; they can be summed, averaged, etc.  In [data warehousing terminology, such lists of numbers would be called measures][13].  If there were a tag for measure, both tagged with it and heart rate and pace would be classified as measures.  The timestamp molecule node would be tagged to a timestamp tag.

All tags are singletons.  Each is a unique meme, created from the *Agent.TagMM* metameme.  There is always exactly one entity in the graph, created from that meme.  When an API call is made to create a new entity, the meme is added and the entity is automatically instantiated.
 
Tags are created with [/modeling/addTag/][14]

Tags are assigned to molecule nodes with [/modeling/addEntityLink/][15]

![][image-3]
 

## \ Tag Inheritance

Tags can be extended, just like you’d extend classes in object oriented programming languages.  If a tag has a [directional link ][16]to another tag, it is an extension of the latter.  Any molecule node that uses a tag, also uses all extension tags.  In this case, we could create tags for *Heart Rate (HR) *and *Pace (P)*, which both link to *Measure (M)*.  HR and P would also both be M tags.  

![][image-4]

We could now tag our heart rate and pace molecule nodes to the appropriate tags.  Both would also be measures.  Tagging either would also be considered indirect tagging of *Measure*.

![][image-5]
 

### Tag Properties

Tags can have parameters, or properties.  These are the input parameters that that any service with this tag will require and what any data molecules with this tag will be required to provide.  Part of the contract that data molecules are agreeing to when a data molecule node is tagged is to be able to provide any required parameters.  Every tag can support a single parameter, which has a name, an optional description and a data type.  The possible data types are:

Str
Int
Num
StrList
IntList
NumList
StrKeyValuePairList
IntKeyValuePairList
IntKeyValuePairList

Properties are defined using [/modeling/addProperty/][17]

Properties are then associated with tags, via  [/modeling/assignTagProperty/][18]


## Service Provider Overview

![][image-6] 

The service molecule is simpler.  Like data molecules, it has a central entity, but it does not deed to define any data structures.  It only needs to link the central entity to the proper tags to define what data it needs.   The central entity is directly tagged in service molecules.  All tags among the service molecule’s [end effectors][19] are considered requirements for enabling that service for a given data molecule.  

A service molecule can apply cardinality to tag links.  By default, the cardinality is 1, meaning 1:1.  A data molecule would have to have one data molecule node tagged with the given tag for the connection to be made.  Any other cardinality value, n, would imply a 1:n relationship.  There would need to be n distinct data molecule nodes tagged with the given tag for the connection to be made.

You need two measures to calculate a coefficient of correlation, so our example service would link to a measure tag and declare a cardinality of 2.  


## Molecule connections and Compatibility

In Graphyne, clusters that share a common singleton are said to have a [singleton bridge][20].  Molecules are clusters and tags are singletons.  Any data molecule that has data molecule nodes tagged with all of the tags that a service has is said to be compatible with that service.  If

In our example, if both the *Heart Rate* and *Pace* data molecule nodes are tagged to the *Measure* tag, then the data and service molecules are said to be compatible.  

![][image-7]

If there are Heart Rate and Pace tags, extending Measure and the respective data molecule nodes are tagged to them, then the data and service molecules are also said to be compatible.  

![][image-8]

Any combination of direct or indirect tagging is allowed when testing compatibility.

![][image-9]


## Event services versus Intent Services
 
Event and intent services similar.  The main difference is in when and how they are invoked.  Intent services - called intents for short - are called at will.  A data molecule owner can ask which intents are compatible and any compatible intent at will.  Querying which intents are available is done via /modeling/getAvailableIntents.

Event services work a bit differently.  Whenever there is a relevant change in the underlying data that a data molecule represents, the data molecule creator would inform Intentsity of a version change.  When this happens, every compatible event service is automatically invoked.

In terms of how the graph clusters of the services molecules, intents and events are nearly identical.  The only difference is the meme from which the central entity is instantiated.  The central entity of events are instantiated from *Agent.ServiceMolecule* and intents are instantiated from *Agent.IntentMolecule*.  The type of central entity defines the service molecule as a whole.  

Event services are created via [/modeling/addServiceMolecule/][21]

Intent services are created via [/modeling/addIntentMolecule/][22]

As with data molecules, service molecules are both automatically linked to their owner and creator entities.

 
## Self-Contained vs Callback Services
 
Every service, whether an event or intent, is either self-contained, or a callback service.  Callback services provide a REST URL, which Intentsity will call when the service is invoked.  Essentially, Intentsity is brokering the REST API call by measuring compatibility and forwarding the invocation to the target URL.  

There is an alternative way for services to work, without using an external callback URL.  They can can execute a native Intentsity action. The default action, that is executed when a service is invoked, requests the callback URL.  If an alternative action is supplied instead and runs entirely in Intentsity, the service is said to be self contained.

Scripts within native Intentsity actions are written in Python.   


## Creator Callback URLs

As mentioned above, creators are responsible for maintaining two REST URL endpoints for the data molecules under their care.  

### Data

The creator element creation endpoint [/modeling/addcreator][23], is a POST endpoint.  One of the json attributes that must be 

### Stimulus
  
wwww


## Runtime

### Events

When the creator app is ready to inform potential event subscribers of a data update, it calls /action/event. This will update the version of the relevant data molecule node and call all compatible event services.  


 
# Other Significant Features


## No Data is Stored in the Graph!

Intentsity’s graph does not store data, only the metadata needed for establishing semantics and links required for establishing relationships between those bits of metadata.  The creator nodes do tell a bit about the app that manages the relevant service or data.  Owner nodes only ever show a unique UUID, but the owner remains anonymous. 


## Accommodation for Intelligent Agents
 
 Intentsity is AI friendly.  Its graph can be read and examined by intelligent agents.  It represents a closed system, with a clear set of rules and possible actions.  The following methods from the [Graphyne Graph API ][24]are exposed via REST.
 
[getClusterJSON][25] via [/ai/getClusterJSON/][26]
[getEntityHasProperty][27] via [/ai/getEntityHasProperty][28]
[getEntityMemeType][29] via [/ai/getEntityMemeType/][30]
[getEntityPropertyType][31] via [/ai/getEntityPropertyType][32]
[getEntityPropertyValue][33] via [/ai/getEntityPropertyValue][34]
[getLinkCounterparts][35] via [/ai/getLinkCounterparts][36]
[getLinkCounterpartsByType][37] via [/ai/getLinkCounterpartsByType][38]



## Custom Actions and Stimuli


 
 

[1]:	https://github.com/davidhstocker/Graphyne
[2]:	https://github.com/davidhstocker/Memetic
[3]:	https://github.com/davidhstocker/Graphyne#subgraphs-and-clusters
[4]:	https://github.com/davidhstocker/Graphyne#creating-entities
[5]:	https://github.com/davidhstocker/Graphyne#singletons
[6]:	https://github.com/davidhstocker/Memetic#memes
[7]:	https://github.com/davidhstocker/Graphyne#creating-entities
[8]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addowner
[9]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addcreator
[10]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#adddatamolecule
[11]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addmolecuenode
[12]:	https://github.com/davidhstocker/Graphyne#singleton-bridges
[13]:	https://en.wikipedia.org/wiki/Measure_(data_warehouse)
[14]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addtag
[15]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addentitylink
[16]:	https://github.com/davidhstocker/Memetic#directionality
[17]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addproperty
[18]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#assigntagproperty
[19]:	https://github.com/davidhstocker/Graphyne#subgraphs-and-clusters
[20]:	https://github.com/davidhstocker/Graphyne#singleton-bridges
[21]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addservicemolecule
[22]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addintentmolecule
[23]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#addcreator
[24]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md
[25]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getclusterjson
[26]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getcluster
[27]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getentityhasproperty
[28]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getentityhasproperty
[29]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getentitymemetype
[30]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getentitymemetype
[31]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getentitypropertytype
[32]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getentitypropertytype
[33]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getentitypropertyvalue
[34]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getentitypropertyvalue
[35]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getlinkcounterparts
[36]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getlinkcounterparts
[37]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Graph%20API%20Methods.md#getlinkcounterpartsbytype
[38]:	https://github.com/davidhstocker/Intentsity/blob/master/Docs/Intentsity%20API%20Reference.md#getlinkcounterpartsbytype

[image-1]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_Connection.png
[image-2]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_MoleculeData.png
[image-3]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_Connection.png
[image-4]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_TagInheritance.png
[image-5]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_MoleculeData2.png
[image-6]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_MoleculeService.png
[image-7]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_Connection.png
[image-8]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_ConnectionAdvanced.png
[image-9]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_ConnectionAdvanced2.png