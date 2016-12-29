# check_xenserver_messages
Checks if there are any System alert messages active on xenServer pool/host. Requires XenServer v6.2+ version as message priorities are not defined properly on older versions.

Example Nagios check command:
Nagios command define:
set $USER26$ under resource.cfg, its xenserver password

```
define command {
   command_name check_xenserver_messages
   command_line $USER1$/check_xenserver_messages.py -H $HOSTADDRESS$ -p "$USER26$"
}
```
