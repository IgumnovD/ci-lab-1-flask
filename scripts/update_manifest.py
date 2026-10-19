"""Update and verify the image of the named application container."""
import os
from pathlib import Path

import yaml


path = Path("k8s-manifests/staging/deployment.yaml")
manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
containers = manifest["spec"]["template"]["spec"]["containers"]
container, = [item for item in containers if item["name"] == "myapp"]
container["image"] = os.environ["STAGING_IMAGE"]
for item in manifest["spec"]["template"]["spec"].get("initContainers", []):
    if item["name"] == "init-db":
        item["image"] = os.environ["STAGING_IMAGE"]
path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
assert yaml.safe_load(path.read_text(encoding="utf-8")) == manifest
