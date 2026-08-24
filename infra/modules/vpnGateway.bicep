// ──────────────────────────────────────────────────────────────
// vpnGateway.bicep — Site-to-site IPsec VPN Gateway
//
// Provisions:
//   - A Standard SKU static public IP for the gateway
//   - A route-based VirtualNetworkGateway (VpnGw1+)
//   - A LocalNetworkGateway representing the remote peer (e.g. a
//     UniFi Dream Machine at a home/site network)
//   - A Connection tying the two together over IKEv2
//
// NOTE: Provisioning/deprovisioning the VirtualNetworkGateway takes
// ~30-45 minutes each way. This module is designed to be deployed
// and fully deleted around test sessions to avoid the ~$140+/mo
// continuous billing of a VpnGw1 SKU sitting idle.
// ──────────────────────────────────────────────────────────────

@description('Azure region for all resources')
param location string

@description('Unique prefix for resource names')
param prefix string

@description('Subnet resource ID for the GatewaySubnet (from networking.bicep)')
param gatewaySubnetId string

@description('VPN Gateway SKU. VpnGw1 is the smallest SKU compatible with a Standard public IP and modern IKEv2 policies.')
@allowed(['VpnGw1', 'VpnGw2', 'VpnGw3'])
param vpnGatewaySku string = 'VpnGw1'

@description('Public IP address of the remote site VPN device (e.g. your UniFi Dream Machine WAN IP)')
param remoteGatewayIp string

@description('LAN address prefix(es) behind the remote site VPN device that Azure should route to')
param remoteAddressPrefixes array = ['192.168.1.0/24']

@description('Pre-shared key for the IPsec tunnel. Must match exactly what is configured on the remote device.')
@secure()
param sharedKey string

@description('Resource tags')
param tags object = {}

resource publicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: '${prefix}-vgw-pip'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource vpnGateway 'Microsoft.Network/virtualNetworkGateways@2023-11-01' = {
  name: '${prefix}-vgw'
  location: location
  tags: tags
  properties: {
    gatewayType: 'Vpn'
    vpnType: 'RouteBased'
    sku: {
      name: vpnGatewaySku
      tier: vpnGatewaySku
    }
    activeActive: false
    ipConfigurations: [
      {
        name: 'vnetGatewayConfig'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: publicIp.id
          }
          subnet: {
            id: gatewaySubnetId
          }
        }
      }
    ]
  }
}

resource localNetworkGateway 'Microsoft.Network/localNetworkGateways@2023-11-01' = {
  name: '${prefix}-lgw-home'
  location: location
  tags: tags
  properties: {
    gatewayIpAddress: remoteGatewayIp
    localNetworkAddressSpace: {
      addressPrefixes: remoteAddressPrefixes
    }
  }
}

resource connection 'Microsoft.Network/connections@2023-11-01' = {
  name: '${prefix}-conn-home'
  location: location
  tags: tags
  properties: {
    connectionType: 'IPsec'
    virtualNetworkGateway1: {
      id: vpnGateway.id
    }
    localNetworkGateway2: {
      id: localNetworkGateway.id
    }
    sharedKey: sharedKey
    connectionProtocol: 'IKEv2'
    ipsecPolicies: [
      {
        ikeEncryption: 'AES256'
        ikeIntegrity: 'SHA256'
        dhGroup: 'DHGroup14'
        ipsecEncryption: 'AES256'
        ipsecIntegrity: 'SHA256'
        pfsGroup: 'PFS14'
        saLifeTimeSeconds: 27000
        saDataSizeKilobytes: 102400000
      }
    ]
  }
}

output vpnGatewayPublicIp string = publicIp.properties.ipAddress
output vpnGatewayId string = vpnGateway.id
output connectionStatus string = connection.properties.connectionStatus
