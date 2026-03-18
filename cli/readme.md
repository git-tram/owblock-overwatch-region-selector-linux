# OWBlock CLI

CLI-only bundle for OWBlock.

## Files
- `owblock.py`
- `regions.json`
- `owblock-cli`

## Usage

List regions:
```bash
sudo ./owblock-cli list
```

Show status:
```bash
sudo ./owblock-cli status
```

Block a region:
```bash
sudo ./owblock-cli block "Singapore"
```

Unblock a region:
```bash
sudo ./owblock-cli unblock "Singapore"
```

Unblock all:
```bash
sudo ./owblock-cli unblock-all
```

## Requirements
- `python3`
- `nftables` / `nft`
