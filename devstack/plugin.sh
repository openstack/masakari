#!/bin/bash
#
# lib/masakari
# Functions to control the configuration and operation of the **Masakari** service

# Dependencies:
# ``functions`` file
# ``DEST``, ``STACK_USER`` must be defined
# ``SERVICE_{HOST|PROTOCOL|TOKEN}`` must be defined

# ``stack.sh`` calls the entry points in this order:
#
# masakari-api
# install - install_masakari
# post-config - configure_masakari
# extra - init_masakari start_masakari
# unstack - stop_masakari cleanup_masakari
#
# masakari-engine
# install - install_masakari
# post-config - configure_masakari
# extra - init_masakari start_masakari
# unstack - stop_masakari cleanup_masakari
#
# masakari-monitors
# post-config - configure_masakarimonitors
# extra - run_masakarimonitors
# unstack - stop_masakari_monitors cleanup_masakari_monitors

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

if is_service_enabled tls-proxy; then
    MASAKARI_SERVICE_PROTOCOL="https"
fi

# Toggle for deploying Masakari under a wsgi server.
MASAKARI_USE_MOD_WSGI=${MASAKARI_USE_MOD_WSGI:-True}


# Functions
# ---------

# setup_masakari_logging() - Adds logging configuration to conf files
function setup_masakari_logging {
    local CONF=$1
    iniset $CONF DEFAULT debug $ENABLE_DEBUG_LOG_LEVEL
    iniset $CONF DEFAULT use_syslog $SYSLOG
    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ]; then
        # Add color to logging output
        setup_colorized_logging $CONF DEFAULT tenant user
    fi
}

# create_masakari_accounts() - Set up common required masakari accounts

# Tenant               User       Roles
# ------------------------------------------------------------------
# service              masakari     admin        # if enabled

function create_masakari_accounts {
    if [[ "$ENABLED_SERVICES" =~ "masakari" ]]; then

        create_service_user "$USERNAME" "admin"

        local masakari_service
        masakari_service=$(get_or_create_service "masakari" \
            "instance-ha" "OpenStack High Availability")
        if [ "$MASAKARI_USE_MOD_WSGI" == "False" ]; then
            get_or_create_endpoint $masakari_service \
                "$REGION_NAME" \
                "$MASAKARI_SERVICE_PROTOCOL://$SERVICE_HOST:$MASAKARI_SERVICE_PORT/v1/\$(tenant_id)s"
        else
            get_or_create_endpoint $masakari_service \
                "$REGION_NAME" \
                "$MASAKARI_SERVICE_PROTOCOL://$SERVICE_HOST/instance-ha/v1/\$(tenant_id)s"
        fi
    fi
}

# stack.sh entry points
# ---------------------

