#!/usr/bin/env python3

import sys
try:
    import yaml
    import json
    from multiprocessing import Process, Queue
    import argparse
    import jsonschema
    import os
    import datetime
    import time
    import subprocess
    import string
    import re
    import shutil

except ModuleNotFoundError as ex:
    print(ex)
    sys.exit(1)

from checker import *
from tests import *
import init


onlyTest = False
killResources = False
noTerraform = False
testsCatalog = ""
cfgPathCLI = None
tcPathCLI = None
usePrivateIPs = False
instanceDefinition = ""
extraInstanceConfig = ""
dependencies = ""
credentials = ""
totalCost = 0
procs = []
viaBackend = False
resultsExist = False
interactive = True
retry = None
destroy = None
destroyOnCompletion = None
clustersToDestroy = None
customNodes = None


def header(noLogo=False, provider=None, results=None):
    """ Prints the header according to parameters.

    Parameters:
        noLogo (bool): Specifies whether "EOSC" has to be shown or not.
        provider (str): Provider on which the suite is being run.
        results (str): Path to the results folder for the current run.
    """

    if noLogo is True:
        if provider is not None:
            if results is None:
                showThis = ["EOSC Cloud Validation Test Suite",
                    "Developed by CERN IT-EFP (ignacio.peluaga.lozada AT cern.ch)",
                    ".........................................................",
                            "Cloud: %s" % provider]
            else:
                showThis = ["EOSC Cloud Validation Test Suite",
                    "Developed by CERN IT-EFP (ignacio.peluaga.lozada AT cern.ch)",
                    ".........................................................",
                    "Cloud: %s" % provider,
                    "Results: results/%s" % results]
        else:
            showThis = ["EOSC Cloud Validation Test Suite",
                "Developed by CERN IT-EFP (ignacio.peluaga.lozada AT cern.ch)",
                "........................................................."]

        logger(showThis, "#", "src/logging/header", override=True)
        if onlyTest is True:
            writeToFile("src/logging/header", "(ONLY TEST EXECUTION)", True)

    else:
        if provider is not None:
            if results is None:
                showThis = ["                 | Cloud Validation Test Suite",
                "█▀▀ █▀▀█ █▀▀ █▀▀ | Developed by CERN IT-EFP",
                "█▀▀ █  █  ▀▄ █   | Contact: ignacio.peluaga.lozada AT cern.ch",
                "▀▀▀ ▀▀▀▀ ▀▀▀ ▀▀▀ | ..........................................",
                "  eosc-portal.eu | Cloud: %s" % provider]
            else:
                showThis = ["                 | Cloud Validation Test Suite",
                "█▀▀ █▀▀█ █▀▀ █▀▀ | Developed by CERN IT-EFP",
                "█▀▀ █  █  ▀▄ █   | Contact: ignacio.peluaga.lozada AT cern.ch",
                "▀▀▀ ▀▀▀▀ ▀▀▀ ▀▀▀ | ..........................................",
                "  eosc-portal.eu | Cloud: %s" % provider,
                "                 | Results: results/%s" % results]
        else:
            showThis = ["                 | Cloud Validation Test Suite",
                "█▀▀ █▀▀█ █▀▀ █▀▀ | Developed by CERN IT-EFP",
                "█▀▀ █  █  ▀▄ █   | Contact: ignacio.peluaga.lozada AT cern.ch",
                "▀▀▀ ▀▀▀▀ ▀▀▀ ▀▀▀ | ..........................................",
                "  eosc-portal.eu | "]

        # this fixes encode errors experienced in some clouds
        try:
            logger(showThis, "#", "src/logging/header", override=True)
            if onlyTest is True:
                writeToFile("src/logging/header", "(ONLY TEST EXECUTION)", True)
        except BaseException as e:
            print("EOSC logo exception: " + str(e))
            header(noLogo=True, provider=provider, results=results)


# logo, no results, no provider
header()

# -----------------CMD OPTIONS--------------------------------------------
parser = argparse.ArgumentParser(prog="./test_suite",
                                 description='EOSC Test-Suite.',
                                 allow_abbrev=False)
parser.add_argument('-y',
                    help='No interactive.',
                    action='store_false',
                    dest="interactive")
parser.add_argument('-o','--onlyTest',
                    help='Only test run.',
                    action='store_true')
parser.add_argument('--usePrivateIPs',
                    help='Use private IPs.',
                    action='store_true')
parser.add_argument('--noTerraform',
                    help='Skip Terraform, run only Ansible.',
                    action='store_true')
parser.add_argument('-c','--configs',
                    help='Path to configs.',
                    type=str,
                    dest="cfgPathCLI")
parser.add_argument('-t','--testsCatalog',
                    help='Path to tests catalog.',
                    metavar="CATALOG",
                    type=str,
                    dest="tcPathCLI")
parser.add_argument('--destroy',
                    nargs='+',
                    dest="clustersToDestroy",
                    help='Destroy infrastructure.',
                    metavar="CLUSTERS",
                    choices=['all']+clusters,
                    type=str)
parser.add_argument('--destroyOnCompletion',
                    nargs='+',
                    dest="clustersToDestroyOnCompletion",
                    help='Destroy infrastructure at the end of the run.',
                    metavar="CLUSTERS",
                    choices=['all']+clusters)
parser.add_argument('--customNodes',
                    help='Use a specific amount of nodes.',
                    metavar="NODES",
                    type=int)
parser.add_argument('--noWatch', 
                    help='Do not use the watch function.',
                    action='store_true')

args = parser.parse_args()

