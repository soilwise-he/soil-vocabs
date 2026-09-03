# Skosmos Deployment for SoilVoc

This folder contains a Docker Compose deployment for browsing SoilVoc in Skosmos. By default, it runs the complete stack locally with Apache Jena Fuseki as the triplestore.

Default stack:

- `skosmos`: official AMD64 Skosmos v3.2 image from `quay.io/natlibfi/skosmos`
- `fuseki`: Apache Jena Fuseki with Jena Text indexing
- `fuseki-cache`: Varnish cache in front of Fuseki
- `plugins/soilvoc-definition-source`: a SoilVoc-only Skosmos plugin that displays definition text with its source and enriches the hierarchy sidebar with semantic SOSA procedure children

The online Virtuoso endpoint remains available as an optional backend through `.env.virtuoso.example` and `config/skosmos-config.ttl`.

## Prerequisites

- For local Windows use, Docker Desktop must be running and accessible from this shell.
- For remote Linux deployment, use Docker Engine and the Docker Compose plugin; see [Publish Online With W3ID](#publish-online-with-w3id).
- Internet access is required for the first run to pull the official Skosmos image and build the Fuseki image.
- The official Skosmos image is AMD64. ARM64 deployments must select a compatible image with `SKOSMOS_IMAGE`.
- The optional remote mode requires access to the Virtuoso endpoint and an updated graph at `https://w3id.org/eusoilvoc`.

## Generate Skosmos Data

`../SoilVoc.ttl` remains the canonical source. Generate the Skosmos display copy before loading it into Fuseki or uploading it to Virtuoso:

```powershell
python .\generate_skosmos_ttl.py
```

This writes `SoilVoc_skosmos.ttl`. The generated copy preserves canonical definition blank-node `rdf:value` text, rewrites legacy `schema:text` values if present, keeps SKOS and SOSA links semantic, adds display-only `eusoilvoc:skosmosHierarchyParent` triples for Skosmos sidebar traversal, and embeds `soilvoc_ontology.ttl` so property/class labels are available from the same RDF file. This lets procedures appear in the sidebar without becoming false SKOS narrower concepts. The canonical `../SoilVoc.ttl` is not changed by this script.

## Start With Local Fuseki

```powershell
cd path\to\soil-vocabs\skosmos
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
.\load-soilvoc.ps1
docker compose restart fuseki-cache skosmos
```

`COMPOSE_PROFILES=local-fuseki` in `.env.example` activates Fuseki and Varnish automatically. The build step builds Fuseki locally and pulls the official Skosmos v3.2 image; it does not build Skosmos.

Skosmos will be available at:

```text
http://localhost:9090/
```

Fuseki and its cache are available on the host for diagnostics at:

```text
http://localhost:9030/skosmos/
http://localhost:9031/skosmos/
```

## Local Smoke Tests

Check container status:

```powershell
docker compose ps
```

Check that the local graph is loaded:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "SELECT (COUNT(*) AS ?triples) WHERE { GRAPH <https://w3id.org/eusoilvoc> { ?s ?p ?o } }" `
  -Uri "http://localhost:9030/skosmos/query"
```

Check a known concept and the custom hierarchy projection:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> SELECT ?label WHERE { GRAPH <https://w3id.org/eusoilvoc> { <https://w3id.org/eusoilvoc#SoilpH> skos:prefLabel ?label } } LIMIT 1" `
  -Uri "http://localhost:9030/skosmos/query"

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX eusoilvoc: <https://w3id.org/eusoilvoc#> SELECT ?parent WHERE { GRAPH <https://w3id.org/eusoilvoc> { eusoilvoc:pHProcedure-pHCaCl2 eusoilvoc:skosmosHierarchyParent ?parent } } LIMIT 1" `
  -Uri "http://localhost:9030/skosmos/query"
```

Check Skosmos search through the local UI service:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:9090/rest/v1/soilvoc/search?query=soil%20porosity&lang=en"
```

Then open `http://localhost:9090/soilvoc/en/` and search for `soil porosity`. Open a concept with a sourced definition such as `MineralConcVolume` and confirm the Definition row includes a Source line. Open `BaseSaturation` to confirm `Has procedure` is shown on the concept page and procedure children are available through the hierarchy navigation.

## Optional Remote Virtuoso

The remote option starts only Skosmos and reads the SoilVoc graph from `https://sparql.soilwise.wetransform.eu/sparql/`:

```powershell
docker compose --profile local-fuseki down
Copy-Item .env.virtuoso.example .env -Force
docker compose up -d
```

No local RDF load is needed in this mode. To return to local Fuseki, copy `.env.example` back to `.env`, start the stack, and run `load-soilvoc.ps1` again.

## Publish Skosmos Alongside W3ID

Example public shape using the optional remote Virtuoso backend:

```text
https://w3id.org/eusoilvoc
  -> HTTPS redirect, managed in perma-id/w3id.org
  -> https://soilwise-he.github.io/soil-vocabs/
  -> GitHub Pages static SoilVoc viewer

https://soilvoc.example.org/soilvoc/en/
  -> reverse proxy on the server
  -> Skosmos Docker container
  -> https://sparql.soilwise.wetransform.eu/sparql/
  -> graph https://w3id.org/eusoilvoc
```

`w3id.org` is not the server that runs Skosmos. It is a persistent redirect service. Keep `https://w3id.org/eusoilvoc` pointing to the GitHub Pages static viewer unless the project explicitly decides to move the canonical public entry point. A Skosmos instance can run on a separate hostname, for example `https://soilvoc.example.org`, as an isolated live demo.

The cleanest Skosmos demo deployment is to serve Skosmos from the root of a dedicated hostname. Avoid deploying Skosmos under a subpath unless necessary; subpath deployments require `skosmos:baseHref` and more reverse-proxy care.

### 1. Prepare the Remote Server

Use a Linux server with:

- Docker Engine and Docker Compose plugin.
- A public DNS name, for example `soilvoc.example.org`.
- Inbound ports `80` and `443` open for HTTP/TLS.
- Outbound HTTPS access to `https://sparql.soilwise.wetransform.eu/sparql/` when using the optional remote backend.

Clone or copy this repository to the server:

```bash
sudo mkdir -p /opt/soil-vocabs
sudo chown "$USER":"$USER" /opt/soil-vocabs
git clone https://github.com/soilwise-he/soil-vocabs.git /opt/soil-vocabs
cd /opt/soil-vocabs/skosmos
```

If the server receives a deployment archive instead of using `git clone`, make sure the `skosmos/config`, `skosmos/plugins`, `skosmos/custom-templates`, `skosmos/Soilwise_workflow_soilvoc.png`, and `skosmos/docker-compose.yml` files are present.

For the remote-Virtuoso deployment, cloning this repository is enough to get the Skosmos Compose file, configuration, and SoilVoc customizations onto the server. The runtime vocabulary data comes from the Virtuoso graph, so no local RDF load step is needed. The default local-Fuseki deployment also needs `SoilVoc_skosmos.ttl` loaded with `load-soilvoc.ps1` or an equivalent Graph Store Protocol request.

### 2. Configure the Production Container

Create a production `.env` file:

```bash
cd /opt/soil-vocabs/skosmos
cp .env.virtuoso.example .env
nano .env
```

Recommended production values:

```dotenv
SKOSMOS_PORT=127.0.0.1:9090
SKOSMOS_CONFIG=./config/skosmos-config.ttl
SKOSMOS_IMAGE=quay.io/natlibfi/skosmos:v3.2
```

Binding `SKOSMOS_PORT` to `127.0.0.1:9090` keeps the unencrypted container port private. Public traffic should enter through the HTTPS reverse proxy.

Set `SKOSMOS_IMAGE` to a Skosmos image tag or digest you have tested. Avoid `latest` unless you intentionally want automatic image changes during redeploys. The official image above is AMD64; an ARM64 host must override it with a compatible image.

To make production look the same as the local deployment, use the same Skosmos image and the same tracked plugin, custom-template, and image assets. The backend-specific `SKOSMOS_CONFIG` selects either local Fuseki or remote Virtuoso. No Skosmos source-code fork or front-end redesign is needed for a normal AMD64 deployment.

Keep `config/skosmos-config.ttl` pointed at Virtuoso:

```turtle
skosmos:sparqlEndpoint <https://sparql.soilwise.wetransform.eu/sparql/> ;
skosmos:sparqlDialect "Generic" ;

:soilvoc a skosmos:Vocabulary, void:Dataset ;
    void:uriSpace "https://w3id.org/eusoilvoc#" ;
    void:sparqlEndpoint <https://sparql.soilwise.wetransform.eu/sparql/> ;
    skosmos:sparqlGraph <https://w3id.org/eusoilvoc> ;
    skosmos:mainConceptScheme <https://w3id.org/eusoilvoc> .
```

Do not start the `local-fuseki` profile in this remote-Virtuoso deployment.

### 3. Start Skosmos

```bash
cd /opt/soil-vocabs/skosmos
docker compose pull
docker compose up -d
docker compose ps
```

Only the `skosmos` service should be running in remote-Virtuoso mode.

Check the container directly from the server:

```bash
curl -I http://127.0.0.1:9090/
curl -I http://127.0.0.1:9090/soilvoc/en/
```

### 4. Add HTTPS Reverse Proxy

Example Nginx site for a dedicated hostname:

```nginx
server {
    listen 80;
    server_name soilvoc.example.org;

    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Optional: serve an RDF dump for W3ID content negotiation.
    location /rdf/ {
        alias /var/www/soilvoc-rdf/;
        types {
            text/turtle ttl;
        }
        default_type text/turtle;
    }
}
```

Install and enable it:

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/soilvoc
sudo ln -s /etc/nginx/sites-available/soilvoc /etc/nginx/sites-enabled/soilvoc
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d soilvoc.example.org
```

If you want RDF content negotiation through W3ID, publish a static copy of the generated Skosmos TTL:

```bash
sudo mkdir -p /var/www/soilvoc-rdf
sudo cp /opt/soil-vocabs/skosmos/SoilVoc_skosmos.ttl /var/www/soilvoc-rdf/SoilVoc_skosmos.ttl
sudo systemctl reload nginx
```

After TLS is issued, verify the public origin:

```bash
curl -I https://soilvoc.example.org/
curl -I https://soilvoc.example.org/soilvoc/en/
curl "https://soilvoc.example.org/rest/v1/soilvoc/search?query=soil%20porosity&lang=en"
curl -I https://soilvoc.example.org/rdf/SoilVoc_skosmos.ttl
```

If you deploy under a subpath such as `https://soilvoc.example.org/skosmos/`, add `skosmos:baseHref <https://soilvoc.example.org/skosmos/>` to `config/skosmos-config.ttl` and adjust the reverse proxy path rules. Prefer a dedicated hostname to avoid this.

### 5. Keep the Existing W3ID Redirect

The `https://w3id.org/eusoilvoc` namespace is already registered in `perma-id/w3id.org`. It currently redirects to the GitHub Pages static viewer at:

```text
https://soilwise-he.github.io/soil-vocabs/
```

For the current deployment model, no W3ID change is needed. Keep the existing `eusoilvoc/.htaccess` target on GitHub Pages, and treat the Skosmos instance as a separate live demo URL. If maintainers, project description, or target-service details change, keep `eusoilvoc/README.md` current in the `perma-id/w3id.org` repository.

Expected W3ID rule:

```apache
# /eusoilvoc/
# Permanent identifier for SoilVoc.
# Maintainer: <NAME>, <EMAIL>, GitHub: <USERNAME>

RewriteEngine On

RewriteRule ^$ https://soilwise-he.github.io/soil-vocabs/ [R=303,L]
RewriteRule ^(.*)$ https://soilwise-he.github.io/soil-vocabs/ [R=303,L]
```

Keep the GitHub Pages static viewer online as the canonical public browsing page. Link to the Skosmos live demo from project documentation if needed, but do not make GitHub Pages redirect to Skosmos while W3ID points to GitHub Pages.

For hash URIs such as `https://w3id.org/eusoilvoc#SoilpH`, the fragment `#SoilpH` is not sent to the W3ID server. The redirect can only act on the base URI `https://w3id.org/eusoilvoc`. This is normal for hash URI vocabularies: the base document should describe the vocabulary, and the fragment identifies a resource inside that document.

### 6. Verify W3ID

```bash
curl -I https://w3id.org/eusoilvoc
curl -L -I https://w3id.org/eusoilvoc
```

Expected behavior:

- The first command returns a `303` redirect after W3ID is configured.
- The second command follows the redirect and reaches `https://soilwise-he.github.io/soil-vocabs/`.
- Opening `https://w3id.org/eusoilvoc` in a browser lands on the SoilVoc GitHub Pages static viewer.

If RDF content negotiation is configured, also test:

```bash
curl -L -H "Accept: text/turtle" https://w3id.org/eusoilvoc
```

### 7. Update the Online Instance

For Skosmos config, plugin, or container changes:

```bash
cd /opt/soil-vocabs
git pull
cd skosmos
docker compose pull
docker compose up -d
docker compose restart skosmos
```

For vocabulary data changes in this remote-Virtuoso production example:

1. Regenerate `skosmos/SoilVoc_skosmos.ttl` locally or in CI.
2. Upload the regenerated TTL to the Virtuoso graph `https://w3id.org/eusoilvoc`.
3. If you publish a static RDF dump, copy the regenerated TTL to `/var/www/soilvoc-rdf/SoilVoc_skosmos.ttl` on the server.
4. Re-run the public smoke tests above.

Because this production example queries Virtuoso directly, no local Fuseki reload is needed. Restart Skosmos only when its config, plugin files, or container image changes.

## Local Fuseki Maintenance

The default `.env.example` uses `config/skosmos-config.local-fuseki.ttl`, starts Fuseki and Varnish through the `local-fuseki` profile, and loads `SoilVoc_skosmos.ttl` into the local graph.

```powershell
cd path\to\soil-vocabs\skosmos
docker compose up -d --build
.\load-soilvoc.ps1
```

If your PowerShell execution policy blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\load-soilvoc.ps1
```

If the stack was already running before a reload, restart the cache and frontend so old responses do not mask the updated graph:

```powershell
docker compose restart fuseki-cache skosmos
```

Equivalent manual load command:

```powershell
Invoke-WebRequest `
  -Method Put `
  -ContentType "text/turtle" `
  -InFile .\SoilVoc_skosmos.ttl `
  -Uri "http://localhost:9030/skosmos/data?graph=https%3A%2F%2Fw3id.org%2Feusoilvoc" `
  -UseBasicParsing
```

## Stop

```powershell
docker compose down
```

## Clean Local Fuseki Reset

This removes the local Fuseki data volume and reloads the Skosmos copy from scratch:

```powershell
docker compose down -v
python .\generate_skosmos_ttl.py
docker compose up -d --build
.\load-soilvoc.ps1
```

## Notes

- Remote SPARQL endpoint: `https://sparql.soilwise.wetransform.eu/sparql/`
- Skosmos vocabulary graph URI: `https://w3id.org/eusoilvoc`
- SoilVoc concept URI space: `https://w3id.org/eusoilvoc#`
- Skosmos UI port: `9090`
- Local Fuseki host port: `9030`
- Local Varnish host port: `9031`
- Local Fuseki is the default backend and uses Skosmos' Jena Text dialect. The optional remote Virtuoso configuration uses the Generic SPARQL dialect.
- The feedback plugin posts to the same-origin path `/api/feedback`. Email delivery is available only on a deployment that provides that route, such as the production Cloudflare Worker; it is not part of the local Compose stack.
- `SoilVoc_skosmos.ttl` is a generated Skosmos display copy; regenerate it from `../SoilVoc.ttl` and `soilvoc_ontology.ttl`.
- Override ports, `SKOSMOS_IMAGE`, or `SKOSMOS_CONFIG` by copying an environment example to `.env` and editing the values.
- W3ID identifier setup: `https://w3id.org/`
- Skosmos Docker notes: `https://github.com/NatLibFi/Skosmos/wiki/Install-Skosmos-with-Fuseki-in-Docker`
- Skosmos configuration reference: `https://github.com/NatLibFi/Skosmos/wiki/Configuration`
