#!/usr/bin/env python3


import sys
try:
    import os
    import time
    import string
    import threading
    from multiprocessing import Process, Queue
    import contextlib
    import io
except ModuleNotFoundError as ex:
    print(ex)
    sys.exit(1)
from aux import *
from init import *
from kubernetesFunctions import *
from ansibleFunctions import *


provisionFailMsg = "Failed to provision raw VMs. Check 'logs' file for details"
bootstrapFailMsg = "Failed to bootstrap '%s' k8s cluster. Check 'logs' file"
msgRoot = "WARNING: default user 'root' for ssh connections (running on %s)"
clusterCreatedMsg = "...%s CLUSTER CREATED (masterIP: %s) => STARTING TESTS\n"
TOserviceAccountMsg = "ERROR: timed out waiting for %s cluster's service account\n"


def runTerraform(toLog, cmd, mainTfDir, baseCWD, test, msg, terraform_cli_vars=None):
    """Run Terraform cmds.

    Parameters:
        mainTfDir (str): Path where the .tf file is.
        baseCWD (str): Path to go back.
        test (str): Cluster identification.
        msg (str): Message to be shown.
        terraform_cli_vars (str): CLI vars to be appended to the cmd.

    Returns:
        int: 0 for success, 1 for failure
    """

    if terraform_cli_vars is not None:
        with open(mainTfDir + "/terraform.tfvars.json", 'w') as varfile:
            json.dump(terraform_cli_vars, varfile, indent=4, sort_keys=True)

    writeToFile(toLog, msg, True)
    os.chdir(mainTfDir)

    tfScript = """
    ((%s) && touch /tmp/validTFrun) |

    while read line; do echo [ %s ] $line; done

    if [ -f /tmp/validTFrun ]; then
    	rm -f /tmp/validTFrun
    	exit 0
    fi
    exit 1
    """ % (cmd, test)

    exitCode = runCMD(tfScript)
    os.chdir(baseCWD)
    return exitCode


def destroyTF(baseCWD, clusters=None):
    """Destroy infrastructure. 'clusters' is an array whose objects specify
       the clusters that should be destroyed. In case no array is given, all
       clusters will be destroyed.

    Parameters:
        baseCWD (str): Path to go back.
        clusters (Array<str>): Clusters to destroy.

    Returns:
        Array<int>: 0 for success, 1 for failure
    """

    if clusters is None:
        clusters = ["shared", "dlTest", "hpcTest"]

    res = []
    for cluster in clusters:
        toLog = "src/logging/footer"
        msg = "  -Destroying %s cluster..." % cluster
        mainTfDir = "src/tests/%s" % cluster
        cmd = "terraform destroy -auto-approve"
        exitCode = runTerraform(toLog, cmd, mainTfDir, baseCWD, cluster, msg)
        #if all(x == 0 for x in exitCode) is True:
        if exitCode is 0:
            cleanupTF("src/tests/%s/" % cluster)
        else:
            print("WARNING: terraform destroy did not succeed completely, tf files not deleted.")
        res.append(exitCode)

    return res


def cleanupTF(mainTfDir):
    """Delete existing terraform stuff in the specified folder.

    Parameters:
        mainTfDir (str): Path to the .tf file.
    """

    for filename in [
        "hosts",
        "config",
        "main.tf",
        "terraform.tfvars",
        "terraform.tfvars.json",
        "terraform.tfstate",
        "terraform.tfstate.backup",
            ".terraform"]:
        file = "%s/%s" % (mainTfDir, filename)
        if os.path.isfile(file):
            os.remove(file)
        if os.path.isdir(file):
            shutil.rmtree(file, True)


