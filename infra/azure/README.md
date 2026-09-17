# Azure Container Apps topology

The deployment has one public entry point:

```text
Browser -- HTTPS --> Frontend Container App (external ingress)
                         |
                         | HTTPS, internal FQDN
                         v
                    Backend Container App (internal ingress)
                         |
                         +--> PostgreSQL private endpoint
                         +--> Redis private endpoint
```

`main.bicep` creates the Container Apps environment and the two apps. The
environment is attached to an existing delegated subnet. PostgreSQL and Redis
remain managed data services outside this template: give the Backend their
private connection strings and disable public network access on both services.
Private DNS zones must be linked to the VNet containing the Container Apps
infrastructure subnet.

The Frontend receives the Backend's generated internal ingress FQDN as
`BACKEND_UPSTREAM`. The public origin is used for both `FRONTEND_URL` and
`API_URL`, so verification email links return through the only public ingress.
The Backend ingress has `external: false`; neither data service is represented
by a public Container App ingress.

## Deploy

Copy `main.bicepparam.example` to an ignored or securely stored parameter file,
replace its example values, and deploy it:

```powershell
az deployment group create `
  --resource-group <resource-group> `
  --template-file infra/azure/main.bicep `
  --parameters <secure-parameters-file>
```

Confirm the ingress boundary after deployment:

```powershell
az containerapp show --resource-group <resource-group> --name jackandbeanstalks-frontend `
  --query "properties.configuration.ingress.{external:external,allowInsecure:allowInsecure,fqdn:fqdn}"
az containerapp show --resource-group <resource-group> --name jackandbeanstalks-backend `
  --query "properties.configuration.ingress.{external:external,allowInsecure:allowInsecure,fqdn:fqdn}"
```

The expected values are `external=true, allowInsecure=false` for Frontend and
`external=false, allowInsecure=false` for Backend. Also verify the selected
PostgreSQL and Redis resources report public network access as disabled.

## HTTPS and authentication smoke test

Create a verified smoke-test account and copy a current verification link from
an actual email. Run the check against the public custom domain:

```powershell
$env:SMOKE_BASE_URL = 'https://app.example.com'
$env:SMOKE_USERNAME = '<verified-test-user>'
$env:SMOKE_PASSWORD = '<password>'
$env:SMOKE_VERIFICATION_URL = 'https://app.example.com/api/verify-email/<token>'
python scripts/azure/verify_https_flow.py
```

The test fails unless the Backend observes `https`, login succeeds, refresh
cookies have `Secure` and the restricted path, refresh rotation succeeds, and
the emailed verification link redirects to the HTTPS Frontend confirmation
page. The verification endpoint is idempotent, so a link can be tested after
the account has already been verified.
