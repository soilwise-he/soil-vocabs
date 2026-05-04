# Skosmos Deployment for SoilVoc

This folder contains a Docker Compose deployment for browsing SoilVoc in Skosmos. By default, Skosmos reads the SoilVoc graph from the online Virtuoso SPARQL endpoint.

Default stack:

- `skosmos`: Skosmos web UI from `quay.io/natlibfi/skosmos`
- `plugins/soilvoc-definition-source`: a SoilVoc-only Skosmos plugin that displays definition text with its source and enriches the hierarchy sidebar with semantic SOSA procedure children

Optional local fallback:

- `fuseki`: Apache Jena Fuseki with Jena Text indexing
- `fuseki-cache`: Varnish cache in front of Fuseki

## Prerequisites

- For local Windows use, Docker Desktop must be running and accessible from this shell.
- For remote Linux deployment, use Docker Engine and the Docker Compose plugin; see [Publish Online With W3ID](#publish-online-with-w3id).
- Internet access is required for the first run to pull the Skosmos image and for runtime access to the Virtuoso endpoint.
- The remote Virtuoso graph must contain the generated Skosmos Turtle file in graph `https://w3id.org/eusoilvoc`.

## Generate Skosmos Data

`../SoilVoc.ttl` remains the canonical source. Generate the Skosmos display copy before uploading it to Virtuoso:

```powershell
python .\generate_skosmos_ttl.py
```

This writes `SoilVoc_skosmos.ttl`. The generated copy preserves canonical definition blank-node `rdf:value` text, rewrites legacy `schema:text` values if present, keeps SKOS and SOSA links semantic, adds display-only `eusoilvoc:skosmosHierarchyParent` triples for Skosmos sidebar traversal, and embeds `soilvoc_ontology.ttl` so property/class labels are available from the same RDF file. This lets procedures appear in the sidebar without becoming false SKOS narrower concepts. The canonical `../SoilVoc.ttl` is not changed by this script.

## Start With Remote Virtuoso

```powershell
cd C:\Users\wang479\Downloads\soil-vocabs\skosmos
Copy-Item .env.example .env
docker compose up -d
```

Skosmos will be available at:

```text
http://localhost:9090/
```

No local RDF load step is needed in this mode. Skosmos queries the remote endpoint directly:

```text
https://sparql.soilwise.wetransform.eu/sparql/
```

## Remote Smoke Tests

Check container status:

```powershell
docker compose ps
```

Check that the remote graph is reachable:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "SELECT (COUNT(*) AS ?triples) WHERE { GRAPH <https://w3id.org/eusoilvoc> { ?s ?p ?o } }" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"
```

Check a known concept and the custom hierarchy projection:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> SELECT ?label WHERE { GRAPH <https://w3id.org/eusoilvoc> { <https://w3id.org/eusoilvoc#SoilpH> skos:prefLabel ?label } } LIMIT 1" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX eusoilvoc: <https://w3id.org/eusoilvoc#> SELECT ?parent WHERE { GRAPH <https://w3id.org/eusoilvoc> { eusoilvoc:pHProcedure-pHCaCl2 eusoilvoc:skosmosHierarchyParent ?parent } } LIMIT 1" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"
```

Check Skosmos search through the local UI service:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:9090/rest/v1/soilvoc/search?query=soil%20porosity&lang=en"
```

Then open `http://localhost:9090/soilvoc/en/` and search for `soil porosity`. Open a concept with a sourced definition such as `MineralConcVolume` and confirm the Definition row includes a Source line. Open `BaseSaturation` to confirm `Has procedure` is shown on the concept page and procedure children are available through the hierarchy navigation.

## Publish Online With W3ID

Target production shape:

```text
https://w3id.org/eusoilvoc
  -> HTTPS redirect, managed in perma-id/w3id.org
  -> https://soilvoc.example.org/soilvoc/en/
  -> reverse proxy on the server
  -> Skosmos Docker container
  -> https://sparql.soilwise.wetransform.eu/sparql/
  -> graph https://w3id.org/eusoilvoc
```

`w3id.org` is not the server that runs Skosmos. It is a persistent redirect service. You still need a real public HTTPS origin for the Skosmos container, for example `https://soilvoc.example.org`. After that origin works, configure `https://w3id.org/eusoilvoc` to redirect to the Skosmos vocabulary page.

The cleanest deployment is to serve Skosmos from the root of a dedicated hostname and let W3ID redirect to `/soilvoc/en/`. Avoid deploying Skosmos under a subpath unless necessary; subpath deployments require `skosmos:baseHref` and more reverse-proxy care.

### 1. Prepare the Remote Server

Use a Linux server with:

- Docker Engine and Docker Compose plugin.
- A public DNS name, for example `soilvoc.example.org`.
- Inbound ports `80` and `443` open for HTTP/TLS.
- Outbound HTTPS access to `https://sparql.soilwise.wetransform.eu/sparql/`.

Clone or copy this repository to the server:

```bash
sudo mkdir -p /opt/soil-vocabs
sudo chown "$USER":"$USER" /opt/soil-vocabs
git clone https://github.com/soilwise-he/soil-vocabs.git /opt/soil-vocabs
cd /opt/soil-vocabs/skosmos
```

If the server receives a deployment archive instead of using `git clone`, make sure the `skosmos/config`, `skosmos/plugins`, and `skosmos/docker-compose.yml` files are present.

For the remote-Virtuoso deployment, cloning this repository is enough to get the Skosmos Compose file, configuration, and SoilVoc plugin onto the server. The runtime vocabulary data comes from the Virtuoso graph, not from local Fuseki, so no local RDF load step is needed unless you deliberately use the `local-fuseki` fallback.

### 2. Configure the Production Container

Create a production `.env` file:

```bash
cd /opt/soil-vocabs/skosmos
cp .env.example .env
nano .env
```

Recommended production values:

```dotenv
SKOSMOS_PORT=127.0.0.1:9090
SKOSMOS_CONFIG=./config/skosmos-config.ttl
SKOSMOS_TAG=3.2
FUSEKI_PORT=9030
CACHE_PORT=9031
JENA_VERSION=5.4.0
```

Binding `SKOSMOS_PORT` to `127.0.0.1:9090` keeps the unencrypted container port private. Public traffic should enter through the HTTPS reverse proxy.

Pin `SKOSMOS_TAG` to a Skosmos image tag you have tested. Avoid `latest` for production unless you intentionally want automatic image changes during redeploys.

To make production look the same as the local deployment, use the same Skosmos image tag, the same `config/skosmos-config.ttl`, and the same `plugins/soilvoc-definition-source` directory. No Skosmos source-code fork or front-end redesign is needed for a normal public deployment.

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

Do not start the `local-fuseki` profile in production unless you intentionally want to use a local fallback triplestore.

### 3. Start Skosmos

```bash
cd /opt/soil-vocabs/skosmos
docker compose pull
docker compose up -d
docker compose ps
```

Only the `skosmos` service should be running in the remote-default mode.

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

### 5. Migrate the Existing W3ID Redirect

The `https://w3id.org/eusoilvoc` namespace is already registered in `perma-id/w3id.org`. It currently redirects to the GitHub Pages static viewer at:

```text
https://soilwise-he.github.io/soil-vocabs/
```

For the Skosmos migration, do not create a new W3ID namespace. Update the existing `eusoilvoc/.htaccess` in the `perma-id/w3id.org` repository so `https://w3id.org/eusoilvoc` points to the new Skosmos HTTPS origin.

Migration steps:

1. Deploy and verify the new Skosmos origin, for example `https://soilvoc.example.org/soilvoc/en/`.
2. Fork or update your fork of `https://github.com/perma-id/w3id.org`.
3. Edit the existing `eusoilvoc/.htaccess`.
4. Replace the old GitHub Pages target `https://soilwise-he.github.io/soil-vocabs/` with the new Skosmos target.
5. Keep `eusoilvoc/README.md` current if maintainers, project description, or target service details changed.
6. Open a pull request to `perma-id/w3id.org`.
7. After merge, verify that `https://w3id.org/eusoilvoc` lands on the Skosmos vocabulary page.

Minimal UI-only migration:

```apache
# /eusoilvoc/
# Permanent identifier for SoilVoc.
# Maintainer: <NAME>, <EMAIL>, GitHub: <USERNAME>

RewriteEngine On

# Previous target:
# https://soilwise-he.github.io/soil-vocabs/

RewriteRule ^$ https://soilvoc.example.org/soilvoc/en/ [R=303,L]
RewriteRule ^(.*)$ https://soilvoc.example.org/soilvoc/en/ [R=303,L]
```

Recommended Linked Data migration if you also publish a static RDF dump from the same HTTPS origin:

```apache
# /eusoilvoc/
# Permanent identifier for SoilVoc.
# Maintainer: <NAME>, <EMAIL>, GitHub: <USERNAME>

RewriteEngine On

# Previous target:
# https://soilwise-he.github.io/soil-vocabs/

RewriteCond %{HTTP_ACCEPT} text/turtle [OR]
RewriteCond %{HTTP_ACCEPT} application/rdf\+xml [OR]
RewriteCond %{HTTP_ACCEPT} application/ld\+json
RewriteRule ^$ https://soilvoc.example.org/rdf/SoilVoc_skosmos.ttl [R=303,L]

RewriteRule ^$ https://soilvoc.example.org/soilvoc/en/ [R=303,L]
RewriteRule ^(.*)$ https://soilvoc.example.org/soilvoc/en/ [R=303,L]
```

The old GitHub Pages page can remain online as a transition page, but it should not remain the W3ID target once Skosmos is production-ready. If you keep it, replace the static viewer with a short notice or redirect to `https://w3id.org/eusoilvoc` or directly to the Skosmos page, so old bookmarks to `https://soilwise-he.github.io/soil-vocabs/` do not strand users on the deprecated viewer.

For hash URIs such as `https://w3id.org/eusoilvoc#SoilpH`, the fragment `#SoilpH` is not sent to the W3ID server. The redirect can only act on the base URI `https://w3id.org/eusoilvoc`. This is normal for hash URI vocabularies: the base document should describe the vocabulary, and the fragment identifies a resource inside that document.

### 6. Verify W3ID After the Pull Request Is Merged

```bash
curl -I https://w3id.org/eusoilvoc
curl -L -I https://w3id.org/eusoilvoc
```

Expected behavior:

- The first command returns a `303` redirect after W3ID is configured.
- The second command follows the redirect and reaches `https://soilvoc.example.org/soilvoc/en/`.
- Opening `https://w3id.org/eusoilvoc` in a browser lands on the SoilVoc Skosmos vocabulary page.

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

For vocabulary data changes:

1. Regenerate `skosmos/SoilVoc_skosmos.ttl` locally or in CI.
2. Upload the regenerated TTL to the Virtuoso graph `https://w3id.org/eusoilvoc`.
3. If you publish a static RDF dump, copy the regenerated TTL to `/var/www/soilvoc-rdf/SoilVoc_skosmos.ttl` on the server.
4. Re-run the public smoke tests above.

Because production Skosmos queries Virtuoso directly, no local Fuseki reload is needed. Restart Skosmos only when its config, plugin files, or container image changes.

## Optional Local Fuseki Fallback

Use this only when you want an offline/local triplestore. It uses `config/skosmos-config.local-fuseki.ttl`, starts Fuseki and Varnish through the `local-fuseki` profile, and loads `SoilVoc_skosmos.ttl` into the local graph.

```powershell
cd C:\Users\wang479\Downloads\soil-vocabs\skosmos
$env:SKOSMOS_CONFIG = "./config/skosmos-config.local-fuseki.ttl"
docker compose --profile local-fuseki up -d --build
.\load-soilvoc.ps1
```

If your PowerShell execution policy blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\load-soilvoc.ps1
```

If the fallback stack was already running before a reload, restart the cache and frontend so old responses do not mask the updated graph:

```powershell
docker compose --profile local-fuseki restart fuseki-cache skosmos
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

For the local Fuseki fallback, include the profile when you want to stop profiled services explicitly:

```powershell
docker compose --profile local-fuseki down
```

## Clean Local Fuseki Reset

This removes the local Fuseki data volume and reloads the Skosmos copy from scratch:

```powershell
docker compose --profile local-fuseki down -v
python .\generate_skosmos_ttl.py
$env:SKOSMOS_CONFIG = "./config/skosmos-config.local-fuseki.ttl"
docker compose --profile local-fuseki up -d --build
.\load-soilvoc.ps1
```

## Notes

- Remote SPARQL endpoint: `https://sparql.soilwise.wetransform.eu/sparql/`
- Skosmos vocabulary graph URI: `https://w3id.org/eusoilvoc`
- SoilVoc concept URI space: `https://w3id.org/eusoilvoc#`
- Skosmos UI port: `9090`
- Local Fuseki fallback host port: `9030`
- Local Varnish fallback host port: `9031`
- The remote default uses Skosmos' Generic SPARQL dialect. Exact label searches such as `soil porosity` work directly; use wildcard terms such as `*porosity*` for partial single-word search checks.
- `SoilVoc_skosmos.ttl` is a generated Skosmos display copy; regenerate it from `../SoilVoc.ttl` and `soilvoc_ontology.ttl`.
- Override ports, image versions, or `SKOSMOS_CONFIG` by copying `.env.example` to `.env` and editing the values.
- W3ID identifier setup: `https://w3id.org/`
- Skosmos Docker notes: `https://github.com/NatLibFi/Skosmos/wiki/Install-Skosmos-with-Fuseki-in-Docker`
- Skosmos configuration reference: `https://github.com/NatLibFi/Skosmos/wiki/Configuration`
