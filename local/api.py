"""
Provides `TisV2Api`, a class to call the TOPMed Imputation Server endpoints (either `dev` or `prod`) programmatically.
"""


from pathlib import Path
from dataclasses import dataclass
from typing import Iterable

import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from pretty_cli import PrettyCli

from local import ansi_colors
from local.request_schema import JobParams, AdminListJobsState
from local.response_schema import JobInfo, JobResponse, JobState, UserResponse


BASE_URL = {
    "dev"  : "https://topmed.dev.imputationserver.org",
    "prod" : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
}


def _get_token(env: str, token_file: Path | None) -> str:
    assert env in [ "dev", "prod" ]

    if token_file is not None:
        assert token_file.is_file(), f"Expected to find provided token file: {token_file}"
    else:
        data_dir = Path("data/")
        assert data_dir.is_dir()

        token_file = data_dir / f"{env}.token"
        assert token_file.is_file(), f"Expected to find default token file: {token_file}"

    with open(token_file, "r") as file_handle:
        token = file_handle.read().strip()

    return token


@dataclass
class AdminKillAllResponse:
    killed : list[JobResponse]
    failed : list[JobResponse]


class TisV2Api:
    """
    Provides API calls to the TOPMed Imputation Server. Basic usage:
    ```
    api = TisV2Api(env="dev")
    jobs = api.list_jobs()
    ...
    ```
    The environnment is either `dev` or `prod`. It expects a token file named `<env>.token` (e.g., `dev.token`) to exist WHERE.

    User methods:
    * `list_jobs()`: Lists all jobs visible by the current user (regardless of current status).
    * `get_job(id)`: Gets detailed information about the requested job.
    * `submit_job(params)`: Submits a job for processing.
    * `cancel_job(id)`: Cancels the specified job.
    * `restart_job(id)`: Retries the specified job.

    Admin methods:
    * `admin_list_jobs(states)`: Calls the admin job listing endpoint.
    * `admin_kill_all()`: Cancels all running jobs.
    """

    env          : str
    base_url     : str
    access_token : str
    headers      : dict[str, str]
    cli          : PrettyCli

    print_http_call        : bool
    print_request_headers  : bool
    print_request_body     : bool
    print_response_headers : bool
    print_response_body    : bool

    def __init__(self,
        env                    : str                      ,
        cli                    : PrettyCli   = PrettyCli(),
        print_http_call        : bool        = True       ,
        print_response_body    : bool        = False      ,
        print_request_headers  : bool        = False      ,
        print_request_body     : bool        = False      ,
        print_response_headers : bool        = False      ,
        token_file             : Path | None = None       ,
    ) -> None:
        assert env in [ "dev", "prod" ]
        self.env = env
        self.cli = cli

        self.print_http_call        = print_http_call
        self.print_request_headers  = print_request_headers
        self.print_request_body     = print_request_body
        self.print_response_headers = print_response_headers
        self.print_response_body    = print_response_body

        self.base_url = BASE_URL[env] + "/api/v2"
        self.access_token = _get_token(env, token_file)

        self.headers = { "X-Auth-Token": self.access_token }

    def _request(self, method: str, url: str, monitor_progress: bool = False, **kwargs) -> requests.Response:
        """
        Internal method used to handle all requests.

        * Wraps `requests.request(...)` and handles setting the base URL and the access header.
        * Always prints HTTP method, relative URL, and response status code.
        * Optionally prints (request and/or response) (headers and/or body), depending on this object's configuration.
        """
        if not url.startswith("/"):
            url = "/" + url

        if self.print_http_call:
            self.cli.blank()
            self.cli.print(f"{ansi_colors.FG_YELLOW}[{method} {url}]{ansi_colors.RESET}", end=" ")

        if (monitor_progress) and ("files" in kwargs):
            total_size = 0
            fields: list[tuple[str, tuple]] = kwargs["files"]
            assert isinstance(fields, list)
            del kwargs["files"]

            if "data" in kwargs:
                assert not kwargs["data"]
                del kwargs["data"]

            for field_name, field_data in fields:
                if field_name == "files":
                    (file_name, _, _) = field_data
                    assert isinstance(file_name, str)
                    p = Path(file_name)
                    total_size += p.stat().st_size

            assert total_size > 0

            with tqdm(desc="Upload", total=total_size, unit="B", unit_scale=True, unit_divisor=1024) as bar:
                def callback(monitor: MultipartEncoderMonitor) -> None:
                    new_bytes = monitor.bytes_read - bar.n
                    bar.update(new_bytes)

                e = MultipartEncoder(fields=fields)
                m = MultipartEncoderMonitor(e, callback)

                headers = self.headers | { "Content-Type": m.content_type }
                response = requests.request(method=method, url=self.base_url + url, headers=headers, data=m, **kwargs)

        else:
            response = requests.request(method=method, url=self.base_url + url, headers=self.headers, **kwargs)

        if self.print_http_call:
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

    def _post(self, url: str, data = None, json = None, monitor_progress: bool = False, **kwargs) -> requests.Response:
        """self._request() wrapper for all internal POST calls."""
        return self._request(method="POST", url=url, data=data, json=json, monitor_progress=monitor_progress, **kwargs)

    def list_jobs(self) -> list[JobInfo]:
        """Lists all jobs submitted by the current user (regardless of current status)."""
        response = self._get(url="jobs")

        if response.status_code != 200:
            return []

        json_data = response.json()["data"]
        jobs = [ JobInfo.from_json(entry) for entry in json_data ]

        return jobs

    def get_job(self, id: str) -> JobInfo:
        """Gets detailed information about the requested job."""
        response = self._get(url=f"jobs/{id}")
        job_json = response.json()
        return JobInfo.from_json(job_json)

    def submit_job(self, params: JobParams) -> JobResponse:
        """Submits a job for processing."""
        response = self._post(url="/jobs/submit/imputationserver2", files=params.get_params())
        # response = self._post(url="/jobs/submit/imputationserver2", files=params.get_params(), monitor_progress=True)

        try:
            return JobResponse.from_json(response.json())
        except:
            return JobResponse.fail()

    def cancel_job(self, id: str) -> JobInfo:
        """Cancels the specified job."""
        response = self._get(url=f"jobs/{id}/cancel")
        return JobInfo.from_json(response.json())

    def restart_job(self, id: str) -> JobResponse:
        """Retries the specified job (must be in a `DEAD` state)."""
        response = self._get(url=f"jobs/{id}/restart")
        return JobResponse.from_json(response.json())

    def admin_list_users(self) -> list[UserResponse]:
        """Calls the admin user listing endpoint."""
        response = self._get(url="admin/users")

        if response.ok:
            users = response.json()["data"]
            users = [ UserResponse.from_json(u) for u in users ]
            return users
        else:
            return []

    def admin_list_jobs(self, states: Iterable[AdminListJobsState]) -> list[JobInfo]:
        """Calls the admin job listing endpoint. Requires at least one state filter to produce output (see `AdminListJobsState`). The access token must have admin rights."""
        jobs = []

        for state in states:
            response = self._get(url="admin/jobs", params={ "state": state })

            if response.status_code != 200:
                return []

            json_data = response.json()["data"]
            jobs += [ JobInfo.from_json(entry) for entry in json_data ]

        return jobs

    def admin_kill_all(self) -> AdminKillAllResponse:
        """Cancels all running jobs. The access token must have admin rights."""
        killed = []
        failed = []

        all_list_states = [ s for s in AdminListJobsState ]
        cancelable_job_states = [ JobState.RUNNING, JobState.WAITING, JobState.EXPORTING ]

        for job in self.admin_list_jobs(states=all_list_states):
            if job.state not in cancelable_job_states:
                continue

            response = self.cancel_job(id=job.id)

            if response.state == JobState.CANCELED:
                killed.append(job.id)
            else:
                failed.append(job.id)

        return AdminKillAllResponse(killed, failed)
