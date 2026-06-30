"""Offline unit tests for image sources (construction + the custom-source contract)."""

from aws_stepfunctions_toolkit import (
    ImageSource,
    PrebuiltImage,
    DockerfileImage,
    BakeImage,
)


def test_prebuilt_image_returns_the_ref_without_building():
    assert (
        PrebuiltImage("acct.dkr.ecr/img:latest").ensure_image()
        == "acct.dkr.ecr/img:latest"
    )


def test_dockerfile_image_auto_generates_a_tag():
    img = DockerfileImage(context="./jobs/foo")
    assert img.tag.startswith("sfn-toolkit-")


def test_bake_image_defaults_tag_to_target_latest():
    assert BakeImage(bake_file="docker-bake.hcl", target="foo").tag == "foo:latest"


def test_custom_image_source_is_accepted():
    class MyImage(ImageSource):
        def ensure_image(self) -> str:
            return "my:tag"

    assert MyImage().ensure_image() == "my:tag"
    assert isinstance(MyImage(), ImageSource)
