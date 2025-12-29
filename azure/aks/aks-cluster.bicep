// Azure Kubernetes Service configuration for multi-region deployment
@description('The name of the AKS cluster')
param clusterName string = 'supfile-aks'

@description('The location for all resources')
param location string = resourceGroup().location

@description('The node count')
param nodeCount int = 2

@description('The VM size for nodes')
param nodeVmSize string = 'Standard_B2s'

// AKS Cluster
resource aksCluster 'Microsoft.ContainerService/managedClusters@2023-05-02' = {
  name: clusterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: '1.28'
    dnsPrefix: clusterName
    agentPoolProfiles: [
      {
        name: 'agentpool'
        count: nodeCount
        vmSize: nodeVmSize
        osType: 'Linux'
        osDiskSizeGB: 30
        mode: 'System'
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      serviceCidr: '10.0.0.0/16'
      dnsServiceIP: '10.0.0.10'
    }
    addonProfiles: {
      httpApplicationRouting: {
        enabled: true
      }
    }
    enableRBAC: true
  }
}

output clusterName string = aksCluster.name
output clusterFqdn string = aksCluster.properties.fqdn

