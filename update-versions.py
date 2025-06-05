#!/usr/bin/env python3
"""A script for generating version information for the docs.

This script generates the following based on the docs directories that are
present:
* A versions.json for the Sphinx version picker
* The "latest" symlink
* A banner-config.json for each version of the docs, which contains text to show
  in a banner at the top of the page.

Usage:
  update-versions DOCS_DIRECTORY

This script assumes it's being run from the directory it is in; if it isn't,
some paths may be wrong.
"""

import json
import sys
from pathlib import Path


def split_version_tag(version):
    """Split a dot-separated version number into its integer components."""
    try:
        return tuple(map(int, version.lstrip("v").split(".")))
    except ValueError:
        return None


def classify_versions(versions):
    """Separate tagged versions from development versions, and sort both.

    Splits the given list of version names into tagged versions (vX.Y) and dev
    versions (everything else), and sorts these versions as described in the
    write_versions_json docstring. Does not insert a "latest" version.

    Returns a tuple of lists: (tag_versions, dev_versions)
    """
    tag_versions = {
        v for v in versions if v.startswith("v") and split_version_tag(v) is not None
    }
    dev_versions = set(versions) - tag_versions - {"latest"}

    tag_versions = sorted(tag_versions, key=split_version_tag, reverse=True)
    dev_versions = sorted(dev_versions)
    if "dev" in dev_versions:
        dev_versions.remove("dev")
        dev_versions = ["dev"] + dev_versions

    return (tag_versions, dev_versions)


def get_release_name(docs_dir, version):
    """Get the full release name of the documentation with the given version."""
    if version == "latest":
        return "latest"
    return (docs_dir / version / "_release").read_text().strip()


def write_versions_json(docs_dir, tag_versions, dev_versions):
    """Write versions.json to the given directory.

    The order the versions appear in version.json matters, and it should not just be
    alphabetical. The versions are sorted as follows:
    - "latest" is always first as long as there is any vX.Y version.
    - Versions formatted like "vX.Y" are next, in descending order using X.Y as a
      version number.
    - "dev", if present, is next
    - Any remaining versions are included in alphabetical order. Generally there
      aren't any.
    In addition to writing versions.json, this function sets up the symlink for
    the "latest" version. This points to the first vX.Y version in the above
    ordering.
    """
    sorted_versions = []
    if tag_versions:
        latest_tag = tag_versions[0]
        print(f"Using {latest_tag} as latest version")
        sorted_versions.append("latest")
        latest_link = docs_dir / "latest"
        latest_link.unlink(missing_ok=True)
        latest_link.symlink_to(latest_tag)

    sorted_versions.extend(tag_versions)
    sorted_versions.extend(dev_versions)

    with (docs_dir / "versions.json").open("w") as fp:
        path_prefix = "/".join(docs_dir.parts[1:])
        json.dump(
            [
                {
                    "version": v,
                    "name": get_release_name(docs_dir, v),
                    "url": f"/tumult-docs/{path_prefix}/{v}/",
                }
                for v in sorted_versions
            ],
            fp,
        )


def write_banner_json(docs_dir, version, is_dev):
    """Write banner-config.json for a given version."""
    # The format of package-banner-config.json is described in this repo's
    # readme. If it changes, be sure to update that description.
    with open(docs_dir / "package-banner-config.json") as fp:
        banner_config = json.load(fp)
    package_name = banner_config["package_name"]
    current_banner_config = banner_config["versions"].get(version, {})

    if not current_banner_config.get("supported", True):
        config = {
            "content": (
                f"This version of of {package_name} is no longer supported. "
                "If possible, upgrading to a newer version is recommended."
            )
        }
    elif is_dev:
        config = {
            "content": (
                "You are reading the documentation for a development version of "
                f"{package_name}. Features and content may be changed prior to release."
            )
        }
    else:
        config = {}

    with open(docs_dir / version / "banner-config.json", "w") as fp:
        json.dump(config, fp)


def main():
    try:
        docs_dir = Path(sys.argv[1])
    except IndexError:
        print("Usage: update-versions DOCS_DIRECTORY")
        sys.exit(1)
    if not docs_dir.exists() or not docs_dir.is_dir():
        print("Given docs directory does not exist, or is not a directory.")
        sys.exit(1)

    versions = [p.name for p in docs_dir.iterdir() if p.is_dir()]
    print(f"Found versions for {docs_dir}: {', '.join(versions)}")

    tag_versions, dev_versions = classify_versions(versions)
    write_versions_json(docs_dir, tag_versions, dev_versions)

    for v in tag_versions:
        write_banner_json(docs_dir, v, False)
    for v in dev_versions:
        write_banner_json(docs_dir, v, True)


if __name__ == "__main__":
    main()