def terraformProvisionment(
        test,
        nodes,
        flavor,
        extraInstanceConfig,
        toLog,
        configs,
        cfgPath,
        testsRoot,
        retry,
        instanceDefinition,
        credentials,
        dependencies,
        baseCWD,
        provDict,
        extraSupportedClouds):
    """Provisions VMs on the provider side and creates a k8s cluster with them.

    Parameters:
        test (str): Indicates the test for which to provision the cluster
        nodes (int): Number of nodes the cluster must contain.
        flavor (str): Flavor to be used for the VMs.
        extraInstanceConfig (str): Extra HCL code to configure VM
        toLog (str): File to which write the log msg.
        configs (dict): Object containing configs.yaml's configurations.
        testsRoot (str): Tests directory root.
        retry (bool): If true, retrying after a failure.
        instanceDefinition (str): HCL code definition of an instance.
        credentials (str): HCL code related to authentication/credentials.
        dependencies (str): HCL code related to infrastructure dependencies.
        baseCWD (str): Path to the base directory.
        provDict (dict): Dictionary containing the supported clouds.
        extraSupportedClouds (dict): Extra supported clouds.

    Returns:
        bool: True if the cluster was succesfully provisioned. False otherwise.
        str: Message informing of the provisionment task result.
    """

    templatesPath = "src/provisionment/tfTemplates/general"
    if configs["providerName"] in extraSupportedClouds:
        templatesPath = "src/provisionment/tfTemplates/%s" % configs["providerName"]

    mainTfDir = testsRoot + test
    terraform_cli_vars = {}
    cfgPath = "%s/%s" % (baseCWD, cfgPath)
    kubeconfig = "%s/src/tests/%s/config" % (baseCWD, test)

    if test == "shared":
        flavor = configs["flavor"]
        mainTfDir = testsRoot + "shared"
        os.makedirs(mainTfDir, exist_ok=True)
        kubeconfig = "~/.kube/config"

    if retry is None:
        randomId = getRandomID() # One randomId per cluster

        nodeName = getNodeName(configs, test, randomId)

        # ---------------- delete TF stuff from previous run if existing
        cleanupTF(mainTfDir)

        # ---------------- manage general variables
        openUser = tryTakeFromYaml(configs,
                                   "openUser",
                                   "root",
                                   msgExcept=msgRoot % configs["providerName"])

        variables = loadFile("src/provisionment/tfTemplates/general/variables.tf", required=True)

        variables = variables.replace(
            "NODES_PH", str(nodes)).replace(
            "PATH_TO_KEY_VALUE", str(configs["pathToKey"])).replace(
            "NAME_PH", nodeName)

        terraform_cli_vars["dockerCE"] = tryTakeFromYaml(configs, "dockerCE", None)
        terraform_cli_vars["dockerEngine"] = tryTakeFromYaml(configs, "dockerEngine", None)
        terraform_cli_vars["kubernetes"] = tryTakeFromYaml(configs, "kubernetes", None)

        writeToFile(mainTfDir + "/main.tf", variables, False) # TODO: do this with terraform_cli_vars too (yamldecode)

        if configs["providerName"] not in extraSupportedClouds:
            # ---------------- main.tf: add raw VMs provisioner
            instanceDefinition = "%s \n %s" % (flavor,
                instanceDefinition.replace(
                    "NAME_PH", "${var.instanceName}-${count.index}"))

            if extraInstanceConfig:
                instanceDefinition += "\n" + extraInstanceConfig

            rawProvisioning = loadFile("%s/rawProvision.tf" %
                                       templatesPath).replace(
                "CREDENTIALS_PLACEHOLDER", credentials).replace(
                "DEPENDENCIES_PLACEHOLDER", dependencies.replace(
                    "DEP_COUNT_PH", "count = %s" % nodes)).replace(
                "PROVIDER_NAME", str(configs["providerName"])).replace(
                "PROVIDER_INSTANCE_NAME", str(
                    configs["providerInstanceName"])).replace(
                "NODE_DEFINITION_PLACEHOLDER", instanceDefinition)

        else:

            rawProvisioning = loadFile("%s/rawProvision.tf" % templatesPath, required=True)

            terraform_cli_vars["configsFile"] = cfgPath
            terraform_cli_vars["flavor"] = flavor
            terraform_cli_vars["customCount"] = nodes
            terraform_cli_vars["instanceName"] = nodeName

            if configs["providerName"] == "azurerm":

                terraform_cli_vars["clusterRandomID"] = randomId # var.clusterRandomID to have unique interfaces and disks names
                terraform_cli_vars["publisher"] = tryTakeFromYaml(configs, "image.publisher", "OpenLogic")
                terraform_cli_vars["offer"] = tryTakeFromYaml(configs, "image.offer", "CentOS")
                terraform_cli_vars["sku"] = str(tryTakeFromYaml(configs, "image.sku", 7.5))
                terraform_cli_vars["imageVersion"] = str(tryTakeFromYaml(configs, "image.version", "latest"))

            if configs["providerName"] == "openstack":

                networkName = tryTakeFromYaml(configs, "networkName", False)
                if networkName is not False:
                    terraform_cli_vars["useDefaultNetwork"] = False
                terraform_cli_vars["region"] = tryTakeFromYaml(configs, "region", None)
                terraform_cli_vars["availabilityZone"] = tryTakeFromYaml(configs, "availabilityZone", None)

            if configs["providerName"] == "google":

                terraform_cli_vars["gpuCount"] = nodes if test == "dlTest" else "0"
                terraform_cli_vars["gpuType"] = tryTakeFromYaml(configs, "gpuType", None)

            if configs["providerName"] in ("aws", "cloudstack", "google", "openstack", "opentelekomcloud", "exoscale"):

                terraform_cli_vars["securityGroups"] = tryTakeFromYaml(configs, "securityGroups", None)

            if configs["providerName"] in ("cloudstack", "oci", "aws", "google"):

                terraform_cli_vars["storageCapacity"] = tryTakeFromYaml(configs, "storageCapacity", None)


        writeToFile(mainTfDir + "/main.tf", rawProvisioning, True)

        # ---------------- RUN TERRAFORM: provision VMs
        beautify = "terraform fmt > /dev/null &&"
        cmd = "terraform init && %s terraform apply -auto-approve" % beautify
        if runTerraform("src/logging/%s" % test,
                        cmd,
                        mainTfDir,
                        baseCWD,
                        test,
                        "Provisioning '%s' VMs..." % flavor,
                        terraform_cli_vars=terraform_cli_vars) != 0:
            return False, provisionFailMsg

    # ---------------- RUN ANSIBLE (first create hosts file)
    result, masterIP = ansiblePlaybook(mainTfDir,
                                       baseCWD,
                                       configs["providerName"],
                                       kubeconfig,
                                       None,
                                       test,
                                       configs["pathToKey"],
                                       openUser,
                                       configs)
    if result != 0:
        return False, bootstrapFailMsg % test

    # ---------------- wait for default service account to be ready and finish
    if waitForSA(kubeconfig) == 0:
        writeToFile(toLog, clusterCreatedMsg % (test, masterIP), True)
        return True, ""
    else:
        return False, TOserviceAccountMsg % test
