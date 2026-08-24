// ──────────────────────────────────────────────────────────────
// main.bicep — Goodwill HVAC (Venstar thermostat fleet) Azure Infrastructure
//
// Deploys the site-to-site VPN used to reach thermostats behind a
// remote site's router (UniFi Dream Machine for home testing; the
// Goodwill site's WAN device for production locations).
//
//   - VNet with a GatewaySubnet
//   - VPN Gateway (VpnGw1+, route-based, IKEv2)
//   - Local network gateway + connection representing the remote site
//
// Deliberately separate from agora-cms's resource group/VNet -- this
// is an unrelated system (thermostat fleet management, not the Agora
// media-device CMS) and the VPN Gateway is meant to be deployed and
// deleted around test sessions to avoid continuous billing.
//
// Usage:
//   az deployment group create \
//     --resource-group heat-controller-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/parameters/dev.bicepparam \
//     --parameters remoteGatewayIp='<your-udm-wan-ip>' sharedKey='<secure>'
// ──────────────────────────────────────────────────────────────

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Unique prefix for resource names (lowercase, no special chars)')
@minLength(3)
@maxLength(20)
param prefix string

@description('VNet address space (must not overlap the remote site LAN or agora-cms\'s VNet)')
param vnetAddressPrefix string = '10.10.0.0/16'

@description('GatewaySubnet address prefix')
param gatewaySubnetPrefix string = '10.10.255.0/27'

@description('VPN Gateway SKU')
@allowed(['VpnGw1', 'VpnGw2', 'VpnGw3'])
param vpnGatewaySku string = 'VpnGw1'

@description('Public (WAN) IP address of the remote site VPN device')
param remoteGatewayIp string

@description('LAN address prefix(es) behind the remote site VPN device')
param remoteAddressPrefixes array = ['192.168.1.0/24']

@description('Pre-shared key for the IPsec tunnel -- must match the remote device config exactly')
@secure()
param sharedKey string

var tags = {
  project: 'goodwill-hvac'
  managedBy: 'bicep'
}

module networking 'modules/networking.bicep' = {
  name: 'networking'
  params: {
    location: location
    vnetName: '${prefix}-vnet'
    vnetAddressPrefix: vnetAddressPrefix
    gatewaySubnetPrefix: gatewaySubnetPrefix
    tags: tags
  }
}

module vpnGateway 'modules/vpnGateway.bicep' = {
  name: 'vpnGateway'
  params: {
    location: location
    prefix: prefix
    gatewaySubnetId: networking.outputs.gatewaySubnetId
    vpnGatewaySku: vpnGatewaySku
    remoteGatewayIp: remoteGatewayIp
    remoteAddressPrefixes: remoteAddressPrefixes
    sharedKey: sharedKey
    tags: tags
  }
}

output vnetId string = networking.outputs.vnetId
output vpnGatewayPublicIp string = vpnGateway.outputs.vpnGatewayPublicIp
output connectionStatus string = vpnGateway.outputs.connectionStatus
