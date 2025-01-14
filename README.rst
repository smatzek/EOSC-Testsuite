============================================
EOSC Cloud Validation Test Suite
============================================

This tool is intended to be used to test and validate commercial cloud services across the stack for research and education environments and it is being used as a validation tool for commercial cloud services procurement in European Commission sponsored projects such as OCRE and ARCHIVER.

Visit |eosc| for more information.

.. |eosc| raw:: html

  <a href="https://www.eosc-portal.eu/" target="_blank">EOSC website</a>

.. header-end

Documentation
---------------------------------------------
The full documentation can be found |docs|.

.. |docs| raw:: html

  <a href="https://eosc-testsuite.readthedocs.io/en/latest/" target="_blank">here</a>


.. body

The test-suite executes four main steps:

1) Infrastructure provisioning: VMs are created using Terraform and then with these several Kubernetes clusters are bootstrapped by Ansible according to the selected tests.

2) Deploy the tests: Kubernetes resource definition files (YAML) are used to deploy the tests.

3) Harvest results: at the end of each test run a result file -written in JSON- is created. This file is collected from the pod running on the cluster.

4) Through a verification system, the Test-Suite can also be triggered from a service running at CERN. This is an optional step and in this case, results are then pushed to a S3 Bucket at CERN. (Under development)

The test set described in the `Tests Catalog <https://eosc-testsuite.readthedocs.io/en/latest/testsCatalog.html>`_ section of the documentation is based on the tests used in the |hnsc| PCP project funded by the European Commission.

.. |hnsc| raw:: html

  <a href="https://www.hnscicloud.eu" target="_blank">Helix Nebula The Science Cloud</a>

The developers would like to thank all test owners and contributors to this project.

**This suite has been tested on:**

+------------------------------+---------------------------------------------------------------------------------+
|OS on launcher machine        | Ubuntu, CentOS, CoreOS, Debian, RedHat, Fedora                                  |
+------------------------------+---------------------------------------------------------------------------------+
|OS running on provider's VMs  | CentOS7, Ubuntu 16.04, Ubuntu 18.04                                             |
+------------------------------+---------------------------------------------------------------------------------+
|Providers / clouds            | | AWS                                                                           |
|                              | | Google Cloud                                                                  |
|                              | | Microsoft Azure                                                               |
|                              | | Oracle Cloud Infrastructure                                                   |
|                              | | Exoscale (CloudStack)                                                         |
|                              | | T-Systems' Open Telekom Cloud (OpenStack)                                     |
|                              | | CERN Private Cloud (OpenStack)                                                |
|                              | | CloudFerro (OpenStack)                                                        |
|                              | | CloudStack                                                                    |
|                              | | OpenStack                                                                     |
|                              | | CloudSigma                                                                    |
+------------------------------+---------------------------------------------------------------------------------+

The suite is being tested in several additional cloud providers. As tests are concluded, the cloud providers names will be added in the table above.

Release notes
---------------------------------------------
(Note the versions are numbered with the date of the release: YEAR.MONTH)

``21.4 - latest``

- Cluster certificate additionally signed for NAT IP (no need to use bastion method, with this solution the cluster can be reached from outside of the provider network. However, previous allocation of floating IPs is now required).

- Added --usePrivateIPs option for bastion's method.

- Removed CloudStack Terraform support (the provider's repository |cloudstack_tf| by HashiCorp).

- Allowed both project-wide and VM-specific ssh key on GCP.

- Improved configuration: select network.

- Updated Distributed GAN test: included NNLO implementation ; more configuration (dataset size).

- Added ProGAN test.

- Allowed subset of costs (general configuration YAML file) and tests (tests catalog YAML file).

- Allowed relative paths for -c and -t.

- Updated CPU benchmark, based on the HEP Benchmarking Suite.

- Added option --noWatch to run without displaying logs, without watch command.

.. |cloudstack_tf| raw:: html

  <a href="https://github.com/hashicorp/terraform-provider-cloudstack" target="_blank">was archived</a>

``20.6``

- Improved support for running on Oracle Cloud Infrastructure and T-Systems' OTC.

- Added option --customNodes to set the number of instances that should be deployed for the shared cluster.

- Using Terraform's yamldecode with configs.yaml for variables instead of Python's replace function with placeholders.

- Disabled general Terraform support: only the providers and clouds that support Terraform and are present on the table above are fully supported by this suite. To run on another provider (supporting Terraform or not), the option '--noTerraform' has to be used.

``20.2``

- Using Ansible for VM configuration instead of Terraform's provisioners.

- Added support for non-Terraform providers (only bootstrap phase).

- Added options to destroy provisioned infrastructure.

- Added options to specify custom paths to configs.yaml and testsCatalog.yaml.

- Added support to use Ubuntu on VMs.

``19.12``

- Project restructured.

- Improved support for running on Google, AWS, Azure, Exoscale, OpenStack and CloudStack.

``19.8``

- Parallel creation of clusters, with different flavors according to tests needs.

- New logging system to keep parallel running tests logs sorted.

- Restructured configuration: moved configuration files to */configurations* and created new files taking HCL code (terraform configuration code) to keep *configs.yaml* clean.

- Automated allowance of root ssh by copying open user's authorized_keys to root's ~/.ssh as well as *sshd_config* modification.

- Usage of Kubernetes API instead of Kubernetes CLI.

- For network test (perfSONAR), usage of API instead of pscheduler CLI.

- New test: Dynamic On Demand Analysis Service, provided by INFN.

- Added configurations validation with jsonschema.

- Created Docker image to run a Test-Suite launcher container: rapidly creates a ready to use Test-Suite launcher.

``19.4``

- New tests: network performance (perfSONAR) and CPU benchmarking.

``19.2``

- First release.


Contact
---------------------------------------------
For more information contact ignacio.peluaga.lozada AT cern.ch


License
---------------------------------------------
Copyright (C) CERN.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see |licenses|.

.. |licenses| raw:: html

  <a href="https://www.gnu.org/licenses/" target="_blank">gnu.org/licenses</a>


.. body-end

.. image:: img/logo.jpg
   :height: 20px
   :width: 20px
   :scale: 20
   :target: https://home.cern/
   :alt: CERN logo
