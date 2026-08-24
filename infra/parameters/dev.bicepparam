using '../main.bicep'

// ──────────────────────────────────────────────────────────────
// dev.bicepparam — home-network VPN test environment
//
// Targets resource group `heat-controller-dev-rg` in the Goodwill
// AI4Good subscription (separate resource group from agora-cms --
// this system is unrelated to the Agora media-device CMS). Region
// westus for parity with the other Goodwill dev resources.
//
// remoteGatewayIp and sharedKey are NOT set here -- pass them at
// deploy time (remoteGatewayIp changes whenever your home WAN IP
// changes; sharedKey must never be committed):
//
//   az deployment group create \
//     --resource-group heat-controller-dev-rg \
//     --template-file infra/main.bicep \
//     --parameters infra/parameters/dev.bicepparam \
//     --parameters remoteGatewayIp='<udm-wan-ip>' \
//                  sharedKey='<secure-shared-key>'
//
// Teardown (delete the whole RG when done testing to stop billing):
//   az group delete --name heat-controller-dev-rg --yes --no-wait
// ──────────────────────────────────────────────────────────────

param prefix = 'heatctl'
param location = 'westus'

// Home LAN behind the UniFi Dream Machine:
param remoteAddressPrefixes = ['192.168.1.0/24']
