#!/usr/bin/perl
# cf_dns-lib.pl - Helper library for Cloudflare DNS Webmin Module

BEGIN { push(@INC, ".."); };
use WebminCore;
use JSON::PP;
use Cwd 'abs_path';
use File::Basename;

&init_config();

our $module_dir = dirname(abs_path(__FILE__));
our $module_config_dir = "/etc/webmin/cf_dns";
if (!-d $module_config_dir) {
    mkdir($module_config_dir, 0755);
}

our $configs_file = "$module_config_dir/configs.json";
our $settings_file = "$module_config_dir/settings.json";
our $log_file = "/var/log/cf_dns.log";

if (!-f $configs_file) {
    open(my $fh, '>', $configs_file);
    print $fh "[]";
    close($fh);
}

if (!-f $settings_file) {
    open(my $fh, '>', $settings_file);
    print $fh '{"interval": 30}';
    close($fh);
}

# Auto-repair systemd service whenever Webmin CGI loads
sub ensure_systemd_service {
    my $service_file = "/etc/systemd/system/cf_dns.service";
    my $py_script = "$module_dir/cf_dns_service.py";
    my $desired_content = "[Unit]\nDescription=Cloudflare DNS Updater Service for Webmin Module\nAfter=network.target\n\n[Service]\nType=simple\nUser=root\nExecStart=/usr/bin/python3 $py_script\nRestart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n";

    my $needs_update = 1;
    if (-f $service_file) {
        open(my $fh, '<', $service_file);
        local $/;
        my $cur = <$fh>;
        close($fh);
        if ($cur eq $desired_content) {
            $needs_update = 0;
        }
    }

    if ($needs_update) {
        open(my $fh, '>', $service_file);
        print $fh $desired_content;
        close($fh);
        system("systemctl daemon-reload >/dev/null 2>&1");
    }
}

&ensure_systemd_service();

sub get_configs {
    if (!-f $configs_file) { return []; }
    local $/;
    open(my $fh, '<', $configs_file) or return [];
    my $content = <$fh>;
    close($fh);
    eval {
        my $json = decode_json($content);
        return $json;
    } or return [];
}

sub save_configs {
    my ($configs) = @_;
    open(my $fh, '>', $configs_file) or return 0;
    print $fh encode_json($configs);
    close($fh);
    return 1;
}

sub get_settings {
    if (!-f $settings_file) { return { interval => 30 }; }
    local $/;
    open(my $fh, '<', $settings_file) or return { interval => 30 };
    my $content = <$fh>;
    close($fh);
    eval {
        return decode_json($content);
    } or return { interval => 30 };
}

sub save_settings {
    my ($settings) = @_;
    open(my $fh, '>', $settings_file) or return 0;
    print $fh encode_json($settings);
    close($fh);
    system("systemctl restart cf_dns >/dev/null 2>&1");
    return 1;
}

sub get_service_status {
    my $out = `systemctl is-active cf_dns 2>/dev/null`;
    chomp($out);
    return ($out eq 'active') ? 1 : 0;
}

sub get_logs {
    if (!-f $log_file) { return ""; }
    my $out = `tail -n 100 $log_file 2>/dev/null`;
    return $out;
}

1;
