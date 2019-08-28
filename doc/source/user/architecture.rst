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

Masakari System Architecture
============================

Masakari comprises of two services api and engine, each performing different
functions. The user-facing interface is a REST API, while internally Masakari
communicates via an RPC message passing mechanism.

The API servers process REST requests, which typically involve database
reads/writes, sending RPC messages to other Masakari engine,
and generating responses to the REST calls.
RPC messaging is done via the **oslo.messaging** library,
an abstraction on top of message queues.
The Masakari engine will run on the same host where the Masakari api is
running, and has a `manager` that is listening for `RPC` messages.
The manager too has periodic tasks.

Components
----------

Below you will find a helpful explanation of the key components
of a typical Masakari deployment.

.. image:: /_static/architecture.png
   :width: 100%

* DB: sql database for data storage.
* API: component that receives HTTP requests, converts commands and
  communicates with masakari engine via the **oslo.messaging** queue.
* Engine: Executes recovery workflow and communicates with nova via HTTP.
