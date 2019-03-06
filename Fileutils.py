'''
Created on June 13, 2018

@author: David Stocker
'''

import re
import os
import codecs
import zipfile
import importlib

import Graphyne.Graph as Graph


#globals
moduleName = 'fileutils'
logType = Graph.logTypes.ENGINE
logLevel = Graph.LogLevel()
tiogaHome = os.path.dirname(os.path.abspath(__file__))



def modulePathToFilePath(modulePath):
    splitPath = re.split('\.', modulePath)
    filePath = os.path.join(tiogaHome, splitPath[0])
    splitPath.remove(splitPath[0])
    for fragment in splitPath:
        filePath = os.path.join(tiogaHome, fragment)
    return filePath



def getModuleFromResolvedPath(fullModuleName):
    try:
        x = importlib.import_module(fullModuleName)
        for fragment in fullModuleName.split('.')[1:]:
            x = getattr(x, fragment)
        return x
    except Exception as e:
        unused_errorMsg = "unable to resolve module at path %s" %fullModuleName
        raise e



def ensureDirectory(targetDir):
    '''Endure that targetDir exists, by creating whatever part of the tree is required '''
    firstGoodAncestor = targetDir
    badAncestors = []
    while not os.access(firstGoodAncestor, os.F_OK):
        tempTuple = os.path.split(firstGoodAncestor)
        firstGoodAncestor = tempTuple[0]
        badAncestors.insert(1, tempTuple[1])
        
    for badAncestor in badAncestors:
        targetDir = os.path.join(firstGoodAncestor, badAncestor)
        print(("creating %s" %targetDir))
        try:
            os.mkdir(targetDir)
        except OSError as e:
            catch = "me"
        
    
    
def getCodePageFromFile(fileURI):
    return "utf-8"



# A recursive examiner for package subdirectories
def walkDirectory(workingDir, packagePath):
    #Go through the subdirectory and load the files up 
    #method = moduleName + '.' + 'walkDirectory'
    
    if packagePath is None:
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Branch is directly off the root'])
        pass
        
    pathSet = {}  # A dict object containing all modules.  Key = module path.  Data = filedata
    dirList = os.listdir(workingDir)
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Child dirs of package path %s ' % packagePath])
    #for nextdir in dirList:
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '... %s ' % dir])
        #pass
        
    for dirEntity in dirList:
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Examining %s' % dirEntity])
        trimmedfile = re.split('\.', dirEntity)
        if packagePath is not None:
            localPackagePath = packagePath + '.' + trimmedfile[0]
        else:
            localPackagePath = trimmedfile
        
        fileName = os.path.join(workingDir, dirEntity)
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'package path = %s' % localPackagePath])
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Examining %s' % fileName])
        #logging.logger.logDebug( method, 'Examining %s' % fileName)
        fileData = {}
        if (os.path.isdir(fileName)) and (re.search( '.', localPackagePath) is None):
            # ensuring that there are no dots in localPackagePath is a workaround to prevent
            #   the engine from choking on repositories that are in versioning repositories, such as svn
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a directory' % fileName])
            pathSubSet = walkDirectory(fileName, localPackagePath)
            pathSet.update(pathSubSet)
        elif re.search( '.py', fileName) is not None:
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a python file' % fileName])
            pass
        elif re.search( '.xml', fileName) is not None:
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is an xml file' % fileName])
            codepage = getCodePageFromFile(fileName)
            fileObj = codecs.open( fileName, "r", codepage )
            fileStream = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in the file   
            fileData[fileStream] = codepage
            pathSet[localPackagePath] = fileData
        else:
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is not a directory, xml or python file and will be ignored' % fileName])
            pass
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return pathSet