if args.cfgPathCLI:
    cfgPathCLI = os.path.abspath(args.cfgPathCLI)
if args.tcPathCLI:
    tcPathCLI = os.path.abspath(args.tcPathCLI)
if args.interactive:
    interactive = args.interactive # disables prompts of overriding tf files and deleting infrastructure
if args.onlyTest:
    onlyTest = args.onlyTest
if args.usePrivateIPs:
    usePrivateIPs = args.usePrivateIPs
if args.customNodes:
    customNodes = args.customNodes
if args.noTerraform:
    noTerraform = True
if args.clustersToDestroy:
    clustersToDestroy = args.clustersToDestroy
    if "all" in clustersToDestroy:
        clustersToDestroy = clusters
    if interactive is False:
        destroyTF(baseCWD, clusters=clustersToDestroy)
    elif input(destroyWarning % clustersToDestroy) == "yes":
        destroyTF(baseCWD, clusters=clustersToDestroy)
    else:
        print("Aborting operation")
    stop(0)
if args.clustersToDestroyOnCompletion:
    clustersToDestroy = args.clustersToDestroyOnCompletion
    if "all" in clustersToDestroy:
        clustersToDestroy = clusters
    destroyOnCompletion = True


# -----------------CHECKS AND PREPARATION---------------------------------
selectedTests = init.initAndChecks(noTerraform,
                                   extraSupportedClouds,
                                   usePrivateIPs,
                                   cfgPathCLI=cfgPathCLI,
                                   tcPathCLI=tcPathCLI)

configs = init.configs
testsCatalog = init.testsCatalog

# logo, no results but provider
header(provider=configs["providerName"])


if not selectedTests:
    writeToFile("src/logging/header",
                "No tests selected, nothing to do!", True)
    stop(0)

if retry is True:
    checkRequiredTFexist(selectedTests)


# -----------------CREATE RESULTS FOLDER AND GENERAL FILE------------------
s3ResDirBase = configs["providerName"] + "/" + str(
    datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))
resDir = "results/%s/detailed" % s3ResDirBase
os.makedirs(resDir)
generalResults = {
    "testing": []
}

# logo with provider and results
header(provider=configs["providerName"], results=s3ResDirBase)


# -----------------RUN TESTS-----------------------------------------------
queue = Queue()
init.queue = queue
cluster = 1

msgArr = ["CLUSTER %s: (parallel running tests):" % (cluster)]
for test in testsSharingCluster:
    if testsCatalog[test]["run"] is True:
        msgArr.append(test)

if len(msgArr) > 1:
    if customNodes is not None:
        numberOfNodes = customNodes
    else:
        numberOfNodes = len(msgArr) - 1
    p = Process(target=sharedClusterTests, args=( # shared cluster provisioning
        msgArr, onlyTest, retry, noTerraform, resDir, numberOfNodes, usePrivateIPs))
    procs.append(p)
    p.start()
    cluster += 1

for test in customClustersTests:
    if testsCatalog[test]["run"] is True:
        logger("CLUSTER %s: %s" % (cluster, test),
               "=", "src/logging/%s" % test)
        p = Process(target=eval(test), args=( # custom clusters provisioning
            onlyTest, retry, noTerraform, resDir, usePrivateIPs))
        procs.append(p)
        p.start()
        cluster += 1

for p in procs:  # All tests launched (functions run): wait for completion
    p.join()

while not queue.empty():
    entry, cost = queue.get()
    if entry:
        generalResults["testing"].append(entry)
    totalCost += cost

if checkResultsExist(resDir) is True:
    # -----------------CALCULATE COSTS-----------------------------------------
    if totalCost > 0:
        generalResults["estimatedCost"] = totalCost
    else:
        writeToFile(
            "src/logging/footer",
            "(Costs aren't correctly set: calculation will not be made)",
            True)

    # -----------------MANAGE RESULTS------------------------------------------

    generalResults["info"] = configs
    generalResults["testsCatalog"] = testsCatalog

    with open("results/" + s3ResDirBase + "/general.json", 'w') as outfile:
        json.dump(generalResults, outfile, indent=4, sort_keys=True)

    msg1 = "TESTING COMPLETED"
    # No results push if local run (only ts-backend has AWS creds for this)
    if viaBackend is True:
        s3Endpoint = "https://s3.cern.ch"
        bucket = "s3://ts-results"
        pushResults = runCMD(
            "aws s3 cp --endpoint-url=%s %s %s/%s --recursive > /dev/null" %
            (s3Endpoint, "results/" + s3ResDirBase, bucket, s3ResDirBase))
        runCMD("cp results/%s/general.json .. " % s3ResDirBase)
        if pushResults != 0:
            logger("S3 upload failed! Is 'awscli' installed and configured?",
                   "!", "src/logging/footer")
        else:
            logger([msg1, "Results on the S3 bucket"],
                   "#", "src/logging/footer")
    else:
        logger(msg1, "*", "src/logging/footer")

    if destroyOnCompletion == True:
        for cluster in clustersToDestroy:
            if checkClusterWasProvisioned(cluster, generalResults["testing"]):
                if destroyTF(baseCWD, clusters=[cluster])[0] != 0:
                    msg = "   ...destroy failed. Check 'logs' file for details"
                else:
                    msg = "   ...cluster destroyed"
                writeToFile("src/logging/footer", msg, True)
    else:
        writeToFile("src/logging/footer", "No destroy scheduled", True)

else:

    # logo with provider, no results
    header(provider=configs["providerName"])
    shutil.rmtree("results/" + s3ResDirBase, True)


logger("Run completed", "#", "src/logging/end")
stop(0)
