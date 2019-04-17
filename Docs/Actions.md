
# Actions

## Introduction

Every service, whether an event or intent, is either self-contained, or a callback service.  Callback services provide a REST URL, which Intentsity will call when the service is invoked.  Essentially, Intentsity is brokering the REST API call by measuring compatibility and forwarding the invocation to the target URL.  

There is an alternative way for services to work, without using an external callback URL.  They can can execute a native Intentsity action. The default action, that is executed when a service is invoked, requests the callback URL.  If an alternative action is supplied instead and runs entirely in Intentsity, the service is said to be self contained.

Scripts within native Intentsity actions are written in Python.   


## Standard Actions

stub


## Custom Actions

stub


