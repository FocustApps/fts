# Selenium grid 4 AKS deployment

To enable remote execution of our tests we will need Selenium grid to do so.

An Azure Kubernetes Service (AKS) cluster will be deployed achieve this and the following information is the guides and programs
used to achieve a working cluster:

## Requirements

1. Have [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?tabs=azure-cli) installed on your computer.
2. Install [Helm](https://helm.sh/docs/intro/install/) as the package manager.

### Initial Setup Steps

This section is only for setting up a NEW Kube cluster.

```shell
az login # login to azure portal
az aks install-cli # install the k8s cli to utilize kubectl
```

The resource group for this deployment is ```fa-fenrir``` on US EAST. If there is a need to deploy to a new location other locations can be found using the following command: ```az account list-locations```

```shell
az group create --name fa-fenrir --location eastus
```

Create a K8s cluster in the resource group.

```shell
az aks create --resource-group fa-fenrir --name fenrir-aks --node-count 2 --generate-ssh-keys
```

#### Communicating with Fenrir AKS

Retrieve credentials for AKS cluster to communicate using kubectl

```shell
az aks get-credentials --resource-group fa-fenrir --name fenrir-aks
```

```shell
kubectl get nodes
kubectl create namespace fenrir-hub
```

#### Deployment

```shell
helm install selenium-grid docker-selenium/selenium-grid --set isolateComponents=true
```

#### Query resource group

```shell
az aks show --resource-group fa-fenrir --name fenrir-aks --query nodeResourceGroup -o tsv
```

Set as environment variable:

```shell
FENRIR_KUBE_GROUP=$(az aks show --resource-group fa-fenrir --name fenrir-aks --query nodeResourceGroup -o tsv)
```

Output should be a resource group name > MC_fenrir-aks_fenrir_eastus

#### Public IP address for query

```shell
az network public-ip create --resource-group MC_fenrir-aks_fenrir_eastus --name fenrirAKSPublicIP --sku Standard --allocation-method static --query publicIp.ipAddress -o tsv
```

Output should be an IP address > 13.92.246.33

Set as environment variable:

```shell
FENRIR_KUBE_PUBLIC_IP=$(az network public-ip create --resource-group $FENRIR_KUBE_GROUP --name fenrirAKSPublicIP --sku Standard --allocation-method static --query publicIp.ipAddress -o tsv)
```

### Resources

- [k8s selenium deployment](https://github.com/SeleniumHQ/docker-selenium/blob/trunk/charts/selenium-grid/README.md)
- [Auto Scaling Selenium Grid in Kubernetes using KEDA + Azure Kubernetes Service](https://medium.com/@gururajhm/auto-scaling-selenium-grid-in-kubernetes-using-keda-azure-kubernetes-service-3244dc00a9a6)
- (Deploying Selenium Grid 4 to Azure Kubernetes Service (AKS) using Azure DevOps)[https://tomaustin.xyz/2021/01/13/deploying-selenium-grid-4-to-azure-kubernetes-service-aks-using-azure-devops/]
- (Deploying an Azure Kubernetes Service (AKS) instance with an Nginx ingress controller)[https://tomaustin.xyz/2020/03/27/deploying-an-azure-kubernetes-service-aks-instance-with-an-nginx-ingress-controller/]
- [Take the Helm with Kubernetes on Windows](https://medium.com/@JockDaRock/take-the-helm-with-kubernetes-on-windows-c2cd4373104b)
- [Migrating from Helm chart nginx-ingress to ingress-nginx](https://rimusz.net/migrating-to-ingress-nginx)
