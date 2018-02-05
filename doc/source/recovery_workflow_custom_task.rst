================================================
Guide for Custom Recovery Workflow Configuration
================================================

If operator wants customized recovery workflow, so here is guidelines mentioned
for how to associate custom tasks from Third Party Library along with standard
recovery workflows in Masakari.:

#.  First make sure required Third Party Library is installed on the Masakari
    engine node. Below is the sample custom task file.
    For example:

.. code-block:: bash

    from oslo_log import log as logging
    from taskflow import task

    LOG = logging.getLogger(__name__)


    class Noop(task.Task):

        def __init__(self, novaclient):
            self.novaclient = novaclient
            super(Noop, self).__init__()

        def execute(self, **kwargs):
            LOG.info("Custom task executed successfully..!!")
            return

#.  Configure custom task in Third Party Library's setup.cfg as below:

For example, Third Party Library's setup.cfg will have following entry points

.. code-block:: bash

    masakari.task_flow.tasks =
        custom_pre_task = <custom_task_class_path_from_third_party_library>
        custom_main_task = <custom_task_class_path_from_third_party_library>
        custom_post_task = <custom_task_class_path_from_third_party_library>

Note: Entry point in Third Party Library's setup.cfg should have same key as
in Masakari setup.cfg for respective failure recovery.

#.  Configure custom task in Masakari's new conf file custom-recovery-methods.conf
    with same name which was given in the setup.cfg to locate class path.
    For example(custom task added in host auto failure config option):

.. code-block:: bash

        host_auto_failure_recovery_tasks = {
        'pre': ['disable_compute_service_task', 'custom_pre_task'],
        'main': ['custom_main_task', 'prepare_HA_enabled_instances_task'],
        'post': ['evacuate_instances_task', 'custom_post_task']}

#.  If there are any configuration parameters required for custom task,
    then add them into custom-recovery-methods.conf under the same
    group/section where they are registered in Third Party Library.
    All config parameters related to recovery method customization
    should be part of newly added conf file.
    Operator will be responsible to generate masakari.conf and related
    configuration files by themselves.

#.  Operator should ensure output of each task should be made available to
    the next tasks needing them.
