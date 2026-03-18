# OWBlock [Overwatch Region Selector]

This zip includes everything needed:

- app/owblock.py
- app/owblock_gui.py
- app/regions.json
- app/requirements.txt
- assets/owblock.png
- scripts/install-owblock.sh
- scripts/owblock
- desktop/owblock.desktop

## Install

```bash
tar -xzf OWBlock-linux-x86_64-v0.1.0.tar.gz
cd OWBlock-linux-x86_64-v0.1.0
sudo ./scripts/install-owblock.sh
```

## Launch

- Menu: **OWBlock**
- Terminal: `owblock`

## Notes

- Requires `python3-venv` on the host.
- Requires `nftables` on the host.
- The launcher uses the working pattern:
  `pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR ...`
