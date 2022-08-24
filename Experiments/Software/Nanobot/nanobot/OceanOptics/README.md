# OceanOptics Rules

In order to use these spectrometers, some `udev` rules must be added. The original [seabreeze](https://github.com/ap--/python-seabreeze) offers support for adding these rules but may be missing the QE-Pro variety.

If using these devices throws an error about missing rules, copy the `10-oceanoptics.rules` file to `/etc/udev/rules.d`:

```
sudo cp 10-oceanoptics.rules /etc/udev/rules.d/

sudo udevadm control --reload-rules
```