"""
Provides `TisV2Api`, a class to call the TOPMed Imputation Server endpoints (either `dev` or `prod`) programmatically.
"""

from pathlib import Path
from getpass import getpass
from dataclasses import dataclass
from typing import Iterable

import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from pretty_cli import PrettyCli

from local import ansi_colors
from local.env import Environment, get_base_url
from local.request_schema import JobParams, AdminListJobsState
from local.response_schema import JobInfo, JobResponse, JobState, UserResponse, LoginResponse, RefpanelResponse, PopulationResponse, DownloadInfo
from local.util import get_user_agent


def get_bar(desc: str, total: int) -> tqdm:
    return tqdm(desc=desc, total=total, unit="B", unit_scale=True, unit_divisor=1024)


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
    * `admin_login(username, password)`: Requests an admin-level token from the server.
    * `admin_list_users()`: Calls the admin user listing endpoint.
    * `admin_list_jobs(states)`: Calls the admin job listing endpoint.
    * `admin_kill_all()`: Cancels all running jobs.
    """

    env          : Environment
    cli          : PrettyCli
    base_url     : str
    user_agent   : str

    token_file       : Path | None
    admin_token_file : Path | None
    access_token     : str  | None
    admin_token      : str  | None

    print_http_call        : bool
    print_request_headers  : bool
    print_request_body     : bool
    print_response_headers : bool
    print_response_body    : bool

    def __init__(self,
        env                    : Environment              ,
        cli                    : PrettyCli   = PrettyCli(),
        print_http_call        : bool        = True       ,
        print_response_body    : bool        = False      ,
        print_request_headers  : bool        = False      ,
        print_request_body     : bool        = False      ,
        print_response_headers : bool        = False      ,
        token_file             : Path | None = None       ,
        admin_token_file       : Path | None = None       ,
    ) -> None:
        self.env = env
        self.cli = cli

        self.token_file       = token_file
        self.admin_token_file = admin_token_file

        self.print_http_call        = print_http_call
        self.print_request_headers  = print_request_headers
        self.print_request_body     = print_request_body
        self.print_response_headers = print_response_headers
        self.print_response_body    = print_response_body

        self.base_url = get_base_url(env)
        self.user_agent = get_user_agent()

        self.access_token = None
        self.admin_token  = None

    def _get_access_token(self, admin: bool = False) -> str:
        token = self.admin_token if admin else self.access_token

        if token is not None:
            return token

        token_file = self.admin_token_file if admin else self.token_file

        if token_file is not None:
            if not token_file.is_file():
                raise ValueError(f"A path to a token file was provided, but the file does not exist: {token_file}")
        else:
            data_dir = Path("data/")
            if not data_dir.exists():
                data_dir.mkdir(parents=False, exist_ok=False)

            full_env = f"{self.env}{'-admin' if admin else ''}"
            token_file = data_dir / f"{full_env}.token"

            if not token_file.is_file():
                self._request_token(admin, token_file)

        with open(token_file, "r") as file_handle:
            token = file_handle.read().strip()

        if admin:
            self.admin_token = token
            self.admin_token_file = token_file
        else:
            self.access_token = token
            self.token_file = token_file

        return token

    def _request_token(self, admin: bool, token_file: Path) -> None:
        # TODO: Handle errors and retries?
        if admin:
            username = input(f"No token file found for admin access to environment '{self.env}'. Will attempt login.\nUsername:")
            password = getpass()
            response = self.admin_login(username, password)
            token = response.access_token
        else:
            token = input(f"No token file found for current environment '{self.env}'. Please enter a valid token:")

        with open(token_file, "w") as file_handle:
            file_handle.write(token)

    def _request(self, method: str, url: str, monitor_progress: bool = False, **kwargs) -> requests.Response:
        """
        Internal method used to handle all requests.

        * Wraps `requests.request(...)` and handles setting the base URL and the access header.
        * Always prints HTTP method, relative URL, and response status code.
        * Optionally prints (request and/or response) (headers and/or body), depending on this object's configuration.
        """
        if not url.startswith("/"):
            url = "/" + url

        admin = False
        if "admin" in kwargs:
            assert isinstance(kwargs["admin"], bool)
            admin = kwargs["admin"]
            del kwargs["admin"]

        headers = {
            "X-Auth-Token" : self._get_access_token(admin),
            "User-Agent"   : self.user_agent,
        }

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

            with get_bar(desc="Upload", total=total_size) as bar:
                def callback(monitor: MultipartEncoderMonitor) -> None:
                    new_bytes = monitor.bytes_read - bar.n
                    bar.update(new_bytes)

                e = MultipartEncoder(fields=fields)
                m = MultipartEncoderMonitor(e, callback)

                headers = headers | { "Content-Type": m.content_type }
                response = requests.request(method=method, url=self.base_url + url, headers=headers, data=m, **kwargs)

        else:
            response = requests.request(method=method, url=self.base_url + url, headers=headers, **kwargs)

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

    def _get(self, url: str, params=None, **kwargs) -> requests.Response:
        """self._request() wrapper for all internal GET calls."""
        return self._request(method="GET", url=url, params=params, **kwargs)

    def _post(self, url: str, data = None, json = None, monitor_progress: bool = False, **kwargs) -> requests.Response:
        """self._request() wrapper for all internal POST calls."""
        return self._request(method="POST", url=url, data=data, json=json, monitor_progress=monitor_progress, **kwargs)

    def list_jobs(self) -> list[JobInfo]:
        """Lists all jobs submitted by the current user (regardless of current status)."""
        response = self._get(url="api/v2/jobs")

        if response.status_code != 200:
            return []

        json_data = response.json()["data"]
        jobs = [ JobInfo.from_json(entry) for entry in json_data ]

        return jobs

    def get_job(self, id: str) -> JobInfo:
        """Gets detailed information about the requested job."""
        response = self._get(url=f"api/v2/jobs/{id}")
        job_json = response.json()
        return JobInfo.from_json(job_json)

    def submit_job(self, params: JobParams) -> JobResponse:
        """Submits a job for processing."""
        response = self._post(url="api/v2/jobs/submit/imputationserver2", files=params.get_params(), monitor_progress=True)

        try:
            return JobResponse.from_json(response.json())
        except:
            return JobResponse.fail()

    def cancel_job(self, id: str) -> JobInfo:
        """Cancels the specified job."""
        response = self._get(url=f"api/v2/jobs/{id}/cancel")
        return JobInfo.from_json(response.json())

    def restart_job(self, id: str) -> JobResponse:
        """Retries the specified job (must be in a `DEAD` state)."""
        response = self._get(url=f"api/v2/jobs/{id}/restart")
        return JobResponse.from_json(response.json())

    def list_refpanels(self) -> list[RefpanelResponse]:
        response = self._get(url="api/v2/server/apps/imputationserver2")
        data = response.json()

        refpanel_data       = next(entry for entry in data["params"] if entry["id"] == "refpanel")
        all_population_data = next(entry for entry in data["params"] if entry["id"] == "population")

        refpanels = [ RefpanelResponse.from_json(entry) for entry in  refpanel_data["values"] ]

        for panel in refpanels:
            refpanel_population_data = next(entry for entry in all_population_data["values"] if panel.api_name in entry["key"])
            panel.populations = [ PopulationResponse.from_json(entry) for entry in  refpanel_population_data["values"] ]

        return refpanels

    def download(self, download_dir: Path, job_id: str) -> list[DownloadInfo]:
        out_dir = download_dir / job_id
        out_dir = out_dir.resolve()

        job = self.get_job(job_id)

        output_params = job.output_params if job.output_params is not None else []

        downloaded_files = []

        for param in output_params:
            self.cli.section(param.description)

            files = param.files if param.files is not None else []

            for file in files:
                download_url = f"share/results/{file.hash}/{file.name}"
                out_file = out_dir / file.name
                out_parent = out_file.parent # Sometimes file.name is a nested path, and it causes issues with open()

                # TODO: Consider adding sync-like behavior where we don't re-download unnecessarily.

                if not out_parent.is_dir():
                    out_parent.mkdir(parents=True, exist_ok=True)

                with self._get(url=download_url, stream=True) as download_response:
                    download_response.raise_for_status()
                    with open(out_file, "wb") as file_handle:
                        with get_bar(desc=file.name, total=file.size) as bar:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                file_handle.write(chunk)
                                bar.update(len(chunk))

                downloaded_files.append(DownloadInfo(name=file.name, path=None, hash=None, size=file.size, user=None, count=None, parameter_id=None))

        return downloaded_files

    def admin_login(self, username: str, password: str) -> LoginResponse:
        """Requests an admin-level token from the server."""
        # TODO: Optionally save the token to disk.
        response = self._post(url="login", data={ "username": username, "password": password })
        return LoginResponse.from_json(response.json())

    def admin_list_users(self) -> list[UserResponse]:
        """Calls the admin user listing endpoint. Requires admin rights."""
        response = self._get(url="api/v2/admin/users", admin=True)

        if response.ok:
            users = response.json()["data"]
            users = [ UserResponse.from_json(u) for u in users ]
            return users
        else:
            return []

    def admin_list_jobs(self, states: Iterable[AdminListJobsState]) -> list[JobInfo]:
        """Calls the admin job listing endpoint. Requires at least one state filter to produce output (see `AdminListJobsState`). Requires admin rights."""
        jobs = []

        for state in states:
            response = self._get(url="api/v2/admin/jobs", params={ "state": state }, admin=True)

            if response.status_code != 200:
                return []

            json_data = response.json()["data"]
            jobs += [ JobInfo.from_json(entry) for entry in json_data ]

        return jobs

    def admin_kill_all(self) -> AdminKillAllResponse:
        """Cancels all running jobs. Requires admin rights."""
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
