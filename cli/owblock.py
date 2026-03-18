#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

TABLE_FAMILY = "inet"
TABLE_NAME = "owblock"
CHAIN_NAME = "output"

RULE_V4_COMMENT = "owblock-ipv4"
RULE_V6_COMMENT = "owblock-ipv6"

SET_NAME_RE = re.compile(r"[^a-z0-9_]+")


class OWBlockError(Exception):
    pass


def run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def slugify(name: str) -> str:
    value = name.strip().lower().replace("-", "_").replace(" ", "_")
    value = SET_NAME_RE.sub("_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError(f"cannot convert region name to set name: {name!r}")
    return value[:40]


def set_names(region: str) -> tuple[str, str]:
    slug = slugify(region)
    return f"r4_{slug}", f"r6_{slug}"


def load_regions(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class OWBlockManager:
    def __init__(self, regions_file: Path | str = "regions.json") -> None:
        self.regions_file = Path(regions_file)
        self.regions = load_regions(self.regions_file)

    def require_nft(self) -> None:
        if shutil.which("nft") is None:
            raise OWBlockError("nft command not found. Install nftables first.")

    def require_root(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            raise OWBlockError("this command must be run as root.")

    def nft_exists_table(self) -> bool:
        result = run(["nft", "list", "table", TABLE_FAMILY, TABLE_NAME], check=False)
        return result.returncode == 0

    def nft_chain_exists(self) -> bool:
        result = run(["nft", "list", "chain", TABLE_FAMILY, TABLE_NAME, CHAIN_NAME], check=False)
        return result.returncode == 0

    def ensure_named_set(self, name: str, set_type: str, flags: str | None = None) -> None:
        result = run(["nft", "list", "set", TABLE_FAMILY, TABLE_NAME, name], check=False)
        if result.returncode == 0:
            return

        cmd = ["nft", "add", "set", TABLE_FAMILY, TABLE_NAME, name, "{", "type", set_type, ";"]
        if flags:
            cmd.extend(["flags", flags, ";"])
        cmd.append("}")
        run(cmd)

    def ensure_rule(self, expr: str, rule_comment: str) -> None:
        result = run(["nft", "-a", "list", "chain", TABLE_FAMILY, TABLE_NAME, CHAIN_NAME], check=False)
        if result.returncode == 0 and rule_comment in result.stdout:
            return
        run(["nft", "add", "rule", TABLE_FAMILY, TABLE_NAME, CHAIN_NAME] + expr.split())

    def ensure_base(self) -> None:
        if not self.nft_exists_table():
            run(["nft", "add", "table", TABLE_FAMILY, TABLE_NAME])

        if not self.nft_chain_exists():
            run([
                "nft", "add", "chain", TABLE_FAMILY, TABLE_NAME, CHAIN_NAME,
                "{", "type", "filter", "hook", "output", "priority", "0", ";", "policy", "accept", ";", "}"
            ])

        self.ensure_named_set("active_v4", "ipv4_addr", "interval")
        self.ensure_named_set("active_v6", "ipv6_addr", "interval")

        self.ensure_rule(
            expr=f'ip daddr @active_v4 meta l4proto {{ tcp, udp }} drop comment "{RULE_V4_COMMENT}"',
            rule_comment=RULE_V4_COMMENT
        )
        self.ensure_rule(
            expr=f'ip6 daddr @active_v6 meta l4proto {{ tcp, udp }} drop comment "{RULE_V6_COMMENT}"',
            rule_comment=RULE_V6_COMMENT
        )

    def split_ips(self, values: List[str]) -> List[str]:
        return [item.strip() for item in values if item.strip()]

    def add_elements(self, set_name: str, elements: List[str]) -> None:
        if not elements:
            return
        run(["nft", "add", "element", TABLE_FAMILY, TABLE_NAME, set_name, "{", ",".join(elements), "}"])

    def flush_set(self, set_name: str) -> None:
        run(["nft", "flush", "set", TABLE_FAMILY, TABLE_NAME, set_name], check=False)

    def set_has_elements(self, set_name: str) -> bool:
        result = run(["nft", "-j", "list", "set", TABLE_FAMILY, TABLE_NAME, set_name], check=False)
        if result.returncode != 0:
            return False
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False
        for item in data.get("nftables", []):
            s = item.get("set")
            if s and s.get("name") == set_name:
                return bool(s.get("elem"))
        return False

    def remove_known_elements_from_active(self, region: str) -> None:
        if region not in self.regions:
            return
        ipv4 = self.split_ips(self.regions[region].get("ipv4", []))
        ipv6 = self.split_ips(self.regions[region].get("ipv6", []))
        if ipv4:
            run(["nft", "delete", "element", TABLE_FAMILY, TABLE_NAME, "active_v4", "{", ",".join(ipv4), "}"], check=False)
        if ipv6:
            run(["nft", "delete", "element", TABLE_FAMILY, TABLE_NAME, "active_v6", "{", ",".join(ipv6), "}"], check=False)

    def list_regions(self) -> List[str]:
        return list(self.regions.keys())

    def get_status_map(self) -> Dict[str, bool]:
        if not self.nft_exists_table():
            return {region: False for region in self.regions}
        result = {}
        for region in self.regions:
            v4_set, v6_set = set_names(region)
            enabled = self.set_has_elements(v4_set) or self.set_has_elements(v6_set)
            result[region] = enabled
        return result

    def block_region(self, region: str) -> None:
        if region not in self.regions:
            raise OWBlockError(f"unknown region: {region}")
        self.require_nft()
        self.require_root()
        self.ensure_base()
        v4_set, v6_set = set_names(region)
        self.ensure_named_set(v4_set, "ipv4_addr", "interval")
        self.ensure_named_set(v6_set, "ipv6_addr", "interval")
        self.flush_set(v4_set)
        self.flush_set(v6_set)
        self.remove_known_elements_from_active(region)
        ipv4 = self.split_ips(self.regions[region].get("ipv4", []))
        ipv6 = self.split_ips(self.regions[region].get("ipv6", []))
        self.add_elements(v4_set, ipv4)
        self.add_elements(v6_set, ipv6)
        if ipv4:
            self.add_elements("active_v4", ipv4)
        if ipv6:
            self.add_elements("active_v6", ipv6)

    def unblock_region(self, region: str) -> None:
        if region not in self.regions:
            raise OWBlockError(f"unknown region: {region}")
        self.require_nft()
        self.require_root()
        self.ensure_base()
        self.remove_known_elements_from_active(region)
        v4_set, v6_set = set_names(region)
        self.flush_set(v4_set)
        self.flush_set(v6_set)

    def unblock_all(self) -> None:
        self.require_nft()
        self.require_root()
        if not self.nft_exists_table():
            return
        self.flush_set("active_v4")
        self.flush_set("active_v6")
        for region in self.regions:
            v4_set, v6_set = set_names(region)
            self.flush_set(v4_set)
            self.flush_set(v6_set)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Block Overwatch regions using nftables")
    parser.add_argument("--regions-file", default="regions.json", help="Path to regions.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("status")
    sub.add_parser("unblock-all")
    p_block = sub.add_parser("block")
    p_block.add_argument("regions", nargs="+", help="Region names")
    p_unblock = sub.add_parser("unblock")
    p_unblock.add_argument("regions", nargs="+", help="Region names")
    args = parser.parse_args()
    manager = OWBlockManager(args.regions_file)
    try:
        if args.cmd == "list":
            print("Available regions:")
            for region in manager.list_regions():
                desc = manager.regions[region].get("description", "")
                print(f"  - {region} ({desc})")
        elif args.cmd == "status":
            print("Region status:")
            for region, enabled in manager.get_status_map().items():
                print(f"  - {region}: {'BLOCKED' if enabled else 'open'}")
        elif args.cmd == "block":
            for region in args.regions:
                manager.block_region(region)
                print(f"blocked: {region}")
        elif args.cmd == "unblock":
            for region in args.regions:
                manager.unblock_region(region)
                print(f"unblocked: {region}")
        elif args.cmd == "unblock-all":
            manager.unblock_all()
            print("unblocked all regions")
    except OWBlockError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    cli()
