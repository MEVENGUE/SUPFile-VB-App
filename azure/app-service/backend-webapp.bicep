// Azure App Service configuration for Backend API
@description('The name of the App Service plan')
param appServicePlanName string = 'supfile-backend-plan'

@description('The name of the App Service')
param appServiceName string = 'supfile-backend-api'

@description('The location for all resources')
param location string = resourceGroup().location

@description('The Docker image to deploy')
param dockerImage string = 'supfile/backend:latest'

@description('The container registry URL')
param containerRegistryUrl string = ''

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'B1' // Basic tier - adjust as needed
    tier: 'Basic'
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// App Service
resource appService 'Microsoft.Web/sites@2022-03-01' = {
  name: appServiceName
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${dockerImage}'
      alwaysOn: true
      http20Enabled: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: containerRegistryUrl
        }
      ]
    }
    httpsOnly: true
  }
}

output appServiceUrl string = 'https://${appService.properties.defaultHostName}'

