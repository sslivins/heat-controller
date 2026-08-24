# heat-controller

Bicep IaC for the site-to-site VPN connecting Azure to the Venstar
T8900 thermostat fleet. This repo is intentionally scoped to just the
networking needed to reach devices behind a remote site's router --
it's separate from `agora-cms`'s infra (different system, different
concern), even though it targets the same Goodwill Azure
tenant/subscription.

## What this deploys

- A dedicated VNet (`10.10.0.0/16`) with a `GatewaySubnet`
- A route-based VPN Gateway (`VpnGw1` by default, IKEv2/AES256/SHA256)
- A local network gateway + connection representing the remote site
  (currently: a UniFi Dream Machine fronting a home LAN, as a proving
  ground before replicating this at real Goodwill sites)

## Cost note -- deploy/delete around test sessions

A VPN Gateway **cannot be paused** -- it's billed continuously
(~$140+/mo for `VpnGw1`) for as long as the resource exists. There is
no "stop for the night" option short of deleting it. The intended
workflow here is:

1. Deploy before a test session (~30-45 min to provision).
2. Test.
3. `az group delete` the whole resource group when done (stops
   billing immediately; the VNet/gateway/public IP are all gone).
4. Redeploy next time (another ~30-45 min).

## Deploy

```bash
az login --tenant af755c27-6a67-4492-b1a4-ca3ce41dea42
az account set --subscription 9e09ebcd-8a09-4696-86c5-6385299f1113

az group create --name agoragw-hvac-dev-rg --location westus

az deployment group create \
  --resource-group agoragw-hvac-dev-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters/goodwill-dev.bicepparam \
  --parameters remoteGatewayIp='<your-udm-wan-ip>' \
               sharedKey='<a-strong-shared-secret>'
```

Grab the gateway's public IP from the deployment output
(`vpnGatewayPublicIp`) -- you'll need it to configure the UniFi Dream
Machine side.

## UniFi Dream Machine configuration

On the UDM: Settings -> VPN -> Site-to-Site VPN -> Create New -> Manual IPsec.

| Setting              | Value                                    |
|----------------------|-------------------------------------------|
| Remote Gateway        | Azure VPN Gateway public IP (from output) |
| Pre-shared Key        | same value passed as `sharedKey` above    |
| IKE Version           | IKEv2                                     |
| Encryption            | AES-256                                   |
| Hashing               | SHA-256                                   |
| DH Group              | 14                                        |
| Local IP/Network      | your home LAN, e.g. `192.168.1.0/24`      |
| Remote IP/Network     | `10.10.0.0/16` (the Azure VNet)           |
| VPN Type              | Route-based                               |

Azure and the UDM don't reliably interoperate over BGP, so this uses
static routes on both sides instead.

## Teardown

```bash
az group delete --name agoragw-hvac-dev-rg --yes --no-wait
```

## Next steps

Once connectivity is validated (e.g. reaching `192.168.1.149` -- the
test T8900 -- from a VM/container in the `10.10.0.0/16` VNet), this
same module set will be parameterized per real Goodwill site and
deployed against each site's actual WAN gateway device instead of a
personal UniFi Dream Machine.
