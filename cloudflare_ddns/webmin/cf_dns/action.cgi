#!/usr/bin/perl
# action.cgi - Handler for quick actions (service start/stop, clear log, force update, delete config)

require './cf_dns-lib.pl';
&ReadParse();

my $action = $in{'action'};

if ($action eq 'start_service') {
    &ensure_systemd_service();
    system("systemctl start cf_dns >/dev/null 2>&1");
} elsif ($action eq 'stop_service') {
    system("systemctl stop cf_dns >/dev/null 2>&1");
} elsif ($action eq 'clear_logs') {
    system("echo '' > $log_file");
} elsif ($action eq 'force_update') {
    my $py_script = "$module_dir/cf_dns_service.py";
    system("python3 $py_script --once >/dev/null 2>&1");
} elsif ($action eq 'delete_config') {
    my $domain = $in{'domain'};
    if ($domain) {
        my $configs = &get_configs();
        my @new_configs = grep { $_->{'RECORD_NAME'} ne $domain } @$configs;
        &save_configs(\@new_configs);
    }
}

&redirect("index.cgi");