def walkRepository():
    method = moduleName + '.' + 'walkRepository'

    dataLocation = os.path.join(tiogaHome, 'IntentsityRepository', 'IntentsitySchema')
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'RML Repository location is %s' % dataLocation])
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Ready to start walking the files of the repository']) 
    
    #Go through the condition repository directory and load the files up
    pathSet = {} 
    packageList = os.listdir(dataLocation)
    for package in packageList:
        #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Examining %s' % package])
        fileName = os.path.join(dataLocation, package)
        fileData = {}
        fileStream = None
        trimmedPackage = re.split('\.', package)
        packagePath = trimmedPackage[0]
        #packages will be zip files.  Free modules wll not be
        try:
            z = zipfile.ZipFile(fileName)
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a zip archve' % fileName])
            #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s contains the following files: %s' % (fileName, z.namelist())])
            for nextFile in z.namelist():
                trimmedfile = re.split('\.', nextFile)
                localPackagePath = packagePath + '.' + trimmedfile[0]
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Examining %s' % localPackagePath])
                try:
                    #if os.path.isdir(file):
                        ##Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a directory' % file)
                        #pathSubSet = walkDirectory(file, localPackagePath)
                        #pathSet.update(pathSubSet)
                    if re.search( '.py', nextFile) is not None:
                        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a python file' % file])
                        pass
                    elif re.search( '.xml', nextFile) is not None:
                        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is an xml file' % file])
                        codepage = getCodePageFromFile(nextFile)
                        fileObj = z.read(nextFile)
                        fileStream = str(fileObj, codepage)
                        fileData[fileStream] = codepage
                        pathSet[localPackagePath] = fileData
                        ##Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s fileStream = %s' % (fileName, fileStream))
                        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s codepage = %s' % (fileName, codepage)])
                        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s packagePath = %s' % (fileName, localPackagePath)])
                    else:
                        #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is not a directory, xml or python file and will be ignored' % file])
                        pass
                except Exception as e:
                    Graph.logQ.put( [logType , logLevel.WARNING , method , u'Problem reading file %s.  "Traceback = %s' % (localPackagePath, e)])
        except:
            # if the file is not a zip, then we'll get this exception
            if os.path.isdir(fileName):
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is a directory' % fileName])
                pathSubSet = walkDirectory(fileName, packagePath)
                pathSet.update(pathSubSet)
            elif re.search( '.xml', fileName) is not None:
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is an xml file' % fileName])
                codepage = getCodePageFromFile(fileName)
                fileObj = codecs.open( fileName, "r", codepage )
                fileStream = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in the file 
                fileData[fileStream] = codepage
                pathSet[packagePath] = fileData
                ##Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s fileStream = %s' % (fileName, fileStream))
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s codepage = %s' % (fileName, codepage)])
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s packagePath = %s' % (fileName, packagePath)])
            else:
                #Graph.logQ.put( [logType , logLevel.DEBUG , method , '%s is not a directory or xml file and will be ignored' % fileName])
                pass
        
                
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , 'Finished walking directories under %s' % dataLocation])
    #Graph.logQ.put( [logType , logLevel.DEBUG , method , "exiting"])
    return pathSet



def defaultCSS():
    ''' A default CSS stylesheet  for formatting HTML generated by Angela Utilities'''
    subdivision = "table.subdivision = {border-style:solid}"
    tableheader = "thead.tableheader {font-size:1.35em;font-weight:bolder}"
    badOVCell = "td.badOVCell {background-color:LightPink}"
    goodOVCell = "td.goodOVCell {background-color:LightGreen}"
    tableHeaderRow = "th.tableHeaderRow {text-align:center;padding-right:50px}"
    badDRow = "tr.badDRow {background-color:LightPink;color:black;font-weight:bold;padding-right:50px;padding-left:10px;padding-top:10px;text-align:top}"
    goodDRow = "tr.goodDRow {background-color:white;color:black;padding-right:50px;padding-left:10px;padding-top:10px;text-align:top}"
    badOverviewRow = "tr.badOverviewRow {background-color:LightPink;color:black;font-weight:bold;padding-right:10px;padding-left:10px;padding-top:10px;text-align:top}"
    goodOverviewRow = "tr.goodOverviewRow {background-color:LightGreen;color:black;padding-right:10px;padding-left:10px;padding-top:10px;text-align:top}"
    detailsCell = "td.detailsCell {padding-right:50px;padding-left:10px;padding-top:10px;text-align:top}"
    vBlankSpace = "div.vBlankSpace {padding-top:100px}"
    hBlankSpace = "div.hBlankSpace {padding-left:100px}"
    vAlignment = "div.vAlignment {margin-top:10px}"
    
    defaultCSS = "<!--\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n-->" %(subdivision, tableheader, badOVCell, goodOVCell, badDRow, goodDRow, badOverviewRow, goodOverviewRow, tableHeaderRow, detailsCell, vBlankSpace, hBlankSpace, vAlignment)
    return defaultCSS

    

