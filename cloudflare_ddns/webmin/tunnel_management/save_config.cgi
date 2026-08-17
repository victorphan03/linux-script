#!/usr/bin/perl
# save_config.cgi - Save Cloudflare API & Tunnel credentials handler

require './tunnel_management-lib.pl';
&ReadParse();

my $res = &run_python_cmd('save_config', {
    api_token => $in{'api_token'},
    account_id => $in{'account_id'},
    tunnel_id => $in{'tunnel_id'},
    zone_id => $in{'zone_id'}
});

if (!$res->{'status'}) {
    &error($res->{'msg'});
}

&webmin_log("save", "config");
&redirect("index.cgi");
