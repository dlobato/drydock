"""Exercise packaging against the actual offline AVD build."""

import hashlib
from ipaddress import ip_interface, ip_network
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

import yaml

from bundle import build_bundle


SOURCE = Path(__file__).resolve().parents[2] / "artifacts/example/containerlab"
NODES = {"spine1", "spine2", "leaf1", "leaf2", "leaf3", "leaf4"}


class BundleTest(unittest.TestCase):
    def test_archived_topology_matches_rendered_fabric(self):
        with tarfile.open(SOURCE / "bundle.tar") as archive:
            topology = yaml.safe_load(archive.extractfile("FABRIC-topology.clab.yml"))
            mapping = json.load(archive.extractfile("interface_mapping.json"))
            nodes = topology["topology"]["nodes"]
            self.assertEqual(set(nodes), NODES)
            self.assertEqual(topology["prefix"], "")
            self.assertEqual(topology["topology"]["defaults"], {"kind": "arista_ceos"})
            self.assertEqual(set(topology["topology"]["kinds"]), {"arista_ceos"})
            kind = topology["topology"]["kinds"]["arista_ceos"]
            self.assertTrue(kind["enforce-startup-config"])
            self.assertEqual(kind["binds"], ["interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro"])
            self.assertEqual(mapping["ManagementIntf"], {"eth0": "Management1"})
            self.assertEqual(
                set(archive.getnames()),
                {"FABRIC-topology.clab.yml", "interface_mapping.json"}
                | {f"intended/configs/{name}.cfg" for name in NODES},
            )

            structured = {}
            for name, node in nodes.items():
                structured[name] = yaml.safe_load((SOURCE / f"intended/structured_configs/{name}.yml").read_text())
                self.assertEqual(structured[name]["hostname"], name)
                config_path = node["startup-config"]
                content = archive.extractfile(config_path).read()
                self.assertEqual(content, (SOURCE / config_path).read_bytes())
                config = content.decode()
                self.assertIn(f"\nhostname {name}\n", config)
                management = structured[name]["management_interfaces"][0]
                address = ip_interface(management["ip_address"])
                self.assertEqual(node["mgmt-ipv4"], str(address.ip))
                self.assertEqual(address.network, ip_network(topology["mgmt"]["ipv4-subnet"]))
                management_config = config.split("\ninterface Management1\n")[1].split("\n!")[0]
                self.assertIn(f"   ip address {address}", management_config)
                if name.startswith("leaf"):
                    pair = "PAIR1" if name in {"leaf1", "leaf2"} else "PAIR2"
                    self.assertEqual(structured[name]["mlag_configuration"]["domain_id"], pair)
                    self.assertIn(f"   domain-id {pair}\n", config)

            links = [tuple(sorted(link["endpoints"])) for link in topology["topology"]["links"]]
            expected = {
                tuple(sorted((f"leaf{leaf}:eth{spine}", f"spine{spine}:eth{leaf}")))
                for leaf in range(1, 5) for spine in (1, 2)
            } | {
                (f"leaf{first}:eth{port}", f"leaf{first + 1}:eth{port}")
                for first in (1, 3) for port in (6, 7)
            }
            self.assertEqual(len(links), 12)
            self.assertEqual(set(links), expected)
            endpoints = [endpoint for link in links for endpoint in link]
            self.assertEqual(len(set(endpoints)), len(endpoints))
            for left, right in links:
                for local, remote in ((left, right), (right, left)):
                    name, port = local.split(":")
                    peer, peer_port = remote.split(":")
                    interface = next(item for item in structured[name]["ethernet_interfaces"]
                                     if item["name"] == mapping["EthernetIntf"][port])
                    self.assertEqual(interface["metadata"]["peer"], peer)
                    self.assertEqual(interface["metadata"]["peer_interface"], mapping["EthernetIntf"][peer_port])

    def test_digest_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            shutil.copytree(SOURCE, source, dirs_exist_ok=True)
            archive = build_bundle(source, "ceos:offline-placeholder")
            original = archive.read_bytes()
            checksum = source / "bundle.tar.sha256"
            self.assertEqual(checksum.read_text(), f"{hashlib.sha256(original).hexdigest()}  bundle.tar\n")
            for path in source.rglob("*.cfg"):
                path.touch()
            self.assertEqual(build_bundle(source, "ceos:offline-placeholder").read_bytes(), original)
            self.assertNotEqual(build_bundle(source, "ceos:different-placeholder").read_bytes(), original)
            with tarfile.open(archive) as bundle:
                topology = yaml.safe_load(bundle.extractfile("FABRIC-topology.clab.yml"))
                self.assertEqual(topology["topology"]["kinds"]["arista_ceos"]["image"], "ceos:different-placeholder")
            config = source / "intended/configs/leaf1.cfg"
            config.write_text(config.read_text() + "! changed configuration\n")
            self.assertNotEqual(build_bundle(source, "ceos:offline-placeholder").read_bytes(), original)

    def test_missing_inputs_do_not_publish_a_bundle(self):
        for missing in ("intended/configs/leaf1.cfg", "interface_mapping.json", "FABRIC-topology.clab.yml"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                source = Path(directory)
                shutil.copytree(SOURCE, source, dirs_exist_ok=True)
                (source / "bundle.tar").unlink()
                (source / "bundle.tar.sha256").unlink()
                (source / missing).unlink()
                with self.assertRaises(FileNotFoundError):
                    build_bundle(source, "ceos:offline-placeholder")
                self.assertFalse((source / "bundle.tar").exists())
                self.assertFalse((source / "bundle.tar.sha256").exists())

    def test_explicit_image_is_required(self):
        for image in ("", "   "):
            with self.subTest(image=image), self.assertRaisesRegex(ValueError, "DRYDOCK_CEOS_IMAGE"):
                build_bundle(SOURCE, image)


if __name__ == "__main__":
    unittest.main()
