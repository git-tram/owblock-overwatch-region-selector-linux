# OWBlock [Overwatch Region Selector]

![OWBlock icon](assets/owblock.png)

## Install

```bash
tar -xzf OWBlock-linux-x86_64-v0.1.1.tar.gz
cd OWBlock-linux-x86_64-v0.1.1
sudo ./scripts/install-owblock.sh
```

## Uninstall
```bash
sudo ./scripts/uninstall-owblock.sh
```

## Launch

- Menu: **OWBlock**
- Terminal: `owblock`

> [!IMPORTANT]
> - If connection hangs/fails, make sure to unblock all servers to avoid a competitive ban. 
> - Restarting the game appears to produce the best results when unblock/blocking servers.

## Notes
> [!Note]
> - Requires `python3-venv` on the host.
> - Requires `nftables` on the host.
> - The launcher uses the working pattern:
   `pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR ...`

## Screenshots
![Main window](docs/images/owblock-app.png)

## Acknowledgements

- [stowmyy/dropship](https://github.com/stowmyy/dropship)
- [foryVERX/Overwatch-Server-Selector](https://github.com/foryVERX/Overwatch-Server-Selector/)

> [!CAUTION]
> Not affiliated with Blizzard, use at your own risk.