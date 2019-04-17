
# Stimuli

## Introduction

Imagine a bird, sitting in a tree and singing.  What sort of sensory experience would you have?  If you had all your faculties and were standing under the tree, you’d see its plumage and hear its song.  But what if you were deaf?  Then you’d only see the plumage and possible see it opening its beak in song.  What if you were blind?  You’d only hear the song.

Now what if you were not physically present, but but only digitally?  If your client was a text client, or a voiced agent, you’d get textual description of the birdsong and the plumage.  A voice bot could even play the song for you.  If you were using a 3D or virtually reality client, you’d see a digital representation of the bird and hear it’s song.

What if your vision - the the virtual vision of your client - was not limited to the trichromatic vision of humans, but had the tetra-chromatic (four channel) vision of a bird or reptile.  You’d see the plumage entirely differently.

![][image-1]

Now imagine that you are playing a multiplayer game, with a friend.  You encounter someone - either an ai driven character or another player.  Your friend sees an innocent little girl, but that’s not what you see.  You see the digital avatar differently.  You see a dangerous demon.  Is what you see or is what your friend sees correct?  That might depend on the context and what your digital capabilities are within the game.  Either way, it is a far richer experience than if you both saw the same thing.

![][image-2]

In all of the above examples, stimuli recipients are processing stimuli differently and in some cases, filtering stimuli.  Intentsity’s stimulus engine is built around this concept of filtering and fine tuning what information is distributed to whom.  

The kinds of stimuli processed and distributed could be anything.  Some examples include, but are not limited to:


- Context appropriate 3D model, texture and shader information for a 3D, VR or augmented reality app.
- Audio
- Multilingual, dynamic text for human consumption, delivered in the preferred language of the consumer.  Intentsity has built in support for such multi-lingual, dynamic text content.
- Intelligent agent friendly semantic information.

Stimuli contain rules for deciding which controllers; using Graphyne conditions.  They also contain descriptors, which define how stimuli should be formatted for distribution.  

## Standard Stimuli

There are three types of standard stimuli used in Intentsity.  
- **JSON** - A stimulus that returns arbitrary JSONs.  By default, most service molecules will use json stimuli to report back to relevant agents.  
- **Text** - This is just a pass through, which will pass along any text string, from actual text to base 64 encoded objects.  
- **Internationalized Text** - This is a translatable, dynamic text element.  In fact, it is a series of parallel (per language) dynamic text stimuli.  Intentsity’s Internationalized Text  processing is flexible and powerful.
- **Custom** - It is also possible to create your own custom stimuli, if one of the above does not do the job.

There are always standard JSON and Text stimuli available to any action.  These are invoked by calling certain actions, specifically Stimulus.PostJSON and Stimulus.PostText and passing the desired output as parameters.

todo  howto

## How Stimuli Work

Stimuli are contained in bundles of one or more stimuli.  In the graph, this is represented by them being connected to a shared parent element, from the Stimulus.StimulusChoice metameme.   It contains a number of Stimulus.ConditionalStimulus entities.  These are Stimulus.Stimulus entities, pared with conditions.  When a stimulus is StimulusChoice entity is referred for processing by an action, the following happens:

1. The flagging action may or may not pass along a list of specific agents, intended as targets.
2. For each of the Stimulus.ConditionalStimulus entities, the conditions are evaluated, to determine the distribution list.  Depending on the condition, the possible recipients might be limited to the proposed list of agents, or they could come from anywhere in the graph.
3. For each Stimulus.ConditionalStimulus entity with a non empty recipient list, a report is generated.
4. If a report requires “resolving”, it is resolved.  An example of resolving is the dynamic text of an internationalized descriptor being constructed.
5. The resolved report is queued for distribution to the destination agents.


![][image-3]


## Invoking Stimuli

stub


## Stimulus Design

If you want to construct your own stimulus, you will need to use the following graph pattern.  

![][image-4]

Action can have a Stimulus.StimulusChoice member.  This is your hook.  StimulusChoice elements in turn can have 1..n ConditionalStimulusMembers.  Each has exactly one [Graphyne.Condition.Condition][1] member and a Stimulus.Stimulus member.  Then the condition in the condition is met, the the stimulus is forwarded.  If you don’t actually want any specific conditions, you can simply use [Graphyne.Condition.True][2] and the stimulus will be forwarded.  You would use this when you have a specific list of agents that you want to message and don’t need or want any additional filtering or selection.

### Stimulus.Stimulus

![][image-5]

