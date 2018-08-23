# SUSE's openQA tests
#
# Copyright © 2016 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

# Summary: Test rollback after migration back to downgraded system
# Maintainer: Oliver Kurz <okurz@suse.de>

use base "consoletest";
use testapi;
use utils;
use strict;
use migration qw(check_rollback_system boot_into_ro_snapshot);

sub run {
    my ($self) = @_;

    boot_into_ro_snapshot;
    select_console 'root-console';
    # 1)
    script_run('touch NOWRITE;test ! -f NOWRITE', 0);
    # 1b) just debugging infos
    script_run("snapper list",        0);
    script_run("cat /etc/os-release", 0);
    # rollback
    script_run("snapper rollback -d rollback-before-migration");
    assert_script_run("snapper list | tail -n 2 | grep rollback");
    script_run("systemctl reboot", 0);
    reset_consoles;
    $self->wait_boot(ready_time => 300, bootloader_time => 300);
    select_console 'root-console';
    check_rollback_system;
}

sub test_flags {
    return {fatal => 1};

}

1;
