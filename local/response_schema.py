"""
Provides typed objects for response payloads.
"""


from enum import Enum, StrEnum
from dataclasses import dataclass
from datetime import datetime


class MessageType(Enum):
    OK      = 0
    ERROR   = 1
    WARNING = 2
    RUNNING = 3


class OutputType(StrEnum):
    LOCAL_FOLDER = "local_folder"
    LOCAL_FILE   = "local_file"


class JobState(Enum):
    DEAD             = -1
    WAITING          =  1
    RUNNING          =  2
    EXPORTING        =  3
    SUCCESS          =  4
    FAILED           =  5
    CANCELED         =  6
    RETIRED          =  7
    SUCCESS_NOTIFIED =  8
    FAIL_NOTIFIED    =  9
    DELETED          = 10


@dataclass
class MessageInfo:
    success : bool
    message : str
    type    : MessageType
    time    : datetime

    @staticmethod
    def from_json(data) -> "MessageInfo":
        return MessageInfo(
            success = bool(data["success"]),
            message = _str_or_none(data, "message"),
            type    = MessageType(data["type"]),
            time    = _db_timestamp_to_datetime(data["time"]),
        )


@dataclass
class StepInfo:
    id           : int
    name         : str
    log_messages : list[MessageInfo] | None

    @staticmethod
    def from_json(data) -> "StepInfo":
        return StepInfo(
            id           = int(data["id"]),
            name         = _str_or_none(data, "name"),
            log_messages = _process_list(data["logMessages"], MessageInfo.from_json),
        )


@dataclass
class TreeItemInfo:
    name     : str
    path     : str
    hash     : str
    size     : str
    folder   : bool
    children : list["TreeItemInfo"] | None

    @staticmethod
    def from_json(data) -> "TreeItemInfo":
        return TreeItemInfo(
            name   = _str_or_none(data, "name"),
            path   = _str_or_none(data, "path"),
            hash   = _str_or_none(data, "hash"),
            size   = _str_or_none(data, "size"),
            folder = bool(data["folder"]),
            children = _process_list(data["childs"], TreeItemInfo.from_json),
        )


@dataclass
class DownloadInfo:
    name         : str
    path         : str
    hash         : str
    size         : str
    user         : str
    count        : int
    parameter_id : int

    @staticmethod
    def from_json(data) -> "DownloadInfo":
        return DownloadInfo(
            name         = _str_or_none(data, "name"),
            path         = _str_or_none(data, "path"),
            hash         = _str_or_none(data, "hash"),
            size         = _str_or_none(data, "size"),
            user         = _str_or_none(data, "user"),
            count        = int(data["count"]),
            parameter_id = int(data["parameterId"]),
        )


@dataclass
class OutputInfo:
    id          : int
    description : str
    value       : str
    name        : str
    job_id      : str
    hash        : str
    type        : OutputType | None
    download    : bool
    auto_export : bool
    tree        : list[TreeItemInfo] | None
    files       : list[DownloadInfo] | None

    @staticmethod
    def from_json(data) -> "OutputInfo":
        return OutputInfo(
            id           = int(data["id"]),
            description  = _str_or_none(data, "description"),
            value        = _str_or_none(data, "value"      ),
            name         = _str_or_none(data, "name"       ),
            job_id       = _str_required(data["jobId"     ]),
            hash         = _str_or_none(data, "hash"       ),
            type         = OutputType(data["type"]) if data["type"] is not None else None,
            download     = bool(data["download"   ]),
            auto_export  = bool(data["autoExport"]),
            tree         = _process_list(data["tree" ], TreeItemInfo.from_json),
            files        = _process_list(data["files"], DownloadInfo.from_json),
        )


@dataclass
class JobInfo:
    application       : str
    application_id    : str
    id                : str
    name              : str | None
    logs              : str | None
    position_in_queue : int | None
    user_agent        : str | None
    username          : str | None
    workspace_size    : str | None
    submitted_on      : datetime
    start_time        : datetime
    end_time          : datetime
    deleted_on        : datetime
    current_time      : datetime
    state             : JobState
    steps             : list[StepInfo  ] | None
    output_params     : list[OutputInfo] | None

    @staticmethod
    def from_json(data) -> "JobInfo":
        return JobInfo(
            application       = _str_required(data["application"  ]),
            application_id    = _str_required(data["applicationId"]),
            id                = _str_required(data["id"           ]),
            name              = _str_or_none(data, "name"          ),
            logs              = _str_or_none(data, "logs"          ),
            position_in_queue = None if (data["positionInQueue"] == -1) else int(data["positionInQueue"]),
            user_agent        = _str_or_none(data, "userAgent"     ),
            username          = _str_or_none(data, "username"      ),
            workspace_size    = _str_or_none(data, "workspaceSize" ),
            submitted_on      = _db_timestamp_to_datetime(data["submittedOn"]),
            start_time        = _db_timestamp_to_datetime(data["startTime"  ]),
            end_time          = _db_timestamp_to_datetime(data["endTime"    ]),
            deleted_on        = _db_timestamp_to_datetime(data["deletedOn"  ]),
            current_time      = _db_timestamp_to_datetime(data["currentTime"]),
            state             = JobState(data["state"]),
            steps             = _process_list(data["steps"       ], StepInfo.from_json  ),
            output_params     = _process_list(data["outputParams"], OutputInfo.from_json),
        )


@dataclass
class JobSubmitted:
    success : bool
    message : str | None
    id      : str | None

    @staticmethod
    def from_json(data) -> "JobSubmitted":
        return JobSubmitted(
            success = bool(data["success"]),
            message = _str_required(data["message"]),
            id      = _str_or_none(data, "id"),
        )

    @staticmethod
    def fail() -> "JobSubmitted":
        return JobSubmitted(success=False, message=None, id=None)


def _str_or_none(d: dict, k: str) -> str | None:
    if (d is None) or (k is None):
        return None

    if not k in d:
        return None

    field = d[k]

    if field is None:
        return None

    field = str(field)

    if len(field) < 1:
        return None

    return field


def _str_required(field) -> str:
    assert isinstance(field, str)
    assert len(field) > 0
    return field


def _process_list(field, func) -> list | None:
    if not isinstance(field, list):
        return None

    if len(field) < 1:
        return None

    return [ func(x) for x in field ]


def _db_timestamp_to_datetime(timestamp) -> datetime:
    # Cloudgene uses ms since the Unix epoch for time.
    return datetime.fromtimestamp(int(timestamp) / 1_000)
