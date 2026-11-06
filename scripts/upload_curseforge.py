"""Mirror the verified ZIP of a published NAG Journey release to CurseForge."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


REPOSITORY = "EbonHold-Labs/NAGJourney-pub"
CURSEFORGE = "https://wow.curseforge.com/api"
TAG = re.compile(r"v(\d+\.\d+\.\d+)(-beta\d+)?")
FOLDERS = {"NAGJourney", "NAGJourneyTerrainData"}


def read_release(tag):
    release = json.loads(subprocess.check_output([
        "gh", "api", f"repos/{REPOSITORY}/releases/tags/{tag}",
    ], text=True, encoding="utf-8"))
    if release["tag_name"] != tag or release["draft"] or not release["published_at"]:
        raise ValueError("A published GitHub release is required.")
    return release


def download_package(directory, tag, version):
    filename = f"NAGJourney-{version}.zip"
    manifest_name = f"NAGJourney-{version}-manifest.json"
    checksum_name = f"NAGJourney-{version}.sha256"
    subprocess.run([
        "gh", "release", "download", tag, "--repo", REPOSITORY, "--dir", str(directory),
        "--pattern", filename, "--pattern", manifest_name, "--pattern", checksum_name,
    ], check=True)
    package = directory / filename
    manifest = json.loads((directory / manifest_name).read_text(encoding="utf-8"))
    client = manifest["supportedClient"]
    interface = client["interface"]
    if (manifest["product"] != "NAGJourney" or manifest["version"] != version
            or client["folder"] != "_forever_" or type(interface) is not int
            or not 16000 <= interface <= 16099):
        raise ValueError("Release manifest does not describe a supported Forever package.")
    with package.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum = (directory / checksum_name).read_text(encoding="ascii").split()
    package_info = manifest["package"]
    if (checksum != [digest, filename] or package_info["filename"] != filename
            or package_info["sha256"] != digest or package_info["size"] != package.stat().st_size):
        raise ValueError("Release ZIP, manifest and SHA-256 file do not match.")
    with zipfile.ZipFile(package) as archive:
        files = archive.namelist()
        if (len(files) != len(set(files)) or len(files) != package_info["fileCount"]
                or {name.split("/", 1)[0] for name in files} != FOLDERS
                or any("\\" in name or ".." in name.split("/") for name in files)
                or archive.testzip() is not None):
            raise ValueError("Release ZIP has invalid contents.")
        for folder in FOLDERS:
            toc = archive.read(f"{folder}/{folder}.toc").decode("utf-8-sig").splitlines()
            for key, value in (("Interface", str(interface)), ("Version", version)):
                header = f"## {key}:"
                if [line for line in toc if line.startswith(header)] != [f"{header} {value}"]:
                    raise ValueError(f"{folder} has unexpected {key} metadata.")
    game_version = f"{interface // 10000}.{interface // 100 % 100}.{interface % 100}"
    print(f"Verified {filename} ({digest}) for WoW {game_version}.", flush=True)
    return package, game_version


def curseforge_request(path, token, directory, *arguments):
    response = directory / "curseforge-response.json"
    # Pass the credential through stdin. Never put it in the URL or command line.
    result = subprocess.run([
        "curl", "-q", "--silent", "--show-error", "--max-time", "120",
        "--proto", "=https", "--header", "@-", "--output", str(response),
        "--write-out", "%{http_code}", *arguments, f"{CURSEFORGE}{path}",
    ], input=f"X-Api-Token: {token}\n", text=True, capture_output=True)
    if result.returncode or not re.fullmatch(r"2\d\d", result.stdout):
        status = result.stdout if re.fullmatch(r"\d{3}", result.stdout) else "unavailable"
        raise ValueError(f"CurseForge request failed (HTTP {status}, curl exit {result.returncode}).")
    return json.loads(response.read_text(encoding="utf-8"))


def resolve_version(versions, name):
    matches = [entry["id"] for entry in versions if entry["name"] == name]
    if len(matches) != 1 or type(matches[0]) is not int or matches[0] <= 0:
        raise ValueError(f"CurseForge must list exactly one game version named {name}.")
    return matches[0]


def reserve_upload(tag):
    # The documented upload API has no idempotency key. Reserve once across
    # event deliveries and manual runs, including ambiguous transport failures.
    reference = f"refs/tags/curseforge-upload/{tag}"
    result = subprocess.run([
        "gh", "api", "--method", "POST", f"repos/{REPOSITORY}/git/refs",
        "-f", f"ref={reference}", "-f", f"sha={os.environ['GITHUB_SHA']}",
    ], capture_output=True)
    if result.returncode:
        raise ValueError(f"Could not reserve {reference}. Check prior runs and repository permissions before retrying.")


def main():
    tag = os.environ.get("RELEASE_TAG", "")
    version_match = TAG.fullmatch(tag)
    if not version_match:
        raise ValueError("Use a stable vX.Y.Z or beta vX.Y.Z-betaN release tag.")
    version = tag[1:]
    beta = bool(version_match[2])
    verify_only = os.environ.get("VERIFY_ONLY", "false") == "true"
    project = os.environ.get("CURSEFORGE_PROJECT_ID", "")
    token = os.environ.get("CURSEFORGE_API_TOKEN", "")
    if not verify_only and not project and not token:
        print("::notice::CurseForge upload is disabled until the project ID and upload token are configured.")
        return
    release = read_release(tag)
    if release["prerelease"] != beta:
        raise ValueError("The release's prerelease flag must match its tag.")
    with tempfile.TemporaryDirectory(prefix="nagjourney-release-") as directory:
        directory = Path(directory)
        package, game_version = download_package(directory, tag, version)
        if not re.fullmatch(r"[1-9]\d*", project) or not token or any(c in token for c in "\r\n"):
            message = "Set the CURSEFORGE_PROJECT_ID Actions variable and CURSEFORGE_API_TOKEN Actions secret."
            if verify_only:
                print(message)
                return
            raise ValueError(message)
        version_id = resolve_version(curseforge_request("/game/versions", token, directory), game_version)
        print(f"CurseForge project {project}, game version {game_version} ({version_id}).", flush=True)
        if verify_only:
            return
        metadata = directory / "metadata.json"
        metadata.write_text(json.dumps({
            "changelog": release["body"] or f"NAG Journey {version}",
            "changelogType": "markdown",
            "displayName": f"NAG Journey {version}",
            "gameVersions": [version_id],
            "releaseType": "beta" if beta else "release",
        }), encoding="utf-8")
        reserve_upload(tag)
        result = curseforge_request(f"/projects/{project}/upload-file", token, directory,
                                    "--form", f"metadata=<{metadata}", "--form", f"file=@{package}")
        file_id = result.get("id")
        if type(file_id) is not int or file_id <= 0:
            raise ValueError("CurseForge returned no file ID. Check the project before retrying.")
        print(f"CurseForge accepted {tag} as file {file_id} for review.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        sys.exit(str(error))