# cleanup_masakari() - Remove residual data files, anything left over from previous
# runs that a clean run would need to clean up
function cleanup_masakari {
# Clean up dirs
    rm -fr $MASAKARI_AUTH_CACHE_DIR/*
    rm -fr $MASAKARI_CONF_DIR/*

    if [ "$MASAKARI_USE_MOD_WSGI" == "True" ]; then
        remove_uwsgi_config "$MASAKARI_UWSGI_CONF" "$MASAKARI_UWSGI"
    fi
}

# cleanup_masakari_monitors() - Remove residual data files, anything left over from previous
# runs that a clean run would need to clean up
function cleanup_masakari_monitors {
# Clean up dirs
    rm -fr $MASAKARI_MONITORS_CONF_DIR/*
}

# iniset_conditional() - Sets the value in the inifile, but only if it's
# actually got a value
function iniset_conditional {
    local FILE=$1
    local SECTION=$2
    local OPTION=$3
    local VALUE=$4

    if [[ -n "$VALUE" ]]; then
        iniset ${FILE} ${SECTION} ${OPTION} ${VALUE}
    fi
}

# configure_masakari() - Set config files, create data dirs, etc
function configure_masakari {
    setup_develop $MASAKARI_DIR

    # Create the masakari conf dir and cache dirs if they don't exist
    sudo install -d -o $STACK_USER ${MASAKARI_CONF_DIR} ${MASAKARI_AUTH_CACHE_DIR}

    # Copy api-paste file over to the masakari conf dir
    cp $MASAKARI_LOCAL_API_PASTE_INI $MASAKARI_API_PASTE_INI

    # (Re)create masakari conf files
    rm -f $MASAKARI_CONF

    # (Re)create masakari api conf file if needed
    if is_service_enabled masakari-api; then
        oslo-config-generator --namespace keystonemiddleware.auth_token \
            --namespace masakari \
            --namespace oslo.db \
            > $MASAKARI_CONF

        # Set common configuration values (but only if they're defined)
        iniset $MASAKARI_CONF DEFAULT masakari_api_workers "$API_WORKERS"
        iniset $MASAKARI_CONF database connection `database_connection_url masakari`
        # Set taskflow connection to store the recovery workflow details in db
        iniset $MASAKARI_CONF taskflow connection `database_connection_url masakari`

        setup_masakari_logging $MASAKARI_CONF

        configure_auth_token_middleware $MASAKARI_CONF masakari $MASAKARI_AUTH_CACHE_DIR
    fi

    # Set os_privileged_user credentials (used for connecting nova service)
    iniset $MASAKARI_CONF DEFAULT os_privileged_user_name nova
    iniset $MASAKARI_CONF DEFAULT os_privileged_user_auth_url "$KEYSTONE_SERVICE_URI"
    iniset $MASAKARI_CONF DEFAULT os_privileged_user_password "$SERVICE_PASSWORD"
    iniset $MASAKARI_CONF DEFAULT os_privileged_user_tenant "$SERVICE_PROJECT_NAME"
    iniset $MASAKARI_CONF DEFAULT graceful_shutdown_timeout "$SERVICE_GRACEFUL_SHUTDOWN_TIMEOUT"

    iniset_rpc_backend masakari $MASAKARI_CONF DEFAULT

    if is_service_enabled tls-proxy; then
        iniset $MASAKARI_CONF DEFAULT masakari_api_listen_port $MASAKARI_SERVICE_PORT_INT
    fi

    if [ "$MASAKARI_USE_MOD_WSGI" == "True" ]; then
        write_uwsgi_config "$MASAKARI_UWSGI_CONF" "$MASAKARI_UWSGI" "/instance-ha"
    fi
}

# configure_masakarimonitors() - Set config files, create data dirs, etc
function configure_masakarimonitors {
    git_clone $MASAKARI_MONITORS_REPO $MASAKARI_MONITORS_DIR $MASAKARI_MONITORS_BRANCH

    # Create masakarimonitors conf dir and cache dirs if they don't exist
    sudo install -d -o $STACK_USER ${MASAKARI_MONITORS_CONF_DIR}
    setup_develop $MASAKARI_MONITORS_DIR

    # (Re)create masakarimonitors conf files
    rm -f $MASAKARI_MONITORS_CONF

    # (Re)create masakarimonitors api conf file if needed
    oslo-config-generator --namespace masakarimonitors.conf \
        --namespace oslo.log \
        --namespace oslo.middleware \
        > $MASAKARI_MONITORS_CONF

    iniset $MASAKARI_MONITORS_CONF api auth_url "$KEYSTONE_SERVICE_URI"
    iniset $MASAKARI_MONITORS_CONF api password "$SERVICE_PASSWORD"
    iniset $MASAKARI_MONITORS_CONF api project_name "$SERVICE_PROJECT_NAME"
    iniset $MASAKARI_MONITORS_CONF api username "$USERNAME"
    iniset $MASAKARI_MONITORS_CONF api user_domain_id "$SERVICE_DOMAIN_ID"
    iniset $MASAKARI_MONITORS_CONF api project_domain_id "$SERVICE_DOMAIN_ID"
    iniset $MASAKARI_MONITORS_CONF api region "$REGION_NAME"

    iniset $MASAKARI_MONITORS_CONF process process_list_path "$MASAKARI_MONITORS_CONF_DIR/process_list.yaml"
    touch $MASAKARI_MONITORS_CONF_DIR/process_list.yaml
}

# install_masakari() - Collect source and prepare
function install_masakari {
    setup_develop $MASAKARI_DIR
}

# init_masakari() - Initializes Masakari Database as a Service
function init_masakari {
    # (Re)Create masakari db
    recreate_database masakari

    # Initialize the masakari database
    $MASAKARI_MANAGE db sync

    # Add an admin user to the 'tempest' alt_demo tenant.
    # This is needed to test the guest_log functionality.
    # The first part mimics the tempest setup, so make sure we have that.
    ALT_USERNAME=${ALT_USERNAME:-alt_demo}
    ALT_TENANT_NAME=${ALT_TENANT_NAME:-alt_demo}
    get_or_create_project ${ALT_TENANT_NAME} default
    get_or_create_user ${ALT_USERNAME} "$ADMIN_PASSWORD" "default" "alt_demo@example.com"
    get_or_add_user_project_role Member ${ALT_USERNAME} ${ALT_TENANT_NAME}

    # The second part adds an admin user to the tenant.
    ADMIN_ALT_USERNAME=${ADMIN_ALT_USERNAME:-admin_${ALT_USERNAME}}
    get_or_create_user ${ADMIN_ALT_USERNAME} "$ADMIN_PASSWORD" "default" "admin_alt_demo@example.com"
    get_or_add_user_project_role admin ${ADMIN_ALT_USERNAME} ${ALT_TENANT_NAME}
}

# start_masakari() - Start running processes
function start_masakari {
    local masakari_url

    if [[ "$ENABLED_SERVICES" =~ "masakari-api" ]]; then
        if [ "$MASAKARI_USE_MOD_WSGI" == "False" ]; then
            run_process masakari-api "$MASAKARI_BIN_DIR/masakari-api --config-file=$MASAKARI_CONF --debug"
            masakari_url=$MASAKARI_SERVICE_PROTOCOL://$MASAKARI_SERVICE_HOST:$MASAKARI_SERVICE_PORT
            # Start proxy if tls enabled
            if is_service_enabled tls_proxy; then
                start_tls_proxy masakari-service '*' $MASAKARI_SERVICE_PORT $SERVICE_HOST $MASAKARI_SERVICE_PORT_INT
            fi
        else
            run_process "masakari-api" "$(which uwsgi) --procname-prefix masakari-api --ini $MASAKARI_UWSGI_CONF"
            masakari_url=$MASAKARI_SERVICE_PROTOCOL://$MASAKARI_SERVICE_HOST/instance-ha/v1
        fi

        echo "Waiting for Masakari API to start..."
        if ! wait_for_service $SERVICE_TIMEOUT $masakari_url; then
            die $LINENO "masakari-api did not start"
        fi
    fi

    if [[ "$ENABLED_SERVICES" =~ "masakari-engine" ]]; then
        run_process masakari-engine "$MASAKARI_BIN_DIR/masakari-engine --config-file=$MASAKARI_CONF --debug"
    fi
}

#install masakari-dashboard
function install_masakaridashboard {
    git_clone $MASAKARI_DASHBOARD_REPO $MASAKARI_DASHBOARD_DIR $MASAKARI_DASHBOARD_BRANCH
    setup_develop $MASAKARI_DASHBOARD_DIR
    ln -fs $MASAKARI_DASHBOARD_DIR/masakaridashboard/local/enabled/_50_masakaridashboard.py \
    $HORIZON_DIR/openstack_dashboard/local/enabled
    ln -fs $MASAKARI_DASHBOARD_DIR/masakaridashboard/local/local_settings.d/_50_masakari.py \
    $HORIZON_DIR/openstack_dashboard/local/local_settings.d
    ln -fs $MASAKARI_DASHBOARD_DIR/masakaridashboard/conf/masakari_policy.yaml \
    $HORIZON_DIR/openstack_dashboard/conf
}

#uninstall masakari-dashboard
function uninstall_masakaridashboard {
    sudo rm -f  $DEST/horizon/openstack_dashboard/local/enabled/_50_masakaridashboard.py
    sudo rm -f  $DEST/horizon/openstack_dashboard/local/local_settings.d/_50_masakari.py
    sudo rm -f  $DEST/horizon/openstack_dashboard/conf/masakari_policy.yaml
    restart_apache_server
}

# stop_masakari() - Stop running processes
function stop_masakari {
    # Kill the masakari services
    local serv
    for serv in masakari-engine masakari-api; do
        stop_process $serv
    done
}

#run masakari-monitors
function run_masakarimonitors {
    run_process masakari-processmonitor "$MASAKARI_BIN_DIR/masakari-processmonitor"
    run_process masakari-instancemonitor "$MASAKARI_BIN_DIR/masakari-instancemonitor"
    run_process masakari-introspectiveinstancemonitor "$MASAKARI_BIN_DIR/masakari-introspectiveinstancemonitor"
}

# stop_masakari_monitors() - Stop running processes
function stop_masakari_monitors {
    # Kill the masakari-monitors services
    local serv
    for serv in masakari-processmonitor masakari-instancemonitor masakari-introspectiveinstancemonitor; do
        stop_process $serv
    done
}

# Dispatcher for masakari plugin
if is_service_enabled masakari; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Masakari"
        if [[ "$ENABLED_SERVICES" =~ "masakari-api" ]]; then
            install_masakari
        fi
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Masakari"
        if [[ "$ENABLED_SERVICES" =~ "masakari-api" ]]; then
            configure_masakari

            if is_service_enabled key; then
            create_masakari_accounts
            fi
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and Start the masakari API and masakari taskmgr components
        if [[ "$ENABLED_SERVICES" =~ "masakari-api" ]]; then
            init_masakari
            echo_summary "Starting Masakari"
            start_masakari
        fi

        if is_service_enabled horizon; then
            # install masakari-dashboard
            echo_summary "Installing masakari-dashboard"
            install_masakaridashboard
        fi
    fi

    if [[ "$1" == "unstack" ]]; then
        if is_service_enabled horizon; then
            echo_summary "Uninstall masakari-dashboard"
            uninstall_masakaridashboard
        fi
        if [[ "$ENABLED_SERVICES" =~ "masakari-api" ]]; then
            stop_masakari
            cleanup_masakari
        fi
    fi
fi

if is_service_enabled masakari-monitors; then
    if [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        if is_service_enabled n-cpu; then
            # Configure masakari-monitors
            echo_summary "Configure masakari-monitors"
            configure_masakarimonitors
        fi
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        if is_service_enabled n-cpu; then
            # Run masakari-monitors
            echo_summary "Running masakari-monitors"
            run_masakarimonitors
        fi
    fi
    if [[ "$1" == "unstack" ]]; then
        if is_service_enabled n-cpu; then
            echo_summary "Uninstall masakari-monitors"
            stop_masakari_monitors
            cleanup_masakari_monitors
        fi
    fi
fi

# Restore xtrace
$XTRACE

# Tell emacs to use shell-script-mode
## Local variables:
## mode: shell-script
## End:

