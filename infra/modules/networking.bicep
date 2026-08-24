// ──────────────────────────────────────────────────────────────
// networking.bicep — VNet with a GatewaySubnet for the site-to-site VPN
//
// Deliberately minimal: this VNet exists only to host the VPN Gateway
// and (later) whatever compute needs to reach devices across the
// tunnel. It is NOT the agora-cms VNet — kept separate so this
// project's teardown/redeploy cycles never touch agora-cms infra.
// ──────────────────────────────────────────────────────────────

@description('Azure region for all resources')
param location string

@description('VNet name')
param vnetName string

@description('VNet address space (must not overlap the remote site LAN(s) or any other peered network)')
param vnetAddressPrefix string = '10.10.0.0/16'

@description('GatewaySubnet address prefix. Name MUST be exactly "GatewaySubnet" -- Azure requires this literal name for VPN Gateway to attach.')
param gatewaySubnetPrefix string = '10.10.255.0/27'

@description('Resource tags')
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: [
      {
        name: 'GatewaySubnet'
        properties: {
          addressPrefix: gatewaySubnetPrefix
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output gatewaySubnetId string = vnet.properties.subnets[0].id
