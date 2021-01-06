=========================
Masakari service overview
=========================

Masakari provides Virtual Machines High Availability(VMHA), and rescues
KVM-based Virtual Machines(VM) from a failure events described below:

* ``VM process down`` -
  restart vm (use nova stop API, and nova start API).
  Libvirt events will be also emitted by other failures.
* ``Provisioning process down`` -
  restarts process, changes nova-compute service status to maintenance mode
  (use nova service-disable).
* ``nova-compute host failure`` -
  evacuate all the VMs from failure host according to the following recovery
  methods (use nova evacuate API).

    * ``auto`` -
      evacuate all the VMs with no destination node for nova scheduler.
    * ``reserved_host`` -
      evacuate all the VMs with reserved hosts as the destination nodes for
      nova scheduler.
    * ``auto_priority`` -
      evacuate all the VMs by using ``auto`` recovery method firstly.
      If failed, then using ``reserved_host`` recovery method.
    * ``rh_priority`` -
      evacuate all the VMs by using ``reserved_host`` recovery method firstly.
      If failed, then using ``auto`` recovery method.

The below services enables deplores to integrate with the Masakari directly
or through custom plug-ins.

The Masakari service consists of the following components:

``masakari-api``
  An OpenStack-native REST API that processes API requests by sending
  them to the ``masakari-engine`` over `Remote Procedure Call (RPC)`.

``masakari-engine``
  Processes the notifications received from ``masakari-api`` by executing the
  recovery workflow in asynchronous way.
