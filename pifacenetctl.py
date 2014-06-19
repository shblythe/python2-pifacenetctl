#!/usr/bin/python2
# vim: set et sts=4 sw=4:
"""
This python module provides a way to control wireless network functions on a
headless Raspberry Pi which has netctl (e.g. arch linux).
It has the following features without the netctl module:
    - Displays a single flashing LED if there is no IP address
    - Displays a 4-led "sweep" to identify the start of the sequence, then
      shows a sequence on LED7-LED4 of the IP address, one nybble at a time
    - Halts the Raspberry Pi when SW4 is pressed
With the netctl module, and a distribution such as archlinux which uses
systemd and netctl, additional functionality:
    - When no IP address is displayed, press SW1-SW3 to attempt to start a
      wireless connection.  These are indexed by the order they appear in the
      following command:
        netctl list | grep wlan0
    - When an IP address is displayed, press SW3 to disconnect the network
      connection

Possible invocations:
    - Import the 'pifacenetctl' module, instantiate the class, and
      use the 'run_state' method in your own loop.
    - Import the 'pifacenetctl' module, instantiate the class, and call the
      'run' method and let it loop for you
    - Use the daemon:
        'python -m pifacenetctl start'

"""
# Standard libraries
import time
import logging
import subprocess
import re
import signal
import sys

# Third-party libraries
from daemon import runner
import pifacedigitalio
import netifaces
netctl_enabled=True
try:
    import netctl
except ImportError:
    netctl_enabled=False
    

class PiFaceNetctl:
    """Instantiate to allow control of netctl via piface switches and LEDs"""
    _STATE_NO_IP=1
    _STATE_GOT_IP=2
    _STATE_HALT=3

    _STATE_NO_IP_LED_FLASH=7
    _STATE_NO_IP_LED_DELAY=.5
    _STATE_NO_IP_SW_CONN0=0x01
    _STATE_NO_IP_SW_CONN1=0x02
    _STATE_NO_IP_SW_CONN2=0x04
    _STATE_NO_IP_SW_HALT=0x08

    _STATE_GOT_IP_START_ATTRACT_LEDS=[0x80,0x40,0x20,0x10,0x20,0x40,0x80]
    _STATE_GOT_IP_START_ATTRACT_MASK=0xf0
    _STATE_GOT_IP_START_ATTRACT_DELAY=.1
    _STATE_GOT_IP_ADDRESS_DELAY=2
    _STATE_GOT_IP_SW_DISCONNECT=0x04
    _STATE_GOT_IP_SW_HALT=0x08

    _LED_ACK_PATTERN=0xf0
    _LED_ACK_MASK=0xf0
    _LED_ACK_DELAY=.1

    def __init__(self):
        self.stdin_path='/dev/null'
        self.stdout_path='/dev/null'
        self.stderr_path='/dev/null'
        self.pidfile_path='/var/run/pisaac-headless-ip.pid'
        self.pidfile_timeout=5
        self.pfd=None
        self.state=self._STATE_NO_IP

    def _led_ack_command(self):
        for times in range(2):
            self.pfd.output_port.value|=self._LED_ACK_PATTERN
            time.sleep(self._LED_ACK_DELAY)
            self.pfd.output_port.value&=~self._LED_ACK_MASK
            time.sleep(self._LED_ACK_DELAY)
        
    def _disconnect_network(self):
        self._led_ack_command()
        netctl.Netctl.stop_active_connection()
        
    def _state_halt(self):
        subprocess.Popen('halt',shell=True)
        while True:
            self._led_ack_command()
    
    def _get_ip_address(self):
        try:
            ip_addr=[int(x) for x in netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0].get('addr').split('.')]
        except:
            ip_addr=None
        return ip_addr
        
    def _state_no_ip(self):
        switches=self.pfd.input_port.value
        self.pfd.output_port.value&=0x0f
        self.pfd.leds[self._STATE_NO_IP_LED_FLASH].value=1
        time.sleep(self._STATE_NO_IP_LED_DELAY)
        self.pfd.leds[self._STATE_NO_IP_LED_FLASH].value=0
        time.sleep(self._STATE_NO_IP_LED_DELAY)
        switches&=self.pfd.input_port.value
        ip_addr=self._get_ip_address()
        if ip_addr:
            self.ip_addr=ip_addr
            self.state=self._STATE_GOT_IP
        elif netctl_enabled and switches & self._STATE_NO_IP_SW_CONN0:
            self._led_ack_command()
            netctl.Netctl.start_connection_by_match_index('wlan0',0)
        elif netctl_enabled and switches & self._STATE_NO_IP_SW_CONN1:
            self._led_ack_command()
            netctl.Netctl.start_connection_by_match_index('wlan0',1)
        elif netctl_enabled and switches & self._STATE_NO_IP_SW_CONN2:
            self._led_ack_command()
            netctl.Netctl.start_connection_by_match_index('wlan0',2)
        elif switches & self._STATE_NO_IP_SW_HALT:
            self.state=self._STATE_HALT

    def _state_got_ip(self):
        for x in self._STATE_GOT_IP_START_ATTRACT_LEDS:
            self.pfd.output_port.value&=~self._STATE_GOT_IP_START_ATTRACT_MASK
            self.pfd.output_port.value|=x
            time.sleep(self._STATE_GOT_IP_START_ATTRACT_DELAY)
        for x in self.ip_addr:
            for shift in [0,4]:
                if not self._get_ip_address():
                    self.ip_addr=[0,0,0,0]
                    self.state=self._STATE_NO_IP
                    return
                self.pfd.output_port.value&=0x0f
                self.pfd.output_port.value|=(x<<shift)&0xf0
                switches=self.pfd.input_port.value
                time.sleep(self._STATE_GOT_IP_ADDRESS_DELAY)
                switches&=self.pfd.input_port.value
                if netctl_enabled and \
                        switches & self._STATE_GOT_IP_SW_DISCONNECT:
                    self._disconnect_network()
                    return
                elif switches & self._STATE_GOT_IP_SW_HALT:
                    self.state=self._STATE_HALT
                    return

    def run_state(self):
        """Run whatever state we're in once, without looping"""
        # First time we come through we're we won't have instantiated
        # PiFaceDigital() - we need to do it here to ensure we do it
        # in the thread where it will be used - otherwise the file-
        # descriptors it uses won't be owned by the right thread.
        if self.pfd==None:
            self.pfd=pifacedigitalio.PiFaceDigital()
        if self.state==self._STATE_NO_IP:
            self._state_no_ip()
        elif self.state==self._STATE_GOT_IP:
            self._state_got_ip()
        elif self.state==self._STATE_HALT:
            self._state_halt()
        else:
            self.state=self._STATE_NO_IP

    def run(self):
        """Loop the state machine forever"""
        while True:
            self.run_state()
               
    @classmethod
    def daemon(cls):
        """Instantiate the daemon runner, accepting start/restart/stop args
        """
        headless=PiFaceNetctl()
        daemon_runner=runner.DaemonRunner(headless)
        daemon_runner.daemon_context.detach_process=True
        daemon_runner.do_action()

if __name__ == "__main__":
    if len(sys.argv)==2 and sys.argv[1]=='-r':
        pfn=PiFaceNetctl()
        pfn.run()
    else:
        PiFaceNetctl.daemon()


