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

## CLI

* `script/tis.py` is the primary API interaction script. It has a lot of options, so using `--help` to find what you need is recommended.
  * `uv run script/tis.py <env> list-jobs` lists all of the user's jobs, past and present.
  * `uv run script/tis.py <env> get-job <job-id>` gives detailed information about a single job.
  * `uv run script/tis.py <env> submit-job <params...>` submits a job with the provided parameters (some mandatory, some optional; check defaults!)
* `script/explore_jwt.py` decodes and pretty-prints the user tokens. They are JWT tokens; there are tools online but this is local and only uses the Python standard library (plus `mff-pretty-cli` for pretty-printing).
* `script/test_endpoints.py` places a few calls to demonstrate and/or test the available endpoints.
  * It expects the test VCF file `data/chr20.R50.merged.1.330k.recode.unphased.small.vcf.gz`, used to submit a light job.

## SDK

All library code is located in `local/`. The main point of interest is the API interface class `local.api.TisV2Api`. It expects a `data/(dev|prod).token` file containing an access token, see below for details.

Currently available methods:
* `api.list_jobs()`: Lists all jobs submitted by the current user (regardless of current status).
* `api.get_job(id)`: Gets detailed information about the requested job.
* `api.submit_job(params)`: Submits a job for processing.

## Access Tokens

The imputation server uses JWT access tokens sent in a request header to verify user identity. A token is needed to access the API endpoints.

You can explicitly get an expirable token by navigating to the Imputation Server website and pressing (your username) -> Profile -> API Access. Please note that admin rights do *not* carry over to this token.

The SDK and CLI tools in this repository expect the existence of a local folder `data/`, inside which they can find tokens stored in plaintext, either in `dev.token` or `prod.token` (as appropriate). Please use caution when copying the token around, anyone with access to it can submit jobs on your behalf and access your existing jobs.
