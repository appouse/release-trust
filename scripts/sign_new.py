#!/usr/bin/env python3
"""Sign release images that are not signed yet (keyless, Sigstore).

Lists the artifacts of the configured Harbor projects, keeps those with a release tag, checks whether a signature
from this workflow already exists (cosign verify) and signs the rest (cosign sign). Only the image digest and this
repository's identity end up in the public transparency log; the private source repositories never do.

Env: HARBOR_SIGNERS — JSON {"<project>": {"username": ..., "password": ...}}: one project-level robot per project
(list, pull, push of signatures), GITHUB_REPOSITORY (owner/name).
Optional: ONLY_IMAGE=<project>/<repo>@sha256:... to sign a single artifact (manual run); DRY_RUN=1.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


SIGNERS = json.loads(os.environ.get("HARBOR_SIGNERS") or "{}")


def login(cfg, project):
    c = SIGNERS[project]
    subprocess.run(["cosign", "login", cfg["registry"], "-u", c["username"], "--password-stdin"],
                   input=c["password"].encode(), check=True, capture_output=True)


def harbor(cfg, path, project):
    c = SIGNERS[project]
    auth = base64.b64encode(f"{c['username']}:{c['password']}".encode()).decode()
    req = urllib.request.Request(f"https://{cfg['registry']}/api/v2.0{path}", headers={"Authorization": "Basic " + auth})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def candidates(cfg, project):
    tag_re = re.compile(cfg["releaseTag"])
    if True:
        page = 1
        while True:
            repos = harbor(cfg, f"/projects/{project}/repositories?page_size=100&page={page}", project)
            for repo in repos:
                name = repo["name"].split("/", 1)[1]
                enc = urllib.parse.quote(urllib.parse.quote(name, safe=""), safe="")
                for art in harbor(cfg, f"/projects/{project}/repositories/{enc}/artifacts?with_tag=true&page_size=100", project):
                    tags = [t["name"] for t in (art.get("tags") or [])]
                    if any(tag_re.match(t) for t in tags) and DIGEST.match(art["digest"]):
                        yield f"{cfg['registry']}/{project}/{name}@{art['digest']}", tags, project
            if len(repos) < 100:
                break
            page += 1


def main():
    cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "trust.json"))
    identity = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/{cfg['workflow']}@refs/heads/{cfg['branch']}"
    only = os.environ.get("ONLY_IMAGE", "").strip()
    if only:
        project = only.split("/", 1)[0]
        if project not in cfg["projects"] or "@" not in only or not DIGEST.match(only.split("@", 1)[1]):
            sys.exit(f"ONLY_IMAGE geçersiz ya da izinli projede değil: {only}")
        refs = [(f"{cfg['registry']}/{only}", ["(elle)"], project)]
    else:
        refs = []
        for project in cfg["projects"]:
            if project not in SIGNERS:
                sys.exit(f"HARBOR_SIGNERS içinde {project} için robot yok")
            refs += list(candidates(cfg, project))
    signed = skipped = 0
    logged_in = None
    for ref, tags, project in refs:
        if project != logged_in:
            login(cfg, project)
            logged_in = project
        ok = subprocess.run(["cosign", "verify", ref, "--certificate-identity", identity,
                             "--certificate-oidc-issuer", cfg["issuer"]], capture_output=True).returncode == 0
        if ok:
            skipped += 1
            continue
        print(f"imzalanıyor: {ref} {tags}", flush=True)
        if os.environ.get("DRY_RUN") != "1":
            subprocess.run(["cosign", "sign", "--yes", ref], check=True)
        signed += 1
    summary = f"imzalanan: {signed}, zaten imzalı: {skipped}, kimlik: {identity}"
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(summary + "\n")


if __name__ == "__main__":
    main()
