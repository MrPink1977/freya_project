"""
import_dorking_knowledge_to_chromadb.py

Imports a comprehensive Google dorking knowledge base into the
ChromaDB 'google_dorking_knowledge' collection running in Docker.

Run from PowerShell:
    python import_dorking_knowledge_to_chromadb.py

Requirements:
    pip install chromadb
"""

import logging
import sys
import time
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "google_dorking_knowledge"
BATCH_SIZE = 20

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── KNOWLEDGE BASE ────────────────────────────────────────────────────────────
# Inline knowledge base — no external file dependency
DORKING_DOCUMENTS = [
    {
        "id": "op_site",
        "category": "core_operators",
        "subcategory": "domain_filtering",
        "title": "site: operator",
        "content": """Operator: site:
Purpose: Restrict search results to a specific domain or subdomain.
Syntax: site:domain.com [keywords]
Examples:
  site:github.com password
  site:tesla.com careers
  site:.gov filetype:pdf budget
  site:reddit.com "home assistant"
Notes:
  - Use site:.edu, site:.gov, site:.mil for institutional searches
  - Combine with -site: to exclude a domain from results
  - site:domain.com -site:subdomain.domain.com excludes a subdomain
  - No space between site: and the domain
  - Works on Bing, DuckDuckGo, and Yahoo with same syntax
Use cases: Limit research to one organization, find all indexed pages of a site, discover subdomains, competitor analysis.""",
    },
    {
        "id": "op_filetype",
        "category": "core_operators",
        "subcategory": "file_filtering",
        "title": "filetype: and ext: operators",
        "content": """Operator: filetype: (alias: ext:)
Purpose: Filter results to a specific file type or extension.
Syntax: filetype:ext [keywords]
Common file types:
  filetype:pdf — PDF documents (reports, manuals, research papers)
  filetype:xls OR filetype:xlsx — Excel spreadsheets
  filetype:doc OR filetype:docx — Word documents
  filetype:ppt OR filetype:pptx — PowerPoint presentations
  filetype:txt — Plain text files (logs, configs, notes)
  filetype:csv — Comma-separated data files
  filetype:xml — XML configuration and data files
  filetype:json — JSON data files
  filetype:sql — SQL database dumps
  filetype:log — Log files
  filetype:env — Environment variable files (often contain secrets)
  filetype:cfg / filetype:conf / filetype:ini — Configuration files
  filetype:bak / filetype:old / filetype:backup — Backup files
  filetype:yaml / filetype:yml — YAML config files
  filetype:toml — TOML config files
  filetype:php / filetype:py / filetype:js / filetype:sh — Source code
  filetype:ps1 — PowerShell scripts
  filetype:kdbx — KeePass password database
  filetype:pem / filetype:key / filetype:p12 — Certificate and key files
Examples:
  filetype:pdf site:nasa.gov "classified"
  filetype:xls inurl:password
  filetype:env "DB_PASSWORD"
  filetype:sql "INSERT INTO users"
Use cases: Find leaked credentials, research documents, source code, configuration files, database dumps.""",
    },
    {
        "id": "op_intitle",
        "category": "core_operators",
        "subcategory": "title_search",
        "title": "intitle: and allintitle: operators",
        "content": """Operator: intitle: / allintitle:
Purpose: Search for pages where the HTML <title> tag contains specific words.
Syntax:
  intitle:word — title contains this single word
  intitle:"exact phrase" — title contains this exact phrase
  allintitle:word1 word2 — title contains ALL listed words (in any order)
Examples:
  intitle:"index of" — open directory listings
  intitle:"index of" /etc/passwd — exposed passwd files
  intitle:"dashboard" inurl:admin — admin dashboards
  intitle:"login" inurl:admin — admin login pages
  intitle:"phpMyAdmin" — exposed phpMyAdmin panels
  intitle:"Kibana" — exposed Kibana dashboards
  intitle:"Grafana" — exposed Grafana dashboards
  intitle:"Jenkins" — exposed Jenkins CI/CD panels
  intitle:"Jupyter Notebook" — exposed Jupyter notebooks
  intitle:"Webcam" OR intitle:"IP Camera" — exposed cameras
  intitle:"router" inurl:admin — router admin panels
  allintitle:admin login panel — pages with all three words in title
Use cases: Finding exposed admin panels, open directories, login pages, dashboards, IoT devices.""",
    },
    {
        "id": "op_inurl",
        "category": "core_operators",
        "subcategory": "url_search",
        "title": "inurl: and allinurl: operators",
        "content": """Operator: inurl: / allinurl:
Purpose: Search for pages where the URL contains specific text.
Examples:
  inurl:admin — pages with "admin" in the URL
  inurl:login — login pages
  inurl:wp-admin — WordPress admin pages
  inurl:phpmyadmin — phpMyAdmin installations
  inurl:/etc/passwd — exposed system files
  inurl:config.php — PHP config files
  inurl:".git" — exposed Git repositories
  inurl:api/v1 — API endpoints
  inurl:swagger — Swagger API documentation
  inurl:actuator — Spring Boot actuator endpoints
  inurl:debug — debug endpoints
  inurl:test — test/staging environments
  inurl:backup — backup directories
  inurl:upload — file upload endpoints
  inurl:shell — web shells
  inurl:php?id= — PHP pages with ID parameter (SQL injection candidates)
  inurl:index.php?page= — LFI candidates
  inurl:.env — exposed .env files
Use cases: Finding admin panels, login pages, exposed APIs, vulnerable parameters, file upload endpoints.""",
    },
    {
        "id": "op_intext",
        "category": "core_operators",
        "subcategory": "content_search",
        "title": "intext: and allintext: operators",
        "content": """Operator: intext: / allintext:
Purpose: Search for pages where the body content contains specific text.
Examples:
  intext:"password" filetype:txt — text files containing the word password
  intext:"BEGIN RSA PRIVATE KEY" — exposed RSA private keys
  intext:"BEGIN OPENSSH PRIVATE KEY" — exposed SSH private keys
  intext:"api_key" filetype:json — JSON files with API keys
  intext:"aws_access_key_id" — exposed AWS credentials
  intext:"DB_PASSWORD" filetype:env — .env files with database passwords
  intext:"secret_key" filetype:py — Python files with secret keys
  intext:"Authorization: Bearer" — pages exposing Bearer tokens
  intext:"mysql_connect" filetype:php — PHP files with MySQL connections
  intext:"ConnectionString" filetype:config — .NET config files with DB strings
  allintext:username password filetype:log — log files with credentials
Use cases: Finding exposed credentials, API keys, private keys, database connection strings.""",
    },
    {
        "id": "op_boolean",
        "category": "core_operators",
        "subcategory": "boolean_logic",
        "title": "Boolean operators: AND, OR, NOT, quotes, wildcard, AROUND",
        "content": """Boolean and Grouping Operators in Google Dorking:

AND: term1 AND term2 (Google uses AND by default)
OR: term1 OR term2  (or pipe: term1 | term2)
  Example: filetype:xls OR filetype:xlsx intext:password
NOT / exclusion (-): -term excludes results containing that term
  Example: site:example.com -www (exclude www subdomain)
  Example: intitle:"index of" -"parent directory"
Exact phrase (""): "exact phrase" — only results with that exact sequence
  Example: "password is" filetype:txt
  Example: "BEGIN CERTIFICATE" site:pastebin.com
Wildcard (*): matches any word or phrase
  Example: "my * password is" — finds "my wifi password is", etc.
  Example: site:*.example.com — matches any subdomain
Number range (..): number1..number2
  Example: iphone $200..$400
Grouping (()): (term1 OR term2) AND term3
  Example: (filetype:xls OR filetype:csv) intext:password site:.edu
AROUND(X) proximity: term1 AROUND(n) term2
  Finds pages where terms appear within n words of each other
  Example: password AROUND(3) username
  Example: "api key" AROUND(5) "secret"
Notes:
  - Operators are case-insensitive
  - Combine multiple operators: site:github.com filetype:env intext:"DB_PASSWORD" -test""",
    },
    {
        "id": "op_temporal",
        "category": "core_operators",
        "subcategory": "time_filtering",
        "title": "Temporal operators: before:, after:, daterange:",
        "content": """Temporal Search Operators:

before:YYYY-MM-DD — results indexed before the date
  Example: "data breach" before:2020-01-01
  Example: site:example.com before:2023-06-01

after:YYYY-MM-DD — results indexed after the date
  Example: "CVE-2024" after:2024-01-01
  Example: filetype:pdf "annual report" after:2023-12-31

daterange: — Julian date format (less commonly used)
  Example: daterange:20240101-20240630

Google Search Tools (UI):
  After searching, click Tools → Any time → filter by hour/day/week/month/year/custom
  More reliable than daterange: operator

Use cases:
  - Finding recently leaked credentials or breaches
  - Researching historical content before a specific event
  - Finding the most current CVE disclosures
  - Tracking when a page was first indexed""",
    },
    {
        "id": "op_cache_related",
        "category": "core_operators",
        "subcategory": "google_special",
        "title": "cache:, related:, info:, define:, inanchor:, phonebook: operators",
        "content": """Google Special-Purpose Operators:

cache:url — shows Google's cached version of a page
  Useful when live page is down, deleted, or changed
  Alternative: web.archive.org (Wayback Machine)

related:domain.com — finds websites similar to the specified domain
  Example: related:reddit.com — finds Reddit-like forums
  Useful for competitor research

info:url — provides Google's summary about a URL
  Shows cache link, similar pages, pages linking to it

define:word — returns dictionary definitions
  Example: define:OSINT

inanchor:text — finds pages where other pages link to them using specific anchor text
  Example: inanchor:"click here to login" — finds login pages linked with that text

phonebook:name location — searches for phone numbers (limited in modern Google)
  Alternative: site:whitepages.com OR site:spokeo.com "name"

loc: / location: — restrict results to a geographic area
  Example: loc:"St. James Missouri" news
  Example: location:"Missouri" site:news.google.com

weather:location — returns weather for a location
  Example: weather:"St. James Missouri"

stocks:TICKER — returns stock information
  Example: stocks:AAPL""",
    },
    {
        "id": "open_dirs_basics",
        "category": "open_directories",
        "subcategory": "directory_listing",
        "title": "Finding open directory listings",
        "content": """Open Directory Hunting — Core Techniques:

What is an open directory?
  A web server with directory browsing enabled, exposing the file system structure
  and allowing anyone to browse and download files.

Core dorks:
  intitle:"index of" — the most classic open directory dork
  intitle:"index of /" — root directory listings
  intitle:"index of" "parent directory" — confirms real directory listing
  intitle:"index of" /backup — backup directories
  intitle:"index of" /uploads — upload directories
  intitle:"index of" /config — configuration file directories
  intitle:"index of" /logs — log file directories
  intitle:"index of" /private — private directories (often misconfigured)
  intitle:"index of" /admin — admin file directories
  intitle:"index of" /db — database file directories

Combining with file types:
  intitle:"index of" "*.sql" — SQL dumps
  intitle:"index of" "*.bak" — backup files
  intitle:"index of" "*.env" — environment files
  intitle:"index of" "*.pem" — certificate/key files
  intitle:"index of" "*.log" — log files
  intitle:"index of" "*.zip" — compressed archives
  intitle:"index of" "*.csv" — data files

Targeting specific sites:
  site:example.com intitle:"index of"
  site:.edu intitle:"index of" /research
  site:.gov intitle:"index of" /reports

Server-specific:
  intitle:"Index of" server.at — Apache server signature
  intitle:"Directory listing for" — Jetty/Java server directory listing""",
    },
    {
        "id": "creds_passwords",
        "category": "sensitive_data",
        "subcategory": "passwords_credentials",
        "title": "Finding exposed passwords and credentials",
        "content": """Exposed Password and Credential Dorks:

Plain text password files:
  filetype:txt intext:password
  filetype:txt intext:"username" intext:"password"
  filetype:log intext:password
  "password is" filetype:txt

Configuration files with credentials:
  filetype:env intext:DB_PASSWORD
  filetype:env intext:DATABASE_URL
  filetype:env intext:SECRET_KEY
  filetype:env intext:API_KEY
  filetype:env intext:AWS_SECRET
  filetype:yaml intext:password
  filetype:yml intext:password
  filetype:config intext:password
  filetype:ini intext:password
  filetype:cfg intext:password
  filetype:conf intext:password
  filetype:xml intext:password
  filetype:properties intext:password

Database credentials:
  filetype:sql intext:"INSERT INTO users"
  filetype:sql intext:password
  intext:"mysql_connect" filetype:php
  intext:"ConnectionString" filetype:config
  intext:"mongodb://" filetype:js
  intext:"redis://" filetype:conf

SSH and private keys:
  intext:"BEGIN RSA PRIVATE KEY"
  intext:"BEGIN DSA PRIVATE KEY"
  intext:"BEGIN EC PRIVATE KEY"
  intext:"BEGIN OPENSSH PRIVATE KEY"
  intext:"BEGIN PGP PRIVATE KEY BLOCK"
  site:github.com "BEGIN RSA PRIVATE KEY"
  site:pastebin.com "BEGIN RSA PRIVATE KEY"

API keys and tokens:
  intext:"api_key" filetype:json
  intext:"aws_access_key_id" filetype:yaml
  intext:"AKIA" — AWS access key prefix
  intext:"Authorization: Bearer" filetype:txt
  intext:"client_secret" filetype:json
  intext:"stripe_secret_key"
  intext:"xoxb-" — Slack Bot tokens
  intext:"xoxp-" — Slack User tokens

WordPress credentials:
  filetype:sql intext:"wp_users"
  inurl:wp-config.php intext:DB_PASSWORD""",
    },
    {
        "id": "creds_cloud",
        "category": "sensitive_data",
        "subcategory": "cloud_credentials",
        "title": "Cloud and infrastructure credential exposure dorks",
        "content": """Cloud Infrastructure Credential Dorks:

AWS (Amazon Web Services):
  intext:"aws_access_key_id" intext:"aws_secret_access_key"
  filetype:csv "AWSAccessKeyId"
  filetype:json "aws_access_key_id"
  filetype:yaml "aws_access_key_id"
  site:github.com "AKIA" — AWS access key IDs start with AKIA
  intext:"[default]" intext:"aws_access_key_id" filetype:ini

Google Cloud Platform (GCP):
  filetype:json "type": "service_account"
  intext:"client_email" intext:"private_key" filetype:json
  intext:"GOOGLE_APPLICATION_CREDENTIALS"

Azure:
  intext:"DefaultEndpointsProtocol=https" intext:"AccountKey="
  filetype:json intext:"clientSecret" intext:"tenantId"
  intext:"AZURE_CLIENT_SECRET"

Docker and Kubernetes:
  filetype:yaml intext:"password:" site:github.com
  filetype:yaml intext:"kind: Secret" — Kubernetes secrets
  intext:"kubeconfig" filetype:yaml

Database services:
  intext:"mongodb+srv://" — MongoDB Atlas connection strings
  intext:"postgres://" intext:"password"
  intext:"mysql://" intext:"password"

CI/CD and DevOps:
  intext:"CIRCLE_TOKEN" OR intext:"CIRCLECI_TOKEN"
  intext:"GITHUB_TOKEN" filetype:yml
  intext:"NPM_TOKEN" filetype:yml
  intext:"DOCKER_PASSWORD" filetype:yml
  filename:terraform.tfvars — Terraform variable files (often have secrets)

Payment:
  intext:"sk_live_" — Stripe live secret keys
  intext:"pk_live_" — Stripe live publishable keys""",
    },
    {
        "id": "vuln_admin_panels",
        "category": "vulnerable_servers",
        "subcategory": "admin_panels",
        "title": "Finding exposed admin panels and login pages",
        "content": """Exposed Admin Panel and Login Page Dorks:

Generic admin panels:
  inurl:admin intitle:login
  inurl:/admin/login
  inurl:administrator
  inurl:wp-admin — WordPress admin
  inurl:wp-login.php — WordPress login
  inurl:joomla/administrator — Joomla admin
  inurl:phpmyadmin — phpMyAdmin database panel
  inurl:adminer — Adminer database panel
  inurl:cpanel — cPanel hosting control panel
  inurl:webmin — Webmin server admin

Network and infrastructure:
  intitle:"pfSense" — pfSense firewall
  intitle:"OPNsense" — OPNsense firewall
  intitle:"Fortinet" inurl:login
  intitle:"Ubiquiti" inurl:login
  intitle:"UniFi" inurl:login
  inurl:8080 intitle:admin — common alternative HTTP port
  inurl:8443 intitle:admin — common alternative HTTPS port

Monitoring and observability:
  intitle:"Grafana" inurl:login
  intitle:"Kibana" — Elasticsearch/Kibana dashboards
  intitle:"Prometheus" inurl:graph — Prometheus metrics
  intitle:"Zabbix" inurl:login
  intitle:"Nagios" inurl:login

Development and CI/CD:
  intitle:"Jenkins" inurl:login
  intitle:"GitLab" inurl:users/sign_in
  intitle:"Portainer" inurl:login — Docker management UI
  intitle:"Rancher" inurl:login — Kubernetes management
  intitle:"Traefik" inurl:dashboard — Traefik reverse proxy dashboard

AI and ML tools:
  intitle:"Jupyter Notebook" — Jupyter notebooks (often unauthenticated)
  intitle:"Streamlit" — Streamlit ML apps
  intitle:"Gradio" — Gradio ML demos
  intitle:"Ollama" inurl:11434 — Ollama LLM server
  intitle:"Open WebUI" — Open WebUI for LLMs
  intitle:"Home Assistant" inurl:login — Home Assistant""",
    },
    {
        "id": "vuln_cameras_iot",
        "category": "vulnerable_servers",
        "subcategory": "cameras_iot",
        "title": "Finding exposed cameras and IoT devices",
        "content": """Exposed Camera and IoT Device Dorks:

IP cameras and webcams:
  intitle:"webcamXP" — WebcamXP software
  intitle:"webcam 7" — Webcam 7 software
  intitle:"IP Camera" inurl:login
  intitle:"Network Camera" inurl:login
  intitle:"Live View / - AXIS" — Axis network cameras
  intitle:"Hikvision" inurl:login — Hikvision cameras
  intitle:"Dahua" inurl:login — Dahua cameras
  intitle:"Amcrest" inurl:login — Amcrest cameras
  inurl:ViewerFrame?Mode= — Panasonic cameras
  inurl:MultiCameraFrame?Mode= — Panasonic multi-camera
  inurl:/view/index.shtml — camera view pages
  inurl:axis-cgi/jpg — Axis camera image CGI

Home routers and modems:
  intitle:"ADSL Router" inurl:admin
  intitle:"Linksys" inurl:admin
  intitle:"NETGEAR" inurl:admin
  intitle:"D-Link" inurl:admin
  intitle:"TP-Link" inurl:admin
  intitle:"ASUS" inurl:admin

Industrial control systems (ICS/SCADA):
  intitle:"SCADA" inurl:login
  intitle:"HMI" inurl:login — Human Machine Interface
  intitle:"Siemens" inurl:portal — Siemens industrial

Smart home and building:
  intitle:"Home Assistant" inurl:login
  intitle:"openHAB" inurl:login
  intitle:"Domoticz" inurl:login
  inurl:8123 intitle:"Home Assistant" — HA on default port

NAS and storage:
  intitle:"Synology" inurl:login
  intitle:"QNAP" inurl:login
  intitle:"TrueNAS" inurl:login

Printers:
  intitle:"HP LaserJet" inurl:hp/device/this.LCDispatcher
  intitle:"Xerox" inurl:status

Notes:
  - Shodan (shodan.io) and Censys (censys.io) are more powerful for IoT device discovery
  - Google dorking for IoT is limited to devices with web interfaces indexed by Google""",
    },
    {
        "id": "vuln_databases",
        "category": "vulnerable_servers",
        "subcategory": "exposed_databases",
        "title": "Finding exposed databases and data stores",
        "content": """Exposed Database Dorks:

Database admin interfaces:
  inurl:phpmyadmin — phpMyAdmin (MySQL/MariaDB)
  inurl:adminer — Adminer (multi-database)
  inurl:pgadmin — pgAdmin (PostgreSQL)
  inurl:mongo-express — Mongo Express (MongoDB)
  inurl:redis-commander — Redis Commander
  inurl:elasticsearch:9200 — Elasticsearch API
  inurl:couchdb:5984 — CouchDB API

Database dumps and backups:
  filetype:sql "CREATE TABLE"
  filetype:sql "INSERT INTO users"
  filetype:sql intext:password
  filetype:sql site:github.com
  filetype:mdb — Microsoft Access databases
  filetype:sqlite — SQLite databases
  intitle:"index of" "*.sql"
  intitle:"index of" "*.sqlite"
  intitle:"index of" "*.db"

Data files with sensitive information:
  filetype:csv intext:email intext:password
  filetype:xls intext:username intext:password
  filetype:xlsx intext:"social security"
  filetype:csv intext:"credit card"

Elasticsearch and NoSQL:
  inurl:9200/_cat/indices — Elasticsearch index listing
  inurl:9200/_search — Elasticsearch search endpoint

Error messages revealing database info:
  intext:"SQL syntax" intext:"mysql_fetch"
  intext:"Warning: mysql_" — MySQL error messages
  intext:"ORA-" intext:"Oracle" — Oracle DB errors
  intext:"Microsoft OLE DB Provider for SQL Server" — MSSQL errors
  intext:"PostgreSQL query failed" — PostgreSQL errors""",
    },
    {
        "id": "osint_people",
        "category": "osint",
        "subcategory": "people_research",
        "title": "OSINT: Finding information about people",
        "content": """OSINT Dorks for People Research:

Finding by name:
  "John Doe" filetype:pdf — documents mentioning a person
  "John Doe" filetype:pdf OR filetype:docx OR filetype:xlsx — multiple doc types
  "John Doe" site:linkedin.com — LinkedIn profile
  "John Doe" site:twitter.com OR site:x.com — Twitter/X profile
  "John Doe" site:facebook.com — Facebook profile
  "John Doe" site:instagram.com — Instagram profile
  "John Doe" site:github.com — GitHub profile
  "John Doe" (site:twitter.com OR site:linkedin.com OR site:facebook.com) — multi-platform

Finding email addresses:
  "john.doe@" — find email addresses starting with a name
  "@gmail.com" "John Doe" — Gmail addresses for a person
  "John Doe" intext:"@" filetype:pdf — PDFs with email addresses
  username*com — wildcard to find email format (e.g., johndoe*com)

Finding by username:
  "johndoe" site:reddit.com — Reddit username
  "johndoe" site:github.com — GitHub username
  "johndoe" (site:twitter.com OR site:instagram.com OR site:tiktok.com)

Phone numbers:
  "555-1234" — search for a specific phone number
  "(555) 555-1234" — formatted phone number
  site:whitepages.com "John Doe" — Whitepages listing
  site:spokeo.com "John Doe" — Spokeo listing

Addresses and locations:
  "John Doe" "123 Main Street" — name + address combination
  "John Doe" "St. James" "Missouri" — name + city + state

Professional information:
  "John Doe" "resume" filetype:pdf — resumes
  "John Doe" "curriculum vitae" filetype:pdf — CVs
  "John Doe" site:linkedin.com "software engineer" — LinkedIn with job title

Court records and public records:
  "John Doe" site:courtlistener.com — court records
  "John Doe" filetype:pdf site:.gov — government documents""",
    },
    {
        "id": "osint_organizations",
        "category": "osint",
        "subcategory": "organization_research",
        "title": "OSINT: Researching organizations and companies",
        "content": """OSINT Dorks for Organization Research:

Company overview:
  site:company.com — all indexed pages
  site:company.com filetype:pdf — all PDFs on their site
  site:company.com inurl:careers OR inurl:jobs — job listings
  site:company.com inurl:investor OR inurl:ir — investor relations
  related:company.com — similar companies

Employee discovery:
  site:linkedin.com "company name" "software engineer" — employees by role
  "@company.com" — email addresses from the domain
  "company.com" intext:email filetype:pdf — PDFs with company emails

Technology stack discovery:
  site:company.com inurl:wp-admin — uses WordPress
  site:company.com inurl:drupal — uses Drupal
  site:company.com filetype:php — PHP-based site
  site:company.com filetype:aspx — ASP.NET-based site

Subdomain discovery:
  site:*.company.com — all subdomains indexed by Google
  site:*.company.com -www — all subdomains except www
  site:*.company.com inurl:admin — admin subdomains
  site:*.company.com inurl:dev OR inurl:staging OR inurl:test — dev environments

Document and report hunting:
  site:company.com filetype:pdf "confidential"
  "company name" filetype:pdf "annual report"
  "company name" filetype:pdf "penetration test"

Financial and legal:
  "company name" site:sec.gov — SEC filings
  "company name" filetype:pdf "10-K" — annual reports

GitHub and code repositories:
  site:github.com "company name" — company GitHub presence
  site:github.com "@company.com" — company email in GitHub
  site:github.com "company.com" filetype:env — leaked env files""",
    },
    {
        "id": "osint_social_media",
        "category": "osint",
        "subcategory": "social_media",
        "title": "OSINT: Social media platform dorking",
        "content": """Social Media Platform-Specific Dorks:

Twitter / X (twitter.com / x.com):
  site:twitter.com "keyword" — tweets containing keyword
  site:x.com "keyword" — same on new domain
  site:twitter.com "@username" — mentions of a username

LinkedIn (linkedin.com):
  site:linkedin.com/in "job title" "company" — people search
  site:linkedin.com/company "company name" — company page
  site:linkedin.com "email" "@company.com" — emails on LinkedIn

Facebook (facebook.com):
  site:facebook.com "keyword" — public Facebook content
  site:facebook.com/groups "keyword" — Facebook groups

Instagram (instagram.com):
  site:instagram.com "username" — Instagram profile

Reddit (reddit.com):
  site:reddit.com "keyword" — Reddit posts and comments
  site:reddit.com/r/subreddit "keyword" — within a subreddit

GitHub (github.com):
  site:github.com "keyword" — GitHub repositories and code
  site:github.com intext:"password" filetype:env — leaked env files
  site:github.com "BEGIN RSA PRIVATE KEY" — exposed private keys

Pastebin and paste sites:
  site:pastebin.com "keyword" — Pastebin pastes
  site:pastebin.com "email@domain.com" — email in pastes
  site:pastebin.com "BEGIN RSA PRIVATE KEY" — keys in pastes
  site:paste.ee "keyword" — Paste.ee
  site:hastebin.com "keyword" — Hastebin

YouTube (youtube.com):
  site:youtube.com "keyword" — YouTube videos
  site:youtube.com intitle:"keyword" — videos with keyword in title

Telegram:
  site:t.me "keyword" — public Telegram channels/groups

Discord:
  inurl:discord.gg — Discord invite links""",
    },
    {
        "id": "files_sensitive_docs",
        "category": "file_hunting",
        "subcategory": "sensitive_documents",
        "title": "Hunting for sensitive documents and reports",
        "content": """Sensitive Document Hunting Dorks:

Confidential and restricted documents:
  filetype:pdf "confidential" "do not distribute"
  filetype:pdf "internal use only"
  filetype:pdf "proprietary" "not for distribution"
  filetype:pdf "draft" "not for release"
  filetype:pdf "classified" site:.gov
  filetype:pdf "for official use only" site:.gov
  filetype:pdf "sensitive but unclassified" site:.gov

Security and audit reports:
  filetype:pdf "penetration test" "findings"
  filetype:pdf "vulnerability assessment"
  filetype:pdf "security audit" "recommendations"
  filetype:pdf "risk assessment" "confidential"

Financial documents:
  filetype:xls "budget" "confidential"
  filetype:xlsx "salary" site:company.com
  filetype:pdf "financial statements" "internal"
  filetype:pdf "merger" "acquisition" "confidential"

Legal documents:
  filetype:pdf "non-disclosure agreement"
  filetype:pdf "settlement agreement" "confidential"

HR and personnel:
  filetype:xls "employee" "salary" site:company.com
  filetype:csv "employee" "email" "phone"

Medical and health:
  filetype:pdf "patient" "confidential" site:.org
  filetype:pdf "HIPAA" "protected health information"

Research and academic:
  filetype:pdf "unpublished" "draft" site:.edu
  filetype:pdf "working paper" site:.edu
  filetype:pdf "thesis" site:.edu

Network and infrastructure diagrams:
  filetype:pdf "network diagram" "confidential"
  filetype:pdf "topology" "internal"

Meeting notes and minutes:
  filetype:pdf "meeting minutes" "confidential"
  filetype:docx "board meeting" "minutes"
  filetype:pptx "strategy" "confidential" site:company.com""",
    },
    {
        "id": "files_logs",
        "category": "file_hunting",
        "subcategory": "log_files",
        "title": "Finding exposed log files",
        "content": """Exposed Log File Dorks:

Web server logs:
  filetype:log intext:"GET /" — Apache/Nginx access logs
  filetype:log intext:"POST /" — POST request logs
  intitle:"index of" "access.log" — Apache access logs in open dirs
  intitle:"index of" "error.log" — error logs
  intitle:"index of" "*.log" — any log files

Application logs:
  filetype:log intext:password — logs containing passwords
  filetype:log intext:username intext:password — credential logs
  filetype:log intext:"login failed" — failed login logs
  filetype:log intext:"authentication failure" — auth failure logs
  filetype:log intext:"SQL" intext:"error" — SQL error logs
  filetype:log intext:"exception" intext:"stack trace" — error stack traces

System logs:
  filetype:log intext:"/etc/passwd" — passwd file references in logs
  filetype:log intext:"sudo" intext:"command" — sudo command logs
  filetype:log intext:"ssh" intext:"accepted" — SSH login logs
  filetype:log intext:"Invalid user" — SSH brute force logs

Database logs:
  filetype:log intext:"mysql" intext:"error" — MySQL error logs
  filetype:log intext:"PostgreSQL" intext:"error" — PostgreSQL logs
  filetype:log intext:"ORA-" — Oracle error logs

Specific log formats:
  ext:log "START test_database" — database test logs
  ext:log intext:"[ERROR]" — error-level log entries
  ext:log intext:"[WARN]" OR intext:"[WARNING]" — warning logs
  ext:log intext:"[DEBUG]" — debug logs
  ext:log intext:"token" OR intext:"session" — session/token logs""",
    },
    {
        "id": "vuln_web_apps",
        "category": "vulnerability_research",
        "subcategory": "web_app_vulns",
        "title": "Web application vulnerability discovery dorks",
        "content": """Web Application Vulnerability Discovery Dorks:

SQL Injection candidates:
  inurl:php?id= — PHP pages with numeric ID parameter
  inurl:asp?id= — ASP pages with ID parameter
  inurl:index.php?id= — common SQLi target
  inurl:product.php?id= — product pages
  inurl:article.php?id= — article pages
  inurl:"?page=" — page parameter
  inurl:"?cat=" — category parameter
  inurl:"?search=" — search parameter

Local File Inclusion (LFI) candidates:
  inurl:index.php?page= — page parameter (classic LFI)
  inurl:include.php?file= — file inclusion parameter
  inurl:view.php?file= — file view parameter
  inurl:template.php?page= — template parameter

Remote Code Execution (RCE) indicators:
  inurl:cmd.php — command execution PHP files
  inurl:shell.php — web shells
  inurl:c99.php — C99 web shell
  inurl:r57.php — R57 web shell
  intitle:"Web Shell" — web shell pages

Error messages revealing vulnerabilities:
  intext:"Warning: mysql_fetch_array()" — MySQL errors
  intext:"Warning: include(" — PHP include errors
  intext:"Fatal error: Call to undefined function" — PHP fatal errors
  intext:"Microsoft OLE DB Provider for SQL Server error" — MSSQL errors
  intext:"ORA-00933: SQL command not properly ended" — Oracle SQL errors
  intext:"Uncaught exception" intext:"stack trace" — application errors

Exposed development artifacts:
  inurl:.git/HEAD — exposed Git repositories
  inurl:.svn/entries — exposed SVN repositories
  inurl:.DS_Store — macOS directory metadata
  inurl:web.config — ASP.NET configuration files
  inurl:phpinfo.php — PHP info pages (reveals server config)
  inurl:info.php — PHP info pages
  inurl:test.php — test PHP pages

Exposed API endpoints:
  inurl:/api/v1 — REST API v1
  inurl:/api/v2 — REST API v2
  inurl:swagger.json — Swagger API spec
  inurl:swagger-ui — Swagger UI
  inurl:openapi.json — OpenAPI spec
  inurl:graphql — GraphQL endpoints
  inurl:graphiql — GraphQL IDE (often unauthenticated)""",
    },
    {
        "id": "vuln_cve_research",
        "category": "vulnerability_research",
        "subcategory": "cve_research",
        "title": "CVE and vulnerability research dorks",
        "content": """CVE and Security Vulnerability Research Dorks:

Finding CVE information:
  "CVE-2024-" filetype:pdf — CVE reports in PDF
  "CVE-2024-" site:nvd.nist.gov — NVD database
  "CVE-2024-" site:cve.mitre.org — MITRE CVE database
  "CVE-2024-" site:exploit-db.com — Exploit-DB
  "CVE-2024-" site:github.com — GitHub PoC exploits
  "CVE-2024-" "proof of concept" — PoC exploits
  "CVE-2024-" "exploit" filetype:py — Python exploits
  "CVE-2024-" "PoC" site:github.com — GitHub PoCs

Specific software vulnerabilities:
  site:nvd.nist.gov "Apache" "critical" after:2024-01-01
  site:nvd.nist.gov "WordPress" "critical" after:2024-01-01
  "Log4Shell" OR "Log4j" CVE-2021-44228 — Log4Shell vulnerability
  "Spring4Shell" CVE-2022-22965 — Spring4Shell

Patch and advisory research:
  site:security.microsoft.com — Microsoft Security Response Center
  site:ubuntu.com/security/notices after:2024-01-01
  site:access.redhat.com/security/cve after:2024-01-01

Bug bounty and disclosure:
  site:hackerone.com "disclosed" "critical" — HackerOne disclosures
  site:bugcrowd.com "vulnerability" — Bugcrowd reports
  "responsible disclosure" "vulnerability" site:company.com

Shodan dorks (use at shodan.io):
  product:"Apache httpd" version:"2.4.49" — specific Apache version
  port:22 "OpenSSH" version:"7.4" — old SSH versions
  http.title:"phpMyAdmin" — phpMyAdmin instances
  org:"Company Name" — all assets of an organization
  ssl.cert.subject.cn:"*.company.com" — SSL certificates for a domain""",
    },
    {
        "id": "advanced_combining",
        "category": "advanced_techniques",
        "subcategory": "query_construction",
        "title": "Advanced query construction and chaining operators",
        "content": """Advanced Dorking Query Construction:

Operator chaining principles:
  - Combine operators to narrow results dramatically
  - Order doesn't matter but readability matters for debugging
  - Start broad, add operators to narrow
  - Use parentheses for OR groups: (op1 OR op2) AND op3

Multi-operator examples:
  site:github.com filetype:env intext:DB_PASSWORD -test -example
  site:*.company.com inurl:admin intitle:login -www
  filetype:pdf site:.gov "classified" after:2020-01-01 before:2024-01-01
  (filetype:xls OR filetype:xlsx OR filetype:csv) intext:password site:.edu
  intitle:"index of" (filetype:sql OR filetype:bak OR filetype:env) -robots.txt
  site:pastebin.com (intext:"api_key" OR intext:"secret_key" OR intext:"password")

Subdomain enumeration via Google:
  site:*.target.com — all subdomains
  site:*.target.com -www -mail -ftp — exclude common subdomains
  site:*.target.com inurl:admin — admin subdomains only
  site:*.target.com inurl:dev OR inurl:staging OR inurl:test — dev environments
  site:*.target.com inurl:api — API subdomains

Technology fingerprinting:
  site:company.com "Powered by WordPress" — CMS detection
  site:company.com inurl:wp-content/themes — WordPress theme detection
  site:company.com filetype:php — PHP-based backend
  site:company.com filetype:aspx — .NET backend
  site:company.com filetype:jsp — Java backend

Google dorking rate limits and workarounds:
  - Google will show CAPTCHA if too many queries are made quickly
  - Space queries out; use different browsers/IPs if needed
  - Use Google's Advanced Search UI (google.com/advanced_search) for complex queries
  - DuckDuckGo, Bing, and Yandex support most operators and have fewer restrictions
  - Bing: site:, filetype:, intitle:, inurl:, intext: all work
  - DuckDuckGo: site:, filetype:, intitle:, inurl: work; less strict rate limiting

Query length limits:
  - Google search query limit: ~32 words or ~2048 characters
  - Break complex queries into multiple searches if needed

Negative filtering best practices:
  -site:example.com — exclude a domain
  -inurl:test — exclude test pages
  -filetype:html — exclude HTML pages (useful when hunting for files)
  -intitle:"404" — exclude 404 error pages""",
    },
    {
        "id": "advanced_alternative_engines",
        "category": "advanced_techniques",
        "subcategory": "alternative_search_engines",
        "title": "Alternative search engines: Bing, DuckDuckGo, Yandex, Shodan, Censys",
        "content": """Alternative Search Engines for Dorking:

Bing (bing.com):
  - Supports: site:, filetype:, intitle:, inurl:, intext:, contains:, ip:, language:
  - Unique: ip:x.x.x.x — find sites hosted on a specific IP
  - Unique: contains:filetype — find pages linking to a file type
  - Often indexes pages Google doesn't (especially older or less popular content)
  - Less aggressive rate limiting than Google

DuckDuckGo (duckduckgo.com):
  - Supports: site:, filetype:, intitle:, inurl:
  - No user tracking; results may differ from Google
  - Less strict rate limiting
  - !bang operators: !g (Google), !b (Bing), !w (Wikipedia), !gh (GitHub)
  - Example: !gh "password" filetype:env — search GitHub via DuckDuckGo

Yandex (yandex.com):
  - Russian search engine; indexes .ru domains much better than Google
  - Supports: site:, url:, title:, mime: (equivalent to filetype:)
  - Reverse image search is considered superior to Google's

Shodan (shodan.io) — Internet of Things search engine:
  - Indexes internet-connected devices, not web pages
  - Searches: port:, product:, version:, org:, country:, city:, hostname:, ssl:
  - Examples:
    port:22 "OpenSSH" — SSH servers
    port:3389 — RDP servers (Remote Desktop)
    port:8123 "Home Assistant" — exposed HA instances
    http.title:"phpMyAdmin" — phpMyAdmin instances
    http.title:"Jupyter Notebook" — exposed Jupyter notebooks
    org:"Company Name" — all assets of an organization
    ssl.cert.subject.cn:"*.company.com" — SSL certs for a domain
  - Requires account for full results; free tier is limited

Censys (censys.io) — Certificate and host search:
  - Focuses on TLS certificates and host data
  - Useful for subdomain discovery via certificate transparency logs
  - Example: certificates.parsed.subject.common_name:"*.company.com"
  - Free tier available

Grep.app (grep.app):
  - Searches across public GitHub repositories
  - Faster than site:github.com for code search

PublicWWW (publicwww.com):
  - Searches HTML source code of websites
  - Useful for finding sites using specific JavaScript libraries or tracking codes

Have I Been Pwned (haveibeenpwned.com):
  - Check if an email has been in a data breach
  - API available for programmatic queries

Wayback Machine (web.archive.org):
  - Archived versions of websites
  - Find deleted pages, old configurations, historical content
  - Example: web.archive.org/web/*/company.com/robots.txt — old robots.txt""",
    },
    {
        "id": "advanced_github_dorking",
        "category": "advanced_techniques",
        "subcategory": "github_code_search",
        "title": "GitHub code search and dorking for secrets and credentials",
        "content": """GitHub Code Search Dorking:

GitHub search operators (at github.com/search):
  language:python — filter by programming language
  filename:.env — search by filename
  path:.env — search by file path
  extension:env — search by extension
  user:username — search within a user's repos
  org:organization — search within an org's repos
  repo:user/repo — search within a specific repo
  stars:>1000 — repos with many stars
  pushed:>2024-01-01 — recently updated repos

Finding credentials in GitHub:
  filename:.env DB_PASSWORD — .env files with DB passwords
  filename:.env SECRET_KEY — .env files with secret keys
  filename:.env AWS_SECRET_ACCESS_KEY — AWS credentials
  filename:config.yml password — YAML configs with passwords
  filename:settings.py SECRET_KEY — Django secret keys
  filename:wp-config.php DB_PASSWORD — WordPress configs
  filename:database.yml password — Rails database configs
  filename:.npmrc _authToken — NPM auth tokens
  filename:credentials aws_access_key_id — AWS credentials file
  extension:pem private — PEM private keys
  extension:ppk private — PuTTY private keys
  "BEGIN RSA PRIVATE KEY" — RSA private keys
  "BEGIN OPENSSH PRIVATE KEY" — OpenSSH private keys
  "api_key" language:python — Python files with API keys
  "client_secret" language:javascript — JS files with client secrets

Finding specific technologies:
  filename:docker-compose.yml — Docker Compose files
  filename:Dockerfile — Dockerfiles
  filename:.travis.yml — Travis CI configs
  filename:.github/workflows — GitHub Actions workflows
  filename:Jenkinsfile — Jenkins pipeline files
  filename:terraform.tfvars — Terraform variable files (often have secrets)
  filename:*.tfstate — Terraform state files

Using Google to search GitHub:
  site:github.com "company.com" filetype:env — Google-indexed GitHub .env files
  site:github.com "company.com" intext:password — Google-indexed GitHub passwords
  site:github.com "BEGIN RSA PRIVATE KEY" — Google-indexed private keys
  site:raw.githubusercontent.com "password" — raw GitHub file content
  site:gist.github.com "password" — search Gists via Google""",
    },
    {
        "id": "advanced_news_research",
        "category": "advanced_techniques",
        "subcategory": "news_research",
        "title": "News, academic, and historical research dorking",
        "content": """News and Research Dorking:

Google News operators:
  source:reuters.com "keyword" — results from Reuters
  source:bbc.co.uk "keyword" — results from BBC
  source:nytimes.com "keyword" — results from NYT
  location:"city name" — news from a specific location
  after:2024-01-01 "keyword" — recent news on a topic

Finding primary sources:
  "keyword" site:reuters.com — Reuters articles
  "keyword" site:apnews.com — AP News
  "keyword" site:bbc.com — BBC
  "keyword" site:npr.org — NPR
  "keyword" filetype:pdf site:.gov — government press releases
  "keyword" site:whitehouse.gov — White House statements

Academic and research sources:
  "keyword" site:scholar.google.com — Google Scholar
  "keyword" site:arxiv.org — arXiv preprints
  "keyword" site:pubmed.ncbi.nlm.nih.gov — PubMed medical research
  "keyword" site:jstor.org — JSTOR academic journals
  "keyword" filetype:pdf site:.edu — academic PDFs
  "keyword" "peer reviewed" filetype:pdf — peer-reviewed papers

Historical research:
  "keyword" site:jstor.org — historical academic articles
  "keyword" filetype:pdf site:.edu "archaeology" — archaeological papers
  "keyword" site:archive.org — Internet Archive
  "keyword" site:loc.gov — Library of Congress
  "keyword" site:si.edu — Smithsonian Institution
  "keyword" site:nationalgeographic.com — National Geographic
  "keyword" site:smithsonianmag.com — Smithsonian Magazine
  "keyword" "ancient" OR "historical" filetype:pdf site:.edu
  "keyword" site:academia.edu — Academia.edu papers

YouTube research:
  site:youtube.com intitle:"keyword" — YouTube videos by title
  site:youtube.com "keyword" "documentary" — documentary videos
  site:youtube.com "keyword" "lecture" — academic lectures""",
    },
    {
        "id": "advanced_query_templates",
        "category": "advanced_techniques",
        "subcategory": "query_templates",
        "title": "Ready-to-use dorking query templates for common tasks",
        "content": """Ready-to-Use Google Dorking Query Templates:

TEMPLATE: Research a person
  "[Full Name]" site:linkedin.com
  "[Full Name]" (site:twitter.com OR site:x.com)
  "[Full Name]" filetype:pdf
  "[Full Name]" "@" — find email addresses
  "[Full Name]" "[City]" "[State]"

TEMPLATE: Research a company
  site:[company.com] — all pages
  site:*.[company.com] -www — all subdomains
  "[Company Name]" site:linkedin.com — employees
  "[Company Name]" filetype:pdf "annual report"
  site:[company.com] inurl:admin OR inurl:login

TEMPLATE: Find leaked credentials for a domain
  site:github.com "[company.com]" filetype:env
  site:pastebin.com "[company.com]" intext:password
  "[company.com]" intext:"BEGIN RSA PRIVATE KEY"
  filetype:env intext:"[company.com]" intext:DB_PASSWORD

TEMPLATE: Find exposed admin panels
  site:[target.com] inurl:admin intitle:login
  site:[target.com] inurl:wp-admin
  site:[target.com] inurl:phpmyadmin
  site:[target.com] intitle:"dashboard"

TEMPLATE: Find open directories
  site:[target.com] intitle:"index of"
  site:[target.com] intitle:"index of" "*.sql"
  site:[target.com] intitle:"index of" "*.env"
  site:[target.com] intitle:"index of" "*.bak"

TEMPLATE: Research a CVE or vulnerability
  "CVE-[YEAR]-[NUMBER]" site:nvd.nist.gov
  "CVE-[YEAR]-[NUMBER]" site:github.com "exploit"
  "CVE-[YEAR]-[NUMBER]" "proof of concept" filetype:py
  "[Software Name]" "vulnerability" after:[YEAR]-01-01

TEMPLATE: Find academic research on a topic
  "[topic]" filetype:pdf site:.edu
  "[topic]" site:arxiv.org
  "[topic]" site:scholar.google.com
  "[topic]" "peer reviewed" filetype:pdf

TEMPLATE: Historical research
  "[historical topic]" site:jstor.org
  "[historical topic]" site:loc.gov filetype:pdf
  "[historical topic]" site:si.edu
  "[historical topic]" "archaeology" filetype:pdf site:.edu

TEMPLATE: Find IoT/camera devices
  intitle:"[device brand]" inurl:login
  intitle:"IP Camera" site:[target.com]
  inurl:ViewerFrame?Mode= site:[target.com]

TEMPLATE: Competitive intelligence
  related:[competitor.com]
  "[competitor name]" site:glassdoor.com
  "[competitor name]" site:linkedin.com "engineer"
  "[competitor name]" filetype:pdf "roadmap" OR "strategy"

TEMPLATE: Bug bounty reconnaissance
  site:*.[target.com] — subdomain enumeration
  site:[target.com] inurl:api — API endpoints
  site:[target.com] inurl:swagger — API docs
  site:[target.com] inurl:.git — exposed Git repos
  site:[target.com] filetype:php inurl:?id= — SQLi candidates
  site:[target.com] inurl:debug OR inurl:test — dev endpoints""",
    },
    {
        "id": "ghdb_categories",
        "category": "ghdb_reference",
        "subcategory": "categories",
        "title": "Google Hacking Database (GHDB) categories and taxonomy",
        "content": """Google Hacking Database (GHDB) — Official Categories:

The GHDB (exploit-db.com/google-hacking-database) organizes dorks into these categories:

1. Footholds — Entry points into systems (login pages, admin panels, remote access)
2. Files Containing Usernames — Files exposing usernames, user lists, account info
3. Sensitive Directories — Directories containing sensitive files (backup, config, private)
4. Web Server Detection — Identifying web server software and versions
5. Vulnerable Files — Files with known vulnerabilities or misconfigurations
6. Vulnerable Servers — Servers with known vulnerabilities or misconfigurations
7. Error Messages — Error pages that reveal sensitive information (DB errors, stack traces)
8. Files Containing Juicy Info — Config files, readme files, changelog files
9. Files Containing Passwords — Files directly containing passwords or credentials
10. Sensitive Online Shopping Info — E-commerce sites exposing customer or payment data
11. Network or Vulnerability Data — Network topology, vulnerability scan results
12. Pages Containing Login Portals — Login pages for VPN, webmail, CRM systems
13. Various Online Devices — IoT devices, network equipment, industrial systems
14. Advisories and Vulnerabilities — Published security advisories and CVE disclosures

Reference: https://www.exploit-db.com/google-hacking-database""",
    },
    {
        "id": "ethics_legal",
        "category": "ethics_and_legal",
        "subcategory": "guidelines",
        "title": "Legal and ethical guidelines for Google dorking",
        "content": """Legal and Ethical Guidelines for Google Dorking:

What is legal:
  - Searching Google with advanced operators is legal in all jurisdictions
  - Viewing publicly indexed web pages is legal
  - Researching your own systems and infrastructure
  - Authorized penetration testing with written permission
  - Academic research and journalism
  - Bug bounty programs within defined scope
  - OSINT research on public figures using publicly available information

What is potentially illegal or unethical:
  - Accessing systems or files you don't have permission to access
  - Using found credentials to log into accounts you don't own
  - Downloading sensitive data found via dorking without authorization
  - Using dorking to facilitate stalking, harassment, or doxxing
  - Accessing private medical, financial, or personal data without consent
  - Using found vulnerabilities to attack systems without authorization

Computer Fraud and Abuse Act (CFAA) — USA:
  - Prohibits unauthorized access to computer systems
  - "Authorization" is key — finding something via Google doesn't grant access
  - Penalties range from fines to federal prison time

GDPR — European Union:
  - Accessing or processing EU citizens' personal data without legal basis is illegal
  - Even if data is publicly accessible, processing it may violate GDPR

Responsible disclosure:
  - If you find a vulnerability via dorking, report it to the organization
  - Use their security contact (security@company.com) or bug bounty program
  - Give them reasonable time to fix before public disclosure

Best practices:
  - Always have written authorization before testing systems you don't own
  - Use dorking for research, journalism, and authorized security testing
  - Don't access, download, or use data you find unless you have permission
  - Keep records of your research methodology""",
    },
]


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Google Dorking Knowledge Base → ChromaDB Importer")
    print("=" * 60)

    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed. Run: pip install chromadb")
        sys.exit(1)

    # Connect to Docker ChromaDB
    log.info(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT} ...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        client.heartbeat()
        log.info("Connected to ChromaDB successfully.")
    except Exception as e:
        log.error(f"Failed to connect to ChromaDB: {e}")
        log.error("Make sure your Docker ChromaDB container is running.")
        sys.exit(1)

    # Get or create the collection
    log.info(f"Getting or creating collection: '{COLLECTION_NAME}' ...")
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Comprehensive Google dorking knowledge base for Freya"},
    )

    total = len(DORKING_DOCUMENTS)
    log.info(f"Importing {total} dorking knowledge documents...")

    # Upsert in batches
    upserted = 0
    for i in range(0, total, BATCH_SIZE):
        batch = DORKING_DOCUMENTS[i : i + BATCH_SIZE]
        ids = [doc["id"] for doc in batch]
        documents = [doc["content"] for doc in batch]
        metadatas = [
            {
                "title": doc["title"],
                "category": doc["category"],
                "subcategory": doc["subcategory"],
                "imported_at": datetime.now().isoformat(),
            }
            for doc in batch
        ]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        upserted += len(batch)
        log.info(f"  Upserted {upserted}/{total} documents...")
        time.sleep(0.1)  # small delay to avoid overwhelming the server

    # Verify
    count = collection.count()
    log.info(f"")
    log.info(f"✅ Import complete!")
    log.info(f"   Collection: '{COLLECTION_NAME}'")
    log.info(f"   Total documents in collection: {count}")
    log.info(f"")
    log.info(f"Categories imported:")
    categories = {}
    for doc in DORKING_DOCUMENTS:
        cat = doc["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, cnt in sorted(categories.items()):
        log.info(f"   {cat}: {cnt} documents")


if __name__ == "__main__":
    main()
