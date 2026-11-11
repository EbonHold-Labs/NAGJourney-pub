import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import upload_curseforge


VERSION = "1.0.6"
LEGACY = ("NAGJourney", "NAGJourneyTerrainData")
SPLIT = ("NAGJourney", "NAGJourneyTerrainData0", "NAGJourneyTerrainData1", "NAGJourneyTerrainData2991")


class PackageLayoutTest(unittest.TestCase):
    def validate(self, folders, wrong_version=None):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            archive = directory / f"NAGJourney-{VERSION}.zip"
            with zipfile.ZipFile(archive, "w") as package:
                for folder in folders:
                    version = "1.0.5" if folder == wrong_version else VERSION
                    package.writestr(f"{folder}/{folder}.toc", f"## Interface: 16001\n## Version: {version}\n")

            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            manifest = {
                "product": "NAGJourney",
                "version": VERSION,
                "supportedClient": {"folder": "_forever_", "interface": 16001},
                "package": {"filename": archive.name, "sha256": digest,
                            "size": archive.stat().st_size, "fileCount": len(folders)},
            }
            (directory / f"NAGJourney-{VERSION}-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (directory / f"NAGJourney-{VERSION}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")

            with patch.object(upload_curseforge.subprocess, "run"):
                validated, game_version = upload_curseforge.download_package(directory, f"v{VERSION}", VERSION)
            self.assertEqual(validated, archive)
            self.assertEqual(game_version, "1.60.1")

    def test_legacy_layout(self):
        self.validate(LEGACY)

    def test_split_layout(self):
        self.validate(SPLIT)

    def test_incomplete_or_mixed_layout(self):
        for folders in (SPLIT[:-1], (*SPLIT, LEGACY[1]), (*SPLIT, "UnexpectedAddon")):
            with self.subTest(folders=folders), self.assertRaisesRegex(ValueError, "invalid contents"):
                self.validate(folders)

    def test_each_split_toc_requires_matching_version(self):
        for folder in SPLIT:
            with self.subTest(folder=folder), self.assertRaisesRegex(ValueError, f"{folder} has unexpected Version"):
                self.validate(SPLIT, wrong_version=folder)
