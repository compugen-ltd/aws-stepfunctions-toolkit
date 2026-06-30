"""CLI interface for AWS Step Functions Toolkit."""

import typer
from typing import Optional
import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

from .testing import generate_mock_data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SFN_", env_file=".env", extra="ignore"
    )
    region: Optional[str] = None
    profile: Optional[str] = None


app = typer.Typer(
    help="AWS Step Functions Toolkit - Tools for managing definitions and history events"
)


@app.command()
def generate_mock(
    execution_arn: str = typer.Argument(..., help="Step Functions execution ARN"),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Output directory for generated files"
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
):
    """Generate mock data files from Step Functions execution."""
    from .workflow_runner._common import resolve_region

    settings = Settings()
    actual_region = resolve_region(region or settings.region)

    sfn_client = boto3.client("stepfunctions", region_name=actual_region)

    result = generate_mock_data(
        execution_arn=execution_arn, output_dir=output_dir, sfn_client=sfn_client
    )

    typer.echo(f"Mock data generated in: {result['output_dir']}")
    typer.echo(f"Files created: history.json, input.json, state_outputs.json")


def main():
    app()


if __name__ == "__main__":
    main()
