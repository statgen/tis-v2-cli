# TOPMed Imputation Server CLI Tool

This repo provides an SDK and CLI tools to interact with the TOPMed Imputation Server programmatically.

List all your jobs in the `dev` environment (CLI):
```sh
uv run script/tis.py dev list-jobs
```

...or do it in a Python script:
```python
api = TisV2Api(env="dev")
all_jobs = api.list_jobs()
```

Get a specific job by its ID in prod (CLI):
```sh
uv run script/tis.py prod get-job <job-ID>
```

Python:
```python
job_id = "..."
one_job = api.get_job(job_id)
```

Submit 10 jobs to dev on a 30s delay:
```sh
uv run script/tis.py \
        --repeat 10 --delay 30 --minimal-output \
    dev submit-job \
        --refpanel hapmap --build hg19 --population eur --file <file-path>
```

## Installation

This repo uses `uv` for dependency management, [see here for details.](https://docs.astral.sh/uv/)

Once you have `uv` installed, navigate to the project root and run:
```sh
uv sync
```

And you're good to go:
```sh
uv run <script> <options...>
```

## Access Tokens

The TOPMed Imputation Server uses JWT access tokens sent in a request header to verify user identity. A token is needed to access the API endpoints.

You can explicitly get an expirable token by navigating to the Imputation Server website and pressing (your username) -> Profile -> API Access. Please note that admin rights do *not* carry over to this token.

The SDK and CLI tools in this repository expect the existence of a local folder `data/`, inside which they can find tokens stored in plaintext, either in `dev.token` or `prod.token` (as appropriate). Please use caution when copying the token around, anyone with access to it can submit jobs on your behalf and access your existing jobs.

## CLI

### TIS

`script/tis.py` is the primary API interaction script. It has a lot of options, so using `--help` to find what you need is recommended.

You always need to specify the target environment `(dev|prod)`. By default, the script expects a text file `data/<env>.token` (e.g., `data/dev.token`) containing a valid access token for the specified environment; a different token file can be specified by passing `--token-file <path-to-token>`

* `uv run script/tis.py <env> list-jobs` lists all of the user's jobs, past and present.
* `uv run script/tis.py <env> get-job <job-id>` gives detailed information about a single job.
* `uv run script/tis.py <env> submit-job <params...>` submits a job with the provided parameters (some mandatory, some optional; check defaults!)
* `uv run script/tis.py <env> cancel-job <job-id>` cancels the selected job.
* `uv run script/tis.py <env> restart-job <job-id>` re-runs the selected job (currently from scratch, hopefully we can do recovery in the future).
* `uv run script/tis.py <env> admin <admin-command> ...` calls admin commands that require an admin-role token. See **Access Tokens** for more details.
  * `uv run script/tis.py <env> admin list-jobs --state (running-ltq | current | retired)` lists jobs from all users from a specific set:
    * `running-ltq`: the main queue for running jobs.
    * `current`: seems to be the pre-processing queue.
    * `retired`: non-running jobs: finished, cancelled, failed...
    * More than one queue can be requested by repeating the `--state <state>` parameters.
  * `uv run script/tis.py <env> admin kill-all` cancels all running jobs.

### Load Test

`script/load_test.py` submits a battery of jobs from any number of accounts, with random duration between submissions. The script requires the following arguments:

* `--min-delay <min-delay>` minimum amount of time each account will wait before submitting a job, in format `((hh:)mm:)ss`.
* `--max-delay <max-delay>` maximum amount of time each account will wait before submitting a job, in format `((hh:)mm:)ss`.
* `--submissions <num-submissions>` number of submission attempts that each accounnt will perform.
* `--token-file <path-to-token>` path to an access token file. This argument can be added repeatedly to have several accounts submitting in parallel. You can also repeat the same token path to have a single identity applying several times in parallel.
* `--vcf-file <path-to-vcf>` the VCF file(s) to submit for each job. This argument can be added repeatedly for multiple-file submissions.

Each `--token-file` argument provided spawns a subprocess that will attempt `--submissions` job submissions sequentially before quitting. The subprocess will sleep a random amount of time between `--min-delay` and `--max-delay` before each submission attempt. If more than one `--token-file` argument is provided, they all run in parallel.

### Other Scripts

* `script/explore_jwt.py` decodes and pretty-prints the user tokens. They are JWT tokens; there are tools online but this is local and only uses the Python standard library (plus `mff-pretty-cli` for pretty-printing).
* `script/test_endpoints.py` places a few calls to demonstrate and/or test the available endpoints.
  * It expects the test VCF file `data/chr20.R50.merged.1.330k.recode.unphased.small.vcf.gz`, used to submit a light job.

## SDK

All library code is located in `local/`. The main point of interest is the API interface class `local.api.TisV2Api`. It expects a `data/(dev|prod).token` file containing an access token, unless a different path is explicitly provided (see **Access Tokens**).

Currently available methods:
* `api.list_jobs()`: Lists all jobs visible by the current user (regardless of current status).
* `api.get_job(id)`: Gets detailed information about the requested job.
* `api.submit_job(params)`: Submits a job for processing.
* `api.cancel_job(id)`: Cancels the specified job.
* `api.restart_job(id)`: Retries the specified job.
* `api.admin_list_jobs(states)`: Calls the admin job listing endpoint.
* `api.admin_kill_all()`: Cancels all running jobs.
