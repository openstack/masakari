===========================================================
Masakari Customized Recovery Workflow Configuration Options
===========================================================

The following is a sample Masakari recovery workflow configuration for
adaptation and use.

.. literalinclude:: _static/masakari-custom-recovery-methods.conf.sample

Minimal Configuration
=====================

#. To generate the sample custom-recovery-methods.conf file, run the following
   command from the top level of the masakari directory::

   $ tox -egenconfig

#. Copy sample file ``etc/masakari/masakari-custom-recovery-methods.conf.sample`` to
   ``/etc/masakari`` directory

#. Remove '.sample' from files ``masakari-custom-recovery-methods.conf.sample`` which
   exist at ``etc/masakari``.
