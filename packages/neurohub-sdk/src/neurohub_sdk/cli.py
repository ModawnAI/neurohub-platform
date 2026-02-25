"""CLI for neurohub-sdk: init, build, deploy, test."""

from __future__ import annotations

import argparse
import json
import os
import sys


def cmd_init(args):
    """Initialize a new NeuroHub service project."""
    name = args.name
    path = os.path.join(os.getcwd(), name)
    os.makedirs(path, exist_ok=True)

    # service.py
    with open(os.path.join(path, "service.py"), "w") as f:
        f.write(f'''\
"""NeuroHub Service: {name}"""

from neurohub_sdk import BaseService, InputContext, OutputContext, ServiceConfig
from neurohub_sdk.schema import SchemaDefinition, InputField, OutputField, UploadSlot


class {name.replace("-", "_").title().replace("_", "")}Service(BaseService):
    config = ServiceConfig(
        name="{name}",
        version="1.0.0",
        display_name="{name}",
        description="TODO: Add description",
    )

    schema = SchemaDefinition(
        inputs=[
            InputField(key="text", type="text", label="입력", required=True),
        ],
        outputs=[
            OutputField(key="result", type="text", label="결과"),
        ],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        text = ctx.get_input("text")
        output = ctx.create_output()
        output.set("result", text)
        return output


if __name__ == "__main__":
    {name.replace("-", "_").title().replace("_", "")}Service().serve()
''')

    # __main__.py
    with open(os.path.join(path, "__main__.py"), "w") as f:
        f.write(f'''\
"""Entry point for the service container."""
from service import {name.replace("-", "_").title().replace("_", "")}Service

if __name__ == "__main__":
    {name.replace("-", "_").title().replace("_", "")}Service().serve()
''')

    # requirements.txt
    with open(os.path.join(path, "requirements.txt"), "w") as f:
        f.write("neurohub-sdk>=0.1.0\n")

    # neurohub.json
    with open(os.path.join(path, "neurohub.json"), "w") as f:
        json.dump(
            {
                "name": name,
                "version": "1.0.0",
                "entry": "service.py",
            },
            f,
            indent=2,
        )

    print(f"Created NeuroHub service at ./{name}/")
    print(f"  service.py      — Service implementation")
    print(f"  requirements.txt — Dependencies")
    print(f"  neurohub.json   — Service metadata")
    print(f"\nNext steps:")
    print(f"  cd {name}")
    print(f"  pip install neurohub-sdk")
    print(f"  python service.py  # Run locally")
    print(f"  neurohub build     # Build container")


def cmd_build(args):
    """Build a Docker image for the service."""
    from neurohub_sdk.packaging import generate_dockerfile

    # Load service module
    sys.path.insert(0, os.getcwd())
    try:
        meta_path = os.path.join(os.getcwd(), "neurohub.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            entry = meta.get("entry", "service.py")
        else:
            entry = "service.py"

        module_name = entry.replace(".py", "")
        mod = __import__(module_name)

        # Find the BaseService subclass
        from neurohub_sdk.base import BaseService as _BS

        svc_cls = None
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, _BS) and obj is not _BS:
                svc_cls = obj
                break

        if not svc_cls:
            print("Error: No BaseService subclass found in", entry)
            sys.exit(1)

        svc = svc_cls()

        # Write Dockerfile
        dockerfile_content = generate_dockerfile(svc)
        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)
        print(f"Generated Dockerfile for {svc.config.name}:{svc.config.version}")

        # Build with Docker
        if not args.no_docker:
            tag = svc.config.image_tag
            os.system(f"docker build -t {tag} .")
            print(f"Built image: {tag}")
        else:
            print("Skipped docker build (--no-docker)")

    finally:
        sys.path.pop(0)


def cmd_deploy(args):
    """Deploy the service to Fly.io."""
    from neurohub_sdk.packaging import generate_fly_toml

    sys.path.insert(0, os.getcwd())
    try:
        meta_path = os.path.join(os.getcwd(), "neurohub.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            entry = meta.get("entry", "service.py")
        else:
            entry = "service.py"

        module_name = entry.replace(".py", "")
        mod = __import__(module_name)

        from neurohub_sdk.base import BaseService as _BS

        svc_cls = None
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, _BS) and obj is not _BS:
                svc_cls = obj
                break

        if not svc_cls:
            print("Error: No BaseService subclass found")
            sys.exit(1)

        svc = svc_cls()
        app_name = args.app_name or svc.config.app_name

        # Generate fly.toml
        fly_toml = generate_fly_toml(svc, app_name=app_name, region=args.region)
        with open("fly.toml", "w") as f:
            f.write(fly_toml)
        print(f"Generated fly.toml for {app_name}")

        if not args.dry_run:
            os.system("fly deploy --remote-only")
        else:
            print("Dry run: skipped fly deploy")

    finally:
        sys.path.pop(0)


def cmd_test(args):
    """Run a local test prediction against the service."""
    import asyncio

    sys.path.insert(0, os.getcwd())
    try:
        meta_path = os.path.join(os.getcwd(), "neurohub.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            entry = meta.get("entry", "service.py")
        else:
            entry = "service.py"

        module_name = entry.replace(".py", "")
        mod = __import__(module_name)

        from neurohub_sdk.base import BaseService as _BS
        from neurohub_sdk.context import InputContext

        svc_cls = None
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, _BS) and obj is not _BS:
                svc_cls = obj
                break

        if not svc_cls:
            print("Error: No BaseService subclass found")
            sys.exit(1)

        svc = svc_cls()

        # Load test input
        if args.input:
            with open(args.input) as f:
                test_input = json.load(f)
        else:
            test_input = {}

        job_spec = {
            "run_id": "test-local",
            "request_id": "test-local",
            "case_id": "test-local",
            "user_inputs": test_input,
            "case_demographics": {},
            "user_options": {},
            "input_artifacts": {},
            "storage": {},
        }

        ctx = InputContext.from_job_spec(job_spec)

        async def _run():
            return await svc.predict(ctx)

        output = asyncio.run(_run())
        result = output.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    finally:
        sys.path.pop(0)


def main():
    parser = argparse.ArgumentParser(
        prog="neurohub",
        description="NeuroHub Service SDK CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new service project")
    init_parser.add_argument("name", help="Service name (e.g. brain-classifier)")

    # build
    build_parser = subparsers.add_parser("build", help="Build Docker image")
    build_parser.add_argument("--no-docker", action="store_true", help="Skip docker build")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy to Fly.io")
    deploy_parser.add_argument("--app-name", help="Override Fly app name")
    deploy_parser.add_argument("--region", default="nrt", help="Fly.io region")
    deploy_parser.add_argument("--dry-run", action="store_true", help="Generate files only")

    # test
    test_parser = subparsers.add_parser("test", help="Run local test prediction")
    test_parser.add_argument("--input", "-i", help="Path to JSON input file")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "deploy":
        cmd_deploy(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
