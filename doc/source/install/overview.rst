=========================
Masakari service overview
=========================

Masakari provides Virtual Machines High Availability(VMHA), and rescues
KVM-based Virtual Machines(VM) from a failure events described below:

* VM process down - restart vm (use nova stop API, and nova start API).
                    Libvirt events will be also emitted by other failures.
* Provisioning process down - restarts process, changes nova-compute service
                              status to maintenance mode
                              (use nova service-disable).
* nova-compute host failure - evacuate all the VMs from failure host to
                              reserved host (use nova evacuate API).

The below services enables deplores to integrate with the Masakari directly
or through custom plug-ins.

The Masakari service consists of the following components:

``masakari-api``
  An OpenStack-native REST API that processes API requests by sending
  them to the ``masakari-engine`` over `Remote Procedure Call (RPC)`.

``masakari-engine``
  Processes the notifications received from ``masakari-api`` by executing the
  recovery workflow in asynchronous way.
