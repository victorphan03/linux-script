#!/usr/bin/perl
# action.cgi - Quick actions handler for tunnel_management

require './tunnel_management-lib.pl';
&ReadParse();

my $action = $in{'action'};

if ($action eq 'delete_route') {
    my $hname = $in{'hostname'};
    my $path = $in{'path'};
    my $res = &run_python_cmd('delete_route', { hostname => $hname, path => $path });
    if (!$res->{'status'}) {
        &error($res->{'msg'});
    }
}

&redirect("index.cgi");
