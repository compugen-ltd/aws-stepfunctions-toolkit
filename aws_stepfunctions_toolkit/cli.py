"""CLI interface for AWS Step Functions Toolkit."""

import typer
from pathlib import Path
from typing import Optional
import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

from .testing import generate_mock_data, generate_revised_definition


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SFN_", env_file=".env", extra="ignore")
    region: str = "us-east-1"
    profile: Optional[str] = None


app = typer.Typer(help="AWS Step Functions Toolkit - Tools for managing definitions and history events")


def get_sfn_client(region: str = None, profile: str = None):
    """Create Step Functions client with optional region and profile."""
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    return session.client('stepfunctions', region_name=region)


@app.command()
def generate_mock(
    execution_arn: str = typer.Argument(..., help="Step Functions execution ARN"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Output directory for generated files"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="AWS profile")
):
    """Generate mock data files from Step Functions execution."""
    settings = Settings()
    actual_region = region or settings.region
    actual_profile = profile or settings.profile
    
    sfn_client = get_sfn_client(actual_region, actual_profile)
    
    result = generate_mock_data(
        execution_arn=execution_arn,
        output_dir=output_dir,
        sfn_client=sfn_client
    )
    
    typer.echo(f"Mock data generated in: {result['output_dir']}")
    typer.echo(f"Files created: history.json, input.json, state_outputs.json")


@app.command()
def generate_definition(
    state_machine_arn: str = typer.Argument(..., help="Step Functions state machine ARN"),
    output_path: Optional[str] = typer.Option(None, "--output-path", "-o", help="Output file path"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="AWS profile")
):
    """Generate revised definition from Step Functions state machine."""
    settings = Settings()
    actual_region = region or settings.region
    actual_profile = profile or settings.profile
    
    sfn_client = get_sfn_client(actual_region, actual_profile)
    
    generate_revised_definition(
        state_machine_arn=state_machine_arn,
        output_path=output_path,
        sfn_client=sfn_client
    )
    
    output_file = Path(output_path) if output_path else Path("data/definition.asl.json")
    typer.echo(f"Revised definition generated: {output_file}")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
