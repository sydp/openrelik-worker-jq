# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess

from openrelik_worker_common.file_utils import create_output_file
from openrelik_worker_common.task_utils import create_task_result, get_input_files

from .app import celery

# Task name used to register and route the task to the correct queue.
TASK_NAME = "openrelik-worker-jq.tasks.filter"

# Task metadata for registration in the core system.
TASK_METADATA = {
    "display_name": "jq",
    "description": "Filter JSON data using jq",
    # Configuration that will be rendered as a web for in the UI, and any data entered
    # by the user will be available to the task function when executing (task_config).
    "task_config": [
        {
            "name": "filter",
            "label": "filter",
            "description": "The jq filter to apply to the input data.",
            "type": "text",
            "required": True,
        },
        {
            "name": "output_format",
            "label": "Output format.",
            "description": "The expected output format.",
            "type": "select",
            "default": "json",
            "items": [ "json", "csv", "text", "jsonl" ],
            "required": True,
        },
    ],
}


@celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
def command(
    self,
    pipe_result: str = None,
    input_files: list = None,
    output_path: str = None,
    workflow_id: str = None,
    task_config: dict = None,
) -> str:
    """Run jq on input files.

    Args:
        pipe_result: Base64-encoded result from the previous Celery task, if any.
        input_files: List of input file dictionaries (unused if pipe_result exists).
        output_path: Path to the output directory.
        workflow_id: ID of the workflow.
        task_config: User configuration for the task.

    Returns:
        Base64-encoded dictionary containing task results.
    """
    input_files = get_input_files(pipe_result, input_files or [])
    output_files = []
    base_command: list[str] = ["jq"]
    base_command_string: str = " ".join(base_command)

    data_type: str = task_config["output_format"]
    jq_filter: str = task_config["filter"]

    for input_file in input_files:
        output_file = create_output_file(
            output_path,
            display_name=input_file.get("display_name"),
            extension=data_type,
            data_type=data_type,
        )
        command: list[str]  = base_command + [jq_filter, input_file.get("path")]
        print(command)
        # Run the command
        with open(output_file.path, "w") as fh:
            subprocess.Popen(command, stdout=fh)

        output_files.append(output_file.to_dict())

    if not output_files:
        raise RuntimeError("No output files generated.")

    return create_task_result(
        output_files=output_files,
        workflow_id=workflow_id,
        command=base_command_string,
        meta={},
    )
