import os
import logging
import json
from pathlib import Path

from aws_stepfunctions_toolkit.strategies import LocalBatchImageStrategy, GetLatestConfigurationStrategy, \
    StaticMockResponseStrategy
from aws_stepfunctions_toolkit.workflow_runner import WorkflowRunner

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def test_example(
        bulk_not_raw_input, definitions: dict[str, str], tmp_path: Path
):
    logger.debug(f"{definitions.keys()=}")
    workfolder = "/Rnd/supplementary/GSE15471"
    variables = {"workfolder": workfolder}

    volumes = [
        (str(tmp_path), workfolder),
    ]
    bake_file = "/home/ubuntu/scripts/pycharmProjects/unigen_pipeline/docker-bake.hcl"

    strategy_mapping = {
        "Batch SubmitJob - Copy Source 2": LocalBatchImageStrategy(
            "royassis_bucket",
            "h5ad_2_prod",
            bake_file,
            volumes=volumes,
            variables=variables
        ),
        "Batch SubmitJob - H5ad2prod - Misc": LocalBatchImageStrategy(
            "royassis_bucket",
            "h5ad_2_prod",
            bake_file,
            volumes=volumes,
            variables=variables
        ),
        "GetLatestConfiguration": GetLatestConfigurationStrategy(),
        "Batch SubmitJob - H5ad2prod - Check Gene Symbol": LocalBatchImageStrategy(
            "royassis_bucket",
            "h5ad_2_prod",
            bake_file,
            volumes=volumes,
            variables=variables
        ),
        "Batch SubmitJob - H5ad2prod - Add Gene Symbols": LocalBatchImageStrategy(
            "royassis_bucket",
            "gene_symbols",
            bake_file,
            volumes=volumes,
            variables=variables
        ),
        "Batch SubmitJob - H5ad2prod - Create Annotations": LocalBatchImageStrategy(
            "royassis_bucket",
            "h5ad_2_prod",
            bake_file,
            user=f"{os.getuid()}:{os.getgid()}",
            volumes=volumes,
            variables=variables
        ),
        "Batch SubmitJob - H5ad2prod - Add Annotations": LocalBatchImageStrategy(
            "royassis_bucket",
            "h5ad_2_prod",
            bake_file,
            volumes=volumes,
            variables=variables
        ),
        "DescribeJobDefinitions": StaticMockResponseStrategy(
            json.dumps(
                {
                    "JobDefinitions": [{
                        "JobDefinitionArn": "arn:aws:batch:us-east-1:000000000000:job-definition/PostNewDatasetBatchJobDefinition:35",
                        "JobDefinitionName": "PostNewDatasetBatchJobDefinition",
                        "Revision": 35,
                        "Type": "container"
                    }]
                }
            )
        ),
        "Batch SubmitJob - H5ad2prod - Deploy": StaticMockResponseStrategy(
            json.dumps(
                {"datasetLocation": "s3://nextgen-tiledb-data-bucket/new/bulk/GSE15471_affy"}
            )
        ),
        "Batch SubmitJob - Cp to h5": StaticMockResponseStrategy(json.dumps({}))
    }

    runner = WorkflowRunner(
        role_arn="arn:aws:iam::000000000000:role/unigen-state-machine-role",
        asl_registry={
            "main": json.loads(definitions["UnigenStateMachine"]),
            "Step Functions StartExecution - H5ad To Prod": json.loads(definitions["H5ad2Prod"])
        },
        variables=variables,
        mock_mapping=strategy_mapping
    )

    runner.start(bulk_not_raw_input, strategy_mapping)
