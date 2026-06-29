"""Pluggable Docker image sources for DockerBatchStrategy.

An ImageSource knows how to produce a locally-runnable image reference, building
or pulling as needed. This decouples *how an image is produced* from *running the
container and capturing its output* (DockerBatchStrategy), so a plain Dockerfile
or a prebuilt image is a first-class path and a Docker bake file is just one
option among several. Users can implement their own ImageSource.
"""
from __future__ import annotations

import os
import uuid
import base64
import logging
from abc import ABC, abstractmethod

import boto3
from python_on_whales import docker

from ._common import resolve_region

logger = logging.getLogger(__name__)


def login_to_ecr(region: str | None = None) -> str:
    """Authenticate the local Docker daemon against the caller's ECR registry."""
    ecr_client = boto3.client("ecr", region_name=resolve_region(region))
    auth_data = ecr_client.get_authorization_token()["authorizationData"][0]
    token = base64.b64decode(auth_data["authorizationToken"]).decode()
    username, password = token.split(":")
    registry = auth_data["proxyEndpoint"].replace("https://", "")
    docker.login(server=registry, username=username, password=password)
    logger.info(f"Logged in to {registry}")
    return registry


def get_codeartifact_token(domain: str, domain_owner: str, region: str | None = None) -> str:
    """Fetch an AWS CodeArtifact authorization token (e.g. to inject into a Docker build)."""
    client = boto3.client("codeartifact", region_name=resolve_region(region))
    response = client.get_authorization_token(domain=domain, domainOwner=domain_owner)
    return response["authorizationToken"]


class ImageSource(ABC):
    """Produces a locally-runnable Docker image reference."""

    @abstractmethod
    def ensure_image(self) -> str:
        """Build or pull as needed; return an image ref runnable by ``docker run``."""


class PrebuiltImage(ImageSource):
    """Run an image that already exists (local tag or a registry/ECR reference).

    Set ``login_ecr=True`` to authenticate to ECR before the (implicit) pull.
    """

    def __init__(self, image: str, login_ecr: bool = False, region: str | None = None):
        self.image = image
        self.login_ecr = login_ecr
        self.region = region

    def ensure_image(self) -> str:
        if self.login_ecr:
            login_to_ecr(self.region)
        return self.image


class DockerfileImage(ImageSource):
    """Build an image from a plain Dockerfile + build context (the common dev path).

    ``context`` is the build-context directory. ``dockerfile`` defaults to
    ``<context>/Dockerfile``. ``tag`` is auto-generated if not given.
    """

    def __init__(self, context: str, dockerfile: str | None = None,
                 build_args: dict | None = None, tag: str | None = None,
                 target: str | None = None, region: str | None = None,
                 login_ecr: bool = False):
        self.context = context
        self.dockerfile = dockerfile
        self.build_args = build_args or {}
        self.tag = tag or f"sfn-toolkit-{uuid.uuid4().hex[:8]}:latest"
        self.target = target
        self.region = region
        self.login_ecr = login_ecr

    def ensure_image(self) -> str:
        if self.login_ecr:
            login_to_ecr(self.region)
        logger.info(f"Building image from Dockerfile context: {self.context}")
        docker.build(
            context_path=str(self.context),
            file=self.dockerfile,
            build_args=self.build_args,
            tags=[self.tag],
            target=self.target,
            load=True,
        )
        return self.tag


class BakeImage(ImageSource):
    """Build an image via ``docker buildx bake`` (advanced / monorepo setups).

    Optionally injects a ``BASE_DIR`` bake variable (``base_dir``) and a
    ``CODEARTIFACT_AUTH_TOKEN`` bake variable (when both codeartifact_* are set,
    for private package installs during the build).
    """

    def __init__(self, bake_file: str, target: str, tag: str | None = None,
                 base_dir: str | None = None, bake_variables: dict | None = None,
                 codeartifact_domain: str | None = None,
                 codeartifact_domain_owner: str | None = None,
                 region: str | None = None):
        self.bake_file = bake_file
        self.target = target
        self.tag = tag or f"{target}:latest"
        self.base_dir = base_dir
        self.bake_variables = bake_variables
        self.codeartifact_domain = codeartifact_domain
        self.codeartifact_domain_owner = codeartifact_domain_owner
        self.region = region

    def ensure_image(self) -> str:
        os.environ["BUILDX_BAKE_ENTITLEMENTS_FS"] = "0"
        bake_vars = dict(self.bake_variables or {})
        if self.base_dir is not None:
            bake_vars["BASE_DIR"] = str(self.base_dir)
        if self.codeartifact_domain and self.codeartifact_domain_owner:
            bake_vars["CODEARTIFACT_AUTH_TOKEN"] = get_codeartifact_token(
                self.codeartifact_domain, self.codeartifact_domain_owner, self.region
            )
        logger.info(f"Building (bake) target: {self.target}")
        docker.buildx.bake(
            targets=[self.target],
            files=[self.bake_file],
            variables=bake_vars,
            set={
                "*.tags": self.tag,
                "*.args.ENVIRONMENT": "dev",
                "*.cache-from": "",
                "*.cache-to": "",
            },
            load=False,
        )
        return self.tag
