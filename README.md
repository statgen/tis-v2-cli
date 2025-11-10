# Imputation Server CLI Tool

The Imputation Server tool `./impute` allows you to interact via CLI with the following imputation servers:

* [TOPMed Imputation Server](https://imputation.biodatacatalyst.nhlbi.nih.gov)
* [Michigan Imputation Server](https://imputationserver.sph.umich.edu)

This repository includes the CLI tool itself, as well as a Python SDK and additional helper scripts.

## Examples

List all your jobs in the TOPMed server (CLI):
```sh
./impute topmed list-jobs
```

...or do it in a Python script:
```python
api = TisV2Api(env="topmed")
all_jobs = api.list_jobs()
```

Get a specific job by its ID in the Michigan server (CLI):
```sh
./impute michigan get-job <job-ID>
```

Python:
```python
api = TisV2API(env="michigan")
one_job = api.get_job(job_id)
```

Submit a job to a custom server called `mcps`:
```sh
./impute mcps submit-job \
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

And you're good to go:
```sh
./impute <options...>
```

## Access Tokens

Supported imputation servers use access tokens to verify user identity. A token is needed to access the API endpoints.

You can get an expirable token by navigating to the server website and pressing `(your username) -> Profile -> API Access`. Please note that admin rights do *not* carry over to this token.

The SDK and CLI tools in this repository expect the existence of a local folder `data/`, inside which they can find tokens stored in plaintext, in a file named `<server>.token` (for example, `data/topmed.token`). If no such file is found, you will be interactively asked for a token (user-level operations), or for login credentials (admin-level operations).

A special admin token is needed for some operations. Admin tokens are stored in `data/<server>-admin.token`. If such a file does not exist, you will be interactively asked for login details. You can force a login by running `./impute admin login`.

**Please use caution when storing and using access tokens! Anyone using your token can impersonate you in the server.**

## CLI

`./impute` is the primary API interaction script. It has a lot of options, so using `--help` to find what you need is recommended.

You always need to specify the target server (e.g., `topmed` or `michigan`). By default, the script expects a text file `data/<server>.token` (e.g., `data/michigan.token`) containing a valid access token for the specified server; a different token file can be specified by passing `--token-file <path-to-token>`

* `./impute <server> list-jobs` lists all your jobs in the selected server, past and present.
* `./impute <server> get-job <job-id>` gives detailed information about a single job.
* `./impute <server> submit-job <params...>` submits a job with the provided parameters (some mandatory, some optional; check defaults!)
* `./impute <server> cancel-job <job-id>` cancels the selected job.
* `./impute <server> restart-job <job-id>` re-runs the selected job from scratch.
* `./impute <server> admin <admin-command> ...` calls commands that require admin-level access. See [Access Tokens](#access-tokens) for more details.
  * `./impute <server> admin login (--username <username) (--password <password>)` gets an admin token from the server.
    * We recommend to skip the password argument. You will be prompted securely for a password input.
  * `./impute <server> admin list-users` lists all users in the given server.
  * `./impute <server> admin list-jobs --state (running-ltq | current | retired)` lists jobs from all users from a specific set:
    * `running-ltq`: the main queue for running jobs.
    * `current`: seems to be the pre-processing queue.
    * `retired`: non-running jobs: finished, cancelled, failed...
    * More than one queue can be requested by repeating the `--state <state>` parameters.
  * `./impute <server> admin kill-all` cancels all running jobs.

## SDK

All library code is located in `local/`. The main point of interest is the API interface class `local.api.TisV2Api`. It expects a `data/<server>.token` file containing an access token, unless a different path is explicitly provided (see [Access Tokens](#access-tokens)).

User methods:
* `list_jobs()`: Lists all jobs visible by the current user (regardless of current status).
* `get_job(id)`: Gets detailed information about the requested job.
* `submit_job(params)`: Submits a job for processing.
* `cancel_job(id)`: Cancels the specified job.
* `restart_job(id)`: Retries the specified job.

Admin methods:
* `admin_login(username, password)`: Requests an admin-level token from the server.
* `admin_list_users()`: Calls the admin user listing endpoint.
* `admin_list_jobs(states)`: Calls the admin job listing endpoint.
* `admin_kill_all()`: Cancels all running jobs.
