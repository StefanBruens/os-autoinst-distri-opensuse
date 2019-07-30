# SUSE's openQA tests
#
# Copyright © 2009-2013 Bernhard M. Wiedemann
# Copyright © 2012-2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

# Summary: Test formula rendering in oomath
# Maintainer: Oliver Kurz <okurz@suse.de>
# Tags: https://bugs.freedesktop.org/show_bug.cgi?id=42301

use base 'x11test';
use strict;
use warnings;
use testapi;
use utils 'type_string_slow';

sub run {
    x11_start_program('oomath');
    if (match_has_tag('ooffice-tip-of-the-day')) {
        # Unselect "_S_how tips on startup", select "_O_k"
        send_key "alt-s";
        send_key "alt-o";
    }
    # be more resilient during the automatic evaluation of formulas to prevent
    # mistyping
    type_string_slow "E %PHI = H %PHI\nnewline\n1 = 1";
    wait_still_screen(1);

    # test broken undo
    send_key 'shift-left';
    send_key '2';
    # undo produces "12" instead of "1"
    send_key 'ctrl-z';
    assert_screen [qw(test-oomath-1 oomath-bsc1127895)];
    if (match_has_tag('oomath-bsc1127895')) {
        record_soft_failure 'bsc#1127895';
        send_key 'alt-f4';
    } else {
        send_key 'alt-f4';
        assert_and_click 'dont-save-libreoffice-btn';    # _Don't save
    }
}

1;
