python2-pifacenetctl
====================

This python module provides a way to monitor the IP address of a
headless Raspberry Pi which has a PiFace Digital fitted, by using LEDs
on the PiFace.  It will also allow the Raspberry Pi to halted by
pressing and holding a button on the PiFace.

If you are using a distribution with netctl, (e.g. arch linux) you can
also control wireless network functions.

It has the following features without the netctl module:
- Displays a single flashing LED if there is no IP address
- Displays a 4-led "sweep" to identify the start of the sequence,
			then shows a sequence on LED7-LED4 of the IP address, one nybble
			at a time
- Halts the Raspberry Pi when SW4 is pressed

With the netctl module, and a distribution such as archlinux which
uses systemd and netctl, additional functionality:
- When no IP address is displayed, press SW1-SW3 to attempt to
			start a wireless connection.  These are indexed by the order
			they appear in the following command:
  * netctl list | grep wlan0
- When an IP address is displayed, press SW3 to disconnect the
			network connection

Possible invocations:
- Import the 'pifacenetctl' module, instantiate the class, and
      use the 'run_state' method in your own loop.
- Import the 'pifacenetctl' module, instantiate the class, and
			call the 'run' method and let it loop for you
- Use the daemon:
  * python -m pifacenetctl start