Stimulus.Stimulus is itself a [switch][3].  It can have either a Stimulus.AnchoredStimulus or a Stimulus.FreeStimulus child.  The difference between these is that an anchored stimulus is a stimulus that has no semantic meaning without some other stimulus to provide context, the anchor, while a free stimulus is free standing. Take the leaves on a tree for example.  You would not want to describe the leaves on a tree, without the tree itself.  

The tree would be free standing.
The leaves would be anchored .  

You actually have several ways that you could construct this:
- Leaves and tree both in the same StimulusChoice.  The leaves use Graphyne.ContitionTrue, but is anchored.  The tree uses whatever stimulus.  In this case, the leaves are passed to the agent client app, even if the tree is not, but the renderer (whatever is presenting the stimulus to the end user in whichever format) is informed that the leaves make no sense without the tree.  It is then up to the renderer to decide what to do.
- Both leaves and tree use the same condition and are both free stimuli.  Either both are passed or both are not.
- Both leaves and tree use the same condition, but leaves are an anchored stimulus.  This is the most robust method, because either both are sent to the renderer, or neither is, but if they are sent, the renderer is informed that the leaves are semantically attached to the tree.

Both free stimuli and anchored stimuli use a similar graph pattern, where the free stimulus is slightly simpler.

### Stimulus.FreeStimulus

![][image-6]

The free stimulus has a two branch structure in its graph.  

One of the branches is a Stimulus.Descriptor.  Like Stimulus.Stimulus, it is a switch.  Its child can be an InternationalizedDescriptor, a text, a JSON or another custom descriptor, derived from the Stimulus.Descriptor metameme.  The free text and JSON descriptors are both singletons, Stimulus.FreeText and Stimulus.JSON respectively.  InternationalizedDescriptor is a metameme and any multi-lingual or dynamic text elements needs to be derived from it.  Designers are  also free to build any other descriptors that they wish.  

Descriptors are executable entities, following the [State Event Script][4] pattern.

The other branch is a Stimulus.StimulusScope, which in turn, connects to an Agent.Scope, which on turn connect to one or more Agent.Page elements.  Agent.Page memes are [singletons][5] and are used as a generic filtering mechanism.  Agent.Scope is a collector, allowing us to link 0..n Agent.Page elements.  Stimulus.StimulusScope, by connecting a Stimulus to Agent.Scope, allows us to re-use that graph pattern, rather than needlessly duplicating it.  

#### Scope and Page

So what is going on with scope ’scope’ and ‘page’?  It is actually quite simple.  They are direct metaphors.  Think of a a window in a building and a person is visible from the outside through one or more windows.  Each of these windows would be the page that the person is visible on.  If you can see that page, it is said to be in scope, from your perspective.  When an agent is assigned to a page, it is only ‘visible’ to stimuli that have that page in scope.  

In practical terms, this is useful as a group rights mechanism.  If I want to restrict a stimulus to a selected group of agents, or a certain kind of agent (e.g. owners or creators), I would make sure that its scope matches a page used by that group.  


### Stimulus.AnchoredStimulus

![][image-7]

The AnchoredStimulus is a superset of the FreeStimulus pattern.  The only difference is the addition of a Stimulus.StimulusAnchor child of Stimulus.Stimulus.  Stimulus.StimulusAnchor is a collector of other Stimulus.Stimulus.  They are not resolved, but their meme ID is simply passed along to the receiving client. If and how to present anchored stimuli is left to the client.


### InternationalizedDescriptor

stub


### Custom Descriptors

stub





[1]:	https://github.com/davidhstocker/Graphyne/blob/master/Docs/Conditions.md#overview
[2]:	https://github.com/davidhstocker/Graphyne/blob/master/Graphyne/Condition.xml
[3]:	https://github.com/davidhstocker/Memetic/blob/master/README.md#exclusive-membership-switch
[4]:	https://github.com/davidhstocker/Graphyne/blob/master/README.md#graphynednastateeventscript-memes
[5]:	https://github.com/davidhstocker/Graphyne/blob/master/README.md#singletons

[image-1]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/PictureStimuli.png
[image-2]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/PictureStimuli2.png
[image-3]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsity_StimulusWorkflow.png
[image-4]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsit_Stimuli1.png
[image-5]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsit_Stimuli2.png
[image-6]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsit_Stimuli3.png
[image-7]:	https://raw.githubusercontent.com/davidhstocker/Intentsity/master/Docs/images/Intentsit_Stimuli4.png