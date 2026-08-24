using '../main.bicep'

// ──────────────────────────────────────────────────────────────
// goodwill-dev.bicepparam — home-network VPN test environment
//
// Targets resource group `agoragw-hvac-dev-rg` in the Goodwill
// AI4Good subscription (same tenant/sub as agora-cms dev, separate
// resource group). Region westus for parity with agoragw-cms-dev-rg.
//
// remoteGatewayIp and sharedKey are NOT set here -- pass them at
// deploy time (remoteGatewayIp changes whenever your home WAN IP
// changes; sharedKey must never be committed):
//
//   az deployment group create \
//     --resource-group agoragw-hvac-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/parameters/goodwill-dev.bicepparam \
//     --parameters remoteGatewayIp='<udm-wan-ip>' \
//                  sharedKey='<secure-shared-key>'
//
// Teardown (delete the whole RG when done testing to stop billing):
//   az group delete --name agoragw-hvac-dev-rg --yes --no-wait
// ──────────────────────────────────────────────────────────────

param prefix = 'agoragwhvac'
param location = 'westus'

// Home LAN behind the UniFi Dream Machine:
param remoteAddressPrefixes = ['192.168.1.0/24']
