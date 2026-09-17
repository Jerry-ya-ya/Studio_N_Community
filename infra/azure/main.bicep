targetScope = 'resourceGroup'

@description('Azure region for the Container Apps environment.')
param location string = resourceGroup().location

@description('Existing VNet subnet delegated to Microsoft.App/environments. It must be able to resolve and reach the private database and Redis endpoints.')
param infrastructureSubnetResourceId string

@description('Public HTTPS origin, without a trailing slash, for example https://app.example.com.')
param publicOrigin string

param containerAppsEnvironmentName string = 'jackandbeanstalks-env'
param frontendAppName string = 'jackandbeanstalks-frontend'
param backendAppName string = 'jackandbeanstalks-backend'
param frontendImage string
param backendImage string

@secure()
@description('Private PostgreSQL connection string. The database must have public network access disabled.')
param databaseUrl string

@secure()
@description('Private Redis connection string. Redis must have public network access disabled.')
param redisUrl string

@secure()
param jwtSecretKey string

param superadminEmail string
param mailServer string
param mailPort int = 587
param mailUsername string

@secure()
param mailPassword string

@secure()
param azureStorageConnectionString string = ''

param azureStorageContainer string = 'cmenstudio-media'

var normalizedPublicOrigin = endsWith(publicOrigin, '/')
  ? substring(publicOrigin, 0, length(publicOrigin) - 1)
  : publicOrigin

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetResourceId
      internal: false
    }
  }
}

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        allowInsecure: false
        targetPort: 5000
        transport: 'auto'
      }
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
        {
          name: 'jwt-secret-key'
          value: jwtSecretKey
        }
        {
          name: 'mail-password'
          value: mailPassword
        }
        {
          name: 'azure-storage-connection-string'
          value: azureStorageConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          env: [
            {
              name: 'FLASK_ENV'
              value: 'production'
            }
            {
              name: 'FRONTEND_URL'
              value: normalizedPublicOrigin
            }
            {
              name: 'API_URL'
              value: normalizedPublicOrigin
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'JWT_SECRET_KEY'
              secretRef: 'jwt-secret-key'
            }
            {
              name: 'SUPERADMIN_EMAIL'
              value: superadminEmail
            }
            {
              name: 'MAIL_SERVER'
              value: mailServer
            }
            {
              name: 'MAIL_PORT'
              value: string(mailPort)
            }
            {
              name: 'MAIL_USERNAME'
              value: mailUsername
            }
            {
              name: 'MAIL_PASSWORD'
              secretRef: 'mail-password'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'azure-storage-connection-string'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER'
              value: azureStorageContainer
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/healthz'
                port: 5000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/healthz'
                port: 5000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 80
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          env: [
            {
              name: 'BACKEND_UPSTREAM'
              value: 'https://${backend.properties.configuration.ingress.fqdn}'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 80
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: 80
                scheme: 'HTTP'
              }
              initialDelaySeconds: 2
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output frontendFqdn string = frontend.properties.configuration.ingress.fqdn
output backendInternalFqdn string = backend.properties.configuration.ingress.fqdn
output backendExternal bool = backend.properties.configuration.ingress.external
