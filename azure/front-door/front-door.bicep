// Azure Front Door configuration for multi-region routing
@description('The name of the Front Door')
param frontDoorName string = 'supfile-frontdoor'

@description('Backend API URL in East US')
param backendEastUsUrl string = ''

@description('Backend API URL in France Central')
param backendFranceCentralUrl string = ''

@description('Frontend URL in East US')
param frontendEastUsUrl string = ''

@description('Frontend URL in France Central')
param frontendFranceCentralUrl string = ''

// Front Door Profile
resource frontDoorProfile 'Microsoft.Network/frontDoorWebApplicationFirewallPolicies@2022-05-01' = {
  name: '${frontDoorName}-waf'
  location: 'Global'
  properties: {
    policySettings: {
      enabledState: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: 'Enabled'
      maxRequestBodySizeInKb: 128
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'Microsoft_DefaultRuleSet'
          ruleSetVersion: '2.1'
          ruleGroupOverrides: []
        }
      ]
    }
  }
}

resource frontDoor 'Microsoft.Network/frontDoors@2020-11-01' = {
  name: frontDoorName
  location: 'Global'
  properties: {
    frontendEndpoints: [
      {
        name: 'supfile-frontend-endpoint'
        properties: {
          hostName: '${frontDoorName}.azurefd.net'
          sessionAffinityEnabledState: 'Enabled'
          sessionAffinityTtlSeconds: 0
          webApplicationFirewallPolicyLink: {
            id: frontDoorProfile.id
          }
        }
      }
    ]
    backendPools: [
      {
        name: 'backend-eastus'
        properties: {
          backends: [
            {
              address: backendEastUsUrl
              httpPort: 443
              httpsPort: 443
              priority: 1
              weight: 50
              backendHostHeader: backendEastUsUrl
            }
          ]
          loadBalancingSettings: {
            id: resourceId('Microsoft.Network/frontDoors/loadBalancingSettings', frontDoorName, 'default-loadbalancing')
          }
          healthProbeSettings: {
            id: resourceId('Microsoft.Network/frontDoors/healthProbeSettings', frontDoorName, 'default-healthprobe')
          }
        }
      }
      {
        name: 'backend-francecentral'
        properties: {
          backends: [
            {
              address: backendFranceCentralUrl
              httpPort: 443
              httpsPort: 443
              priority: 1
              weight: 50
              backendHostHeader: backendFranceCentralUrl
            }
          ]
          loadBalancingSettings: {
            id: resourceId('Microsoft.Network/frontDoors/loadBalancingSettings', frontDoorName, 'default-loadbalancing')
          }
          healthProbeSettings: {
            id: resourceId('Microsoft.Network/frontDoors/healthProbeSettings', frontDoorName, 'default-healthprobe')
          }
        }
      }
      {
        name: 'frontend-eastus'
        properties: {
          backends: [
            {
              address: frontendEastUsUrl
              httpPort: 443
              httpsPort: 443
              priority: 1
              weight: 50
              backendHostHeader: frontendEastUsUrl
            }
          ]
          loadBalancingSettings: {
            id: resourceId('Microsoft.Network/frontDoors/loadBalancingSettings', frontDoorName, 'default-loadbalancing')
          }
          healthProbeSettings: {
            id: resourceId('Microsoft.Network/frontDoors/healthProbeSettings', frontDoorName, 'default-healthprobe')
          }
        }
      }
      {
        name: 'frontend-francecentral'
        properties: {
          backends: [
            {
              address: frontendFranceCentralUrl
              httpPort: 443
              httpsPort: 443
              priority: 1
              weight: 50
              backendHostHeader: frontendFranceCentralUrl
            }
          ]
          loadBalancingSettings: {
            id: resourceId('Microsoft.Network/frontDoors/loadBalancingSettings', frontDoorName, 'default-loadbalancing')
          }
          healthProbeSettings: {
            id: resourceId('Microsoft.Network/frontDoors/healthProbeSettings', frontDoorName, 'default-healthprobe')
          }
        }
      }
    ]
    loadBalancingSettings: [
      {
        name: 'default-loadbalancing'
        properties: {
          sampleSize: 4
          successfulSamplesRequired: 3
          additionalLatencyMilliseconds: 50
        }
      }
    ]
    healthProbeSettings: [
      {
        name: 'default-healthprobe'
        properties: {
          path: '/health'
          protocol: 'Https'
          intervalInSeconds: 30
        }
      }
    ]
    routingRules: [
      {
        name: 'api-routing'
        properties: {
          frontendEndpoints: [
            {
              id: resourceId('Microsoft.Network/frontDoors/frontendEndpoints', frontDoorName, 'supfile-frontend-endpoint')
            }
          ]
          acceptedProtocols: ['Https']
          patternsToMatch: ['/api/*']
          routeConfiguration: {
            '@odata.type': '#Microsoft.Azure.FrontDoor.Models.FrontdoorForwardingConfiguration'
            backendPool: {
              id: resourceId('Microsoft.Network/frontDoors/backendPools', frontDoorName, 'backend-eastus')
            }
            forwardingProtocol: 'HttpsOnly'
            cacheConfiguration: {
              queryParameterStripDirective: 'StripNone'
              dynamicCompression: 'Enabled'
            }
          }
        }
      }
      {
        name: 'frontend-routing'
        properties: {
          frontendEndpoints: [
            {
              id: resourceId('Microsoft.Network/frontDoors/frontendEndpoints', frontDoorName, 'supfile-frontend-endpoint')
            }
          ]
          acceptedProtocols: ['Https']
          patternsToMatch: ['/*']
          routeConfiguration: {
            '@odata.type': '#Microsoft.Azure.FrontDoor.Models.FrontdoorForwardingConfiguration'
            backendPool: {
              id: resourceId('Microsoft.Network/frontDoors/backendPools', frontDoorName, 'frontend-eastus')
            }
            forwardingProtocol: 'HttpsOnly'
            cacheConfiguration: {
              queryParameterStripDirective: 'StripNone'
              dynamicCompression: 'Enabled'
            }
          }
        }
      }
    ]
  }
}

output frontDoorHostName string = '${frontDoorName}.azurefd.net'

