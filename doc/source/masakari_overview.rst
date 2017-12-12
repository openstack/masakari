..
      Copyright 2017 NTT DATA

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=========================
Masakari service overview
=========================

Masakari provides a Virtual Machines High Availability(VMHA), and rescues a
KVM-based Virtual Machines(VM) from a failure events of the following:

* VM process down - restart vm (use nova stop API, and nova start API).
                    Libvirt events will be also emitted by other failures.
* Provisioning process down - restarts process, changes nova-compute service
                              status to maintenance mode
                              (use nova service-disable).
* nova-compute host failure - evacuate all the VMs from failure host to
                              reserved host (use nova evacuate API).

The service enables deployers to integrate with the Masakari service
directly or through custom plug-ins.

The Masakari service consists of the following components:

``masakari-api``
  An OpenStack-native REST API that processes API requests by sending
  them to the ``masakari-engine`` over `Remote Procedure Call (RPC)`.

``masakari-engine``
  Processes the notifications recevied from ``masakari-api`` by execcuting the
  recovery workflow in asynchronus way.
