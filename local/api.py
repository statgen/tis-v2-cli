"""
Provides `TisV2Api`, a class to call the TOPMed Imputation Server endpoints (either `dev` or `prod`) programmatically.
"""


import requests
from pathlib import Path

from pretty_cli import PrettyCli

from local import ansi_colors
from local.request_schema import JobParams
from local.response_schema import JobInfo, JobSubmitted


BASE_URL = {
    "dev"  : "https://topmed.dev.imputationserver.org",
    "prod" : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
}


def _get_token(env: str) -> str:
    assert env in [ "dev", "prod" ]

    data_dir = Path("data/")
    assert data_dir.is_dir()

    token_file = data_dir / f"{env}.token"
    assert token_file.is_file(), f"Expected to find token file: {token_file}"

    with open(token_file, "r") as file_handle:
        token = file_handle.read().strip()

    return token


class TisV2Api:
    """
    Provides API calls to the TOPMed Imputation Server. Basic usage:
    ```
    api = TisV2Api(env="dev")
    jobs = api.list_jobs()
    ...
    ```
    The environnment is either `dev` or `prod`. It expects a token file named `<env>.token` (e.g., `dev.token`) to exist WHERE.

    Available methods:
    * `list_jobs()`: Lists all jobs submitted by the current user (regardless of current status).
    * `get_job(id)`: Gets detailed information about the requested job.
    * `submit_job(params)`: Submits a job for processing.
    """

    env          : str
    base_url     : str
    access_token : str
    headers      : dict[str, str]
    cli          : PrettyCli

    print_request_headers  : bool
    print_request_body     : bool
    print_response_headers : bool
    print_response_body    : bool

    def __init__(self,
        env                    : str                    ,
        cli                    : PrettyCli = PrettyCli(),
        print_response_body    : bool      = False      ,
        print_request_headers  : bool      = False      ,
        print_request_body     : bool      = False      ,
        print_response_headers : bool      = False      ,
    ) -> None:
        assert env in [ "dev", "prod" ]
        self.env = env
        self.cli = cli

        self.print_request_headers  = print_request_headers
        self.print_request_body     = print_request_body
        self.print_response_headers = print_response_headers
        self.print_response_body    = print_response_body

        self.base_url = BASE_URL[env] + "/api/v2"
        self.access_token = _get_token(env)

        self.headers = { "X-Auth-Token": self.access_token }

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Internal method used to handle all requests.

        * Wraps `requests.request(...)` and handles setting the base URL and the access header.
        * Always prints HTTP method, relative URL, and response status code.
        * Optionally prints (request and/or response) (headers and/or body), depending on this object's configuration.
        """
        if not url.startswith("/"):
            url = "/" + url

        self.cli.blank()
        self.cli.print(f"{ansi_colors.FG_YELLOW}[{method} {url}]{ansi_colors.RESET}", end=" ")

        response = requests.request(method=method, url=self.base_url + url, headers=self.headers, **kwargs)

        color = ansi_colors.FG_GREEN if (response.status_code == 200) else ansi_colors.FG_RED
        self.cli.print(f"{color}{response.status_code}{ansi_colors.RESET}")
        self.cli.blank()

        for (flag, title, data) in [
            (self.print_request_headers , "Request Headers" , response.request.headers),
            (self.print_request_body    , "Request Body"    , response.request.body   ),
            (self.print_response_headers, "Response Headers", response.headers        ),
            (self.print_response_body   , "Response Body"   , response.text           ),
        ]:
            if flag:
                self.cli.section(title)
                self.cli.print(data)
                self.cli.small_divisor()

        return response

    def _get(self, url: str, params=None) -> requests.Response:
        """self._request() wrapper for all internal GET calls."""
        return self._request(method="GET", url=url, params=params)

    def _post(self, url: str, data=None, json=None, **kwargs) -> requests.Response:
        """self._request() wrapper for all internal POST calls."""
        return self._request(method="POST", url=url, data=data, json=json, **kwargs)

    def list_jobs(self) -> list[JobInfo]:
        """Lists all jobs submitted by the current user (regardless of current status)."""
        response = self._get("jobs")

        if response.status_code != 200:
            return []

        json_data = response.json()["data"]
        jobs = [ JobInfo.from_json(entry) for entry in json_data ]

        return jobs

    def get_job(self, id: str) -> JobInfo:
        """Gets detailed information about the requested job."""
        response = self._get(f"jobs/{id}")
        job_json = response.json()
        return JobInfo.from_json(job_json)

    def submit_job(self, params: JobParams) -> JobSubmitted:
        """Submits a job for processing."""
        response = self._post("/jobs/submit/imputationserver2", files=params.get_params())
        return JobSubmitted.from_json(response.json())
