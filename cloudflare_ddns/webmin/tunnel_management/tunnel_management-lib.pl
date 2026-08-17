#!/usr/bin/perl
# tunnel_management-lib.pl - Helper library for Cloudflare Tunnel Webmin Module

BEGIN { push(@INC, ".."); };
use WebminCore;
use JSON::PP;
use Cwd 'abs_path';
use File::Basename;

&init_config();

our $module_dir = dirname(abs_path(__FILE__));
our $module_config_dir = "/etc/webmin/tunnel_management";
if (!-d $module_config_dir) {
    mkdir($module_config_dir, 0755);
}

our $config_file = "$module_config_dir/config.json";

if (!-f $config_file) {
    open(my $fh, '>', $config_file);
    print $fh "{}";
    close($fh);
}

sub get_config {
    if (!-f $config_file) { return {}; }
    local $/;
    open(my $fh, '<', $config_file) or return {};
    my $content = <$fh>;
    close($fh);
    eval {
        return decode_json($content);
    } or return {};
}

sub save_config {
    my ($conf) = @_;
    open(my $fh, '>', $config_file) or return 0;
    print $fh encode_json($conf);
    close($fh);
    return 1;
}

sub run_python_cmd {
    my ($action, $params_hash) = @_;
    my $py_script = "$module_dir/tunnel_backend.py";
    
    my $json_payload = encode_json({ action => $action, params => $params_hash || {} });
    $json_payload =~ s/'/'\\''/g;

    my $raw_output = `python3 $py_script '$json_payload' 2>&1`;

    my $decoded = eval { decode_json($raw_output); };
    if ($decoded && ref($decoded) eq 'HASH' && exists $decoded->{'status'}) {
        return $decoded;
    }

    # Fallback to result.json file
    my $res_file = "$module_config_dir/result.json";
    if (-f $res_file) {
        open(my $rf, '<', $res_file);
        local $/;
        my $content = <$rf>;
        close($rf);
        my $file_decoded = eval { decode_json($content); };
        if ($file_decoded && ref($file_decoded) eq 'HASH') {
            return $file_decoded;
        }
    }

    return { status => 0, msg => "Raw output: $raw_output" };
}

1;
