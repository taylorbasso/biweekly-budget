#!/usr/bin/env python3
"""Build, push, and roll out biweekly-budget to ECS Fargate.

All AWS infrastructure (ECR, ECS, ALB, DNS, IAM, ...) lives in the basso-infra
Terraform repo (basso-root/us-west-2/biweekly-budget). The task definition
points at the ECR repo's :latest tag, so a deploy is just: build the image,
push it, and force a new ECS deployment.

Requires boto3 (`pip install -e '.[deploy]'`) and a podman or docker CLI
(override with CONTAINER_CMD) for image builds.
"""
from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

import boto3

APP_NAME = "biweekly-budget"
URL = "https://budget.taylorbasso.dev"
REPO_ROOT = Path(__file__).resolve().parent.parent


def log(msg: str) -> None:
    print(f"==> {msg}")


def main() -> None:
    container_cmd = os.environ.get("CONTAINER_CMD", "podman")
    session = boto3.Session()
    ecr = session.client("ecr")
    ecs = session.client("ecs")

    repo_uri = ecr.describe_repositories(repositoryNames=[APP_NAME])["repositories"][0][
        "repositoryUri"
    ]
    image_uri = f"{repo_uri}:latest"

    log(f"Building image ({container_cmd})")
    subprocess.run([container_cmd, "build", "-t", image_uri, str(REPO_ROOT)], check=True)

    log("Logging in to ECR")
    auth = ecr.get_authorization_token()["authorizationData"][0]
    user, password = base64.b64decode(auth["authorizationToken"]).decode().split(":", 1)
    subprocess.run(
        [container_cmd, "login", "--username", user, "--password-stdin", auth["proxyEndpoint"]],
        input=password.encode(),
        check=True,
    )

    log("Pushing image")
    subprocess.run([container_cmd, "push", image_uri], check=True)

    log("Rolling out new deployment")
    ecs.update_service(cluster=APP_NAME, service=APP_NAME, forceNewDeployment=True)
    ecs.get_waiter("services_stable").wait(cluster=APP_NAME, services=[APP_NAME])

    print(f"\nDeployed: {URL}")


if __name__ == "__main__":
    main()
