# Imputation Server CLI Tool

The Imputation Server tool `./impute` allows you to interact via CLI with imputation servers such as:

* [TOPMed Imputation Server](https://imputation.biodatacatalyst.nhlbi.nih.gov)
* [Michigan Imputation Server](https://imputationserver.sph.umich.edu)

It supports any imputation server running [Cloudgene 3](https://www.cloudgene.io/) and [Imputation Server 2](https://github.com/genepi/imputationserver2). See [Adding Servers](#adding-servers) for details on communicating with other servers.

This repository includes the CLI tool itself, as well as a Python SDK and additional helper scripts.

## Examples

List all your jobs in the TOPMed server (CLI):
```sh
./impute job list topmed
```

...or do it in a Python script:
```python
from local.api import get_api
api = get_api("topmed")
all_jobs = api.list_jobs()
```

Get a specific job by its ID in the Michigan server (CLI):
```sh
./impute job get michigan <job-ID>
```

Python:
```python
from local.api import get_api
api = get_api("michigan")
one_job = api.get_job(job_id)
```

Register a server called `mcps`:
```sh
./impute server register mcps <url>
```

Submit a job to the newly registered server:
```sh
./impute job submit mcps \
        --name 'My test!' \
        --refpanel topmed-r3 \
        --population all \
        --build hg19 \
        --file data/chr20.vcf.gz \
        --file data/chr21.vcf.gz
```

## Installation

This repo uses `uv` for dependency management, [see here for details.](https://docs.astral.sh/uv/)

Once you have `uv` installed, navigate to the project root and run:
```sh
uv sync
```

And you're good to go! You can see all available commands by running:
```sh
./impute --help
```

## Access Tokens

Supported imputation servers use access tokens to verify user identity. A token is needed to access the API endpoints.

You can get an expirable token by navigating to the server website and pressing `(your username) -> Profile -> API Access`. Please note that admin rights do *not* carry over to this token.

The SDK and CLI tools in this repository expect the existence of a local folder `data/`, inside which they can find tokens stored in plaintext, in a file named `<server>.token` (for example, `data/topmed.token`). If no such file is found, you will be interactively asked for a token (user-level operations), or for login credentials (admin-level operations).

A special admin token is needed for some operations. Admin tokens are stored in `data/<server>-admin.token`. If such a file does not exist, you will be interactively asked for login details. You can force a login by running `./impute admin login`.

**Please use caution when storing and using access tokens! Anyone using your token can impersonate you in the server.**

## CLI

`./impute` is the primary API interaction script. It has a lot of options, so using `--help` to find what you need is recommended.

Many commands require you to specify which server they apply to (e.g., `topmed` or `michigan`). By default, the script expects a text file `data/<server>.token` (e.g., `data/michigan.token`) containing a valid access token for the specified server; a different token file can be specified by passing `--token-file <path-to-token>`

* `./impute version` prints the utility's version.
* `./impute server` contains subcommands for managing available servers.
  * `./impute server register <name> <url>` adds a server registry entry mapping the provided `name` (must be unique) to the provided `url`. The server is queried for basic information.
  * `./impute server show (name)` lists complete information about all registered servers (if `name` is not provided), or about the selected server (if `name` is provided).
* `./impute job` contains subcommands for interacting with your jobs in a specific server.
  * `./impute job submit <server> <params...>` submits a job with the provided parameters (some mandatory, some optional; check defaults!)
  * `./impute job download <server> <job-id>` downloads all files for the given job.
  * `./impute job get <server> <job-id>` gives detailed information about a single job.
  * `./impute job list <server>` lists all your jobs in the selected server, past and present.
  * `./impute job cancel <server> <job-id>` cancels the selected job.
  * `./impute job restart <server> <job-id>` re-runs the selected job from scratch.
* `./impute admin` contains subcommands that require admin-level access. See [Access Tokens](#access-tokens) for more details.
  * `./impute admin login <server> (--username <username) (--password <password>)` gets an admin token from the server.
    * We recommend to skip the password argument. You will be prompted securely for a password input.
  * `./impute admin list-users <server> admin` lists all users in the given server.
  * `./impute admin list-jobs <server> admin --state (running-ltq | current | retired)` lists jobs from all users from a specific set:
    * `running-ltq`: the main queue for running jobs.
    * `current`: seems to be the pre-processing queue.
    * `retired`: non-running jobs: finished, cancelled, failed...
    * More than one queue can be requested by repeating the `--state <state>` parameters.
  * `./impute admin kill-all <server>` cancels all running jobs.

## SDK

All library code is located in `local/`. The main point of interest is the API interface class `local.api.TisV2Api`. It expects a `data/<server>.token` file containing an access token, unless a different path is explicitly provided (see [Access Tokens](#access-tokens)).

User methods:
* `list_jobs()`: Lists all jobs visible by the current user (regardless of current status).
* `get_job(id)`: Gets detailed information about the requested job.
* `submit_job(params)`: Submits a job for processing.
* `cancel_job(id)`: Cancels the specified job.
* `restart_job(id)`: Retries the specified job.
* `list_refpanels()`: Lists all refpanels in the server, including details such as the available populations.
* `download(download_dir, job_id)`: Downloads all files associated with the provided `job_id`, and saves them in `download_dir/<job-id>`

Admin methods:
* `admin_login(username, password)`: Requests an admin-level token from the server.
* `admin_list_users()`: Calls the admin user listing endpoint.
* `admin_list_jobs(states)`: Calls the admin job listing endpoint.
* `admin_kill_all()`: Cancels all running jobs.

## Adding Servers

To register a new server, run:
```bash
./impute server register <server-id> <base-url>
```

Information about all registered servers can be found in `data/servers.yaml`. The provided `server-id` must be unique (up to normalization), and not clash with any registered aliases. The `base-url` must correspond to a Cloudgene server, e.g., <https://imputation.biodatacatalyst.nhlbi.nih.gov> for the TOPMed Imputation Server.

When a new server is registered, it is called to get information on its reference panels, and the available population options in each reference panel.
