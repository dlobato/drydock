"""Exercise the fixed scale fixture without allocating switch workloads."""

import ipaddress
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from examples.demo.anta import SCALE_NODES
from examples.scale import expand


class ScaleTests(unittest.TestCase):
    def test_scale_inventory_has_100_distinct_switches_and_49_complete_mlag_pairs(self):
        source = Path("examples/evpn-symmetric-irb")
        original = {p: p.read_bytes() for p in source.rglob("*.yml")}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fabric"
            shutil.copytree(source, target)
            expand(target)
            groups = yaml.safe_load((target / "group_vars/LEAVES.yml").read_text())[
                "l3leaf"
            ]
            inventory = yaml.safe_load((target / "inventory.yml").read_text())["all"][
                "children"
            ]["FABRIC"]["children"]
            names = set(inventory["SPINES"]["hosts"])
            addresses = set()
            interfaces = set()
            for group in groups["node_groups"]:
                hosts = inventory["LEAVES"]["children"][group["group"]]["hosts"]
                self.assertEqual(set(hosts), {node["name"] for node in group["nodes"]})
                self.assertEqual(len(hosts), 2)
                for node in group["nodes"]:
                    names.add(node["name"])
                    addresses.add(ipaddress.ip_interface(node["mgmt_ip"]).ip)
                    interfaces.add(tuple(node["uplink_switch_interfaces"]))
            self.assertEqual(names, SCALE_NODES)
            self.assertEqual(len(groups["node_groups"]), 49)
            self.assertEqual(len(addresses), 98)
            self.assertEqual(len(interfaces), 98)
            self.assertEqual(groups["defaults"]["uplink_ipv4_pool"], "10.242.0.0/22")
            result = {p: p.read_bytes() for p in target.rglob("*.yml")}
            expand(target)
            self.assertEqual(result, {p: p.read_bytes() for p in result})
        self.assertEqual(original, {p: p.read_bytes() for p in original})


if __name__ == "__main__":
    unittest.main()
