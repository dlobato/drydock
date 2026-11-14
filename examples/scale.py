"""Expand a private copy of the EVPN example to two spines and 49 MLAG pairs."""

from pathlib import Path

import yaml


def expand(directory: Path):
    leaves_path = directory / "group_vars/LEAVES.yml"
    leaves = yaml.safe_load(leaves_path.read_text())
    leaves["l3leaf"]["defaults"]["uplink_ipv4_pool"] = "10.242.0.0/22"
    leaves["l3leaf"]["node_groups"] = [
        {
            "group": f"PAIR{pair}",
            "bgp_as": f"65100.{pair}",
            "nodes": [
                {
                    "name": f"leaf{number}",
                    "id": number,
                    "mgmt_ip": f"192.0.2.{20 + number}/24",
                    "uplink_switch_interfaces": [
                        f"Ethernet{number}",
                        f"Ethernet{number}",
                    ],
                }
                for number in (2 * pair - 1, 2 * pair)
            ],
        }
        for pair in range(1, 50)
    ]
    inventory = yaml.safe_load((directory / "inventory.yml").read_text())
    inventory["all"]["children"]["FABRIC"]["children"]["LEAVES"]["children"] = {
        f"PAIR{pair}": {"hosts": {f"leaf{2 * pair - 1}": None, f"leaf{2 * pair}": None}}
        for pair in range(1, 50)
    }
    fabric = yaml.safe_load((directory / "group_vars/FABRIC.yml").read_text())
    for interfaces in fabric["default_interfaces"]:
        if interfaces["types"] == ["spine"]:
            interfaces["downlink_interfaces"] = ["Ethernet1-98"]
    for path, value in (
        (leaves_path, leaves),
        (directory / "inventory.yml", inventory),
        (directory / "group_vars/FABRIC.yml", fabric),
    ):
        path.write_text(yaml.safe_dump(value, sort_keys=False))
