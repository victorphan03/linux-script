#!/usr/bin/perl
# save_route.cgi - Save new ingress route handler

require './tunnel_management-lib.pl';
&ReadParse();

my $sub = $in{'subdomain'};
my $dom = $in{'domain'};
my $path = $in{'path'};
my $stype = $in{'service_type'};
my $turl = $in{'target_url'};

if (!$dom || !$turl) {
    &error("Domain and Target Address & Port are required!");
}

$turl =~ s/^(http|https|tcp|udp|ssh|rdp|unix):\/\///i;

my $full_hostname = $sub ? "$sub.$dom" : $dom;
my $target_service = "$stype://$turl";

my $res = &run_python_cmd('add_route', {
    hostname => $full_hostname,
    path => $path,
    service_target => $target_service
});

if (!$res->{'status'}) {
    &error($res->{'msg'});
}

&redirect("index.cgi");
