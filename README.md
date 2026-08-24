# heat-controller

Centralized scheduling and control for a fleet of Venstar T8900
thermostats, plus the Azure networking (Bicep) needed to reach devices
behind a remote site's router.

- **`heatctl/`** -- FastAPI app: device registry + centralized
  schedule (day/time -> setpoints) + a background scheduler loop that
  pushes due schedule entries to devices via
  [`pyvenstar`](https://pypi.org/project/pyvenstar/).
- **`infra/`** -- Bicep IaC for the site-to-site VPN (see "Networking"
  below).

## Why is scheduling centralized instead of on-device?

The T8900 Local API has no remote-writable weekly schedule endpoint --
schedules configured through the device's own UI aren't reachable or
settable over the network. So `heatctl` keeps the schedule in its own
Postgres DB and a background loop (`heatctl/scheduler.py`) pushes
setpoints to each device at the right time, rather than relying on
each device to run its own schedule.

## Running locally (Docker)

```bash
cp .env.example .env
docker compose up --build
```

This starts the FastAPI app (`localhost:8080`) and a Postgres 16
container. On startup, Alembic migrations are not yet wired into the
container's startup path -- run them once against the compose stack:

```bash
docker compose exec app alembic upgrade head
```

API docs: `http://localhost:8080/docs`

## Running tests locally (no Docker required)

Tests run entirely against an in-memory SQLite DB -- no Postgres
needed for `pytest`.

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt -r requirements-test.txt
pytest -q --cov=heatctl --cov-report=term-missing
```

## Database migrations

Schema changes go through Alembic (`alembic/versions/`), same pattern
as `agora-cms`:

```bash
alembic revision --autogenerate --rev-id 0002 -m "short description"
alembic upgrade head
alembic check   # verifies the migration matches the models exactly
```

## Security notes

- Device credentials (`devices.username`/`devices.password`) are
  stored in plaintext columns -- acceptable only because every
  deployment target (docker volume, Azure Postgres Flexible Server)
  encrypts the underlying disk/volume at rest. If that assumption ever
  changes, move these behind Key Vault / envelope encryption first.
- The T8900 Local API itself has no required authentication beyond an
  optional PIN/Digest -- network-level isolation (a dedicated
  VLAN/SSID + firewall rules restricting device access to this
  service's host only) is the primary control. This is exactly what
  the VPN Gateway below is for at each Goodwill site.

## Networking

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

az group create --name heat-controller-dev-rg --location westus

az deployment group create \
  --resource-group heat-controller-dev-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam \
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
az group delete --name heat-controller-dev-rg --yes --no-wait
```

## Next steps

Once connectivity is validated (e.g. reaching `192.168.1.149` -- the
test T8900 -- from a VM/container in the `10.10.0.0/16` VNet), this
same module set will be parameterized per real Goodwill site and
deployed against each site's actual WAN gateway device instead of a
personal UniFi Dream Machine.
