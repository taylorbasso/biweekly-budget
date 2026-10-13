#!/usr/bin/env python3
"""ECS Fargate Spot deployment for biweekly-budget, via boto3.

Subcommands:
  setup      One-time (re-runnable) AWS setup: ECR repo, log group, task
             execution role, ECS cluster, security group locked to your
             current public IP. Writes deploy/config.json.
  deploy     Build + push the image, register a task-def revision, create or
             update the service, and print the task's public URL.
  update-ip  Re-lock the security group to your current public IP.

Requires boto3 (`pip install -e '.[deploy]'`) and a podman or docker CLI
(override with CONTAINER_CMD) for image builds.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

APP_NAME = "biweekly-budget"
CONTAINER_PORT = 8000
DEPLOY_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DEPLOY_DIR / "config.json"
TASK_DEF_PATH = DEPLOY_DIR / "task-def.json"


def log(msg: str) -> None:
    print(f"==> {msg}")


def load_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        sys.exit("deploy/config.json not found — run `deploy/deploy.py setup` first.")
    config: dict[str, str] = json.loads(CONFIG_PATH.read_text())
    return config


def my_public_ip() -> str:
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10) as resp:
        return str(resp.read().decode().strip())


def error_code(err: ClientError) -> str:
    return str(err.response.get("Error", {}).get("Code", ""))


# --- ingress helpers -------------------------------------------------------


def allow_ip(ec2: Any, sg_id: str, ip: str) -> None:
    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": CONTAINER_PORT,
                    "ToPort": CONTAINER_PORT,
                    "IpRanges": [{"CidrIp": f"{ip}/32"}],
                }
            ],
        )
    except ClientError as err:
        if error_code(err) != "InvalidPermission.Duplicate":
            raise


# --- setup -----------------------------------------------------------------


def ensure_ecr_repo(ecr: Any) -> str:
    try:
        repo = ecr.describe_repositories(repositoryNames=[APP_NAME])["repositories"][0]
    except ClientError as err:
        if error_code(err) != "RepositoryNotFoundException":
            raise
        repo = ecr.create_repository(repositoryName=APP_NAME)["repository"]
    return str(repo["repositoryUri"])


def ensure_log_group(logs: Any) -> None:
    try:
        logs.create_log_group(logGroupName=f"/ecs/{APP_NAME}")
    except ClientError as err:
        if error_code(err) != "ResourceAlreadyExistsException":
            raise


def ensure_execution_role(iam: Any) -> str:
    role_name = f"{APP_NAME}-execution-role"
    try:
        return str(iam.get_role(RoleName=role_name)["Role"]["Arn"])
    except ClientError as err:
        if error_code(err) != "NoSuchEntity":
            raise
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    arn = str(
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust))[
            "Role"
        ]["Arn"]
    )
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    )
    print("Waiting for IAM role to propagate...")
    time.sleep(10)
    return arn


def ensure_cluster(ecs: Any) -> None:
    clusters = ecs.describe_clusters(clusters=[APP_NAME])["clusters"]
    if clusters and clusters[0]["status"] == "ACTIVE":
        return
    ecs.create_cluster(
        clusterName=APP_NAME,
        capacityProviders=["FARGATE", "FARGATE_SPOT"],
        defaultCapacityProviderStrategy=[
            {"capacityProvider": "FARGATE_SPOT", "weight": 1}
        ],
    )


def find_network(ec2: Any) -> tuple[str, list[str]]:
    """Prefer subnets whose Name tag contains 'ublic'; else the default VPC."""
    tagged = ec2.describe_subnets(
        Filters=[{"Name": "tag:Name", "Values": ["*ublic*"]}]
    )["Subnets"]
    if tagged:
        vpc_id = str(tagged[0]["VpcId"])
        subnets = [str(s["SubnetId"]) for s in tagged if s["VpcId"] == vpc_id]
        print(f"Using public subnets in {vpc_id}: {', '.join(subnets)}")
        return vpc_id, subnets

    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        sys.exit("No subnets tagged *Public* and no default VPC found.")
    vpc_id = str(vpcs[0]["VpcId"])
    subs = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    print(f"No *Public*-tagged subnets; falling back to default VPC {vpc_id} (all subnets).")
    return vpc_id, [str(s["SubnetId"]) for s in subs]


def ensure_security_group(ec2: Any, vpc_id: str) -> str:
    sg_name = f"{APP_NAME}-sg"
    groups = ec2.describe_security_groups(
        Filters=[
            {"Name": "group-name", "Values": [sg_name]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )["SecurityGroups"]
    if groups:
        sg_id = str(groups[0]["GroupId"])
    else:
        sg_id = str(
            ec2.create_security_group(
                GroupName=sg_name,
                Description=f"{APP_NAME}: inbound {CONTAINER_PORT} from owner IP only",
                VpcId=vpc_id,
            )["GroupId"]
        )
    allow_ip(ec2, sg_id, my_public_ip())
    return sg_id


def cmd_setup(_: argparse.Namespace) -> None:
    session = boto3.Session()
    region = session.region_name
    if not region:
        sys.exit("No default AWS region configured (aws configure set region <region>).")
    account_id = session.client("sts").get_caller_identity()["Account"]

    log("ECR repository")
    repo_uri = ensure_ecr_repo(session.client("ecr"))
    print(repo_uri)

    log("CloudWatch log group")
    ensure_log_group(session.client("logs"))

    log("IAM task execution role")
    role_arn = ensure_execution_role(session.client("iam"))

    log("ECS cluster")
    ensure_cluster(session.client("ecs"))

    ec2 = session.client("ec2")
    log("VPC + public subnets")
    vpc_id, subnet_ids = find_network(ec2)

    log("Security group locked to your current public IP")
    sg_id = ensure_security_group(ec2, vpc_id)

    config = {
        "aws_account_id": account_id,
        "aws_region": region,
        "ecr_repo_uri": repo_uri,
        "execution_role_arn": role_arn,
        "vpc_id": vpc_id,
        "subnet_ids": subnet_ids,
        "security_group_id": sg_id,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nSetup complete. Wrote {CONFIG_PATH.relative_to(DEPLOY_DIR.parent)}:")
    print(json.dumps(config, indent=2))
    print("\nNext: deploy/deploy.py deploy")


# --- deploy ----------------------------------------------------------------


def push_image(config: dict[str, Any], image_uri: str) -> None:
    container_cmd = os.environ.get("CONTAINER_CMD", "podman")

    log(f"Building image ({container_cmd})")
    subprocess.run(
        [container_cmd, "build", "-t", image_uri, str(DEPLOY_DIR.parent)], check=True
    )

    log("Logging in to ECR")
    ecr = boto3.client("ecr", region_name=config["aws_region"])
    auth = ecr.get_authorization_token()["authorizationData"][0]
    user, password = base64.b64decode(auth["authorizationToken"]).decode().split(":", 1)
    subprocess.run(
        [container_cmd, "login", "--username", user, "--password-stdin",
         auth["proxyEndpoint"]],
        input=password.encode(),
        check=True,
    )

    log("Pushing image")
    subprocess.run([container_cmd, "push", image_uri], check=True)


def register_task_definition(config: dict[str, Any], image_uri: str, ecs: Any) -> None:
    log("Registering task definition")
    rendered = (
        TASK_DEF_PATH.read_text()
        .replace("__EXECUTION_ROLE_ARN__", config["execution_role_arn"])
        .replace("__IMAGE_URI__", image_uri)
        .replace("__AWS_REGION__", config["aws_region"])
    )
    ecs.register_task_definition(**json.loads(rendered))


def upsert_service(config: dict[str, Any], ecs: Any) -> None:
    services = ecs.describe_services(cluster=APP_NAME, services=[APP_NAME])["services"]
    if services and services[0]["status"] == "ACTIVE":
        log("Updating existing service")
        ecs.update_service(
            cluster=APP_NAME,
            service=APP_NAME,
            taskDefinition=APP_NAME,
            forceNewDeployment=True,
        )
        return
    log("Creating service")
    ecs.create_service(
        cluster=APP_NAME,
        serviceName=APP_NAME,
        taskDefinition=APP_NAME,
        desiredCount=1,
        capacityProviderStrategy=[{"capacityProvider": "FARGATE_SPOT", "weight": 1}],
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": config["subnet_ids"],
                "securityGroups": [config["security_group_id"]],
                "assignPublicIp": "ENABLED",
            }
        },
    )


def task_public_ip(config: dict[str, Any], ecs: Any) -> str:
    task_arn = ecs.list_tasks(cluster=APP_NAME, serviceName=APP_NAME)["taskArns"][0]
    task = ecs.describe_tasks(cluster=APP_NAME, tasks=[task_arn])["tasks"][0]
    eni_id = next(
        d["value"]
        for d in task["attachments"][0]["details"]
        if d["name"] == "networkInterfaceId"
    )
    ec2 = boto3.client("ec2", region_name=config["aws_region"])
    eni = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
    return str(eni["NetworkInterfaces"][0]["Association"]["PublicIp"])


def cmd_deploy(_: argparse.Namespace) -> None:
    config = load_config()
    image_uri = f"{config['ecr_repo_uri']}:latest"
    ecs = boto3.client("ecs", region_name=config["aws_region"])

    push_image(config, image_uri)
    register_task_definition(config, image_uri, ecs)
    upsert_service(config, ecs)

    log("Waiting for service to stabilize")
    ecs.get_waiter("services_stable").wait(cluster=APP_NAME, services=[APP_NAME])

    print(f"\nDeployed: http://{task_public_ip(config, ecs)}:{CONTAINER_PORT}")
    print(
        f"(Only reachable from the IP allowed in the {APP_NAME}-sg security group — "
        "run `deploy/deploy.py update-ip` if your IP changed.)"
    )


# --- update-ip -------------------------------------------------------------


def cmd_update_ip(_: argparse.Namespace) -> None:
    config = load_config()
    sg_id = config["security_group_id"]
    ec2 = boto3.client("ec2", region_name=config["aws_region"])

    ip = my_public_ip()
    print(f"Current public IP: {ip}")

    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
    for perm in sg["IpPermissions"]:
        if perm.get("FromPort") != CONTAINER_PORT:
            continue
        for rng in perm.get("IpRanges", []):
            cidr = rng["CidrIp"]
            if cidr != f"{ip}/32":
                ec2.revoke_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": CONTAINER_PORT,
                            "ToPort": CONTAINER_PORT,
                            "IpRanges": [{"CidrIp": cidr}],
                        }
                    ],
                )
                print(f"Revoked stale rule for {cidr}")

    allow_ip(ec2, sg_id, ip)
    print(f"Security group {sg_id} now allows only {ip}/32 on port {CONTAINER_PORT}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="one-time AWS setup").set_defaults(func=cmd_setup)
    sub.add_parser("deploy", help="build, push, and roll out").set_defaults(func=cmd_deploy)
    sub.add_parser("update-ip", help="re-lock security group to current IP").set_defaults(
        func=cmd_update_ip
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
